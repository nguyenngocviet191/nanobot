# Nanobot - Limitations & Improvements

## ⚠️ Current Limitations

### 1. Concurrency & Performance

| Issue | Severity | Impact |
|-------|----------|--------|
| **Single-Agent Loop** | Medium | Per-session serial processing; cross-session only |
| **No Horizontal Scaling** | High | Cannot run multiple instances sharing state |
| **In-Memory Session Cache** | Medium | Large number of sessions → memory pressure |
| **Tool Concurrency Batching** | Low | Limited by concurrency_safe flag on tools |

### 2. Context Management

| Issue | Severity | Impact |
|-------|----------|--------|
| **Token Budget** | Medium | Hard limit on conversation length |
| **Microcompact Strategy** | Low | Only summaries certain tool results |
| **No RAG Integration** | Medium | Cannot query historical knowledge |
| **Dream Consolidation Async** | Low | Background task may delay |

### 3. Channel Limitations

| Channel | Limitation | Workaround |
|---------|------------|------------|
| **WhatsApp** | Requires Node.js bridge | Rebuild after upgrade |
| **WeChat** | iLinkai API required | Paid service dependency |
| **QQ** | Private messages only | No group chat support |
| **Email** | No attachment streaming | Limited to 2MB per attachment |

### 4. LLM Provider Constraints

| Issue | Description |
|-------|-------------|
| **Rate Limiting** | No per-provider rate limit config |
| **Context Caching** | Only Anthropic supports prompt caching |
| **Model Routing** | No intelligent fallback between models |
| **Cost Tracking** | No built-in cost monitoring |

### 5. Security Concerns

| Issue | Severity | Mitigation |
|-------|----------|------------|
| **Workspace Isolation** | Medium | Path validation before operations |
| **Exec Tool** | High | Sandboxed but powerful; review access |
| **Config Secrets** | Low | Environment variable support exists |
| **No Audit Logging** | Medium | Would need external logging |

### 6. Missing Features

| Feature | Status | Priority |
|---------|--------|----------|
| **Streaming in API** | Not supported | High |
| **Web Search Config** | Limited providers | Medium |
| **Multi-Agent Orchestration** | Subagent only | Medium |
| **Persistent MCP Connections** | Reconnects on restart | Low |
| **Team Mode Persistence** | In-memory only | Medium |

## 🔧 Recommended Improvements

### High Priority

#### 1. Streaming API Support
```python
# Current: API does not support stream=true
# Recommended: Add SSE or WebSocket streaming

async def handle_chat_completions_stream(request):
    """POST /v1/chat/completions with stream=true"""
    # Implement Server-Sent Events
    # Or WebSocket upgrade
```

#### 2. Cost Tracking & Budgeting
```python
# Recommended: Add usage tracking
class UsageTracker:
    def track(self, provider: str, model: str, tokens: dict):
        """Track token usage per session"""
        pass
        
    def get_cost(self, session_key: str) -> float:
        """Calculate total cost for session"""
        pass
```

#### 3. RAG Integration for Memory
```python
# Recommended: Add vector search for historical context
class MemoryRAG:
    def add_to_index(self, session_key: str, content: str):
        """Add to vector index"""
        pass
        
    def query(self, question: str, top_k: int = 5) -> list[str]:
        """Retrieve relevant context"""
        pass
```

### Medium Priority

#### 4. Horizontal Scaling Architecture
```python
# Recommended: Add shared state backend
class RedisSessionBackend:
    """Redis-backed session manager for scaling"""
    async def save(self, session: Session):
        pass
        
    async def load(self, key: str) -> Session:
        pass
```

#### 5. Intelligent Model Routing
```python
# Recommended: Add fallback chain
class ModelRouter:
    def route(self, task_type: str, budget: float) -> str:
        """Select best model based on task and budget"""
        pass
        
# Config example:
# "routing": {
#   "code": ["claude-opus", "gpt-4", "deepseek"],
#   "chat": ["claude-haiku", "gpt-3.5"]
# }
```

#### 6. Persistent MCP Connections
```python
# Recommended: Add MCP connection persistence
class MCPConnectionManager:
    async def reconnect(self):
        """Reconnect to MCP servers on startup"""
        pass
        
    def get_tools(self, server: str) -> list[Tool]:
        """Cache MCP tools"""
        pass
```

### Low Priority

#### 7. Advanced Security Features
```python
# Recommended: Add audit logging
class AuditLogger:
    def log(self, action: str, session_key: str, details: dict):
        """Log all tool executions"""
        pass
        
# Recommended: Rate limiting per user
class RateLimiter:
    def check(self, user_id: str) -> bool:
        """Rate limit check"""
        pass
```

#### 8. Team Mode Persistence
```python
# Recommended: Save team state
class TeamStateStore:
    def save(self, team_id: str, state: dict):
        """Persist team configuration"""
        pass
        
    def load(self, team_id: str) -> dict:
        """Load team state"""
        pass
```

## 📋 Technical Debt

### Code Quality

| Item | Description | Effort |
|------|-------------|--------|
| Type hints incomplete | Many functions lack type annotations | Medium |
| Exception handling | Generic `except Exception` in places | Low |
| Documentation | Some internal APIs undocumented | Medium |
| Test coverage | No coverage for channel integrations | High |

### Architecture

| Item | Description | Effort |
|------|-------------|--------|
| Circular dependencies | Some import cycles exist | Low |
| Config schema | No runtime validation | Medium |
| Error codes | No standardized error codes | Low |
| Plugin system | Channels hardcoded in registry | Medium |

### Performance

| Item | Description | Effort |
|------|-------------|--------|
| Session loading | JSONL parsing on every request | Medium |
| Tool definitions | Regenerated per call | Low |
| Memory estimation | Token counting overhead | Low |
| Channel polling | Some channels use polling | Varies |

## 🎯 Roadmap Suggestions

### Short Term (1-3 months)
1. ✅ Streaming API support
2. ✅ Cost tracking dashboard
3. ✅ Better error messages
4. 🔄 Type hint completion
5. 🔄 Test coverage improvement

### Medium Term (3-6 months)
1. ⬜ RAG memory integration
2. ⬜ Redis session backend
3. ⬜ Intelligent model routing
4. ⬜ Audit logging
5. ⬜ Webhook support

### Long Term (6-12 months)
1. ⬜ Multi-agent orchestration
2. ⬜ Distributed scaling
3. ⬜ Custom channel SDK
4. ⬜ Enterprise SSO
5. ⬜ Usage analytics dashboard

## 💡 Lessons Learned

### What Works Well
1. **Plugin Architecture**: Easy to add new channels
2. **Message Bus**: Clean separation of concerns
3. **Provider Abstraction**: Multi-LLM support without vendor lock-in
4. **Config-Driven**: Flexible deployment options
5. **Lightweight Core**: Fast iteration and easy debugging

### What Could Be Better
1. **Session Persistence**: JSONL is simple but slow at scale
2. **Error Recovery**: Some edge cases not handled gracefully
3. **Documentation**: Some internal APIs need better docs
4. **Testing**: Channel integrations lack automated tests
5. **Monitoring**: No built-in metrics/observability
