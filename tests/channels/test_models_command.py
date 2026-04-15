"""Tests for /models command functionality."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Check optional Telegram dependencies before running tests
try:
    import telegram  # noqa: F401
except ImportError:
    pytest.skip("Telegram dependencies not installed (python-telegram-bot)", allow_module_level=True)

from nanobot.bus.queue import MessageBus
from nanobot.channels.telegram import TelegramChannel, TelegramConfig


class _FakeHTTPXRequest:
    instances: list["_FakeHTTPXRequest"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.__class__.instances.append(self)

    @classmethod
    def clear(cls) -> None:
        cls.instances.clear()


class _FakeUpdater:
    def __init__(self, on_start_polling) -> None:
        self._on_start_polling = on_start_polling

    async def start_polling(self, **kwargs) -> None:
        self._on_start_polling()


class _FakeBot:
    def __init__(self) -> None:
        self.sent_messages: list[dict] = []
        self.inline_keyboards: list[dict] = []
        self.get_me_calls = 0

    async def get_me(self):
        self.get_me_calls += 1
        return SimpleNamespace(id=999, username="nanobot_test")

    async def set_my_commands(self, commands) -> None:
        self.commands = commands

    async def send_message(self, chat_id: int, text: str, parse_mode=None, reply_markup=None, **kwargs):
        self.sent_messages.append({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": reply_markup,
        })
        return SimpleNamespace(message_id=len(self.sent_messages))

    async def edit_message_text(self, chat_id: int, message_id: int, text: str, parse_mode=None, reply_markup=None, **kwargs):
        self.sent_messages.append({
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": reply_markup,
            "edited": True,
        })

    async def send_chat_action(self, **kwargs) -> None:
        pass


class _FakeApp:
    def __init__(self, on_start_polling) -> None:
        self.bot = _FakeBot()
        self.updater = _FakeUpdater(on_start_polling)
        self.handlers = []
        self.error_handlers = []

    def add_error_handler(self, handler) -> None:
        self.error_handlers.append(handler)

    def add_handler(self, handler) -> None:
        self.handlers.append(handler)

    async def initialize(self) -> None:
        pass

    async def start(self) -> None:
        pass


class _FakeBuilder:
    def __init__(self, app: _FakeApp) -> None:
        self.app = app

    def token(self, token: str):
        return self

    def request(self, request):
        return self

    def get_updates_request(self, request):
        return self

    def build(self):
        return self.app


def _make_telegram_update(
    *,
    chat_type: str = "private",
    text: str | None = None,
    chat_id: int = 12345,
    message_id: int = 1,
):
    user = SimpleNamespace(id=12345, username="alice", first_name="Alice")
    message = SimpleNamespace(
        chat=SimpleNamespace(type=chat_type, is_forum=False),
        chat_id=chat_id,
        text=text,
        entities=[],
        caption=None,
        caption_entities=[],
        reply_to_message=None,
        photo=None,
        voice=None,
        audio=None,
        document=None,
        location=None,
        media_group_id=None,
        message_thread_id=None,
        message_id=message_id,
    )
    return SimpleNamespace(message=message, effective_user=user)


def _make_callback_query(
    *,
    data: str,
    chat_id: int = 12345,
    message_id: int = 1,
):
    message = SimpleNamespace(
        chat=SimpleNamespace(type="private"),
        chat_id=chat_id,
        message_id=message_id,
    )
    return SimpleNamespace(
        data=data,
        message=message,
        edit_message_text=AsyncMock(),
        answer=AsyncMock(),
    )


class MockProviderConfig:
    """Mock provider config for testing."""
    def __init__(self, api_key="", api_base=None, extra_headers=None, models=None):
        self.api_key = api_key
        self.api_base = api_base
        self.extra_headers = extra_headers or {}
        self.models = models or []


class TestModelsCommandRegistration:
    """Test that /models command is properly registered."""

    @pytest.mark.asyncio
    async def test_models_command_in_bot_commands(self, monkeypatch) -> None:
        """Test that 'models' command is in BOT_COMMANDS list."""
        _FakeHTTPXRequest.clear()
        config = TelegramConfig(
            enabled=True,
            token="123:abc",
            allow_from=["*"],
        )
        bus = MessageBus()
        channel = TelegramChannel(config, bus)
        app = _FakeApp(lambda: setattr(channel, "_running", False))
        builder = _FakeBuilder(app)

        monkeypatch.setattr("nanobot.channels.telegram.HTTPXRequest", _FakeHTTPXRequest)
        monkeypatch.setattr(
            "nanobot.channels.telegram.Application",
            SimpleNamespace(builder=lambda: builder),
        )

        await channel.start()

        # Check models command is registered
        assert any(cmd.command == "models" for cmd in app.bot.commands)
        models_cmd = next(c for c in app.bot.commands if c.command == "models")
        assert "Switch" in models_cmd.description or "model" in models_cmd.description.lower()


class TestDefaultProviderModels:
    """Test DEFAULT_PROVIDER_MODELS dictionary."""

    def test_has_required_providers(self) -> None:
        """Test that DEFAULT_PROVIDER_MODELS has required providers."""
        defaults = TelegramChannel.DEFAULT_PROVIDER_MODELS

        assert "anthropic" in defaults
        assert "openai" in defaults
        assert "deepseek" in defaults

    def test_anthropic_has_claude_models(self) -> None:
        """Test that Anthropic provider has Claude models."""
        defaults = TelegramChannel.DEFAULT_PROVIDER_MODELS

        anthropic_models = defaults["anthropic"]
        assert any("claude" in m.lower() for m in anthropic_models)

    def test_openai_has_gpt_models(self) -> None:
        """Test that OpenAI provider has GPT models."""
        defaults = TelegramChannel.DEFAULT_PROVIDER_MODELS

        openai_models = defaults["openai"]
        assert any("gpt" in m.lower() for m in openai_models)

    def test_moonshot_has_kimi_models(self) -> None:
        """Test that Moonshot provider has Kimi models."""
        defaults = TelegramChannel.DEFAULT_PROVIDER_MODELS

        moonshot_models = defaults.get("moonshot", [])
        assert any("kimi" in m.lower() for m in moonshot_models)


class TestGetModelsForProvider:
    """Test _get_models_for_provider method with mocked config."""

    def _make_channel(self):
        config = TelegramConfig(
            enabled=True,
            token="123:abc",
            allow_from=["*"],
        )
        bus = MessageBus()
        return TelegramChannel(config, bus)

    @pytest.mark.asyncio
    async def test_returns_default_models_for_known_provider(self) -> None:
        """Test that default models are returned for known providers."""
        channel = self._make_channel()

        # Mock _get_config to return None (so it falls back to defaults)
        with patch.object(channel, '_get_config', return_value=None):
            models = await channel._get_models_for_provider("anthropic")

        assert "claude-3-5-sonnet-20241022" in models
        assert "claude-3-opus-20240229" in models

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_provider(self) -> None:
        """Test that empty list is returned for unknown provider."""
        channel = self._make_channel()

        with patch.object(channel, '_get_config', return_value=None):
            models = await channel._get_models_for_provider("unknown_provider")

        assert models == []


class TestApplyModelToSession:
    """Test _apply_model_to_session method."""

    @pytest.mark.asyncio
    async def test_stores_model_in_session_metadata(self, tmp_path, monkeypatch) -> None:
        """Test that selected model is stored in session metadata."""
        config = TelegramConfig(
            enabled=True,
            token="123:abc",
            allow_from=["*"],
        )
        bus = MessageBus()
        channel = TelegramChannel(config, bus)

        # Mock workspace path
        monkeypatch.setattr("nanobot.config.paths.get_workspace_path", lambda: tmp_path)

        await channel._apply_model_to_session("12345", "anthropic/claude-3-5-sonnet-20241022")

        # Verify session was created and stored
        from nanobot.session.manager import SessionManager
        session_mgr = SessionManager(tmp_path)
        session = session_mgr.get_or_create("telegram:12345")

        assert session.metadata.get("temp_model") == "anthropic/claude-3-5-sonnet-20241022"


class TestCallbackQueryModelSelection:
    """Test model selection via callback query."""

    @pytest.mark.asyncio
    async def test_model_callback_stores_and_shows_indicator(self, tmp_path, monkeypatch) -> None:
        """Test that clicking model stores it and shows indicator."""
        config = TelegramConfig(
            enabled=True,
            token="123:abc",
            allow_from=["*"],
        )
        bus = MessageBus()
        channel = TelegramChannel(config, bus)

        # Mock workspace path
        monkeypatch.setattr("nanobot.config.paths.get_workspace_path", lambda: tmp_path)

        callback = _make_callback_query(data="mdl:model:anthropic:claude-3-5-sonnet-20241022")
        update = SimpleNamespace(callback_query=callback)

        await channel._on_callback_query(update, None)

        # Verify session stored the model
        from nanobot.session.manager import SessionManager
        session_mgr = SessionManager(tmp_path)
        session = session_mgr.get_or_create("telegram:12345")

        assert session.metadata.get("temp_model") == "anthropic/claude-3-5-sonnet-20241022"


class TestProviderModelsIntegration:
    """Integration tests for provider model resolution."""

    def test_provider_config_has_models_field(self) -> None:
        """Test that ProviderConfig accepts models field."""
        from nanobot.config.schema import ProviderConfig

        config = ProviderConfig(
            api_key="test-key",
            models=["model-a", "model-b"]
        )

        assert config.models == ["model-a", "model-b"]

    def test_provider_config_defaults_to_empty_models(self) -> None:
        """Test that ProviderConfig defaults models to empty list."""
        from nanobot.config.schema import ProviderConfig

        config = ProviderConfig(api_key="test-key")

        assert config.models == []