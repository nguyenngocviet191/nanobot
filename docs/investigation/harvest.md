# Nanobot - Harvest (Design Patterns & Best Practices)

## 🎯 Giới thiệu

Document này trích xuất các **design patterns**, **best practices**, và **code patterns** xuất sắc từ dự án Nanobot mà có thể áp dụng vào các dự án khác.

## 🏗️ Design Patterns

### 1. Plugin-based Architecture (Channel System)

**Vấn đề**: Cần hỗ trợ nhiều chat platform mà không hardcode

**Giải pháp**:
```python
# Base class định nghĩa interface
class BaseChannel(ABC):
    name: str = "base"
    
    def __init__(self, config: Any, bus: MessageBus):
        self.config = config
        self.bus = bus
    
    @abstractmethod
    async def start(self) -> None: pass
    
    @abstractmethod
    async def stop(self) -> None: pass
    
    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None: pass

# Implement cụ thể cho từng platform
class TelegramChannel(BaseChannel):
    name = "telegram"
    
    async def start(self):
        # Telegram-specific logic
        pass

# Registry để discover và instantiate
class ChannelRegistry:
    _channels: dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, channel_cls: type):
        cls._channels[name] = channel_cls
    
    @classmethod
    def create(cls, name: str, config: Any, bus: MessageBus):
        if name not in cls._channels:
            raise ValueError(f"Unknown channel: {name}")
        return cls._channels[name](config, bus)
```

**Áp dụng**: Webhook systems, notification services, multi-provider integrations

---

### 2. Strategy Pattern với Retry (LLM Provider)

**Vấn đề**: Nhiều LLM provider với API khác nhau, cần retry logic thông minh

**Giải pháp**:
```python
class LLMProvider(ABC):
    """Base class với unified retry policy"""
    
    _RETRY_DELAYS = (1, 2, 4)
    _TRANSIENT_ERROR_MARKERS = ("429", "rate limit", "500", ...)
    
    @abstractmethod
    async def chat(self, messages, tools, model, ...) -> LLMResponse:
        pass
    
    async def chat_with_retry(self, **kwargs) -> LLMResponse:
        """Unified retry với exponential backoff"""
        for attempt in range(len(self._RETRY_DELAYS)):
            response = await self.chat(**kwargs)
            
            if not self._is_transient_error(response):
                return response
                
            delay = self._RETRY_DELAYS[attempt]
            await asyncio.sleep(delay)
        
        return response
    
    @classmethod
    def _is_transient_error(cls, response: LLMResponse) -> bool:
        """Phân loại error có retry được không"""
        content = (response.content or "").lower()
        return any(marker in content for marker in cls._TRANSIENT_ERROR_MARKERS)

# Concrete implementations
class AnthropicProvider(LLMProvider):
    async def chat(self, messages, tools, model, ...) -> LLMResponse:
        # Anthropic-specific implementation
        pass

class OpenAIProvider(LLMProvider):
    async def chat(self, messages, tools, model, ...) -> LLMResponse:
        # OpenAI-specific implementation
        pass
```

**Áp dụng**: API gateway, multi-cdn fallback, payment processor integrations

---

### 3. Repository Pattern với Caching (Session)

**Vấn đề**: Session data cần persistence và fast access

**Giải pháp**:
```python
class SessionManager:
    """Repository với in-memory cache"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self._cache: dict[str, Session] = {}
    
    def get_or_create(self, key: str) -> Session:
        """Cache-first access pattern"""
        if key in self._cache:
            return self._cache[key]
        
        session = self._load(key) or Session(key=key)
        self._cache[key] = session
        return session
    
    def save(self, session: Session) -> None:
        """Write-through cache"""
        self._persist(session)
        self._cache[session.key] = session
    
    def _load(self, key: str) -> Session | None:
        """Load from disk"""
        path = self.storage_path / f"{key}.json"
        if not path.exists():
            return None
        return Session.from_json(path.read_text())
    
    def _persist(self, session: Session) -> None:
        """Atomic write"""
        path = self.storage_path / f"{session.key}.json"
        temp = path.with_suffix('.tmp')
        temp.write_text(session.to_json())
        temp.replace(path)
```

**Áp dụng**: User profiles, cache management, document storage

---

### 4. Chain of Responsibility (Command Router)

**Vấn đề**: Multiple command handlers với priority levels

