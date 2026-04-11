# Nanobot - Features & Core Functionality

## 🎯 Feature Overview

Nanobot cung cấp một bộ tính năng toàn diện cho việc xây dựng personal AI agent:

### Core Features
1. **Multi-Channel Messaging** - Kết nối với 12+ nền tảng chat
2. **Tool-Calling Agent Loop** - LLM với function calling
3. **Session Memory** - Lưu trữ và quản lý lịch sử hội thoại
4. **Scheduled Tasks** - Cron-based reminders
5. **Heartbeat Tasks** - Periodic background tasks
6. **MCP Integration** - Model Context Protocol support
7. **Skills System** - Extensible skill plugins
8. **Multi-Provider Support** - 20+ LLM providers

## 💬 Chat Channels

### Supported Platforms

| Channel | Protocol | Features |
|---------|----------|----------|
| **Telegram** | Bot API | Streaming, Media, Voice |
| **Discord** | WebSocket | Threads, Streaming |
| **Slack** | Socket Mode | Reactions, Threads |
| **Feishu** | WebSocket | CardKit Streaming |
| **WhatsApp** | Socket.IO | QR Login |
| **WeChat** | HTTP Polling | QR Login |
| **DingTalk** | Stream Mode | Bot |
| **Matrix** | Client-Server | E2EE |
| **QQ** | WebSocket | Private msgs |
| **Email** | IMAP/SMTP | Auto-reply |
| **Wecom** | WebSocket | Enterprise |
| **Mochat** | Socket.IO | ClawHub |

### Channel Implementation Pattern

```python
# Example: Channel pattern from base.py
class BaseChannel(ABC):
    name: str = "base"
    
    def __init__(self, config: Any, bus: MessageBus):
        self.config = config
        self.bus = bus
        
    async def start(self) -> None:
        """Connect and listen for messages"""
        pass
        
    async def stop(self) -> None:
        """Disconnect and cleanup"""
        pass
        
    async def send(self, msg: OutboundMessage) -> None:
        """Send message to platform"""
        pass
```

## 🤖 Agent Loop

### Execution Flow

```python
# Simplified from nanobot.py
class AgentLoop:
    async def run(self):
        while self._running:
            msg = await self.bus.consume_inbound()
            task = asyncio.create_task(self._dispatch(msg))
            
    async def _dispatch(self, msg: InboundMessage):
        session = self.sessions.get_or_create(msg.session_key)
        messages = self.context.build_messages(...)
        result = await self.runner.run(AgentRunSpec(...))
        await self.bus.publish_outbound(OutboundMessage(...))
```

### Key Components

1. **ContextBuilder** - Xây dựng prompt từ history, current message, system prompt
2. **AgentRunner** - Tool-calling loop với retry logic
3. **ToolRegistry** - Quản lý available tools
4. **Session** - Conversation history management

## 🔧 Tool System

### Built-in Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `read_file` | Read file content | Code analysis |
| `write_file` | Write/create files | Code generation |
| `edit_file` | Edit existing files | Incremental changes |
| `exec` | Run shell commands | System operations |
| `grep` | Search in files | Code search |
| `glob` | Find files by pattern | File discovery |
| `web_search` | Internet search | Real-time info |
| `web_fetch` | Fetch web pages | Content extraction |
| `list_dir` | Directory listing | File browsing |
| `message` | Send chat message | Notifications |
| `cron` | Schedule tasks | Reminders |

### Tool Execution Pipeline

```python
# From runner.py
async def _execute_tools(self, spec: AgentRunSpec, tool_calls):
    # Partition tools into batches (safe for concurrency)
    batches = self._partition_tool_batches(tool_calls)
    
    for batch in batches:
        if spec.concurrent_tools:
            results = await asyncio.gather(*[
                self._run_tool(tool_call) for tool_call in batch
            ])
        else:
            for tool_call in batch:
                result = await self._run_tool(tool_call)
```

### Concurrency Safety

```python
# Tools can declare concurrency safety
class Tool:
    concurrency_safe: bool = True  # Can run with other tools
    
# Batching logic from runner.py
if tool.concurrency_safe:
    current_batch.append(tool_call)
else:
    # Execute alone
```

## 🧠 Memory Management

### Token-Based Consolidation

```python
# From agent/memory.py concept
class MemoryManager:
    def maybe_consolidate(self, session: Session):
        tokens = self.estimate_tokens(session.messages)
        if tokens > self.token_threshold:
            self._dream_consolidate(session)
```

### Session Structure

```python
@dataclass
class Session:
    key: str                    # channel:chat_id
    messages: List[dict]        # Conversation history
    metadata: dict              # Custom metadata
    last_consolidated: int      # Consolidation point
    
    def get_history(self, max_messages: int = 500) -> List[dict]:
        """Return unconsolidated messages aligned to legal boundaries"""
        pass
```

### JSONL Persistence

```
sessions/
├── telegram_12345.jsonl
├── discord_67890.jsonl
└── cli_direct.jsonl
```

Format:
```jsonl
{"_type": "metadata", "key": "telegram:12345", "created_at": "...", "updated_at": "...", "metadata": {...}}
{"role": "user", "content": "Hello", "timestamp": "..."}
{"role": "assistant", "content": "Hi there!", "timestamp": "..."}
```

## ⏰ Scheduled Tasks (Cron)

### Cron Integration

```python
# From cron/service.py
class CronService:
    def add_job(self, spec: CronSpec):
        schedule = croniter(spec.expression, now)
        # Schedule next run
        
    async def check_and_run(self):
        now = datetime.now()
        for job in self.due_jobs(now):
            await self._execute_job(job)
```

### Built-in Cron Tool

