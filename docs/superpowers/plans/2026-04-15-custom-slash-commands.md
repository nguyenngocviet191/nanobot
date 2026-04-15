# Custom Slash Commands via Markdown Files - Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm custom slash commands bằng cách tạo file markdown trong `workspace/commands/`. Command được forward cho agent xử lý như một instruction.

**Architecture:** Minimal approach - chỉ thêm fallback trong TelegramChannel để check custom commands khi không match built-in command. Không thay đổi CommandRouter. Backward compatible hoàn toàn.

**Tech Stack:** Python 3.11+, python-telegram-bot, frontmatter (để parse markdown files)

---

## File Structure

```
nanobot/
├── command/
│   ├── __init__.py              # Export CustomCommandsLoader
│   └── custom_commands.py        # NEW: Lightweight markdown command loader
├── channels/
│   └── telegram.py               # MODIFY: Add custom commands fallback
tests/
└── command/
    └── test_custom_commands.py  # NEW: Tests
workspace/
└── commands/                     # NEW: User creates commands here
    └── weather.md                # Example command
```

---

## Chunk 1: Custom Commands Loader

### Task 1: Create `nanobot/command/custom_commands.py`

**Files:**
- Create: `nanobot/command/custom_commands.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/command/test_custom_commands.py
import pytest
from pathlib import Path
from nanobot.command.custom_commands import CustomCommandsLoader

def test_load_command_from_file(tmp_path):
    # Create a test command file
    cmd_file = tmp_path / "weather.md"
    cmd_file.write_text("""---
name: weather
description: Get weather
---
Use wttr.in to get weather for {args}
""")

    loader = CustomCommandsLoader(tmp_path)
    content = loader.get_command_content("weather")

    assert content is not None
    assert "Use wttr.in" in content
    assert "{args}" in content

def test_command_not_found(tmp_path):
    loader = CustomCommandsLoader(tmp_path)
    content = loader.get_command_content("nonexistent")
    assert content is None

def test_get_commands_for_telegram(tmp_path):
    # Create test commands
    (tmp_path / "weather.md").write_text("""---
name: weather
description: Get weather info
---
Weather command
""")
    (tmp_path / "translate.md").write_text("""---
name: translate
description: Translate text
---
Translate command
""")

    loader = CustomCommandsLoader(tmp_path)
    commands = loader.get_bot_commands()

    assert len(commands) == 2
    assert {"command": "weather", "description": "Get weather info"} in commands
    assert {"command": "translate", "description": "Translate text"} in commands
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd f:/Project/nanobot && python -m pytest tests/command/test_custom_commands.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
# nanobot/command/custom_commands.py
"""Custom slash commands loaded from markdown files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import frontmatter

from loguru import logger


class CustomCommandsLoader:
    """
    Load custom slash commands from markdown files.

    Directory: workspace/commands/*.md
    Each file defines one command with YAML frontmatter.
    """

    FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?",
        re.DOTALL,
    )

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()
        self.commands_dir = self.workspace / "commands"

    def get_command_content(self, name: str) -> str | None:
        """
        Get command content by name.

        Args:
            name: Command name (case-insensitive)

        Returns:
            Command content (markdown body after frontmatter) or None if not found
        """
        if not self.commands_dir.exists():
            return None

        file = self.commands_dir / f"{name.lower()}.md"
        if not file.exists():
            return None

        try:
            post = frontmatter.load(file)
            return post.content.strip()
        except Exception as e:
            logger.warning("Failed to load command {}: {}", name, e)
            return None

    def get_command_metadata(self, name: str) -> dict[str, Any] | None:
        """Get command metadata from frontmatter."""
        if not self.commands_dir.exists():
            return None

        file = self.commands_dir / f"{name.lower()}.md"
        if not file.exists():
            return None

        try:
            post = frontmatter.load(file)
            return dict(post.metadata)
        except Exception as e:
            logger.warning("Failed to load command metadata {}: {}", name, e)
            return None

    def list_commands(self) -> list[dict[str, str]]:
        """List all available commands with their metadata."""
        if not self.commands_dir.exists():
            return []

        commands = []
        for file in self.commands_dir.glob("*.md"):
            try:
                post = frontmatter.load(file)
                name = post.metadata.get("name", file.stem.lower())
                desc = post.metadata.get("description", "")
                commands.append({
                    "name": name,
                    "description": desc[:32] if desc else "",
                    "file": str(file),
                })
            except Exception:
                continue

        return commands

    def get_bot_commands(self) -> list[dict[str, str]]:
        """
        Get commands formatted for Telegram Bot API.
        Telegram limit: max 100 commands, description max 32 chars.
        """
        commands = self.list_commands()
        result = []
        for cmd in commands:
            result.append({
                "command": cmd["name"],
                "description": cmd["description"][:32],
            })
        return result[:100]

    def command_exists(self, name: str) -> bool:
        """Check if a command exists."""
        if not self.commands_dir.exists():
            return False
        return (self.commands_dir / f"{name.lower()}.md").exists()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd f:/Project/nanobot && python -m pytest tests/command/test_custom_commands.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd f:/Project/nanobot
git add nanobot/command/custom_commands.py tests/command/test_custom_commands.py
git commit -m "feat(command): add CustomCommandsLoader for markdown-based slash commands"
```

---

## Chunk 2: Integrate into TelegramChannel

### Task 2: Update TelegramChannel to use CustomCommandsLoader

