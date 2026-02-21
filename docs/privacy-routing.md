# Privacy & ZDR Routing Design

**Date:** 2026-02-21  
**Status:** Draft - For Discussion

---

## Overview

Route privacy-sensitive requests through Zero Data Retention (ZDR) providers and models automatically.

---

## Goals

1. Auto-detect ZDR capability where possible (OpenRouter API)
2. Detailed pricing (input/output/cache per 1M tokens)
3. Keep `picorouter/privacy` as the virtual provider name
4. Extensible: tag any model as privacy-friendly

---

## Model Metadata Schema

### Config Format

```yaml
profiles:
  chat:
    cloud:
      providers:
        openrouter:
          models:
            # Auto-populated from OpenRouter API
            - name: anthropic/claude-3-opus-20240229
              zdr: true
              price_input: 15.00
              price_output: 75.00
              price_cache: 3.00
            - name: meta-llama/llama-3-70b-instruct
              zdr: false
              price_input: 0.80
              price_output: 0.90
              price_cache: 0.10
            # Manual override
            - name: custom/model
              zdr: true
              price_input: 0
              price_output: 0

        kilo:
          models:
            - name: minimax/m2.5:free
              zdr: false
              price_input: 0
              price_output: 0
```

### Provider ZDR Support

| Provider | Auto-Detect ZDR | Method |
|----------|----------------|--------|
| OpenRouter | ✅ Yes | `&privacy=true` flag + API response |
| Anthropic | ⚠️ Partial | Enterprise flag in API |
| Groq | ❌ No | Manual config |
| Kilo | ❌ No | Manual config |

---

## Implementation Plan

### Phase 1: OpenRouter API Integration

1. Fetch models from OpenRouter API (`https://openrouter.ai/api/v1/models`)
2. Parse `privacy` field from each model
3. Parse pricing: `price_per_1k_input`, `price_per_1k_output`, `price_per_1k_cache`
4. Cache locally in `~/.picorouter/cache/openrouter_models.json`

### Phase 2: Privacy Virtual Provider

Update `VirtualProvider._route_local_only()` to:

1. **Priority 1:** Local providers (Ollama, LM Studio) — always ZDR
2. **Priority 2:** ZDR-tagged cloud models from configured providers
3. **Priority 3:** ZDR-capable providers with privacy flag

```python
async def _route_privacy(self, messages, router, **kwargs):
    # 1. Try local first
    for model in router.profile.get("local", {}).get("models", []):
        if await router.try_local(messages, model, **kwargs):
            return await router.local_chat(messages, model, **kwargs)
    
    # 2. Try ZDR-tagged models from cloud providers
    for prov_name, prov in router.cloud.items():
        for model_cfg in prov.models:
            if model_cfg.get("zdr", False):
                try:
                    return await prov.chat(messages, model_cfg.name, **kwargs)
                except RateLimitError:
                    continue
    
    # 3. Try ZDR via OpenRouter privacy flag
    if "openrouter" in router.cloud:
        # Add &privacy=true to request
        ...
    
    raise Exception("No privacy-compliant providers available")
```

### Phase 3: Provider Metadata

Extend `Provider` class to support model metadata:

```python
class CloudProvider:
    def __init__(self, name, config):
        ...
        self.models = []  # List of model configs with metadata
    
    def get_zdr_models(self):
        return [m for m in self.models if m.get("zdr", False)]
```

---

## CLI Commands

```bash
# Refresh OpenRouter model cache (auto-detect ZDR + prices)
python picorouter.py models sync --provider openrouter

# List models with ZDR flag
python picorouter.py models list --zdr

# Show pricing for a model
python picorouter.py models pricing anthropic/claude-3-opus-20240229
```

---

## OpenRouter API Response Format

Expected fields from `GET /api/v1/models`:

```json
{
  "id": "anthropic/claude-3-opus-20240229",
  "name": "Anthropic: Claude 3 Opus",
  "pricing": {
    "prompt": "15.00",
    "completion": "75.00",
    "image": "0.00",
    "cached-prompt": "3.00"
  },
  "privacy": {
    "zero_retention": true,
    "public_streaming": false
  },
  ...
}
```

---

## Open Questions

1. **Refresh frequency:** How often to auto-sync model data? (daily/weekly)
2. **Fallback:** If no ZDR model available, fail or degrade to non-ZDR?
3. **Price threshold:** Default max price for privacy route?
4. **Cache invalidation:** TTL for OpenRouter model cache?

---

## Related

- LATER.md: Android/Termux support
- FEATURES.md: Provider comparison