```
# Agent có thể tạo cron jobs qua tool
cron.create(expression="0 9 * * MON-FRI", message="Daily standup!")
cron.list()
cron.remove(job_id)
```

## 🔁 Heartbeat Tasks

### Periodic Background Tasks

```python
# From heartbeat/service.py
class HeartbeatService:
    interval: int = 300  # 5 minutes default
    
    async def tick(self):
        """Run heartbeat checks"""
        for task in self.tasks:
            await task.check()
```

### HEARTBEAT.md Pattern

```markdown
# HEARTBEAT.md
- Check GitHub notifications every 30 minutes
- Summarize unread emails every hour
- Clean up temporary files daily
```

## 🔌 MCP (Model Context Protocol)

### MCP Integration

```python
# From nanobot.py
async def _connect_mcp(self):
    for server_config in self.mcp_servers:
        stack = clientAiohttp_connect(server_config)
        self._mcp_stacks[name] = stack
```

### MCP Tool Naming

- MCP tools được prefix với `mcp_`
- Example: `mcp_github_list_repos`
- Automatic tool registration

## 🛠️ Skills System

### Built-in Skills

| Skill | Description |
|-------|-------------|
| `clawhub` | ClawHub marketplace integration |
| `cron` | Scheduled task management |
| `github` | GitHub API operations |
| `memory` | Memory persistence |
| `skill-creator` | Create new skills |
| `summarize` | Text summarization |
| `tmux` | Terminal session management |
| `weather` | Weather information |

### Skill Structure

```
nanobot/skills/
├── skill_name/
│   ├── skill.md          # Skill definition
│   └── (optional files)  # Supporting files
```

### ClawHub Integration

```python
# Auto-discover và install skills từ ClawHub
Read https://clawhub.ai/skill.md
# nanobot tự động parse và cài đặt
```

## 🔄 Provider System

### Supported Providers

| Provider | Type | Features |
|----------|------|----------|
| `openai` | Direct | GPT-4, Whisper |
| `anthropic` | Direct | Claude |
| `openrouter` | Gateway | All models |
| `deepseek` | Direct | DeepSeek models |
| `groq` | Gateway | Fast inference |
| `gemini` | Direct | Gemini models |
| `azure_openai` | Azure | Enterprise |
| `ollama` | Local | Self-hosted |
| `vllm` | Local | Self-hosted |
| + 10+ more | | |

### Provider Interface

```python
class LLMProvider(ABC):
    async def chat(self, messages, tools, model, ...) -> LLMResponse:
        """Main chat method - must implement"""
        pass
        
    async def chat_with_retry(self, ...) -> LLMResponse:
        """With exponential backoff retry"""
        pass
        
    async def chat_stream(self, ..., on_content_delta) -> LLMResponse:
        """Streaming support"""
        pass
```

### Retry Policy

```python
# From base.py
_RETRY_DELAYS = (1, 2, 4)  # seconds
_TRANSIENT_ERROR_MARKERS = ("429", "rate limit", "500", ...)
_NON_RETRYABLE_429 = ("insufficient_quota", "billing_hard_limit", ...)
```

## 📡 OpenAI-Compatible API

### Endpoints

```bash
POST /v1/chat/completions   # Chat completion
GET  /v1/models             # List models
GET  /health                # Health check
```

### Usage Example

```bash
curl -X POST http://localhost:18792/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "session_id": "my-session"
  }'
```

## ⚙️ Configuration System

### Config Structure

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "${OPENROUTER_API_KEY}"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5",
      "provider": "openrouter"
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "${TELEGRAM_TOKEN}",
      "allowFrom": ["USER_ID"]
    }
  }
}
```

### Environment Variable Substitution

```json
{
  "token": "${TELEGRAM_TOKEN}",
  "apiKey": "${OPENAI_API_KEY}"
}
```

## 🔒 Security Features

### Access Control

```python
# Channel-level access control
class BaseChannel:
    def is_allowed(self, sender_id: str) -> bool:
        allow_list = self.config.get("allowFrom", [])
        if "*" in allow_list:
            return True
        return sender_id in allow_list
```

### Workspace Isolation

```python
# Tool execution bounded to workspace
def validate_path(self, path: Path) -> Path:
    """Ensure path is within workspace"""
    resolved = path.resolve()
    if not resolved.is_relative_to(self.workspace):
        raise SecurityError("Path outside workspace")
    return resolved
```

## 📊 Streaming Support

### Streaming Architecture

```mermaid
sequenceDiagram
    LLM->>Runner: stream delta
    Runner->>Hook: on_stream(delta)
    Hook->>Loop: _bus_progress(delta)
    Loop->>Bus: publish_outbound(_stream_delta)
    Bus->>Channel: send_delta(chat_id, delta)
    Channel->>User: Real-time display
    
    LLM->>Runner: stream end
    Runner->>Hook: on_stream_end()
    Hook->>Loop: Finalize response
```

### Streaming Channels

- **Telegram**: Via editMessageText
- **Discord**: Via channel.send()
- **Feishu**: CardKit updates
- **Slack**: Per-segment edits

## 🔧 CLI Commands

### Available Commands

| Command | Description |
|---------|-------------|
| `nanobot agent` | Start interactive CLI agent |
| `nanobot gateway` | Start multi-channel gateway |
| `nanobot channels login <channel>` | Authenticate channel |
| `nanobot onboard` | Interactive setup wizard |
| `nanobot cron list` | List scheduled tasks |
| `nanobot status` | System status |

### Slash Commands (In-Chat)

| Command | Description |
|---------|-------------|
| `/stop` | Stop current task |
| `/restart` | Restart agent |
| `/clear` | Clear session |
| `/status` | Show status |
| `/team <command>` | Team mode |
| `/skill <name>` | Skill management |
