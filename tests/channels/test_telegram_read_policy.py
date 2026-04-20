"""Tests for Telegram 'read' group policy.

The 'read' policy:
- Reads all messages (adds reaction emoji)
- Only replies when @mentioned or replying to bot's message
- Provides full context to AI without spamming replies
"""

import pytest
from telegram import MessageEntity

# Check optional Telegram dependencies before running tests
try:
    import telegram  # noqa: F401
except ImportError:
    pytest.skip("Telegram dependencies not installed (python-telegram-bot)", allow_module_level=True)

from nanobot.bus.queue import MessageBus
from nanobot.channels.telegram import TelegramChannel, TelegramConfig


def _make_telegram_update(
    text: str | None = None,
    caption: str | None = None,
    chat_type: str = "group",
    user_id: int = 1,
    username: str = "testuser",
    message_id: int = 100,
    reply_to_message=None,
    entities=None,
    caption_entities=None,
):
    """Helper to create a Telegram Update object."""
    from types import SimpleNamespace
    from telegram import Update, Message, Chat, User

    user = User(id=user_id, is_bot=False, first_name="Test", username=username)
    chat = Chat(id=123, type=chat_type)

    msg = Message(
        message_id=message_id,
        date=None,
        chat=chat,
        from_user=user,
        text=text,
        caption=caption,
        caption_entities=caption_entities,
        reply_to_message=reply_to_message,
        **({"entities": entities} if entities else {}),
    )

    update = Update(update_id=1, message=msg)
    return update


class _FakeApp:
    """Fake Telegram application for testing."""

    def __init__(self, bot):
        self.bot = bot

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass


class _FakeBot:
    """Fake bot for testing."""

    def __init__(self, bot_id=42, bot_username="testbot"):
        self.id = bot_id
        self.username = bot_username
        self.get_me_calls = 0
        self.reactions = []
        self.sent_messages = []
        self._typing = False

    async def get_me(self):
        self.get_me_calls += 1
        from types import SimpleNamespace
        return SimpleNamespace(id=self.id, username=self.username, is_bot=True)

    async def send_message(self, **kwargs):
        self.sent_messages.append(kwargs)

    async def set_message_reaction(self, **kwargs):
        self.reactions.append(kwargs)


@pytest.mark.asyncio
async def test_read_policy_reads_all_messages() -> None:
    """'read' policy should process all group messages (for reaction)."""
    channel = TelegramChannel(
        TelegramConfig(enabled=True, token="123:abc", allow_from=["*"], group_policy="read"),
        MessageBus(),
    )
    fake_bot = _FakeBot()
    channel._app = _FakeApp(fake_bot)

    handled = []

    async def capture_handle(**kwargs) -> None:
        handled.append(kwargs)

    channel._handle_message = capture_handle
    channel._start_typing = lambda _chat_id: None

    # Plain group message without mention
    await channel._on_message(_make_telegram_update(text="hello group"), None)

    # Should NOT forward to agent (no mention)
    assert len(handled) == 0

    # But SHOULD add reaction
    assert len(fake_bot.reactions) == 1


@pytest.mark.asyncio
async def test_read_policy_replies_when_mentioned() -> None:
    """'read' policy should reply when @mentioned."""
    channel = TelegramChannel(
        TelegramConfig(enabled=True, token="123:abc", allow_from=["*"], group_policy="read"),
        MessageBus(),
    )
    fake_bot = _FakeBot(bot_username="testbot")
    channel._app = _FakeApp(fake_bot)

    handled = []

    async def capture_handle(**kwargs) -> None:
        handled.append(kwargs)

    channel._handle_message = capture_handle
    channel._start_typing = lambda _chat_id: None

    # Message with @mention
    entities = [MessageEntity(type="mention", offset=0, length=len("@testbot"))]
    await channel._on_message(
        _make_telegram_update(text="@testbot hello", entities=entities), None
    )

    # Should forward to agent
    assert len(handled) == 1
    assert handled[0]["content"] == "@testbot hello"

    # Should also add reaction
    assert len(fake_bot.reactions) == 1


@pytest.mark.asyncio
async def test_read_policy_replies_when_replying_to_bot() -> None:
    """'read' policy should reply when replying to bot's message."""
    from types import SimpleNamespace

    channel = TelegramChannel(
        TelegramConfig(enabled=True, token="123:abc", allow_from=["*"], group_policy="read"),
        MessageBus(),
    )
    fake_bot = _FakeBot(bot_id=42)
    channel._app = _FakeApp(fake_bot)

    handled = []

    async def capture_handle(**kwargs) -> None:
        handled.append(kwargs)

    channel._handle_message = capture_handle
    channel._start_typing = lambda _chat_id: None

    # Reply to bot's message
    bot_user = SimpleNamespace(id=42, is_bot=True, username="testbot")
    bot_msg = SimpleNamespace(
        message_id=99,
        text="Bot message",
        from_user=bot_user,
    )
    await channel._on_message(
        _make_telegram_update(text="thanks!", reply_to_message=bot_msg), None
    )

    # Should forward to agent (content includes reply prefix)
    assert len(handled) == 1
    assert "thanks!" in handled[0]["content"]

    # Should also add reaction
    assert len(fake_bot.reactions) == 1


