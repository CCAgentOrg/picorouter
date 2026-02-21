# Docker

## Quick Start

```bash
# Pull and run
docker run -p 8080:8080 ccagentorg/picorouter

# With config
docker run -p 8080:8080 \
  -v $(pwd)/picorouter.yaml:/app/picorouter.yaml \
  -e OPENAI_API_KEY="sk-..." \
  ccagentorg/picorouter
```

---

## Image Variants

| Tag | Description | Size |
|-----|-------------|------|
| `latest` | Latest release | ~80MB |
| `v0.0.2` | Specific version | ~80MB |
| `slim` | Slimmer (coming) | ~60MB |

---

## Basic Usage

### Run with API Keys

```bash
docker run -p 8080:8080 \
  -e OPENAI_API_KEY="sk-..." \
  -e ANTHROPIC_API_KEY="sk-ant-..." \
  -e GROQ_API_KEY="gsk_..." \
  ccagentorg/picorouter
```

### Run with Config File

```bash
# Create config
cat > picorouter.yaml << 'EOF'
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
    yolo: false
default_profile: chat
server:
  host: 0.0.0.0
  port: 8080
EOF

# Run with config
docker run -p 8080:8080 \
  -v $(pwd)/picorouter.yaml:/app/picorouter.yaml \
  ccagentorg/picorouter
```

---

## Ollama Integration

### Option 1: Host Network

Use `network: host` to access host's Ollama:

```bash
docker run -p 8080:8080 \
  --network host \
  -v $(pwd)/picorouter.yaml:/app/picorouter.yaml \
  ccagentorg/picorouter
```

Config:
```yaml
local:
  provider: ollama
  endpoint: http://localhost:11434
```

### Option 2: Docker Host Gateway

```bash
docker run -p 8080:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v $(pwd)/picorouter.yaml:/app/picorouter.yaml \
  ccagentorg/picorouter
```

Config:
```yaml
local:
  provider: ollama
  endpoint: http://host.docker.internal:11434
```

### Option 3: Separate Ollama Container

```bash
# Start Ollama
docker run -d --name ollama -p 11434:11434 ollama/ollama

# Start PicoRouter
docker run -p 8080:8080 \
  --link ollama \
  -v $(pwd)/picorouter.yaml:/app/picorouter.yaml \
  ccagentorg/picorouter
```

Config:
```yaml
local:
  provider: ollama
  endpoint: http://ollama:11434
```

---

## Docker Compose (Recommended)

### Basic

```yaml
version: '3.8'
services:
  picorouter:
    image: ccagentorg/picorouter
    ports:
      - "8080:8080"
    volumes:
      - ./picorouter.yaml:/app/picorouter.yaml
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    restart: unless-stopped
```

### With Ollama

```yaml
version: '3.8'
services:
  picorouter:
    image: ccagentorg/picorouter
    ports:
      - "8080:8080"
    volumes:
      - ./picorouter.yaml:/app/picorouter.yaml
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - ollama
    restart: unless-stopped

  ollama:
    image: ollama/ollama
    volumes:
      - ollama:/root/.ollama
    restart: unless-stopped

volumes:
  ollama:
```

Run:
```bash
docker-compose up -d
```

---

## Production

### Health Check

```yaml
services:
  picorouter:
    image: ccagentorg/picorouter
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Resource Limits

```yaml
services:
  picorouter:
    image: ccagentorg/picorouter
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
```

### Nginx Reverse Proxy

```yaml
# nginx.conf
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://picorouter:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `GROQ_API_KEY` | No | Groq API key |
| `KILO_API_KEY` | No | Kilo API key |
| `GOOGLE_API_KEY` | No | Google AI API key |
| `MISTRAL_API_KEY` | No | Mistral API key |
| `COHERE_API_KEY` | No | Cohere API key |
| `PICOROUTER_API_KEY` | No | PicoRouter auth key |
| `PICOROUTER_SECRETS_BACKEND` | No | env/dotenv/vaultwarden |
| `PICOROUTER_CONFIG_BACKEND` | No | file/sqlite/turso |

---

## Build Locally

```bash
# Clone
git clone https://github.com/CCAgentOrg/picorouter
cd picorouter

# Build
docker build -t picorouter .

# Run
docker run -p 8080:8080 picorouter
```

---

## Troubleshooting

### Can't Connect to Ollama

```bash
# Check Ollama is running
docker logs ollama

# Check network
docker exec picorouter curl http://host.docker.internal:11434/api/tags
```

### Port Already in Use

```bash
# Use different port
docker run -p 8081:8080 ccagentorg/picorouter
```

### View Logs

```bash
docker logs -f picorouter
```
