# PicoRouter

**Your personal OpenRouter** — lean, local-first, and you control everything.

Bring all your models together — configure routing profiles, and PicoRouter automatically picks the best one for each request. OpenRouter.ai itself is just one provider in the chain.

[🌀 Pico family](https://github.com/cashlessconsumer) — PicoClaw, PicoLM, PicoRouter

## Why PicoRouter?

- **Local first**: Ollama / LM Studio — always free, unlimited, private
- **Cloud fallback**: Seamlessly cycle through free tiers when local isn't available
- **Intelligent routing**: Content-aware model selection based on prompt analysis
- **OpenAI-compatible**: Works with any LLM app (Claude Code, Cursor, Continue, etc.)
- **Lean**: <50MB memory, minimal dependencies
- **Usage tracking**: Full metadata, tokens, cost, duration — stored locally or in Turso

## Quick Start

```bash
# Clone
git clone https://github.com/cashlessconsumer/picorouter.git
cd picorouter

# Install
pip install -r requirements.txt

# Generate config (interactive TUI)
python picorouter.py config --example

# Run server
python picorouter.py serve --profile coding
```

Then point your LLM app to `http://localhost:8080/v1`

## Features

### Intelligent Routing

Content-aware routing based on prompt analysis:

```yaml
profiles:
  coding:
    routing:
      - if: contains_code      # Detects code patterns
        use_local: true
        models: [codellama]
      - if: short_prompt       # < 200 chars
        use_local: true
        models: [llama3:fast]
```

### Multi-Provider Support

```yaml
cloud:
  providers:
    kilo:
      models: [minimax/m2.5:free]
    groq:
      models: [llama-3.1-70b-versatile]
    openrouter:
      models: [openrouter/free]
```

### YOLO Mode

When you want to burn everything:

```bash
picorouter serve --profile yolo
```

Fires all providers at once, takes first success.

### Turso Database

Store all logs in Turso/LibSQL:

```yaml
database:
  turso_url: "libsql://your-db.turso.io"
```

Tables created automatically:
- `requests` — chat/completion logs
- `search_logs` — web search logs

## Architecture

```
Request → Analyze Prompt → Match Routing Rule
                            ↓
                    Local Model → Fail → Cloud Provider A → 429 → B → ✓
```

## Supported Providers

| Provider | Type | Free Tier |
|----------|------|-----------|
| Ollama | Local | ✓ Unlimited |
| LM Studio | Local | ✓ Unlimited |
| Kilo.ai | Cloud | ✓ Yes |
| Groq | Cloud | ✓ Yes |
| OpenRouter | Cloud | ✓ Yes |

## API Endpoints

```
POST /v1/chat/completions
POST /v1/completions
GET  /v1/models
GET  /health
GET  /stats          # Usage statistics
GET  /logs           # Recent requests
```

## Usage Dashboard

```bash
# View stats
curl http://localhost:8080/stats

# CLI view
python picorouter.py logs -s
python picorouter.py logs -n 20
```

Stats include:
- Total requests, tokens, cost (USD)
- By routing (seamless/yolo), provider, model, profile

## Use Cases

1. **Private LLM for sensitive work** — Local Ollama, no data leaves your machine
2. **Never hit rate limits** — Seamlessly cycle through free tiers
3. **Content-aware routing** — Code goes to coder models, chat to chat models
4. **Development workflow** — Use local for speed, cloud for quality
5. **Web search with logs** — All searches tracked in Turso

## License

MIT — CashlessConsumer 🦀