**Giải pháp**:
```python
Handler = Callable[[CommandContext], Awaitable[OutboundMessage | None]]

class CommandRouter:
    """Tiers: priority → exact → prefix → interceptors"""
    
    def __init__(self):
        self._priority: dict[str, Handler] = {}
        self._exact: dict[str, Handler] = {}
        self._prefix: list[tuple[str, Handler]] = []
        self._interceptors: list[Handler] = []
    
    def priority(self, cmd: str, handler: Handler):
        self._priority[cmd] = handler
    
    def exact(self, cmd: str, handler: Handler):
        self._exact[cmd] = handler
    
    def prefix(self, pfx: str, handler: Handler):
        self._prefix.append((pfx, handler))
        self._prefix.sort(key=lambda p: len(p[0]), reverse=True)  # Longest first
    
    async def dispatch(self, ctx: CommandContext) -> OutboundMessage | None:
        # Tier 1: Priority
        if handler := self._priority.get(ctx.raw.lower()):
            return await handler(ctx)
        
        # Tier 2: Exact match
        if handler := self._exact.get(ctx.raw.lower()):
            return await handler(ctx)
        
        # Tier 3: Longest prefix match
        for pfx, handler in self._prefix:
            if ctx.raw.lower().startswith(pfx):
                ctx.args = ctx.raw[len(pfx):]
                return await handler(ctx)
        
        # Tier 4: Interceptors
        for interceptor in self._interceptors:
            if result := await interceptor(ctx):
                return result
        
        return None
```

**Áp dụng**: Middleware chains, plugin systems, request routing

---

### 5. Event-Driven Architecture (Message Bus)

**Vấn đề**: Decouple producers và consumers

**Giải pháp**:
```python
@dataclass
class InboundMessage:
    channel: str
    sender_id: str
    chat_id: str
    content: str

@dataclass
class OutboundMessage:
    channel: str
    chat_id: str
    content: str

class MessageBus:
    """Async queue-based pub/sub"""
    
    def __init__(self):
        self._inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
    
    async def publish_inbound(self, msg: InboundMessage):
        await self._inbound.put(msg)
    
    async def publish_outbound(self, msg: OutboundMessage):
        await self._outbound.put(msg)
    
    async def consume_inbound(self) -> InboundMessage:
        return await self._inbound.get()
    
    async def dispatch_outbound(self, handler: Callable):
        """Process outbound messages"""
        while True:
            msg = await self._outbound.get()
            await handler(msg)
```

**Áp dụng**: Microservices communication, event sourcing, chat systems

---

## 🔧 Implementation Patterns

### 1. Type-safe Configuration

```python
from pydantic import BaseModel, Field
from typing import Literal

class ChannelConfig(BaseModel):
    enabled: bool = False
    allowFrom: list[str] = Field(default_factory=list)

class TelegramConfig(ChannelConfig):
    token: str = ""
    groupPolicy: Literal["mention", "open"] = "mention"

class AgentConfig(BaseModel):
    model: str = "anthropic/claude-sonnet-4"
    provider: str = "openrouter"
    maxIterations: int = 100

class Config(BaseModel):
    channels: dict[str, ChannelConfig] = Field(default_factory=dict)
    agents: dict[str, AgentConfig] = Field(default_factory=dict)

# Usage
config = Config.model_validate(json.load(open("config.json")))
telegram = config.channels.get("telegram", TelegramConfig())
```

### 2. Async Context Manager

```python
class ResourcePool:
    async def __aenter__(self):
        self.connection = await acquire_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await release_connection(self.connection)

# Usage
async with ResourcePool() as pool:
    result = await pool.connection.query("SELECT *")
```

### 3. Graceful Shutdown

```python
class Service:
    def __init__(self):
        self._running = False
        self._tasks: list[asyncio.Task] = []
    
    async def run(self):
        self._running = True
        while self._running:
            task = asyncio.create_task(self._do_work())
            self._tasks.append(task)
            task.add_done_callback(self._tasks.remove)
    
    def stop(self):
        self._running = False
    
    async def close(self):
        self.stop()
        await asyncio.gather(*self._tasks, return_exceptions=True)
```

### 4. Runtime Checkpoint (Fault Tolerance)

```python
class AgentLoop:
    async def _dispatch(self, msg: InboundMessage):
        try:
            result = await self._process(msg)
        except Exception:
            # Save checkpoint for recovery
            await self._save_checkpoint(msg)
            raise
        
        self._clear_checkpoint()
        return result
    
    async def _restore_on_restart(self):
        """Resume interrupted task"""
        checkpoint = self._load_checkpoint()
        if checkpoint:
            # Replay partial state
            await self._resume_from_checkpoint(checkpoint)
```

### 5. Token Budget Management

```python
class TokenBudget:
    def __init__(self, max_tokens: int, output_tokens: int = 500):
        self.max_tokens = max_tokens
        self.output_reserve = output_tokens
    
    def compute_input_budget(self) -> int:
        return self.max_tokens - self.output_reserve
    
    def estimate_messages(self, messages: list[dict]) -> int:
        return sum(self._count_tokens(m) for m in messages)
    
    def truncate_to_budget(self, messages: list[dict]) -> list[dict]:
        budget = self.compute_input_budget()
        while self.estimate_messages(messages) > budget:
            messages.pop(0)  # Remove oldest
        return messages
```

