# PicoRouter Features

## Core Features

### Local-First Routing
- Connects to local models (Ollama, LM Studio)
- Always tries local first — free, unlimited, private
- Falls back to cloud when local unavailable

### Cloud Provider Support
- **Kilo.ai** — Free models available
- **Groq** — Fast inference
- **OpenRouter** — Aggregates many providers
- **Any OpenAI-compatible API** — Add your own

### Intelligent Routing
Automatically routes prompts based on content analysis:

| Feature | Detection |
|---------|----------|
| `contains_code` | Functions, classes, imports, code blocks |
| `contains_reasoning` | "think step by step", "explain why" |
| `short_prompt` | Under 200 characters |
| `long_prompt` | Over 1000 characters |
| `language:python` | Specific language detection |

### Profiles
Pre-configured routing profiles:

- **chat** — General conversation
- **coding** — Code-focused tasks  
- **yolo** — Fire all providers, return first success
- **claw** — Optimized for OpenClaw

### YOLO Mode
When enabled, fires all providers simultaneously and returns the first response. Maximum speed, maximum cost.

---

## API & Integration

### OpenAI-Compatible API
Standard OpenAI endpoints:

```
POST /v1/chat/completions
POST /v1/completions
GET  /v1/models
```

Works with any OpenAI-compatible client.

### App Integrations
Tested with:

- **OpenClaw** — Set baseUrl to `http://localhost:8080/v1`
- **VSCode / Cursor** — Configure OpenAI API base
- **Continue** — VSCode extension
- **Claude Code** — Via OPENAI_API_BASE env var
- **Any LLM app** — Point to localhost:8080

---

## Usage Tracking

### Request Logging
Logs every request with:

- Timestamp
- Provider used
- Model used
- Tokens (input/output/total)
- Duration (ms)
- Cost (USD estimate)
- Status (success/error)

### Dashboard

**API:**
```
GET /stats   → Usage statistics
GET /logs   → Recent requests
```

**CLI:**
```bash
python picorouter.py logs -s  # stats
python picorouter.py logs -n 20 # recent
```

### Cost Estimation
Built-in cost tracking per provider:

| Provider | Cost/M Tokens |
|----------|--------------|
| local:ollama | $0 |
| local:lmstudio | $0 |
| kilo (free) | $0 |
| groq | $0.18 |
| openrouter | varies |

---

## Database

### Turso/LibSQL Support
Store logs in Turso cloud database:

```yaml
database:
  turso_url: "libsql://your-db.turso.io"
```

### JSONL Fallback
Default: logs to `logs/requests.jsonl`

---

## CLI Tools

| Command | Description |
|---------|-------------|
| `serve` | Start API server |
| `chat` | Interactive chat |
| `config` | Generate config |
| `logs` | View usage logs |

### Server Options
```bash
python picorouter.py serve --profile coding --port 8080 --host 0.0.0.0
```

---

## Configuration

### Config File
`picorouter.yaml` — Full control over:

- Local model endpoints
- Cloud provider credentials
- Routing rules
- Profiles
- Database settings

### Environment Variables
```bash
KILO_API_KEY=sk-...
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-...
```

---

## Technical Specs

### Dependencies
- Python 3.11+
- pyyaml
- httpx

### Memory Usage
<50MB — Lean and minimal

### Architecture
Single-file application (`picorouter.py`) with modular classes

---

## Roadmap

### Coming Soon
- [ ] Streaming support
- [ ] Request queuing
- [ ] Response caching
- [ ] More providers
- [ ] Web UI dashboard
- [ ] Metrics export (Prometheus)

### Considered
- [ ] Plugin system
- [ ] Multi-user support
- [ ] API key rotation
- [ ] Usage alerts
