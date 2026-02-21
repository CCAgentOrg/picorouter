# AGENTS.md - PicoRouter Project Guide

## Project Structure

```
picorouter/
├── picorouter/          # Core package
│   ├── __init__.py      # Version info
│   ├── __main__.py      # CLI entry point
│   ├── api.py           # HTTP server
│   ├── config.py        # Config loading (YAML, SQLite, Turso)
│   ├── keys.py          # API key management
│   ├── logger.py        # Request logging
│   ├── providers.py     # Local/cloud providers
│   ├── router.py        # Routing logic
│   ├── storage.py       # Storage backends (JSONL, SQLite, Turso)
│   └── secrets.py       # Secrets management
├── sdk/                 # Python SDK
├── tui/                 # Terminal UI
├── web/                 # Web UI
├── docs/                # Documentation
├── tests/               # Test suite
└── picorouter.py        # Wrapper entry point
```

## Build / Lint / Test Commands

```bash
# Install dependencies
make install
pip install -r requirements.txt

# Run all tests
make test
pytest tests/ -v

# Run single test
pytest tests/test_picorouter.py::TestLocalProvider::test_chat_success -v
pytest tests/ -k "test_short_prompt" -v

# Run tests with coverage
make coverage
pytest tests/ --cov=picorouter --cov-report=term-missing --cov-report=html -v

# Lint (flake8)
flake8 picorouter/ --max-line-length=100 --ignore=E501,W503 || true

# Check syntax
python -m py_compile picorouter/__main__.py picorouter/*.py

# Run server
make run
python picorouter.py serve
```

## Code Style Guidelines

### Python Version
- **Minimum:** Python 3.9+
- **CI uses:** Python 3.11
- **Type checking:** Basic mode (pyright)

### Imports
```python
# Order: stdlib → third-party → local
import os
import json
from datetime import datetime
from typing import Optional, List, Dict

import yaml
import httpx

from picorouter.providers import CloudProvider, Router
```
- Group by type with blank lines between sections
- No unused imports (flake8 enforced)
- Import local modules after third-party

### Type Hints
```python
# Use typing module types
def load(self) -> Dict:
    pass

async def chat(self, messages: list, model: str, **kwargs) -> Dict:
    pass

def validate_key(self, key: str) -> Optional[dict]:
    pass

def get_recent(self, limit: int = 50) -> List:
    pass
```
- Add type hints for function signatures
- Use `Optional[Type]` for nullable returns
- Use `List`, `Dict`, `Optional` from `typing`
- `**kwargs` does not need type hint

### Naming Conventions
```python
# Classes: PascalCase
class Router:
class CloudProvider:
class KeyManager:

# Functions/Methods: snake_case
def load_config():
async def chat():
def validate_key():

# Constants: UPPER_SNAKE_CASE
COST_PER_MILLION = {}
PROVIDER_ENDPOINTS = {}

# Private methods: underscore prefix
def _find_path():
def _init_db():
def _update_stats():
```

### Error Handling
```python
# Network errors - raise and let caller handle
async def chat(self, messages, model, **kwargs):
    response = await self.client.post(...)
    response.raise_for_status()
    return response.json()

# Parse errors - specific exception
try:
    data = json.loads(body)
except json.JSONDecodeError:
    self.send_error_json(400, "Invalid JSON")
    return

# Catch for local provider fallback
try:
    await self.local.chat(messages, model, **kwargs)
    return True
except Exception:
    return False  # Fallback to cloud

# Rate limits - catch 429
if response.status_code == 429:
    raise RateLimitError("Rate limit exceeded")
```

### Documentation
```python
"""PicoRouter - Module description.

Multi-line docstring for classes/modules with additional details.
"""

class Router:
    """Main router class."""

    def __init__(self, config: dict, profile_name: str = None):
        """Initialize router."""
        pass

    async def chat(self, messages: list, **kwargs) -> Dict:
        """Route and execute chat request."""
        pass
```
- Module docstring at top of file
- Class docstring: one-line description
- Method docstrings: one-line, no @param/@return tags

### Async/Await
```python
# Async methods for I/O operations
async def chat(self, messages: list, **kwargs) -> Dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(...)
        return response.json()

# Running async from sync code
loop = asyncio.new_event_loop()
result = loop.run_until_complete(self.router.chat(messages))
loop.close()
```
- Use `httpx.AsyncClient` for async HTTP
- Always use `async with` context manager
- Create event loop for sync→async bridging

### Testing
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock

@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {"profiles": {...}}

@pytest.mark.asyncio
async def test_chat_success(mock_config):
    """Successful local chat."""
    provider = LocalProvider({"endpoint": "http://localhost:11434"})

    with patch('picorouter.providers.httpx.AsyncClient') as mock_client:
        mock_resp = Mock()
        mock_resp.json.return_value = {"message": {"role": "assistant", "content": "Hello!"}}

        result = await provider.chat([{"role": "user", "content": "Hi"}])
        assert result["message"]["content"] == "Hello!"
```
- Use pytest with pytest-asyncio
- Mark async tests with `@pytest.mark.asyncio`
- Use `Mock` for objects, `AsyncMock` for coroutines
- Patch with full module path: `'picorouter.providers.httpx.AsyncClient'`

## Key Classes

### Router
- `chat(messages, **kwargs)` — Main entry point
- `local_chat()` — Local provider only
- `cloud_chat(provider, **kwargs)` — Cloud provider only
- `yolo_chat()` — Fire all, return first success

### CloudProvider
- Handles Kilo, Groq, OpenRouter, OpenAI, Anthropic, etc.
- Rate limit detection (429 → RateLimitError)
- API key from config or environment variables

### LocalProvider
- Ollama, LM Studio support
- Model listing via `/api/tags` endpoint
- Health checks

### KeyManager
- Multi-key support with `pico_*` prefix
- Per-key rate limits and profile restrictions
- Per-key capabilities (chat/stats/logs)
- Key validation with expiration

## Conventions

- **Python:** 3.9+, type hints where helpful (basic mode)
- **Async:** `httpx.AsyncClient` for HTTP
- **Config:** YAML file (default), with SQLite/Turso backends
- **Errors:** Catch 429 for rate limits, fallback chain
- **Logging:** JSONL (file) or SQLite, cost tracking per provider
- **API Keys:** Environment variables → .env file → Vaultwarden

## Adding Providers

1. Add endpoint to `PROVIDER_ENDPOINTS` in `providers.py`
2. Add cost to `COST_PER_MILLION` in `logger.py` or `storage.py`
3. Update `config.example.yaml` with example
4. Add test case in `tests/test_picorouter.py`

## Adding Interfaces

- **SDK:** Add to `sdk/picorouter.py`
- **TUI:** Add to `tui/picorouter_tui.py`
- **Web:** Add to `web/app.py`
- **CLI:** Add to `picorouter/__main__.py`

## Configuration Backends

- **FileBackend:** YAML file (default)
- **SQLiteConfigBackend:** Embedded SQLite
- **TursoConfigBackend:** LibSQL with sync

## Storage Backends

- **JSONLBackend:** File-based JSONL (default)
- **SQLiteBackend:** Embedded SQLite with indexes
- **TursoBackend:** LibSQL with sync

## Release

See `RELEASE.md` for checklist.
