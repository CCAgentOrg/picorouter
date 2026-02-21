# PicoRouter Docker

Run PicoRouter in containers.

## Quick Start

```bash
# Pull and run
docker run -d \
  -p 8080:8080 \
  -v ./picorouter.yaml:/app/picorouter.yaml:ro \
  -e KILO_API_KEY=sk-xxx \
  -e GROQ_API_KEY=gsk_xxx \
  --name picorouter \
  ccagentorg/picorouter
```

---

## Build

```bash
# Build image
docker build -t picorouter .

# Or pull from GitHub Container Registry
docker pull ghcr.io/ccagentorg/picorouter:latest
```

---

## Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Services

### API Server
```yaml
picorouter:
  build: .
  ports:
    - "8080:8080"
  volumes:
    - ./picorouter.yaml:/app/picorouter.yaml
  environment:
    - KILO_API_KEY=${KILO_API_KEY}
```

### Web UI
```yaml
web:
  build: .
  ports:
    - "5000:5000"
  command: python web/app.py
  environment:
    - PICOROUTER_URL=http://picorouter:8080
```

### TUI
```yaml
tui:
  build: .
  stdin_open: true
  tty: true
  command: python tui/picorouter_tui.py
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `KILO_API_KEY` | Kilo.ai API key |
| `GROQ_API_KEY` | Groq API key |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `PICOROUTER_KEY` | PicoRouter API key |

---

## Volumes

| Path | Description |
|------|-------------|
| `/app/picorouter.yaml` | Config file (mount read-only) |
| `/app/logs` | Request logs |

---

## Production

```yaml
version: '3.8'

services:
  picorouter:
    image: ccagentorg/picorouter
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./picorouter.yaml:/app/picorouter.yaml:ro
    environment:
      - KILO_API_KEY=${KILO_API_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Alpine Size

The image is based on Alpine Linux for minimal size (~50MB).
