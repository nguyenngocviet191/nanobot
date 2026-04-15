# Markdown Command Loader - Thêm Slash Commands bằng Markdown

## Bối cảnh

Hiện tại nanobot có 2 cách thêm commands:

| Cách | Nơi định nghĩa | Cần code? |
|------|-----------------|-----------|
| **Python commands** | `nanobot/command/builtin.py` | ✅ Có |
| **Skills** | `workspace/skills/*.md` | ❌ Không |

**Vấn đề**: Thêm Python command cần sửa code, restart bot.

**Giải pháp**: Markdown Command Loader - thêm command mới bằng cách tạo file markdown.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Telegram / Channel                            │
│  User gõ: /weather Hanoi                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Command Dispatcher                              │
│  Priority → Exact → Prefix → Markdown Commands                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
┌─────────────────┐                   ┌─────────────────────────┐
│ Python Commands │                   │  Markdown Command Loader │
│ (builtin.py)   │                   │  (workspace/commands/)   │
└─────────────────┘                   └─────────────────────────┘
```

---

## 1. Cấu trúc Command File

### 1.1 Định dạng file

```
workspace/
└── commands/
    ├── weather.md
    ├── translate.md
    └── ... (mỗi file = 1 command)
```

### 1.2 Frontmatter Schema

```yaml
---
name: weather                    # Tên command (để tương thích với skill)
description: Get weather info     # Mô tả hiển thị trong Telegram menu
usage: /weather <city>           # Cách sử dụng
category: utility                # Nhóm command (tùy chọn)
version: 1.0                     # Phiên bản (tùy chọn)
---
```

### 1.3 Ví dụ: weather.md

```markdown
---
name: weather
description: Get weather for a city
usage: /weather <city>
category: utility
---
# Weather Command

Use wttr.in to get weather information for any city.

## Usage

```
/weather Hanoi
/weather Tokyo
/weather "New York"
```

## Implementation

1. Fetch from wttr.in: `https://wttr.in/{city}?format=j1`
2. Parse JSON response
3. Return formatted weather info

## Response Format

```
🌤️ Weather in {city}
━━━━━━━━━━━━━━━━━━
🌡️ Temperature: {temp}°C
💧 Humidity: {humidity}%
🌬️ Wind: {wind} km/h
```

## Error Handling

- City not found: "City not found. Please check the name."
- Network error: "Unable to fetch weather. Please try again."
```

---

## 2. Implementation

### 2.1 Markdown Command Loader

```python
# nanobot/command/markdown_commands.py

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter

from loguru import logger


@dataclass
class MarkdownCommand:
    """A command loaded from markdown file."""
    name: str
    description: str
    usage: str
    content: str
    category: str = "general"
    version: str = "1.0"
    source_file: Path | None = None


