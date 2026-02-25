# Changelog

All notable changes to PicoRouter will be documented in this file.

## [0.0.3] - 2026-02-25

### Added
- **Budget control per API key** - Set daily, monthly, or lifetime budget limits
- **Explicit provider:model routing** - Use "kilo:minimax/m2.5:free" syntax
- **Auto-fallback between providers** - If model exists on multiple providers, try each
- **Header routing fully implemented** - X-PicoRouter-* headers for all routing controls
- **CLI budget flags** - `--budget` and `--budget-period` for key management
- **Web UI budget fields** - Budget and period inputs in settings page
- **Health monitoring** - /health endpoint, status CLI, auto-exclude down providers
- **Request logging** - logs/requests.jsonl with status and cost tracking
- **Privacy routing design** - ZDR (Zero Data Retention) model routing

### Fixed
- **Critical syntax error** in storage.py (TursoBackend initialization)
- **Duplicate code** in __main__.py (models parser defined twice)
- **Empty exception blocks** - Added proper exception handling with logging in:
  - config.py (SQLite config JSON parsing)
  - storage.py (JSONL log file parsing)
  - api.py (query parameter parsing)
- **Missing VaultwardenBackend.delete()** - Implemented secret deletion via bw CLI
- **Rate limiter thread-safety** - Added threading.Lock to prevent race conditions
- **Missing imports** - Restored BaseHTTPRequestHandler, Router, and KeyManager imports in api.py
- **Fragile models.dev parsing** - Improved with multiple strategies, better error handling
- **YOLO mode test** - Fixed incorrect await on task.result()
- **Test isolation** - Fixed logger tests to use relative assertions
- **API handler tests** - Fixed handler instantiation for Python 3.12

### Security
- **API input validation** - Added comprehensive validation for /v1/chat/completions:
  - Message structure validation (role, content fields)
  - Role validation (system, user, assistant only)
  - Content length limits (100k characters per message)
  - Numeric parameter validation (temperature: 0-2.0, top_p: 0-1.0, max_tokens: 1-32000)
  - Model parameter sanitization
  - Type checking for all inputs

### Improved
- Better error logging for debugging
- Thread-safe rate limiting for production use
- Complete Vaultwarden secrets backend implementation
- Robust models.dev data parsing with fallback strategies
- Test coverage improvements

---

## [0.0.1] - 2026-02-21

### Added
- **Local-first routing**: Ollama, LM Studio — free, unlimited, private
- **15+ cloud providers**: OpenAI, Anthropic, Google, Mistral, Cohere, Together, DeepInfra, Fireworks, Replicate, Azure, Kilo, Groq, OpenRouter
- **Intelligent routing**: Content-aware (code, reasoning, short/long prompts)
- **Virtual providers**: picorouter/privacy, free, fast, sota
- **Header routing**: X-PicoRouter-* headers for runtime control
- **Multi-key auth**: Per-key rate limits, profiles, capabilities
- **Storage backends**: JSONL, SQLite, Turso/LibSQL
- **Config backends**: File (YAML), SQLite, Turso
- **Secrets backends**: Env, .env, Vaultwarden, Encrypted file
- **Tailscale support**: --host tailscale, --show-ips
- **Model discovery**: CLI for models.dev integration
- **OpenAI-compatible API**: /v1/chat/completions
- **Docker**: Alpine ~50MB image

### Features
- Seamless failover (429/error → next provider)
- YOLO mode (fire all, return first)
- Usage tracking (tokens, cost, logs)
- Profiles (chat, coding, yolo, custom)

### CLI Commands
- `serve` — Start API server
- `chat` — Interactive chat
- `logs` — View/request stats
- `key` — API key management
- `secrets` — Provider key management
- `models` — models.dev discovery
- `config` — Config generation

---

## [0.0.0] - 2026-02-20 (Initial)

### Added
- Basic router with local + cloud providers
- Simple config file
- JSONL logging
