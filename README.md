# PicoRouter

**Your personal OpenRouter** — lean, local-first, and you control everything.

Bring all your models together — configure routing profiles, and PicoRouter automatically picks the best one for each request. Connects directly to any cloud provider, model service, or gateway.

**One router, many apps** — Run PicoRouter locally, then point OpenClaw, VSCode, Cursor, Continue, or any LLM app to `http://localhost:8080/v1`.

[🌀 Pico family](https://github.com/cashlessconsumer) — PicoClaw, PicoLM, PicoRouter

---

## Why PicoRouter?

- **Local first**: Ollama / LM Studio — always free, unlimited, private
- **Cloud fallback**: Seamlessly cycle through free tiers when local isn't available
- **Intelligent routing**: Content-aware model selection based on prompt analysis
- **OpenAI-compatible**: Works with any LLM app
- **Lean**: <50MB memory, minimal dependencies
- **Usage tracking**: Full metadata, tokens, cost, duration

---

## Interfaces

| Interface | Description |
|-----------|-------------|
| **API** | REST API at `/v1/chat/completions` |
| **CLI** | `python picorouter.py serve\|chat\|logs` |
| **SDK** | Python client in `sdk/` |
| **Web UI** | Separate PWA at [picorouter-web](https://github.com/CCAgentOrg/picorouter-web) |

---

## Quick Start

```bash
# Clone
git clone https://github.com/cashlessconsumer/picorouter.git
cd picorouter

# Install
pip install -r requirements.txt

# Generate config
python picorouter.py config --example

# Run server
python picorouter.py serve --profile coding
```

Then point your LLM app to `http://localhost:8080/v1`

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your LLM App                          │
│  (OpenClaw, VSCode, Cursor, Continue, etc.)             │
└─────────────────────┬───────────────────────────────────┘
                      │ POST /v1/chat/completions
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     PicoRouter                             │
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Profile  │───▶│   Prompt    │───▶│   Routing    │  │
│  │  Selector  │    │  Analyzer   │    │    Engine    │  │
│  └─────────────┘    └──────────────┘    └──────────────┘  │
│         │                                       │          │
│         ▼                                       ▼          │
│  ┌─────────────┐                      ┌──────────────┐   │
│  │    Local    │                      │     Cloud    │   │
│  │  (Ollama)  │───fail/429──────────▶│   Providers  │   │
│  └─────────────┘                      │ (Kilo, Groq, │   │
│                                      │  OpenRouter) │   │
│                                      └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Config File Locations

PicoRouter looks for config in this order:
1. `./picorouter.yaml` (current directory)
2. `~/.picorouter.yaml` (home directory)
3. `~/.config/picorouter.yaml`

### Profile Structure

Each profile defines how requests are routed:

```yaml
profiles:
  my-profile:
    local:
      provider: ollama              # or "lmstudio"
      endpoint: http://localhost:11434
      models:
        - llama3
        - codellama
    
    cloud:
      providers:
        kilo:
          api_key: ${KILO_API_KEY}
          models:
            - minimax/m2.5:free
        groq:
          api_key: ${GROQ_API_KEY}
          models:
            - llama-3.1-70b-versatile
        openrouter:
          api_key: ${OPENROUTER_API_KEY}
          models:
            - openrouter/free
    
    routing:
      - if: contains_code
        use_local: true
        models: [codellama]
      - if: short_prompt
        use_local: true
        models: [llama3]
      - if: contains_reasoning
        providers: [groq]
    
    yolo: false  # fire all providers at once
```

### Routing Rules

| Condition | Description |
|----------|-------------|
| `contains_code` | Detects code patterns (functions, classes, imports, etc.) |
| `contains_reasoning` | Detects reasoning keywords (think step by step, explain why, etc.) |
| `short_prompt` | Prompts under 200 characters |
| `long_prompt` | Prompts over 1000 characters |
| `language:python` | Detects specific language |

### Environment Variables

Set these before running:

```bash
export KILO_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."
export OPENROUTER_API_KEY="sk-or-..."
```

### Database (Optional)

Store logs in Turso/LibSQL:

```yaml
database:
  turso_url: "libsql://your-db.turso.io"
```

Or use a local file:

```yaml
database:
  local_db: "picorouter.db"
```

---

## Profiles

### Pre-defined Profiles

PicoRouter comes with these profiles:

#### chat
Default profile for general conversation. Tries local models first.

#### coding  
Optimized for code tasks. Routes code prompts to coder models.

#### yolo
Fires all providers at once, returns first success. Maximum speed, maximum cost.

#### claw
Optimized for OpenClaw. Uses Kilo.ai as primary.

### Switching Profiles

```bash
# Run with specific profile
python picorouter.py serve --profile coding

# Or change in config
default_profile: coding
```

---

## Usage

### CLI Commands

```bash
# Start server
python picorouter.py serve
python picorouter.py serve --profile coding --port 8080

# Interactive chat
python picorouter.py chat --message "Hello"

# View logs
python picorouter.py logs
python picorouter.py logs -s  # stats only

# Generate config
python picorouter.py config --example
```

### API Endpoints

```
POST /v1/chat/completions  - Chat completions (OpenAI-compatible)
POST /v1/completions       - Text completions
GET  /v1/models            - List available models
GET  /health               - Health check
GET  /stats                - Usage statistics
GET  /logs                 - Recent requests
```

### Using with LLM Apps

#### OpenClaw
Set in your config:
```json
{
  "models": {
    "providers": {
      "kilocode": {
        "baseUrl": "http://localhost:8080/v1"
      }
    }
  }
}
```

#### VSCode / Cursor
Set in settings.json:
```json
{
  "openai": {
    "apiBaseUrl": "http://localhost:8080/v1"
  }
}
```

#### Continue (VSCode extension)
```json
{
  "apiBaseUrl": "http://localhost:8080/v1"
}
```

#### Claude Code
```bash
export OPENAI_API_KEY="dummy"  # not used
export OPENAI_API_BASE="http://localhost:8080/v1"
```

---

## Usage Dashboard

### Via API

```bash
# Get stats
curl http://localhost:8080/stats

# Response:
{
  "total_requests": 150,
  "by_provider": {"kilo": 100, "local:ollama": 50},
  "by_profile": {"coding": 120, "chat": 30},
  "total_tokens": 450000,
  "total_cost_usd": 0.12
}

# Get recent logs
curl http://localhost:8080/logs?limit=10
```

### Via CLI

```bash
# View stats
python picorouter.py logs -s

# View recent requests
python picorouter.py logs -n 20
```

### Log Format

Each request logs:
```json
{
  "timestamp": "2026-02-21T01:00:00",
  "request_id": "req_20260221010000",
  "profile": "coding",
  "provider": "kilo",
  "model": "minimax/m2.5:free",
  "routing": "seamless",
  "input_tokens": 150,
  "output_tokens": 850,
  "tokens_used": 1000,
  "duration_ms": 2500,
  "cost_usd": 0.0005,
  "status": "success"
}
```

---

## Adding Custom Providers

### Generic OpenAI-Compatible Provider

```yaml
cloud:
  providers:
    my-provider:
      base_url: "https://api.example.com/v1"
      api_key: ${MY_PROVIDER_API_KEY}
      models:
        - model-1
        - model-2
```

### Provider with Custom Headers

```yaml
cloud:
  providers:
    custom:
      base_url: "https://api.example.com/v1"
      api_key: ${API_KEY}
      headers:
        X-Custom-Header: value
      models:
        - model-name
```

---

## Cost Estimation

PicoRouter estimates costs based on token usage:

| Provider | Cost/Million Tokens |
|----------|---------------------|
| local:ollama | $0.00 |
| local:lmstudio | $0.00 |
| kilo | $0.00 (free models) |
| groq | $0.18 |
| openrouter | $0.00-50.00 (varies) |

Custom rates can be added in `picorouter.py`:

```python
COST_PER_MILLION = {
    "local:ollama": 0,
    "kilo": 0,
    "groq": 0.18,
    "your-provider": 0.50,
}
```

---

## Troubleshooting

### Local models not connecting

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Update endpoint in config
local:
  endpoint: http://localhost:11434
```

### Rate limiting

If a provider returns 429, PicoRouter automatically tries the next one. Increase provider list for redundancy.

### Check what's available

```bash
# List models from all providers
curl http://localhost:8080/v1/models
```

### Debug mode

```bash
# Run with verbose output
python picorouter.py serve 2>&1 | tee debug.log
```

---

## Files

```
picorouter/
├── picorouter.py       # Main application
├── config.example.yaml # Example configuration
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── setup.sh           # Setup helper
├── tests/             # Unit tests
│   └── test_picorouter.py
└── logs/              # Request logs (created at runtime)
    └── requests.jsonl
```

---

## License

MIT — CashlessConsumer 🦀
