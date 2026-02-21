# PicoRouter vs OpenRouter — Feature Comparison

| Feature | OpenRouter.ai | PicoRouter | Notes |
|---------|---------------|------------|-------|
| **Core** | | | |
| Local models | ❌ | ✅ | Ollama, LM Studio |
| Cloud providers | 100+ | 3 (Kilo, Groq, OpenRouter) | Extensible |
| Local-first routing | ❌ | ✅ | Free, unlimited, private |
| **Routing** | | | |
| Automatic failover | ✅ | ✅ | On 429/error |
| Content-aware routing | ❌ | ✅ | Code/reasoning detection |
| Profiles | ❌ | ✅ | chat, coding, yolo, custom |
| YOLO mode (fire all) | ❌ | ✅ | Max speed, all providers |
| **API** | | | |
| OpenAI-compatible | ✅ | ✅ | `/v1/chat/completions` |
| Streaming | ✅ | ⚠️ | Basic |
| Custom endpoints | ❌ | ⚠️ | Via config |
| **Authentication** | | | |
| API keys | ✅ | ✅ | Multiple keys |
| Per-key limits | ❌ | ✅ | Rate limits per key |
| Per-key profiles | ❌ | ✅ | Profile restrictions |
| Per-key capabilities | ❌ | ✅ | chat/stats/logs control |
| Key expiration | ❌ | ✅ | Auto-expiry |
| **Analytics** | | | |
| Usage tracking | ✅ | ✅ | Tokens, cost |
| Request logs | ✅ | ✅ | JSONL |
| Cost by model | ✅ | ⚠️ | Basic |
| **Deployment** | | | |
| Self-hosted | ❌ | ✅ | Run anywhere |
| Docker | ❌ | ✅ | Alpine image |
| OpenWrt/embedded | ❌ | ✅ | Python 3.9+, minimal deps |
| **Interface** | | | |
| Web UI | ✅ | ⚠️ | Separate PWA repo |
| CLI | ❌ | ✅ | serve, chat, logs |
| SDK | ✅ | ⚠️ | Simple Python |
| **Pricing** | | | |
| Service cost | 5% markup | $0 | Self-hosted |
| Free models | ✅ | ✅ | Kilo, Groq, Ollama |

---

## Summary

| Use Case | Recommendation |
|----------|---------------|
| Want all 100+ models | OpenRouter.ai |
| Want local + privacy | PicoRouter |
| Want free + self-hosted | PicoRouter |
| Want embedded/IoT | PicoRouter |
| Want content-aware routing | PicoRouter |
| Want per-key controls | PicoRouter |

---

## Feature Details

### OpenRouter.ai Strengths

- **Massive model selection** — 100+ models from Anthropic, OpenAI, Meta, etc.
- **Unified billing** — One bill for all providers
- **Built-in credits** — No need to manage multiple accounts
- **Production-ready** — High availability, SLAs

### PicoRouter Strengths

- **Local-first** — Free, unlimited, private with Ollama
- **Self-hosted** — No cloud dependency
- **Embedded** — Runs on Raspberry Pi, OpenWrt, etc.
- **Content-aware** — Auto-detects code, reasoning, prompt length
- **Multi-key** — Granular API key management
- **No markup** — 100% of API costs go to providers

---

## Migration from OpenRouter

If switching from OpenRouter to PicoRouter:

```python
# Before (OpenRouter)
client = OpenAI(
    base_url="https://openrouter.ai/v1",
    api_key="sk-or-..."
)

# After (PicoRouter)
client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="pico_xxx"  # Optional
)
```

### Equivalent Models

| OpenRouter | PicoRouter |
|------------|------------|
| openai/gpt-3.5-turbo | Use cloud provider |
| anthropic/claude-3-haiku | Use cloud provider |
| meta-llama/llama-3-70b | local:llama3 |
| mistralai/mixtral-8x7b | local:mistral |

---

## Conclusion

**OpenRouter.ai** = Best for accessing many cloud models with unified billing.

**PicoRouter** = Best for local-first, privacy, self-hosting, embedded, or cost-sensitive use cases.

PicoRouter can complement OpenRouter — use local for simple tasks, fall back to OpenRouter for specialized models.
