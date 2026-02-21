# Changelog

All notable changes to PicoRouter will be documented in this file.

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
