# PicoRouter SDK

Python client library for PicoRouter.

## Install

```bash
pip install picorouter
```

Or from source:
```bash
pip install -e ./sdk
```

---

## Quick Start

```python
from picorouter import PicoRouter

# Connect to local PicoRouter
client = PicoRouter("http://localhost:8080")

# Simple chat
response = client.chat_simple("Hello!")

# Or with more control
response = client.chat(
    messages=[
        {"role": "user", "content": "Write a Python function"}
    ],
    temperature=0.7,
    max_tokens=1000
)

print(response["choices"][0]["message"]["content"])
```

---

## API Reference

### PicoRouter

```python
client = PicoRouter(
    base_url="http://localhost:8080",  # PicoRouter URL
    api_key="pico_xxx",               # Optional API key
    timeout=120                        # Request timeout
)
```

#### Methods

**chat(messages, model=None, profile=None, temperature=0.7, max_tokens=None, **kwargs)**
- `messages`: List of message dicts `[{"role": "user", "content": "..."}]`
- `model`: Optional model override
- `profile`: Optional profile to use
- `temperature`: Sampling temperature (0-2)
- `max_tokens`: Max tokens to generate
- Returns: OpenAI-compatible response dict

**chat_simple(message, **kwargs)**
- Simple single-message chat
- Returns: Assistant's response text

**models()**
- List available models
- Returns: List of model dicts

**stats()**
- Get usage statistics
- Returns: Stats dict

**logs(limit=50)**
- Get recent logs
- Returns: List of log entries

**health()**
- Check server health
- Returns: Boolean

---

## Examples

### With API Key

```python
client = PicoRouter(
    base_url="http://localhost:8080",
    api_key="pico_xxx"
)
```

### Streaming

```python
response = client.chat(
    messages=[{"role": "user", "content": "Count to 5"}],
    stream=True
)

for chunk in response.iter_lines():
    print(chunk)
```

### Async

```python
import asyncio
from picorouter import PicoRouter

async def main():
    client = PicoRouter("http://localhost:8080")
    # Note: SDK uses sync requests by default
    # Use aiohttp for async

asyncio.run(main())
```

---

## Convenience Function

```python
from picorouter import chat

# One-liner
result = chat("Hello!", base_url="http://localhost:8080")
```

---

## Error Handling

```python
from picorouter import PicoRouter
import requests

try:
    client = PicoRouter("http://localhost:8080")
    response = client.chat_simple("Hello")
except requests.exceptions.ConnectionError:
    print("Cannot connect to PicoRouter")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e}")
```
