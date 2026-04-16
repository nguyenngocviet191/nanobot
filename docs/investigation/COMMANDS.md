# Nanobot - Slash Commands System

## 🎯 Tổng quan

Nanobot có hệ thống **Slash Commands** mạnh mẽ cho phép user tương tác trực tiếp với agent thông qua các commands được định nghĩa sẵn.

## 🏗️ Kiến trúc Command Router

### Location
`nanobot/command/router.py`

### 4-Tier Dispatch System

```mermaid
flowchart TD
    A[User Message] --> B{Is Priority?}
    B -->|Yes| C[/stop, /restart]
    B -->|No| D{Exact Match?}
    D -->|Yes| E[/clear, /status]
    D -->|No| F{Prefix Match?}
    F -->|Yes| G[/team, /skill]
    F -->|No| H{Interceptors?}
    H -->|Yes| I[Custom Handlers]
    H -->|No| J[Pass to Agent]
```

### CommandContext

```python
@dataclass
class CommandContext:
    """Everything a command handler needs."""
    msg: InboundMessage       # Original message
    session: Session | None  # Current session
    key: str                 # Session key
    raw: str                 # Raw message text
    args: str = ""          # Arguments after command
    loop: Any = None        # Reference to agent loop
```

## 📋 Command Tiers

### Tier 1: Priority Commands

**Đặc điểm**:
- Xử lý **TRƯỚC KHI** acquire dispatch lock
- Cho phép interrupt đang chạy tasks
- Không bị block bởi session locks

**Đăng ký**:
```python
router.priority("/stop", stop_handler)
router.priority("/restart", restart_handler)
```

**Ví dụ Handler**:
```python
async def stop_handler(ctx: CommandContext) -> OutboundMessage | None:
    ctx.loop.stop()
    return OutboundMessage(
        channel=ctx.msg.channel,
        chat_id=ctx.msg.chat_id,
        content="🛑 Agent stopped."
    )
```

### Tier 2: Exact Commands

**Đặc điểm**:
- Exact string match (case-insensitive)
- Xử lý bên trong dispatch lock

**Đăng ký**:
```python
router.exact("/clear", clear_handler)
router.exact("/status", status_handler)
```

**Ví dụ Handler**:
```python
async def clear_handler(ctx: CommandContext) -> OutboundMessage | None:
    if ctx.session:
        ctx.session.clear()
        return OutboundMessage(
            channel=ctx.msg.channel,
            chat_id=ctx.msg.chat_id,
            content="🗑️ Session cleared."
        )
```

### Tier 3: Prefix Commands

**Đặc điểm**:
- Longest-prefix-first matching
- Args được extract tự động

**Đăng ký**:
```python
router.prefix("/team ", team_handler)
router.prefix("/skill ", skill_handler)
router.prefix("/exec ", exec_handler)
```

**Ví dụ Handler**:
```python
async def team_handler(ctx: CommandContext) -> OutboundMessage | None:
    # ctx.args chứa phần sau "/team "
    team_args = ctx.args.strip()
    
    if team_args.startswith("create "):
        return await handle_team_create(team_args[7:])
    elif team_args.startswith("add "):
        return await handle_team_add(team_args[4:])
    
    return OutboundMessage(
        channel=ctx.msg.channel,
        chat_id=ctx.msg.chat_id,
        content="Usage: /team create|add|remove|list|chat"
    )
```

### Tier 4: Interceptors

**Đặc điểm**:
- Predicate-based handlers
- Cho phép conditional routing
- Fallback cuối cùng trước khi pass to agent

**Đăng ký**:
```python
router.intercept(team_mode_interceptor)
router.intercept(admin_check_interceptor)
```

**Ví dụ Handler**:
```python
async def team_mode_interceptor(ctx: CommandContext) -> OutboundMessage | None:
    """Check nếu team mode active và route appropriately."""
    if ctx.msg.metadata.get("team_mode"):
        # Handle team routing
        return await handle_team_message(ctx)
    return None  # Continue to normal processing
```

## 🔄 Dispatch Logic

```python
async def dispatch(self, ctx: CommandContext) -> OutboundMessage | None:
    """Try all tiers in order, return first match."""
    cmd = ctx.raw.lower()
    
    # Tier 1: Priority
    if handler := self._priority.get(cmd):
        return await handler(ctx)
    
    # Tier 2: Exact match
    if handler := self._exact.get(cmd):
        return await handler(ctx)
    
    # Tier 3: Prefix match (longest first)
    for pfx, handler in self._prefix:
        if cmd.startswith(pfx):
            ctx.args = ctx.raw[len(pfx):]  # Extract args
            return await handler(ctx)
    
    # Tier 4: Interceptors
    for interceptor in self._interceptors:
        if result := await interceptor(ctx):
            return result
    
    return None  # No match → pass to agent
```

## 📦 Built-in Commands

| Command | Tier | Mô tả |
|---------|------|-------|
| `/stop` | Priority | Dừng task đang chạy |
| `/restart` | Priority | Restart agent |
| `/clear` | Exact | Xóa session history |
| `/status` | Exact | Hiển thị trạng thái |
| `/models` | Channel-specific | Chọn AI provider/model qua inline buttons |
| `/dream` | Exact | Trigger Dream memory consolidation |
| `/dream-log` | Prefix | Xem thay đổi của Dream |
| `/dream-restore` | Prefix | Khôi phục memory về phiên bản trước |
| `/team` | Prefix | Team mode commands |
| `/skill` | Prefix | Skill management |
| `/cron` | Prefix | Cron commands |

## 💡 Best Practices

1. **Priority commands** chỉ cho actions cần interrupt ngay lập tức
2. **Prefix commands** nên xử lý nhanh, không blocking
3. **Args parsing** nên dùng `ctx.args` thay vì parse lại `ctx.raw`
4. **Interceptors** dùng cho cross-cutting concerns

## 🔧 Thêm Custom Command

```python
from nanobot.command.router import CommandRouter

def register_my_commands(router: CommandRouter):
    # Exact command
    router.exact("/mycmd", my_handler)
    
    # Prefix command
    router.prefix("/myprefix ", my_prefix_handler)

async def my_handler(ctx) -> OutboundMessage | None:
    return OutboundMessage(
        channel=ctx.msg.channel,
        chat_id=ctx.msg.chat_id,
        content="Command executed!"
    )
```

## 📁 Related Files

- `nanobot/command/router.py` - Command router implementation
- `nanobot/command/builtin.py` - Built-in commands
- `nanobot/command/__init__.py` - Module exports