@pytest.mark.asyncio
async def test_read_policy_private_chat_always_replies() -> None:
    """'read' policy should always reply in private chats."""
    channel = TelegramChannel(
        TelegramConfig(enabled=True, token="123:abc", allow_from=["*"], group_policy="read"),
        MessageBus(),
    )
    fake_bot = _FakeBot()
    channel._app = _FakeApp(fake_bot)

    handled = []

    async def capture_handle(**kwargs) -> None:
        handled.append(kwargs)

    channel._handle_message = capture_handle
    channel._start_typing = lambda _chat_id: None

    # Private chat message (no mention needed)
    await channel._on_message(
        _make_telegram_update(text="hello private", chat_type="private"), None
    )

    # Should forward to agent
    assert len(handled) == 1
    assert handled[0]["content"] == "hello private"


@pytest.mark.asyncio
async def test_read_policy_no_typing_for_unmentioned() -> None:
    """'read' policy should NOT show typing indicator for unmentioned messages."""
    channel = TelegramChannel(
        TelegramConfig(enabled=True, token="123:abc", allow_from=["*"], group_policy="read"),
        MessageBus(),
    )
    fake_bot = _FakeBot()
    channel._app = _FakeApp(fake_bot)

    typing_started = []

    def capture_typing(chat_id: str) -> None:
        typing_started.append(chat_id)

    channel._start_typing = capture_typing
    channel._handle_message = lambda **kwargs: None

    # Plain group message
    await channel._on_message(_make_telegram_update(text="hello"), None)

    # Should NOT start typing
    assert len(typing_started) == 0

    # But should add reaction
    assert len(fake_bot.reactions) == 1


@pytest.mark.asyncio
async def test_read_policy_typing_for_mentioned() -> None:
    """'read' policy SHOULD show typing indicator for mentioned messages."""
    channel = TelegramChannel(
        TelegramConfig(enabled=True, token="123:abc", allow_from=["*"], group_policy="read"),
        MessageBus(),
    )
    fake_bot = _FakeBot(bot_username="testbot")
    channel._app = _FakeApp(fake_bot)

    typing_started = []

    def capture_typing(chat_id: str) -> None:
        typing_started.append(chat_id)

    channel._start_typing = capture_typing

    async def noop_handle(**kwargs) -> None:
        pass

    channel._handle_message = noop_handle

    # Mentioned message
    entities = [MessageEntity(type="mention", offset=0, length=len("@testbot"))]
    await channel._on_message(
        _make_telegram_update(text="@testbot help", entities=entities), None
    )

    # SHOULD start typing
    assert len(typing_started) == 1
    assert typing_started[0] == "123"


@pytest.mark.asyncio
async def test_read_policy_caption_mention() -> None:
    """'read' policy should detect mentions in captions."""
    channel = TelegramChannel(
        TelegramConfig(enabled=True, token="123:abc", allow_from=["*"], group_policy="read"),
        MessageBus(),
    )
    fake_bot = _FakeBot(bot_username="testbot")
    channel._app = _FakeApp(fake_bot)

    handled = []

    async def capture_handle(**kwargs) -> None:
        handled.append(kwargs)

    channel._handle_message = capture_handle
    channel._start_typing = lambda _chat_id: None

    # Photo with caption mention
    caption_entities = [MessageEntity(type="mention", offset=0, length=len("@testbot"))]
    await channel._on_message(
        _make_telegram_update(
            caption="@testbot what is this?", caption_entities=caption_entities
        ),
        None,
    )

    # Should forward to agent
    assert len(handled) == 1
    assert handled[0]["content"] == "@testbot what is this?"


@pytest.mark.asyncio
async def test_read_policy_vs_open_policy() -> None:
    """'read' policy should NOT reply to plain messages, unlike 'open' policy."""
    # Test 'read' policy
    read_channel = TelegramChannel(
        TelegramConfig(enabled=True, token="123:abc", allow_from=["*"], group_policy="read"),
        MessageBus(),
    )
    read_channel._app = _FakeApp(_FakeBot())

    read_handled = []
    read_channel._handle_message = lambda **kw: read_handled.append(kw)
    read_channel._start_typing = lambda _c: None

    await read_channel._on_message(_make_telegram_update(text="hello"), None)

    # 'read' policy: should NOT handle plain message
    assert len(read_handled) == 0

    # Test 'open' policy
    open_channel = TelegramChannel(
        TelegramConfig(enabled=True, token="123:abc", allow_from=["*"], group_policy="open"),
        MessageBus(),
    )
    open_channel._app = _FakeApp(_FakeBot())

    open_handled = []

    async def capture_open(**kw) -> None:
        open_handled.append(kw)

    open_channel._handle_message = capture_open
    open_channel._start_typing = lambda _c: None

    await open_channel._on_message(_make_telegram_update(text="hello"), None)

    # 'open' policy: SHOULD handle plain message
    assert len(open_handled) == 1