class MarkdownCommandLoader:
    """
    Load commands from markdown files.

    Directory structure:
    - workspace/commands/*.md     (user commands)
    - nanobot/commands/*.md       (builtin commands)
    """

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()

    def _get_command_dirs(self) -> list[Path]:
        """Get all directories to scan for commands."""
        dirs = [
            self.workspace / "commands",
            Path(__file__).parent.parent / "commands",
        ]
        return [d for d in dirs if d.exists()]

    def load_command(self, file: Path) -> MarkdownCommand | None:
        """Load a single command from markdown file."""
        try:
            post = frontmatter.load(file)
            metadata = post.metadata

            # Name from filename or frontmatter
            name = metadata.get("name") or file.stem.lower()

            # Description from frontmatter
            description = metadata.get("description", "")

            # Usage: fallback to /{name}
            usage = metadata.get("usage") or f"/{name}"

            return MarkdownCommand(
                name=name,
                description=description,
                usage=usage,
                content=post.content.strip(),
                category=metadata.get("category", "general"),
                version=metadata.get("version", "1.0"),
                source_file=file,
            )
        except Exception as e:
            logger.warning("Failed to load command from {}: {}", file, e)
            return None

    def load_commands(self) -> dict[str, MarkdownCommand]:
        """
        Load all commands from all command directories.

        Returns:
            Dict of command_name -> MarkdownCommand
        """
        commands: dict[str, MarkdownCommand] = {}

        for cmd_dir in self._get_command_dirs():
            for file in cmd_dir.glob("*.md"):
                cmd = self.load_command(file)
                if cmd:
                    # User commands override builtin
                    if cmd.name not in commands or self._is_user_dir(cmd_dir):
                        commands[cmd.name] = cmd

        return commands

    def get_command(self, name: str) -> MarkdownCommand | None:
        """Get a specific command by name."""
        return self.load_commands().get(name.lower())

    def list_commands(self, category: str | None = None) -> list[MarkdownCommand]:
        """List all commands, optionally filtered by category."""
        commands = self.load_commands().values()
        if category:
            commands = [c for c in commands if c.category == category]
        return sorted(commands, key=lambda c: c.name)

    def get_bot_commands(self) -> list[dict[str, str]]:
        """
        Get commands formatted for Telegram Bot API.

        Telegram limits: max 100 commands, each command max 32 chars description.
        """
        commands = self.load_commands()
        result = []

        for cmd in sorted(commands.values(), key=lambda c: c.name):
            # Telegram command format: /name description
            # Description max 32 chars
            desc = cmd.description[:32] if cmd.description else ""
            result.append({
                "command": cmd.name,
                "description": desc,
            })

        # Telegram limit
        return result[:100]

    @staticmethod
    def _is_user_dir(path: Path) -> bool:
        """Check if directory is user workspace."""
        return "workspace" in str(path)

    def reload(self) -> None:
        """Clear cache and reload commands."""
        # Currently commands are loaded on-demand
        # Future: add caching
        pass
```

### 2.2 Command Dispatcher Update

```python
# nanobot/command/router.py

class CommandRouter:
    """4-tier dispatch: Priority → Exact → Prefix → Markdown"""

    def __init__(self):
        self._priority: dict[str, Callable] = {}
        self._exact: dict[str, Callable] = {}
        self._prefix: list[tuple[str, Callable]] = []
        self._interceptors: list[Callable] = []
        # NEW: Markdown commands
        self._markdown_loader: MarkdownCommandLoader | None = None

    def set_markdown_loader(self, loader: MarkdownCommandLoader) -> None:
        """Set markdown command loader."""
        self._markdown_loader = loader

    async def dispatch(self, ctx: CommandContext) -> OutboundMessage | None:
        """Dispatch command through all tiers."""

        # 1. Priority (no lock needed)
        raw = ctx.raw
        if raw in self._priority:
            return await self._priority[raw](ctx)

        # 2. Exact match
        if raw in self._exact:
            return await self._exact[raw](ctx)

        # 3. Prefix match (longest first)
        for prefix, handler in sorted(self._prefix, key=lambda x: -len(x[0])):
            if raw.startswith(prefix):
                ctx.args = raw[len(prefix):].strip()
                return await handler(ctx)

        # 4. NEW: Markdown commands
        if self._markdown_loader:
            cmd_name = raw.strip("/").split()[0].lower()
            if cmd := self._markdown_loader.get_command(cmd_name):
                ctx.args = " ".join(raw.strip("/").split()[1:])
                return await self._dispatch_markdown_command(cmd, ctx)

        # 5. Interceptors
        for interceptor in self._interceptors:
            if result := await interceptor(ctx):
                return result

        return None

    async def _dispatch_markdown_command(
        self,
        cmd: MarkdownCommand,
        ctx: CommandContext,
    ) -> OutboundMessage | None:
        """
        Dispatch to markdown command.
        Passes content to agent for execution.
        """
        from nanobot.bus.events import OutboundMessage

        # Build prompt from command content
        prompt = f"""Execute this command:

{cmd.content}

User args: {ctx.args}

Return the result of executing this command."""

        # For simple commands, agent can execute directly
        # For complex commands, route through agent
        return OutboundMessage(
            chat_id=ctx.msg.chat_id or ctx.key,
            content=f"Command /{cmd.name}: {ctx.args}",
            metadata={
                "_command": cmd.name,
                "_command_prompt": prompt,
            },
        )
