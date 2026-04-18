# 9router Provider

9router is an OpenAI-compatible gateway at `http://103.245.237.43:20128/v1`. It routes requests to various models including combo-code, combo-claw, glm, kimi, and MiniMax models.

## How It Works

The `custom` provider in nanobot's registry acts as a direct passthrough to 9router:

```python
ProviderSpec(
    name="custom",
    keywords=(),
    env_key="",
    display_name="Custom",
    backend="openai_compat",
    is_direct=True,  # Skips API key validation — you provide everything
)
```

Key characteristics:
- **`is_direct=True`**: No API key validation. You supply `api_key` and `api_base` explicitly.
- **`backend="openai_compat"`**: Uses `OpenAICompatProvider` — handles all OpenAI-compatible APIs.
- **No keywords**: Not auto-matched by model name — only used when `provider: "custom"` is set.

## Configuration

In `~/.nanobot/config.json`:

```json
{
  "providers": {
    "custom": {
      "api_key": "sk-fc0b27cf63ed9f2a-mv60em-335e7a61",
      "api_base": "http://103.245.237.43:20128/v1"
    }
  },
  "agents": {
    "defaults": {
      "provider": "custom",
      "model": "combo-code"
    }
  }
}
```

## Available Models

| Model | Description |
|-------|-------------|
| `combo-code` | Code generation model |
| `combo-claw` | General purpose model |
| `glm/glm-5.1` | Zhipu GLM-5.1 |
| `oc/glm-5.1` | Zhipu GLM-5.1 (organization) |
| `oc/kimi-k2.5` | Moonshot Kimi K2.5 (organization) |
| `oc/minimax-m2.7` | MiniMax M2.7 (organization) |
| `minimax/MiniMax-M2.7` | MiniMax M2.7 |

Model prefixes:
- `oc/` — Organization-scoped models (require special routing)
- `glm/`, `minimax/` — Provider-prefixed models

## Provider Resolution Logic

1. **`agents.defaults.provider = "custom"`** → Uses `providers.custom` config
2. The `custom` provider's `is_direct=True` flag skips API key validation
3. All requests go to `providers.custom.api_base` with `providers.custom.api_key`

## Test Script

To verify 9router connectivity:

```python
#!/usr/bin/env python3
"""Test 9router endpoint."""

import asyncio
import httpx

PROVIDERS = {
    "9router": {
        "api_key": "sk-fc0b27cf63ed9f2a-mv60em-335e7a61",
        "api_base": "http://103.245.237.43:20128/v1",
        "models": [
            "combo-code", "combo-claw",
            "glm/glm-5.1", "oc/glm-5.1",
            "oc/kimi-k2.5", "oc/minimax-m2.7",
            "minimax/MiniMax-M2.7"
        ],
    },
}

async def test_model(api_base: str, api_key: str, model: str) -> str:
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
    try:
        r = await httpx.AsyncClient().post(url, headers=headers, json=payload, timeout=15)
        if r.status_code == 200:
            return "✅ OK"
        return f"❌ {r.status_code}: {r.text[:100]}"
    except Exception as e:
        return f"❌ {type(e).__name__}: {e}"

async def main():
    cfg = PROVIDERS["9router"]
    print("\n=== 9router ===")
    for model in cfg["models"]:
        status = await test_model(cfg["api_base"], cfg["api_key"], model)
        print(f"  {model:30s} → {status}")

asyncio.run(main())
```

## Adding 9router as a Built-in Provider

To avoid setting `provider: "custom"` each time, add 9router to the registry in `nanobot/providers/registry.py`:

```python
# 9router: OpenAI-compatible gateway
ProviderSpec(
    name="nine_router",  # Python identifier (NOT "9router" — to_snake("9router") = "9router" invalid)
    keywords=("9router",),
    env_key="",
    display_name="9router",
    backend="openai_compat",
    is_gateway=True,
    is_direct=True,
    detect_by_base_keyword="103.245.237.43",
    default_api_base="http://103.245.237.43:20128/v1",
),
```

Then add to `ProvidersConfig` in `config/schema.py`:
```python
nine_router: ProviderConfig = Field(
    default_factory=ProviderConfig,
    validation_alias="9router",      # Config JSON uses "9router"
    serialization_alias="9router",
)
```

Then in config.json you can use:
```json
{
  "providers": {
    "9router": {
      "api_key": "sk-fc0b27cf63ed9f2a-mv60em-335e7a61"
    }
  },
  "agents": {
    "defaults": {
      "provider": "9router",
      "model": "combo-code"
    }
  }
}
```

**Implementation notes:**
- `to_snake("9router")` returns `"9router"` (invalid Python identifier)
- `find_by_name()` handles the translation: `9router` → `nine_router`
- Registry `ProviderSpec.name`: `nine_router` (Python identifier)
- Config field: `nine_router` with `validation_alias="9router"` (config uses `"9router"`)