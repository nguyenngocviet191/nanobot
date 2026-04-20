# Vision Model Feature - Technical Documentation

## Overview

Vision model cho phép bot Telegram đọc và phân tích hình ảnh. Khi user gửi ảnh (có hoặc không có caption), bot sẽ tự động chuyển sang vision model để xử lý ảnh trước khi trả lời.

## Supported Image Formats

- `.jpg`, `.jpeg`
- `.png`
- `.gif`
- `.webp`

## Configuration

### File: `config.json`

Vision model được cấu hình trong section `channels.telegram.vision_model`:

```json
{
  "channels": {
    "telegram": {
      "token": "YOUR_BOT_TOKEN",
      "allowed_users": [123456789],
      "vision_model": [
        "nine_router/oc/kimi-k2.5",
        "nine_router/oc/glm-5.1"
      ]
    }
  },
  "agents": {
    "defaults": {
      "provider": "nine_router",
      "model": "combo-claw"
    }
  },
  "providers": {
    "nine_router": {
      "type": "openai_compat",
      "apiKey": "sk-9router",
      "apiBase": "http://103.245.237.43:20128/v1",
      "models": ["combo-claw", "glm/glm-5", "oc/kimi-k2.5", "oc/glm-5.1"]
    }
  }
}
```

**Lưu ý quan trọng:**
- `vision_model` phải đặt trong `channels.telegram`, KHÔNG phải `agents.defaults`
- Model name phải match với models trong provider config
- Prefix (e.g., `nine_router/`) phải khớp với provider name

## Architecture

### Flow xử lý

```
User sends image(s)
        ↓
Telegram receives Update
        ↓
_on_message() [telegram.py:987]
        ↓
_download_message_media() - tải ảnh về local
        ↓
_check for image files (.jpg, .jpeg, .png, .gif, .webp)
        ↓
_get_vision_models() - lấy vision model từ config
        ↓
Set metadata["_vision_model"] = [vision_models]
        ↓
_handle_message() - gửi đến agent loop
        ↓
loop.py: _pre_process() [line 707]
        ↓
Extract metadata["_vision_model"]
        ↓
Call provider with vision model
        ↓
Agent receives image + description → responds
```

### Key Components

#### 1. `_get_vision_models()` [telegram.py:889]

```python
def _get_vision_models(self) -> list[str]:
    """Get configured vision models from config."""
    if hasattr(self.config, "vision_model") and self.config.vision_model:
        return [m for m in self.config.vision_model if m]
    return []
```

- Đọc từ `TelegramConfig.vision_model`
- Trả về list model names

#### 2. `_on_message()` [telegram.py:987]

Xử lý message thông thường:
- Download media
- Check image extension
- Gọi `_get_vision_models()`
- Set `metadata["_vision_model"]`

#### 3. `_flush_media_group()` [telegram.py:1077]

Xử lý media group (nhiều ảnh hoặc ảnh + caption):
- Buffer các message trong 600ms
- Sau đó gộp lại thành 1 message
- Check vision model cho image files trong buffer
- Gửi đến `_handle_message()`

#### 4. `loop.py:_pre_process()` [line 707]

Nhận metadata và switch model:
```python
vision_models = msg.metadata.get("_vision_model")
if vision_models:
    for vm in vision_models:
        if self._provider_manager.has_model(vm):
            model = vm
            break
```

## Edge Cases

### 1. Chỉ gửi ảnh (không caption)

- Telegram gửi 1 message với photo
- `_download_message_media()` trả về media_paths
- Check extension → set vision model → xử lý thành công ✅

### 2. Gửi ảnh + caption

- Telegram gửi thành media group (2 message)
- Message 1: ảnh với caption embedded
- Message 2: caption text
- `_flush_media_group()` buffer cả 2
- Check vision model cho media → set → xử lý thành công ✅

### 3. Gửi nhiều ảnh

- Mỗi ảnh được download
- Tất cả paths được buffer
- Vision model check với first image
- Xử lý tất cả ảnh cùng lúc

### 4. Không có vision_model trong config

- `_get_vision_models()` trả về `[]`
- `has_images` check vẫn True nhưng không set metadata
- Bot sử dụng default model
- Ảnh có thể được xử lý bằng MCP tool `analyze_image` fallback

## Troubleshooting

### 1. Bot không switch sang vision model

**Nguyên nhân:** `vision_model` không đúng vị trí trong config

**Kiểm tra:**
```bash
cat config.json | grep -A5 '"telegram"'
```

**Đảm bảo:**
```json
"telegram": {
  "vision_model": ["provider/model-name"]
}
```

### 2. Ảnh đọc được nhưng caption không

**Nguyên nhân:** Media group flow không check vision model

**Kiểm tra:** Đảm bảo `_flush_media_group()` có gọi `_get_vision_models()`

### 3. Model name không match

**Nguyên nhân:** Model trong `vision_model` không tồn tại trong provider

**Kiểm tra:**
```json
"providers": {
  "nine_router": {
    "models": ["model1", "model2"]
  }
}
```

Vision model phải nằm trong danh sách models của provider.

## Files Modified

| File | Changes |
|------|---------|
| `nanobot/channels/telegram.py` | Thêm `vision_model` vào `TelegramConfig`, `_get_vision_models()`, check vision trong `_flush_media_group()` |
| `nanobot/agent/loop.py` | Logic switch model khi có `_vision_model` metadata |
| `config.json` | Thêm `vision_model` vào `channels.telegram` |

## Future Improvements

1. **Multi-image handling**: Xử lý từng ảnh riêng biệt thay vì gộp
2. **Image captioning**: Tự động generate caption cho ảnh trước khi xử lý
3. **Vision model fallback**: Thử vision model khác nếu primary fails
4. **Config validation**: Warn nếu vision_model không tồn tại trong provider