**Files:**
- Modify: `nanobot/channels/telegram.py:224-238` (__init__)
- Modify: `nanobot/channels/telegram.py:303-326` (start - add handlers)
- Modify: `nanobot/channels/telegram.py:836-858` (_forward_command)

- [ ] **Step 1: Add CustomCommandsLoader to TelegramChannel.__init__**

```python
# After line 237, add:
from nanobot.command.custom_commands import CustomCommandsLoader

# In __init__, after self._stream_bufs initialization:
self._custom_commands = CustomCommandsLoader(self.workspace)
```

- [ ] **Step 2: Add handler for custom commands (after existing command handlers)**

```python
# In start() method, after line 316 (dream-log handler), add:
# Custom commands handler - must be last (catch-all for slash commands)
self._app.add_handler(
    MessageHandler(
        filters.Regex(r"^/[a-zA-Z0-9_]+(?:\s+.*)?$"),
        self._on_custom_command,
    )
)
```

- [ ] **Step 3: Add _on_custom_command handler**

```python
async def _on_custom_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle custom slash commands from workspace/commands/"""
    if not update.message or not update.effective_user:
        return

    message = update.message
    content = message.text or ""

    # Only handle if it looks like a command
    if not content.startswith("/"):
        return

    # Extract command name
    parts = content.strip("/").split()
    cmd_name = parts[0].lower()

    # Check if it's a custom command
    cmd_content = self._custom_commands.get_command_content(cmd_name)
    if cmd_content is None:
        return  # Not a custom command, let other handlers try

    # It's a custom command - forward to agent
    user = update.effective_user
    self._remember_thread_context(message)

    # Build instruction with command content and args
    args = " ".join(parts[1:]) if len(parts) > 1 else ""
    instruction = f"""Execute this command:

{cmd_content}

User args: {args}"""

    await self._handle_message(
        sender_id=self._sender_id(user),
        chat_id=str(message.chat_id),
        content=instruction,
        metadata=self._build_message_metadata(message, user),
        session_key=self._derive_topic_session_key(message),
    )
```

- [ ] **Step 4: Run existing tests to ensure no regression**

Run: `cd f:/Project/nanobot && python -m pytest tests/channels/test_telegram_channel.py -v`
Expected: PASS (all existing tests)

- [ ] **Step 5: Commit**

```bash
cd f:/Project/nanobot
git add nanobot/channels/telegram.py
git commit -m "feat(telegram): integrate custom commands loader"
```

---

## Chunk 3: Add frontmatter dependency

### Task 3: Add frontmatter to dependencies

**Files:**
- Modify: `pyproject.toml:20-54` (dependencies)

- [ ] **Step 1: Add frontmatter to dependencies**

In `pyproject.toml`, add `"python-frontmatter>=1.0.0,<2.0.0",` to the dependencies list (alphabetically after `filelock`).

- [ ] **Step 2: Verify dependency can be installed**

Run: `cd f:/Project/nanobot && uv pip install python-frontmatter --dry-run`
Expected: Shows it would install correctly

- [ ] **Step 3: Commit**

```bash
cd f:/Project/nanobot
git add pyproject.toml
git commit -m "chore: add python-frontmatter dependency"
```

---

## Chunk 4: Create example command file

### Task 4: Add example weather.md command

**Files:**
- Create: `workspace/commands/weather.md`

- [ ] **Step 1: Create example command file**

```markdown
---
name: weather
description: Get weather for a city (no API key required)
category: utility
---
# Weather Command

Use wttr.in to get current weather for any city.

## Usage
```
/weather Hanoi
/weather Tokyo
/weather "New York"
```

## Implementation
1. Fetch: `curl -s "wttr.in/{city}?format=%l:+%c+%t+%h+%w"`
2. Parse the output
3. Return formatted weather info

## Response Format
🌤️ Weather in {city}
🌡️ Temperature: {temp}
💧 Humidity: {humidity}%
🌬️ Wind: {wind}

## Notes
- City names are case-insensitive
- Use + or %20 for spaces
- Works without API key via wttr.in
```

- [ ] **Step 2: Commit**

```bash
cd f:/Project/nanobot
git add workspace/commands/weather.md
git commit -m "feat(examples): add weather command example"
```

---

## Chunk 5: Full integration test

### Task 5: Integration test

**Files:**
- No new files, use existing infrastructure

- [ ] **Step 1: Install dependencies**

Run: `cd f:/Project/nanobot && uv pip install python-frontmatter`

- [ ] **Step 2: Run all related tests**

Run: `cd f:/Project/nanobot && python -m pytest tests/command/test_custom_commands.py tests/channels/test_telegram_channel.py -v`
Expected: ALL PASS

- [ ] **Step 3: Manual verification (if applicable)**

Test the bot locally to ensure `/weather Hanoi` works as expected.

---

## Verification Steps

After implementation, verify:

1. **Unit tests pass**: `pytest tests/command/test_custom_commands.py -v`
2. **No regression**: `pytest tests/channels/test_telegram_channel.py -v`
3. **Custom command loads**: Create `workspace/commands/hello.md` and verify it appears in `/help`
4. **Command execution**: `/weather Hanoi` should trigger the agent with the command content

---

## Rollback Plan

If issues arise:
1. Revert telegram.py changes - custom commands is opt-in
2. Remove frontmatter from pyproject.toml
3. Keep custom_commands.py as standalone utility (doesn't affect existing code)