# Feature: `/models` Command - Inline Model Selection

## Context

User wants a `/models` slash command that shows inline buttons to select AI provider and model for the current session. The selection should be temporary (session-only) and display an indicator after selection.

## Design Summary

**Approach:** Built-in command (not markdown command)
**Flow:** Two-tier navigation (Provider → Model)
**Storage:** Session metadata (`session.metadata["temp_model"]`)
**Display:** Edit message to show model indicator after selection

---

## Architecture

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
1. Store in session.metadata["temp_model"]
2. Edit message → "🤖 Using: {provider}/{model}"
```

---

## Provider Model Resolution

### Priority Order

```
1. Config "models" field in ProviderConfig
       ↓ (if empty or not set)
2. Fetch from provider's /v1/models API
       ↓ (if fails or empty)
3. Hardcoded defaults from PROVIDERS registry
```

### Config Schema Change

**File:** `nanobot/config/schema.py`

```python
class ProviderConfig(Base):
    api_key: str = ""
    api_base: str | None = None
    extra_headers: dict[str, str] | None = None
    models: list[str] = []  # NEW: explicit model list override
```

**File:** `nanobot/config/schema.py` (ProvidersConfig already allows extra fields via `extra="allow"`)

### Config Example

```json
{
  "providers": {
    "custom": {
      "apiKey": "...",
      "apiBase": "https://my-endpoint.com/v1",
      "models": ["custom-model-1", "custom-model-2"]
    },
    "openrouter": {
      "apiKey": "sk-or-..."
    }
  }
}
```

---

## Model Resolution Implementation

```python
async def _get_models_for_provider(provider_name: str, config: Config) -> list[str]:
    """
    Get available models for a provider.
    Priority: config.models > fetch from API > hardcoded defaults
    """
    from nanobot.providers.registry import PROVIDERS, find_by_name

    # 1. Check explicit config
    provider_config = getattr(config.providers, provider_name, None)
    if provider_config and provider_config.models:
        return provider_config.models

    # 2. Try fetch from /v1/models
    if provider_config and provider_config.api_key:
        fetched = await _fetch_models_from_api(provider_name, provider_config)
        if fetched:
            return fetched

    # 3. Fallback to hardcoded defaults
    return _get_hardcoded_models(provider_name)
```

---

## Hardcoded Default Models

```python
DEFAULT_PROVIDER_MODELS = {
    "anthropic": [
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
    ],
    "deepseek": [
        "deepseek-chat",
        "deepseek-coder",
    ],
    "openrouter": [],  # Must fetch - dynamic gateway
    "gemini": [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-pro-exp-0806",
    ],
    "moonshot": [
        "moonshot-v1-8k",
        "moonshot-v1-32k",
        "kimi-k2.5",
    ],
    # ... add more as needed
}
```

---

## Telegram Implementation

### 1. Register Command

**File:** `nanobot/channels/telegram.py`

```python
class TelegramChannel(BaseChannel):
    BOT_COMMANDS = [
        # ... existing commands ...
        BotCommand("models", "Switch AI model for this session"),
    ]

    async def start(self) -> None:
        # ... existing code ...

        # Add /models handler
        self._app.add_handler(
            MessageHandler(
                filters.Regex(r"^/models(?:@\w+)?(?:\s+.*)?$"),
                self._on_models_command,
            )
        )

        # Add callback query handler for inline buttons
        self._app.add_handler(CallbackQueryHandler(self._on_callback_query))
