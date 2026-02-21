# AGENTS.md - PicoRouter Project Guide

## Project Structure

```
picorouter/
├── picorouter/          # Core package
│   ├── __init__.py      # Version info
│   ├── __main__.py      # CLI entry point
│   ├── api.py           # HTTP server
│   ├── config.py        # Config loading
│   ├── keys.py          # API key management
│   ├── logger.py        # Request logging
│   ├── providers.py     # Local/cloud providers
│   └── router.py        # Routing logic
├── sdk/                 # Python SDK
├── tui/                 # Terminal UI
├── web/                 # Web UI
├── docs/                # Documentation
├── tests/               # Test suite
└── picorouter.py        # Wrapper entry point
```

## Key Classes

### Router
- `chat(messages, **kwargs)` — Main entry point
- `local_chat()` — Local provider
- `cloud_chat()` — Cloud provider  
- `yolo_chat()` — Fire all, return first

### CloudProvider
- Handles Kilo, Groq, OpenRouter
- Rate limit handling
- Error wrapping

### LocalProvider
- Ollama / LM Studio support
- Model listing
- Health checks

### KeyManager
- Multi-key support
- Per-key capabilities
- Rate limits
- Expiration

## Conventions

- **Python**: 3.11+, type hints where helpful
- **Async**: `httpx.AsyncClient` for HTTP
- **Config**: YAML, environment variable fallbacks
- **Errors**: Catch 429 for rate limits, fallback chain
- **Logging**: JSONL + in-memory stats

## Adding Providers

1. Add endpoint to `PROVIDER_ENDPOINTS` in `providers.py`
2. Add cost to `COST_PER_MILLION` in `logger.py`
3. Update `config.example.yaml` with example

## Adding Interfaces

- **SDK**: Add to `sdk/picorouter.py`
- **TUI**: Add to `tui/picorouter_tui.py`
- **Web**: Add to `web/app.py`

## Testing

```bash
make test
make coverage
```

## Release

See `RELEASE.md` for checklist.
