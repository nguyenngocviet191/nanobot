# Show Token Usage Footer

Hiển thị số token IN/OUT ở cuối mỗi phản hồi của agent — áp dụng cho cả CLI và toàn bộ channel (Telegram, v.v.).

---

## Cấu hình

Thêm vào `~/.nanobot/config.json`, section `agents.defaults`:

```json
{
  "agents": {
    "defaults": {
      "showTokenUsage": true
    }
  }
}
```

**Mặc định**: `false` (tắt).

---

## Output mẫu

```
Chào Shin! Mình sẵn sàng hỗ trợ.

tokens: in=6,548 out=104
```

---

## Cách hoạt động

```
LLM run xong
    │
    ▼
_process_message() trả về
    │
    ▼
_last_usage populated (prompt_tokens, completion_tokens)
    │
    ├─── Non-streaming SDK ──→ footer embedded trong response.content
    │
    ├─── CLI interactive ────→ footer gửi qua bus → in ra console
    │
    └─── Telegram / channel ─→ footer gửi qua bus → Telegram message mới
```

**Lý do không gửi footer trong `on_stream_end`**: callback này được gọi _trong khi_ LLM đang chạy, trước khi usage data được cập nhật. Footer chỉ sẵn sàng sau khi `_process_message()` hoàn tất.

---

## Files thay đổi

| File | Thay đổi |
|------|----------|
| `nanobot/config/schema.py` | Thêm `show_token_usage: bool = False` vào `AgentDefaults` |
| `nanobot/agent/loop.py` | Nhận param, gửi footer sau `_process_message()` |
| `nanobot/cli/commands.py` | Pass `show_token_usage` vào `AgentLoop` (3 nơi) |
| `nanobot/nanobot.py` | Pass `show_token_usage` vào `AgentLoop` (SDK) |

### Vị trí trong `AgentDefaults` (schema.py)

```python
class AgentDefaults(Base):
    # ...
    show_token_usage: bool = False  # append token usage IN/OUT at the end of each response
```

`show_token_usage` nằm trong `AgentDefaults` (không phải `ChannelsConfig`) vì nó áp dụng cho mọi kênh đầu ra, kể cả CLI.

### Logic gửi footer (loop.py)

```python
# Sau khi _process_message() hoàn tất:
is_non_streaming_sdk = (
    response is not None
    and not response.metadata.get("_streamed")
)
if self.show_token_usage and self._last_usage and not is_non_streaming_sdk:
    prompt = self._last_usage.get("prompt_tokens", 0)
    completion = self._last_usage.get("completion_tokens", 0)
    if prompt or completion:
        footer = f"\n\ntokens: in={prompt:,} out={completion:,}"
        await self.bus.publish_outbound(OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id,
            content=footer,
            metadata={},
        ))
```

Ba trường hợp:

| Trường hợp | `_streamed` | Xử lý footer |
|------------|-------------|--------------|
| Non-streaming SDK | `False` | Embedded trong `response.content` |
| CLI interactive | `True` | Gửi riêng → in ra console |
| Telegram streaming | `True` | Gửi riêng → Telegram message mới |
