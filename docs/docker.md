# Docker

## Quick Start

```bash
docker run -p 8080:8080 ccagentorg/picorouter
```

## With Config

```bash
docker run -p 8080:8080 \
  -v $(pwd)/picorouter.yaml:/app/picorouter.yaml \
  -e OPENAI_API_KEY="sk-..." \
  -e ANTHROPIC_API_KEY="sk-ant-..." \
  ccagentorg/picorouter
```

## With Ollama

```bash
docker run -p 8080:8080 \
  -v $(pwd)/picorouter.yaml:/app/picorouter.yaml \
  --add-host=host.docker.internal:host-gateway \
  ccagentorg/picorouter
```

Update config:
```yaml
local:
  provider: ollama
  endpoint: http://host.docker.internal:11434
  models: [llama3]
```

## Docker Compose

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

## Build Locally

```bash
docker build -t picorouter .
docker run -p 8080:8080 picorouter
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GROQ_API_KEY` | Groq API key |
| `KILO_API_KEY` | Kilo API key |
| `PICOROUTER_API_KEY` | PicoRouter auth key |
| `PICOROUTER_SECRETS_BACKEND` | Secrets backend (env/dotenv/vaultwarden) |
