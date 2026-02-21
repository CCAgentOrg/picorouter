# PicoRouter — Feature Comparison

## LLM Router Landscape

| Router | Type | Local | Self-Hosted | Content Routing | Multi-Key | Target |
|--------|------|-------|-------------|-----------------|-----------|--------|
| **OpenRouter.ai** | Cloud | ❌ | ❌ | ❌ | ❌ | General |
| **Portkey.ai** | Cloud | ❌ | ❌ | ✅ | ✅ | Enterprise |
| **LiteLLM** | Open Source | ✅ | ✅ | ❌ | ❌ | Devs |
| **Higress** | Open Source | ✅ | ✅ | ❌ | ❌ | Cloud Native |
| **APIAgent** | Open Source | ✅ | ✅ | ✅ | ✅ | Developers |
| **PicoRouter** | Open Source | ✅ | ✅ | ✅ | ✅ | Embedded/Personal |

---

## PicoRouter vs Competitors

| Feature | OpenRouter | Portkey | LiteLLM | PicoRouter |
|---------|-----------|---------|---------|------------|
| **Core** | | | | |
| Local models (Ollama) | ❌ | ❌ | ✅ | ✅ |
| Cloud providers | 100+ | 100+ | 100+ | 15+ |
| Local-first routing | ❌ | ❌ | ⚠️ | ✅ |
| **Routing** | | | | |
| Automatic failover | ✅ | ✅ | ✅ | ✅ |
| Content-aware | ❌ | ✅ | ❌ | ✅ |
| Profiles | ❌ | ❌ | ❌ | ✅ |
| YOLO mode | ❌ | ❌ | ❌ | ✅ |
| **Auth** | | | | |
| Multi-key | ❌ | ✅ | ❌ | ✅ |
| Per-key limits | ❌ | ✅ | ❌ | ✅ |
| Per-key profiles | ❌ | ✅ | ❌ | ✅ |
| **Deploy** | | | | |
| Self-hosted | ❌ | ❌ | ✅ | ✅ |
| Docker | ❌ | ❌ | ✅ | ✅ |
| OpenWrt/embedded | ❌ | ❌ | ❌ | ✅ |
| Minimal deps | ❌ | ❌ | ⚠️ | ✅ |
| **Cost** | | | | |
| Service markup | 5% | 10% | $0 | $0 |

---

## Feature Deep Dive

### OpenRouter.ai
- **Type:** Cloud service
- **Pros:** 100+ models, unified billing
- **Cons:** No local, 5% markup, no self-hosting

### Portkey.ai  
- **Type:** Cloud service
- **Pros:** Observability, AI gateway, 100+ providers
- **Cons:** 10% markup, no local models, enterprise-focused

### LiteLLM
- **Type:** Open source
- **Pros:** 100+ providers, Kubernetes ingress, OpenAI-compatible
- **Cons:** Heavy (FastAPI), no content-aware routing, basic auth

### PicoRouter
- **Type:** Open source (personal/embedded)
- **Pros:** 
  - Local-first (Ollama, LM Studio)
  - Minimal (Python 3.9+, no FastAPI)
  - Content-aware routing (code/reasoning/length)
  - YOLO mode (fire all, take first)
  - Multi-key with profiles
  - Runs on Raspberry Pi, OpenWrt
- **Cons:** Fewer cloud providers (15 vs 100+), no built-in observability

---

## When to Use What

| Use Case | Choice |
|----------|--------|
| Access 100+ cloud models | OpenRouter |
| Enterprise gateway + observability | Portkey |
| Kubernetes AI gateway | LiteLLM |
| **Local-first + privacy** | **PicoRouter** |
| **Embedded/IoT/edge** | **PicoRouter** |
| **Content-aware routing** | **PicoRouter** |
| **Free self-hosted** | **PicoRouter** |
| **Simple personal router** | **PicoRouter** |

---

## Migration

### From OpenRouter
```python
# OpenRouter
client = OpenAI(base_url="https://openrouter.ai/v1", api_key="sk-or-...")

# PicoRouter
client = OpenAI(base_url="http://localhost:8080/v1", api_key="pico_xxx")
```

### From LiteLLM
```python
# LiteLLM
litellm.router = litellm.Router(model_list=[...])

# PicoRouter
# config.yaml handles everything
```

---

## PicoRouter Philosophy

**"Pico" = Tiny, focused, efficient**

- **<50MB memory** — Runs on edge devices
- **Python 3.9+** — No 3.11 requirement
- **Plain http.server** — No FastAPI bloat
- **Local-first** — Free, unlimited, private
- **Content-aware** — Routes based on prompt analysis
- **YOLO mode** — Fire all, fastest wins
