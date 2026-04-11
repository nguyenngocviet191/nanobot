# Nanobot - Investigation Overview

## 🎯 Mục đích dự án

**Nanobot** là một **Ultra-Lightweight Personal AI Agent** - một framework AI agent nhẹ cân được phát triển bởi HKUDS team. Dự án được lấy cảm hứng từ [OpenClaw](https://github.com/openclaw/openclaw) với mục tiêu cung cấp chức năng agent core với **99% ít dòng code hơn** các framework truyền thống.

**Slogan**: "Delivers core agent functionality with 99% fewer lines of code"

## 📊 Quality Metrics

- **Version**: 0.1.5 (released 2026-04-05)
- **Python**: ≥3.11
- **License**: MIT
- **GitHub**: https://github.com/HKUDS/nanobot
- **PyPI**: nanobot-ai
- **Cộng đồng**: Discord, Feishu, WeChat groups
- **Tài liệu**: nanobot.wiki

## 🛠 Tech Stack

### Core Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| `typer` | ≥0.20.0 | CLI framework |
| `anthropic` | ≥0.45.0 | Claude API |
| `pydantic` | ≥2.12.0 | Data validation |
| `openai` | ≥2.8.0 | OpenAI API |
| `websockets` | ≥16.0 | WebSocket support |
| `httpx` | ≥0.28.0 | HTTP client |
| `loguru` | ≥0.7.3 | Logging |
| `rich` | ≥14.0.0 | Terminal UI |
| `croniter` | ≥6.0.0 | Cron scheduling |
| `mcp` | ≥1.26.0 | Model Context Protocol |
| `jinja2` | ≥3.1.0 | Template engine |

### Channel Integrations
- **Telegram**: python-telegram-bot
- **Discord**: discord.py
- **Slack**: slack-sdk
- **Feishu**: lark-oapi
- **DingTalk**: dingtalk-stream
- **Matrix**: matrix-nio
- **WhatsApp**: Socket.IO bridge
- **WeChat**: ilinkai API
- **QQ**: qq-botpy
- **Email**: IMAP/SMTP native

### Optional Dependencies
- `api`: aiohttp (for OpenAI-compatible API server)
- `wecom`: wecom-aibot-sdk-python
- `weixin`: qrcode, pycryptodome
- `matrix`: matrix-nio[e2e]
- `discord`: discord.py
- `langsmith`: langsmith
- `pdf`: pymupdf

## 🚀 Quick Setup

```bash
# Install from source (latest features)
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .

# Or install from PyPI (stable)
pip install nanobot-ai

# Initialize
nanobot onboard

# Configure API key in ~/.nanobot/config.json
# Then run
nanobot agent
```

## 📁 Project Structure

```
nanobot/
├── nanobot.py          # Main entry point
├── agent/              # Agent core logic
│   ├── loop.py         # Main agent loop
│   ├── runner.py       # Tool-using LLM loop
│   ├── context.py       # Context building
│   ├── memory.py        # Memory management
│   ├── hook.py         # Lifecycle hooks
│   └── tools/           # Tool registry
├── api/                # OpenAI-compatible API
├── bus/                # Message bus
├── channels/           # Chat platform integrations
├── cli/                # CLI commands
├── command/            # Slash commands
├── config/             # Configuration management
├── cron/               # Scheduled tasks
├── heartbeat/          # Periodic tasks
├── providers/          # LLM providers
├── security/           # Security utilities
├── session/            # Session management
├── skills/             # Built-in skills
├── templates/          # Agent templates
└── utils/              # Utilities
```

## 🎯 Key Value Propositions

1. **Ultra-Lightweight**: Codebase nhỏ gọn, dễ hiểu và modify
2. **Research-Ready**: Code sạch, dễ mở rộng cho nghiên cứu
3. **Lightning Fast**: Khởi động nhanh, resource thấp
4. **Easy-to-Use**: Deploy trong 2 phút

## 🔗 Integration Points

- **LLM Providers**: 20+ providers (OpenAI, Anthropic, OpenRouter, DeepSeek, etc.)
- **Chat Platforms**: 12+ channels
- **Skills**: ClawHub marketplace, custom skills
- **MCP**: Model Context Protocol support
- **OpenAI API**: OpenAI-compatible HTTP API

## 📈 Release Cadence

Dự án có vòng phát triển rất nhanh:
- **4/5/2026**: v0.1.5 - Dream two-stage memory, production-ready sandboxing
- **~50 commits/month** trong năm 2026
- Active community feedback loop