```

### 2. Provider Listing

```python
async def _on_models_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /models command - show provider selection."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    config = self._load_config()
    providers = self._get_configured_providers(config)

    if not providers:
        await update.message.reply_text("⚠️ No providers configured.")
        return

    # Build provider buttons (2 per row)
    buttons = []
    for provider in providers:
        buttons.append([
            InlineKeyboardButton(
                provider["label"],
                callback_data=f"mdl:prov:{provider['name']}"
            )
        ])

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "🤖 *Select AI Provider*\n\nUse buttons below to choose provider:",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
```

### 3. Model Listing (Callback Handler)

```python
async def _on_callback_query(self, update: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    query = update.callback_query
    await query.answer()

    data = query.data
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    if data.startswith("mdl:prov:"):
        # Provider selected → show models
        provider_name = data.split(":")[2]
        models = await self._get_models_for_provider(provider_name)

        if not models:
            await query.edit_message_text("⚠️ No models available for this provider.")
            return

        # Build model buttons
        buttons = [
            [InlineKeyboardButton(model, callback_data=f"mdl:model:{provider_name}:{model}")]
            for model in models
        ]
        buttons.append([
            InlineKeyboardButton("← Back", callback_data="mdl:back:providers")
        ])

        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(
            f"🤖 *Select Model for {provider_name}*\n\nTap to select:",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif data.startswith("mdl:model:"):
        # Model selected → apply and show indicator
        _, _, provider_name, model_name = data.split(":", 3)
        model_full = f"{provider_name}/{model_name}"

        # Store in session
        await self._apply_model_to_session(chat_id, model_full)

        # Update message to indicator
        await query.edit_message_text(
            f"🤖 Using: {model_full}",
            parse_mode="Markdown",
        )

    elif data == "mdl:back:providers":
        # Back to provider list → re-show providers
        await self._on_models_command_with_edit(query, context)
```

### 4. Session Model Application

```python
async def _apply_model_to_session(self, chat_id: str, model_full: str) -> None:
    """Store selected model in session metadata."""
    # Get session key for this chat
    session_key = f"telegram:{chat_id}"

    # Get or create session
    session = self.sessions.get_or_create(session_key)

    # Store temp model
    session.metadata["temp_model"] = model_full
    self.sessions.save(session)

    logger.info("Session {} temp model set to {}", session_key, model_full)
```

### 5. Config Loader Helper

```python
def _get_configured_providers(self, config: Config) -> list[dict]:
    """Get providers that have API key configured."""
    providers = []
    for spec in PROVIDERS:
        provider_config = getattr(config.providers, spec.name, None)
        if provider_config and provider_config.api_key:
            providers.append({
                "name": spec.name,
                "label": spec.label,
                "api_key": provider_config.api_key,
                "api_base": provider_config.api_base or spec.default_api_base or "",
            })
    return providers
```

### 6. Model Fetch from API

```python
async def _fetch_models_from_api(self, provider_name: str, provider_config) -> list[str]:
    """Try to fetch model list from provider's /v1/models endpoint."""
    if not provider_config.api_base:
        return []

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{provider_config.api_base}/models",
                headers={"Authorization": f"Bearer {provider_config.api_key}"},
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
    except Exception as e:
        logger.debug("Failed to fetch models from {}: {}", provider_name, e)
    return []
```

---

## Message Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│ User types: /models                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Bot replies:                                               │
│ 🤖 Select AI Provider                                      │
│                                                             │
│ [Anthropic] [OpenAI] [DeepSeek]                            │
│ [Google] [Meta] ...                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    User taps "Anthropic"
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Bot edits message:                                         │
│ 🤖 Select Model for Anthropic                              │
│                                                             │
│ [claude-3-5-sonnet-20241022]                               │
│ [claude-3-opus-20240229]                                   │
│ [claude-3-haiku-20240307]                                  │
│ [← Back]                                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    User taps "claude-3-5-sonnet-20241022"
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Bot edits message:                                         │
│ 🤖 Using: anthropic/claude-3-5-sonnet-20241022             │
└─────────────────────────────────────────────────────────────┘
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `nanobot/config/schema.py` | Add `models: list[str]` to `ProviderConfig` |
| `nanobot/channels/telegram.py` | Add `/models` command, callback handler, model resolution |

---

## Error Handling

| Scenario | Response |
|----------|----------|
| No providers configured | "⚠️ No providers configured." |
| Provider has no models | "⚠️ No models available for this provider." |
| API fetch fails | Fallback to config.models or hardcoded defaults |
| Session not found | Create new session, apply model |

---

## Edge Cases

1. **User clicks rapidly** - CallbackQuery handler should handle gracefully, no double-selection
2. **Session expires** - temp_model persists in session file, survives restarts
3. **Provider removed from config** - Button won't appear since provider list comes from configured providers
4. **Message edit fails** (e.g., too old) - Catch exception, send new message instead