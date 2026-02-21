# PicoRouter

![Release](https://img.shields.io/github/v/release/CCAgentOrg/picorouter)
![Docker](https://img.shields.io/docker/pulls/ccagentorg/picorouter)
![PyPI](https://img.shields.io/pypi/v/picorouter)
![License](https://img.shields.io/github/license/CCAgentOrg/picorouter)
![Tests](https://img.shields.io/github/actions/workflow/status/CCAgentOrg/picorouter/ci)

> Your personal OpenRouter — lean, local-first, AI model router

Bring all your models together — configure routing profiles, and PicoRouter automatically picks the best one for each request.

**One router, many apps** — Run locally, then point OpenClaw, VSCode, Cursor, Continue to `http://localhost:8080/v1`.

## Features

- **Local-first** — Ollama, LM Studio support with auto-failover
- **Intelligent routing** — Content-aware (code, reasoning, length) and header-based
- **15+ providers** — OpenAI, Anthropic, Google, Mistral, Cohere, and aggregators
- **Multi-key auth** — Per-key rate limits, profiles, capabilities
- **Virtual providers** — `picorouter/privacy`, `picorouter/free`, `picorouter/fast`, `picorouter/sota`
- **Pluggable backends** — JSONL, SQLite, Turso for storage and config
- **Minimal** — <50MB memory, Python 3.9+, Alpine Docker ~50MB

## Quick Start

```bash
# Clone and install
git clone https://github.com/CCAgentOrg/picorouter
cd picorouter
pip install -r requirements.txt

# Generate config and run
python picorouter.py config --example
python picorouter.py serve
```

Then point your app to `http://localhost:8080/v1`

## API

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

## CLI

```bash
# Server
python picorouter.py serve --profile chat --host tailscale

# Chat
python picorouter.py chat -m "Hello"

# Keys
python picorouter.py key add -n mykey --rate-limit 60
python picorouter.py key list

# Secrets
python picorouter.py secrets list
python picorouter.py secrets set --provider openai --key "sk-..."
```

## Profiles

```yaml
profiles:
  chat:
    local:
      provider: ollama
      endpoint: http://localhost:11434
      models: [llama3]
    cloud:
      providers:
        kilo:
          models: [minimax/m2.5:free]
        groq:
          models: [llama-3.1-70b-versatile]
    routing:
      - if: short_prompt
        use_local: true
      - if: contains_code
        use_local: true
```

## Docker

```bash
docker run -p 8080:8080 ccagentorg/picorouter
```

## Architecture

```
App → PicoRouter → Local (Ollama)
              ↓ fail/429
              Cloud (Kilo/Groq/OpenAI/...)
```

## Documentation

- [**Features**](FEATURES.md) — Comparison with OpenRouter, Portkey, LiteLLM
- [**API**](docs/api.md) — OpenAI-compatible endpoints
- [**CLI**](docs/cli.md) — Command-line reference
- [**Docker**](docs/docker.md) — Container usage
- [**Install**](INSTALL.md) — Installation options
- [**Development**](DEVELOP.md) — Contributing guide

## License

MIT — CashlessConsumer 🦀
