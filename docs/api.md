# API Reference

## Endpoints

### POST /v1/chat/completions
Chat completions (OpenAI-compatible).

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "model": "llama3",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Response:**
```json
{
  "id": "chatcmpl-20260221010000",
  "object": "chat.completion",
  "created": 1705800000,
  "model": "llama3",
  "choices": [{
    "message": {"role": "assistant", "content": "Hello!"},
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```

### GET /v1/models
List available models.

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "local:llama3", "object": "model", "owned_by": "local"},
    {"id": "kilo:minimax/m2.5:free", "object": "model", "owned_by": "kilo"}
  ]
}
```

### GET /health
Health check.

**Response:**
```json
{"status": "ok"}
```

### GET /stats
Usage statistics.

**Response:**
```json
{
  "total_requests": 150,
  "by_provider": {"kilo": 100, "local:ollama": 50},
  "by_profile": {"coding": 120, "chat": 30},
  "total_tokens": 450000,
  "total_cost_usd": 0.12,
  "errors": 3
}
```

### GET /logs
Recent request logs.

**Query Parameters:**
- `limit` - Number of logs (default: 50, max: 100)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2026-02-21T01:00:00",
      "profile": "chat",
      "provider": "kilo",
      "model": "minimax/m2.5:free",
      "tokens_used": 100,
      "status": "success"
    }
  ]
}
```

## Authentication

### API Key
Pass API key in Authorization header:

```bash
curl -H "Authorization: Bearer pico_xxx" \
  http://localhost:8080/v1/chat/completions
```

### Per-Key Limits
Each key can have:
- Rate limits (requests/minute)
- Profile restrictions
- Capability restrictions (chat/stats/logs)

## Header Routing

Override routing with headers:

```bash
# Force provider
curl -H "X-PicoRouter-Provider: openai" \
  -H "X-PicoRouter-Model: gpt-4o-mini" \
  ...

# Force profile
curl -H "X-PicoRouter-Profile: coding" ...

# Force local only
curl -H "X-PicoRouter-Local: true" ...

# Enable YOLO mode
curl -H "X-PicoRouter-Yolo: true" ...
```
