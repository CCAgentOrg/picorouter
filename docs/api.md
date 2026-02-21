# PicoRouter API

## Base URL
```
http://localhost:8080/v1
```

## Authentication

Pass API key in header:
```
Authorization: Bearer your_api_key
```

---

## Endpoints

### Chat Completions
```
POST /v1/chat/completions
```

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
  "id": "chatcmpl-20250221120000",
  "object": "chat.completion",
  "created": 1708500000,
  "model": "llama3",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

### List Models
```
GET /v1/models
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "local:llama3", "object": "model", "created": 0, "owned_by": "local"},
    {"id": "kilo:minimax/m2.5:free", "object": "model", "created": 0, "owned_by": "kilo"}
  ]
}
```

### Health Check
```
GET /health
```

**Response:** `{"status": "ok"}`

### Stats
```
GET /stats
```
Requires authentication.

**Response:**
```json
{
  "total_requests": 100,
  "total_tokens": 50000,
  "total_cost_usd": 0.05,
  "errors": 2
}
```

### Logs
```
GET /logs?limit=50
```
Requires authentication.

---

## Streaming

Set `stream: true` in request:
```json
{
  "messages": [{"role": "user", "content": "Tell a story"}],
  "stream": true
}
```

Returns Server-Sent Events (SSE).
