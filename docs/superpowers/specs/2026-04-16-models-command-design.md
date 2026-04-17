# Feature: `/models` Command - Inline Model Selection

## Status: ✅ Implemented & Fixed (2026-04-18)

## Context

User wants a `/models` slash command that shows inline buttons to select AI provider and model for the current session. The selection should be temporary (session-only) and display an indicator after selection.

## Design Summary

**Approach:** Built-in command (not markdown command)
**Flow:** Two-tier navigation (Provider → Model)
**Storage:** In-memory dict trên channel → propagate qua message metadata → `loop.sessions`
**Display:** Edit message to show model indicator after selection

---

## Architecture (Actual Implementation)

```
User: /models
    │
    ▼
TelegramChannel._on_models_command()
    │
    ▼
Load configured providers from Config
    │
    ▼
Send inline keyboard (provider buttons)
    │
    ▼
User taps provider
    │
    ▼
CallbackQuery handler → Edit message with model buttons
    │
    ▼
User taps model
    │
    ▼
1. self._session_models[session_key] = model_full   ← in-memory, không tạo SessionManager mới
2. Edit message → "🤖 Using: {provider}/{model}"
    │
    ▼
User gửi bất kỳ message/command (kể cả /status)
    │
    ▼
_enrich_metadata_with_model()  ← inject _temp_model vào InboundMessage.metadata
    │
    ▼
loop._process_message()
    │
    ▼
session.metadata["temp_model"] = model   ← update loop.sessions (đúng instance)
loop.sessions.save(session)              ← persist xuống disk
```

---

## Tại sao không dùng SessionManager riêng

**Vấn đề gốc:** `_apply_model_to_session` ban đầu tạo `SessionManager(workspace)` mới. Instance này save xuống disk nhưng `loop.sessions` có in-memory cache riêng → cache stale → `/status` vẫn hiện model cũ.

**Giải pháp:** Channel lưu model vào `self._session_models` (dict thuần), inject qua message metadata, để loop tự update `loop.sessions` của nó.

---

## Luồng `/status` sau khi đổi model

```
/status
  → _forward_command()
  → _enrich_metadata_with_model()        ← đọc từ self._session_models
  → metadata["_temp_model"] = "zhipu/glm-5-turbo"
  → loop._process_message()
  → session.metadata["temp_model"] = ... ← sync vào loop.sessions
  → cmd_status()
  → ctx.msg.metadata.get("_temp_model")  ← đọc trực tiếp từ message metadata
  → hiện đúng model ngay lập tức ✓
```

`cmd_status` đọc model theo thứ tự ưu tiên:
1. `ctx.msg.metadata["_temp_model"]` — từ message hiện tại (fresh nhất)
2. `session.metadata["temp_model"]` — persist từ lần trước
3. `loop.model` — model mặc định của agent

---

## Provider Model Resolution

### Priority Order

```
1. Config "models" field trong ProviderConfig
       ↓ (nếu rỗng)
2. Fetch từ provider's /v1/models API
       ↓ (nếu lỗi hoặc rỗng)
3. Hardcoded defaults từ PROVIDERS registry
```

### Config Schema

**File:** `nanobot/config/schema.py`

```python
class ProviderConfig(Base):
    api_key: str = ""
    api_base: str | None = None
    extra_headers: dict[str, str] | None = None
    models: list[str] = []  # explicit model list override
```

### Config Example

```json
{
  "providers": {
    "custom": {
      "apiKey": "...",
      "apiBase": "https://my-endpoint.com/v1",
      "models": ["custom-model-1", "custom-model-2"]
    }
  }
}
```

---

## Telegram Implementation

### Files Modified

| File | Changes |
|------|---------|
| `nanobot/channels/telegram.py` | `_session_models` dict, `_enrich_metadata_with_model()`, `/models` handlers |
| `nanobot/agent/loop.py` | Sync `_temp_model` từ metadata, `_run_agent_loop` nhận optional `model` param |
| `nanobot/command/builtin.py` | `cmd_status` đọc `_temp_model` từ message metadata |

### Key Methods

```python
# telegram.py
def _enrich_metadata_with_model(self, metadata: dict, chat_id: str, session_key: str | None) -> dict:
    """Inject temp model override vào metadata cho AgentLoop."""
    effective_key = session_key or f"telegram:{chat_id}"
    if temp_model := self._session_models.get(effective_key):
        return {**metadata, "_temp_model": temp_model}
    return metadata

async def _apply_model_to_session(self, chat_id: str, model_full: str) -> None:
    """Store selected model in memory — propagate qua message metadata."""
    session_key = f"telegram:{chat_id}"
    self._session_models[session_key] = model_full
    logger.info("Session {} temp model set to {}", session_key, model_full)
```

```python
# loop.py — trong _process_message()
if temp_model := msg.metadata.get("_temp_model"):
    if session.metadata.get("temp_model") != temp_model:
        session.metadata["temp_model"] = temp_model
        self.sessions.save(session)
```

```python
# builtin.py — trong cmd_status()
model = ctx.msg.metadata.get("_temp_model") or session.metadata.get("temp_model") or loop.model
```

### Handler Registration

```python
# /models command
self._app.add_handler(MessageHandler(
    filters.Regex(r"^/models(?:@\w+)?(?:\s+.*)?$"),
    self._on_models_command,
))
# Callback query cho inline buttons
self._app.add_handler(CallbackQueryHandler(self._on_callback_query))
```

⚠️ **Bắt buộc** include `"callback_query"` trong `allowed_updates` khi polling, nếu không inline button clicks sẽ không hoạt động.

---

## Message Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│ User: /models                                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 🤖 Select AI Provider                                       │
│ [Anthropic] [OpenAI] [DeepSeek] ...                         │
└─────────────────────────────────────────────────────────────┘
                              ↓ tap provider
┌─────────────────────────────────────────────────────────────┐
│ 🤖 Select Model for Anthropic                               │
│ [claude-3-5-sonnet-20241022]                                │
│ [claude-3-opus-20240229]                                    │
│ [← Back]                                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓ tap model
┌─────────────────────────────────────────────────────────────┐
│ 🤖 Using: anthropic/claude-3-5-sonnet-20241022              │
└─────────────────────────────────────────────────────────────┘
                              ↓
                  self._session_models[key] = model
                              ↓ next message/command
                  _enrich_metadata_with_model() → loop syncs
```

---

## Error Handling

| Scenario | Response |
|----------|----------|
| No providers configured | "⚠️ No providers configured." |
| Provider has no models | "⚠️ No models available for this provider." |
| API fetch fails | Fallback to config.models hoặc hardcoded defaults |

---

## Known Limitations

- `self._session_models` là in-memory → mất khi bot restart. Sau restart, model vẫn được load từ disk (vì `loop.sessions` persist `session.metadata["temp_model"]` xuống disk khi xử lý message đầu tiên).
- Model override là per-session (per chat_id). Topic threads dùng key riêng.