## 📚 Best Practices

### 1. Environment Variable Substitution

```python
import os
import re

def resolve_config(config: dict) -> dict:
    """Resolve ${VAR} references from environment"""
    def resolve_value(value):
        if isinstance(value, str):
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            for var in matches:
                value = value.replace(f'${{{var}}}', os.environ.get(var, ''))
            return value
        if isinstance(value, dict):
            return {k: resolve_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [resolve_value(v) for v in value]
        return value
    
    return resolve_config(config) if isinstance(config, dict) else config
```

### 2. Safe File Operations

```python
def safe_path_join(base: Path, user_path: str) -> Path:
    """Ensure path is within base directory"""
    # Normalize and resolve
    requested = (base / user_path).resolve()
    
    # Security check
    if not requested.is_relative_to(base):
        raise PermissionError("Path outside workspace")
    
    return requested
```

### 3. Idempotent Operations

```python
class CronScheduler:
    def add_job(self, job_id: str, spec: JobSpec):
        # Idempotent: update if exists
        if job_id in self._jobs:
            self._jobs[job_id] = spec
        else:
            self._jobs[job_id] = spec
```

### 4. Streaming Response Pattern

```python
async def stream_response(response: LLMResponse, callback):
    """Stream tokens as they arrive"""
    for delta in response.stream():
        await callback(delta)
    await callback("<DONE>")
```

### 5. Health Check Pattern

```python
class HealthCheck:
    async def check(self) -> dict:
        return {
            "status": "healthy",
            "checks": {
                "database": await self._check_db(),
                "llm": await self._check_llm(),
                "channels": await self._check_channels(),
            }
        }
```

## 🚀 Code Snippets có thể tái sử dụng

### 1. Async Retry Decorator

```python
def async_retry(max_attempts=3, delays=(1, 2, 4)):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(delays[attempt])
        return wrapper
    return decorator

@async_retry(max_attempts=3)
async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        return await client.get(url)
```

### 2. Rate Limiter

```python
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, calls: int, period: float):
        self.calls = calls
        self.period = period
        self._buckets: dict[str, list[float]] = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        now = time.time()
        bucket = self._buckets[key]
        
        # Remove old calls
        bucket[:] = [t for t in bucket if now - t < self.period]
        
        if len(bucket) < self.calls:
            bucket.append(now)
            return True
        return False
```

### 3. Circuit Breaker

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"
    
    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise CircuitOpenError()
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "open"
            raise
```

### 4. JSONL Writer

```python
class JSONLWriter:
    def __init__(self, path: Path):
        self.path = path
        self._file = None
    
    def __enter__(self):
        self._file = open(self.path, 'w')
        return self
    
    def __exit__(self, *args):
        if self._file:
            self._file.close()
    
    def write(self, obj: dict):
        self._file.write(json.dumps(obj, ensure_ascii=False) + '\n')
        self._file.flush()
```

### 5. Config-driven Object Factory

```python
class ObjectFactory:
    _registry: dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, cls_type: type):
        cls._registry[name] = cls_type
    
    @classmethod
    def create(cls, name: str, config: dict):
        if name not in cls._registry:
            raise ValueError(f"Unknown type: {name}")
        return cls._registry[name](**config)
```

## 📋 Checklist cho Project mới

```markdown
## Architecture Checklist
- [ ] Plugin system cho extensions
- [ ] Async-first design
- [ ] Graceful shutdown handling
- [ ] Health check endpoints
- [ ] Structured logging (Loguru)
- [ ] Type hints throughout
- [ ] Pydantic cho config validation
- [ ] Environment variable resolution
- [ ] Error classification (retryable vs not)
- [ ] Circuit breaker cho external services
- [ ] Rate limiting
- [ ] Checkpoint/restore cho fault tolerance
- [ ] JSONL cho append-only logs
```

## 🎓 Kết luận

Nanobot cung cấp một ví dụ xuất sắc về cách xây dựng một **lightweight AI agent framework** với:

1. **Clean Architecture**: Separation of concerns rõ ràng
2. **Extensibility**: Plugin-based design cho channels và providers
3. **Resilience**: Retry logic, circuit breakers, graceful shutdown
4. **Simplicity**: Code nhỏ gọn, dễ hiểu và maintain
5. **Production-Ready**: Error handling, logging, health checks

Các patterns trong document này có thể được áp dụng cho:
- Chatbot frameworks
- API gateways
- Multi-provider integrations
- Event-driven systems
- Tool-calling agents
