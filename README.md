# PicoRouter v0.0.2

[![Release](https://img.shields.io/github/v/release/CCAgentOrg/picorouter)](https://github.com/CCAgentOrg/picorouter/releases)
[![Docker](https://img.shields.io/docker/pulls/ccagentorg/picorouter)](https://hub.docker.com/r/ccagentorg/picorouter)
[![PyPI](https://img.shields.io/pypi/v/picorouter)](https://pypi.org/project/picorouter/)
[![License](https://img.shields.io/github/license/CCAgentOrg/picorouter)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/CCAgentOrg/picorouter/ci)](https://github.com/CCAgentOrg/picorouter/actions)

**Your personal OpenRouter** — lean, local-first, AI model router.

Bring all your models together — configure routing profiles, and PicoRouter automatically picks the best one for each request.

**One router, many apps** — Run locally, then point OpenClaw, VSCode, Cursor, Continue to `http://localhost:8080/v1`.

---

## ✨ Features

### 🌊 Local-First
- Ollama, LM Studio — free, unlimited, private
- Auto-failover to cloud when unavailable

### 🧠 Intelligent Routing
- **Content-aware**: Detects code, reasoning, short/long prompts
- **Header-based**: X-PicoRouter-* headers for runtime control
- **Virtual providers**: privacy, free, fast, sota

### 🔌 15+ Providers
- **Local**: Ollama, LM Studio
- **Free**: Kilo, Groq, OpenRouter
- **Cloud**: OpenAI, Anthropic, Google, Mistral, Cohere
- **Aggregators**: Together, DeepInfra, Fireworks

### 🔐 Multi-Key Auth
- Per-key rate limits
- Per-key profile restrictions
- Per-key capabilities (chat/stats/logs)

### 💾 Storage Backends
- JSONL (file) — default
- SQLite — embedded
- Turso/LibSQL — local-first sync

### 🔑 Secrets Management
- Environment variables (default)
- .env file
- Vaultwarden
- Encrypted file

### 🐳 Lean
- <50MB memory
- Python 3.9+
- No FastAPI — plain http.server
- Docker: Alpine ~50MB

---

## 🚀 Quick Start

```bash
# Clone & install
git clone https://github.com/CCAgentOrg/picorouter
cd picorouter
pip install -r requirements.txt

# Generate config
python picorouter.py config --example

# Run server
python picorouter.py serve
```

Then point your app to `http://localhost:8080/v1`

---

## 📡 API

```bash
# Chat completions
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'

# List models
curl http://localhost:8080/v1/models

# Stats
curl http://localhost:8080/stats
```

---

## 🧩 Profiles

```yaml
profiles:
  chat:
    local:
      provider: ollama
      models: [llama3]
    cloud:
      providers:
        kilo:
          models: [minimax/m2.5:free]
    routing:
      - if: short_prompt
        use_local: true
    yolo: false

  coding:
    local:
      models: [codellama]
    routing:
      - if: contains_code
        use_local: true

  yolo:
    yolo: true  # Fire all, return first
```

---

## 🏷️ Virtual Providers

| Provider | Behavior |
|----------|----------|
| `picorouter/privacy` | Local only |
| `picorouter/free` | Local → Kilo → Groq |
| `picorouter/fast` | Groq → Kilo → Local |
| `picorouter/sota` | OpenAI → Anthropic → Google |

---

## 📝 Header Routing

```bash
# Force provider
curl -H "X-PicoRouter-Provider: openai" ...

# Force profile
curl -H "X-PicoRouter-Profile: coding" ...

# Force local only
curl -H "X-PicoRouter-Local: true" ...

# Enable YOLO mode
curl -H "X-PicoRouter-Yolo: true" ...
```

---

## 🔧 CLI

```bash
# Server
python picorouter.py serve --profile chat --host tailscale
python picorouter.py serve --show-ips

# Chat
python picorouter.py chat -m "Hello"

# Keys
python picorouter.py key add -n mykey --rate-limit 60
python picorouter.py key list

# Secrets
python picorouter.py secrets list
python picorouter.py secrets set --provider openai --key "sk-..."

# Models (from models.dev)
python picorouter.py models search --free
python picorouter.py models sync -o config.yaml
```

---

## 🐳 Docker

```bash
docker run -p 8080:8080 ccagentorg/picorouter
```

---

## 📦 Install

```bash
# Via curl
curl -sL https://raw.githubusercontent.com/CCAgentOrg/picorouter/main/install.sh | bash

# Via pip
pip install picorouter
```

---

## 🏢 Architecture

```
App → PicoRouter → Local (Ollama)
              ↓ fail/429
              Cloud (Kilo/Groq/OpenAI/...)
```

---

## 📄 License

MIT — CashlessConsumer 🦀