```

### 2.3 Telegram Channel Update

```python
# nanobot/channels/telegram.py

class TelegramChannel(BaseChannel):
    # ... existing code ...

    async def start(self) -> None:
        # ... existing initialization ...

        # Register commands with Telegram
        await self._register_commands()

    async def _register_commands(self) -> None:
        """Register bot commands with Telegram API."""
        from telegram import BotCommand

        # Load markdown commands
        loader = MarkdownCommandLoader(workspace=self.workspace)
        bot_commands_data = loader.get_bot_commands()

        # Always include essential commands
        essential_commands = {
            "help": "Show all commands",
            "new": "Start new conversation",
        }

        # Convert to BotCommand objects
        commands: list[BotCommand] = []

        # Add markdown commands
        for cmd_data in bot_commands_data:
            commands.append(BotCommand(
                command=cmd_data["command"],
                description=cmd_data["description"]
            ))

        # Ensure essential commands exist
        existing = {c.command for c in commands}
        for name, desc in essential_commands.items():
            if name not in existing:
                commands.append(BotCommand(command=name, description=desc))

        # Register with Telegram
        try:
            await self._app.bot.set_my_commands(commands)
            logger.info("Registered {} bot commands", len(commands))
        except Exception as e:
            logger.warning("Failed to register bot commands: {}", e)

        # Store loader for command dispatch
        self._markdown_command_loader = loader

    def _setup_handlers(self) -> None:
        """Setup message and command handlers."""
        # Existing handlers...

        # Command handler for markdown commands
        self._app.add_handler(
            MessageHandler(
                filters.Regex(r"^/[a-zA-Z0-9_]+(?:\s+.*)?$"),
                self._on_markdown_command,
            )
        )

    async def _on_markdown_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle markdown command (fallback after built-in commands)."""
        if not update.message or not update.effective_user:
            return

        message = update.message
        user = update.effective_user
        content = message.text.strip()

        # Extract command name
        cmd_name = content.strip("/").split()[0].lower()
        args = " ".join(content.split()[1:])

        # Get command from loader
        if not hasattr(self, "_markdown_command_loader"):
            return

        loader = self._markdown_command_loader
        if cmd := loader.get_command(cmd_name):
            # Process command
            await self._handle_markdown_command(
                cmd=cmd,
                args=args,
                update=update,
                user=user,
            )

    async def _handle_markdown_command(
        self,
        cmd: MarkdownCommand,
        args: str,
        update: Update,
        user,
    ) -> None:
        """Execute a markdown command."""
        # Build command context
        session_key = self._derive_topic_session_key(update.message)
        metadata = self._build_message_metadata(update.message, user)

        # Execute command (pass to agent loop)
        await self._handle_message(
            sender_id=self._sender_id(user),
            chat_id=str(update.message.chat_id),
            content=f"/{cmd.name} {args}",
            metadata=metadata,
            session_key=session_key,
        )
```

---

## 3. Sử dụng

### 3.1 Tạo Command mới

```bash
# Tạo file
mkdir -p workspace/commands
cat > workspace/commands/weather.md << 'EOF'
---
name: weather
description: Get weather for a city
usage: /weather <city>
category: utility
---
# Weather Command

Use wttr.in to get weather information.

## Usage
```
/weather Hanoi
```

## Response
Return formatted weather info.
EOF
```

### 3.2 Restart bot để load command mới

```bash
# Restart Telegram bot
nanobot gateway --config config.yaml

# Hoặc restart process
/restart
```

### 3.3 Kiểm tra commands

```
/help
```

Bot sẽ hiển thị tất cả available commands bao gồm cả markdown commands.

---

## 4. So sánh

| Aspect | Python Command | Markdown Command | Skill |
|--------|---------------|------------------|-------|
| **File** | `builtin.py` | `commands/*.md` | `skills/*.md` |
| **Cần code** | ✅ | ❌ | ❌ |
| **Xử lý phức tạp** | ✅ | ⚠️ Limited | ⚠️ Limited |
| **Linh hoạt** | ✅ Full | ⚠️ Agent-assisted | ⚠️ Agent-assisted |
| **Tự động register** | ❌ | ✅ | ❌ |
| **Priority** | High | Low | N/A |
| **Execution** | Direct function | Via agent | Via agent |

---

## 5. Hạn chế

| Hạn chế | Giải thích | Giải pháp |
|---------|-------------|-----------|
| **Restart required** | Command mới cần restart bot | Thêm file watcher (future) |
| **Telegram cache** | Telegram cache command list | Gửi /help để refresh |
| **Rate limit** | `set_my_commands` bị rate limit | Không gọi liên tục |
| **Complex logic** | Markdown không gọi API trực tiếp | Dùng Python command |
| **Security** | Markdown commands chạy qua agent | Validate input |

---

## 6. Command Categories

```yaml
# Suggested categories
categories:
  - utility      # /weather, /translate, /search
  - developer    # /code, /debug, /deploy
  - system       # /status, /restart, /config
  - fun          # /joke, /meme, /quote
```

---

## 7. Priority System

Commands được dispatch theo thứ tự:

```
1. Priority Commands (/stop, /restart)
   ↓
2. Exact Match Commands (/help, /status)
   ↓
3. Prefix Match Commands (/dream-log, /dream-restore)
   ↓
4. Markdown Commands (user-defined)
   ↓
5. Interceptors (fallback)
```

---

## 8. Ví dụ Commands

### 8.1 weather.md

```markdown
---
name: weather
description: Get weather for a city
usage: /weather <city>
category: utility
---
# Weather Command

Get current weather for any city using wttr.in.

## Usage
```
/weather Hanoi
/weather Tokyo
/weather "New York"
```

## Response Format
```
🌤️ Weather in {city}
━━━━━━━━━━━━━━━━━━
🌡️ Temperature: {temp}°C
💧 Humidity: {humidity}%
🌬️ Wind: {wind} km/h
```

## Notes
- City name is case-insensitive
- Use quotes for cities with spaces
```

### 8.2 translate.md

```markdown
---
name: translate
description: Translate text between languages
usage: /translate <from> <to> <text>
category: utility
---
# Translate Command

Translate text using LibreTranslate.

## Usage
```
/translate en vi "Hello world"
/translate ja en "こんにちは"
```

## Arguments
- from: Source language code (en, vi, ja, etc.)
- to: Target language code
- text: Text to translate

## Notes
- Language codes follow ISO 639-1
- Maximum 500 characters per translation
```

### 8.3 shorturl.md

```markdown
---
name: shorturl
description: Create a short URL
usage: /shorturl <url>
category: utility
---
# Short URL Command

Create a shortened URL using is.gd or tinyurl.

## Usage
```
/shorturl https://example.com/very/long/url
```

## Arguments
- url: Full URL to shorten

## Response
Shortened URL that redirects to original.

## Notes
- Works with http and https URLs
- Shortened URLs valid for 1 year
```

---

## 9. Implementation Checklist

```markdown
- [ ] 1. Tạo `nanobot/command/markdown_commands.py` - MarkdownCommandLoader
- [ ] 2. Cập nhật `nanobot/command/router.py` - Thêm markdown dispatch tier
- [ ] 3. Cập nhật `nanobot/channels/telegram.py` - Auto register commands
- [ ] 4. Tạo `workspace/commands/` directory structure
- [ ] 5. Thêm sample commands (weather, translate, shorturl)
- [ ] 6. Viết documentation
- [ ] 7. Viết tests
```

---

## 10. Future Enhancements

| Feature | Description |
|---------|-------------|
| **Hot reload** | Watch file changes, auto-reload commands |
| **Command aliases** | Multiple names for same command |
| **Sub-commands** | `/weather today`, `/weather tomorrow` |
| **Command groups** | `/admin restart`, `/admin config` |
| **Variables** | `{{user.name}}`, `{{chat.id}}` in responses |
| **Integrations** | Connect to external APIs |
