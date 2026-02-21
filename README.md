# PicoRouter

**Minimal AI model router** — local-first with intelligent cloud fallback.

[🌀 Pico family](https://github.com/cashlessconsumer) — PicoClaw, PicoLM, PicoRouter

## Why PicoRouter?

- **Local first**: Ollama / LM Studio — always free, unlimited, private
- **Cloud fallback**: Seamlessly cycle through free tiers when local isn't available
- **Intelligent routing**: Content-aware model selection based on prompt analysis
- **OpenAI-compatible**: Works with any LLM app (Claude Code, Cursor, Continue, etc.)
- **Lean**: <50MB memory, minimal dependencies
- **Built-in search**: MCP server for your SearXNG instance

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

## Configuration

See `config.example.yaml` for full options.

### Environment Variables

```bash
export KILO_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."
export OPENROUTER_API_KEY="sk-or-..."
```

## API Endpoints

```
POST /v1/chat/completions
POST /v1/completions
GET  /v1/models
GET  /health

# Usage tracking
GET  /stats          # Usage statistics
GET  /logs           # Recent requests (JSONL)
```

## Usage Dashboard

```bash
# View stats
curl http://localhost:8080/stats

# View recent logs
curl http://localhost:8080/logs
curl http://localhost:8080/logs?limit=100

# CLI view
python picorouter.py logs -s
python picorouter.py logs -n 20
```

Stats include:
- Total requests
- Total tokens
- Total cost (USD, estimated)
- Requests by routing (seamless/yolo)
- Requests by provider
- Requests by model
- Requests by profile
- Error count

Each log entry includes:
- timestamp, request_id, profile, provider, model
- routing mode, tokens (in/out/total), duration_ms, cost_usd

## PicoSearch MCP Server

Built-in search via MCP (Model Context Protocol):

```bash
# Run the MCP search server
python mcpsearch.py
```

### Tools exposed:
- `search` - Search the web via SearXNG
- `search_stats` - View search usage stats

### Config (picorouter.yaml):
```yaml
search:
  searxng_url: https://ccsearxng.zeabur.app

# Optional: Turso database for logs
database:
  turso_url: "libsql://your-db.turso.io"
```

### Usage in Claude Code / Continue:
Add to your MCP config:
```json
{
  "mcpServers": {
    "picorouter-search": {
      "command": "python",
      "args": ["/path/to/picorouter/mcpsearch.py"]
    }
  }
}
```

Then use: `Search the web for...` in your AI assistant.

## PicoSearch - Multi-Provider Web Search

Standalone web search with provider fallback + Turso logging:

```bash
# CLI search
python picosearch.py -q "Python async best practices"

# Run as MCP server
python picosearch.py --mcp

# View stats
python picosearch.py --stats
```

### Providers (tried in order):
1. **SearXNG** — Your self-hosted instance (free, private)
2. **Brave** — API-based (needs key)
3. **DuckDuckGo** — Free fallback

### Config (picorouter.yaml):
```yaml
search:
  searxng_url: https://ccsearxng.zeabur.app
  brave_api_key: "your-brave-key"

database:
  turso_url: "libsql://your-db.turso.io"
```

### Logs to Turso:
- `search_logs` table with query, provider, results_count, duration_ms, error
- Falls back to JSONL if no Turso

## Use Cases

1. **Private LLM for sensitive work** — Local Ollama, no data leaves your machine
2. **Never hit rate limits** — Seamlessly cycle through free tiers
3. **Content-aware routing** — Code goes to coder models, chat to chat models
4. **Development workflow** — Use local for speed, cloud for quality

## License

MIT — CashlessConsumer 🦀
