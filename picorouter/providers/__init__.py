"""PicoRouter - Provider registry and base classes.

Easy to add new providers:
1. Add endpoint to PROVIDERS dict
2. Create provider class if needed (for custom handling)
"""

import asyncio
import os
import httpx
from typing import Optional, List, Dict
from picorouter.secrets import SecretsManager, PROVIDER_KEYS

_secrets = SecretsManager()


# =============================================================================
# Provider Registry
# =============================================================================

# All supported providers
# Format: "name": {"endpoint": "...", "default_models": [...], "class": ProviderClass}
PROVIDERS = {
    # Local
    "ollama": {
        "endpoint": None,  # Handled by LocalProvider
        "class": "local",
    },
    "lmstudio": {
        "endpoint": None,  # Handled by LocalProvider
        "class": "local",
    },
    # Free / Low-cost
    "kilo": {
        "endpoint": "https://api.kilo.ai/api/openrouter/",
        "default_models": ["minimax/m2.5:free"],
    },
    "groq": {
        "endpoint": "https://api.groq.com/openai/",
        "default_models": ["llama-3.1-70b-versatile"],
    },
    "openrouter": {
        "endpoint": "https://openrouter.ai/api/v1/",
        "default_models": ["openrouter/free"],
    },
    # Major providers
    "openai": {
        "endpoint": "https://api.openai.com/v1/",
        "default_models": ["gpt-4o-mini"],
    },
    "anthropic": {
        "endpoint": "https://api.anthropic.com/v1/",
        "default_models": ["claude-3-haiku-20240307"],
        "api_style": "anthropic",
    },
    "google": {
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/",
        "default_models": ["gemini-1.5-flash"],
        "api_style": "google",
    },
    "mistral": {
        "endpoint": "https://api.mistral.ai/v1/",
        "default_models": ["mistral-small-latest"],
    },
    "cohere": {
        "endpoint": "https://api.cohere.ai/v1/",
        "default_models": ["command-r-plus"],
    },
    "ai21": {
        "endpoint": "https://api.ai21.com/v1/",
        "default_models": ["jamba-1.5-mini"],
    },
    # Aggregators
    "together": {
        "endpoint": "https://api.together.ai/v1/",
        "default_models": ["meta-llama/Llama-3-70b-chat-hf"],
    },
    "deepinfra": {
        "endpoint": "https://api.deepinfra.com/v1/openai/v1/",
        "default_models": ["meta-llama/Llama-3-70b-instruct"],
    },
    "fireworks": {
        "endpoint": "https://api.fireworks.ai/v1/",
        "default_models": ["llama-v3-70b-instruct"],
    },
    "anyscale": {
        "endpoint": "https://api.endpoints.anyscale.com/v1/",
        "default_models": ["meta-llama/Llama-3-70b-Instruct"],
    },
    "replicate": {
        "endpoint": "https://api.replicate.com/v1/",
        "default_models": ["llama-3-70b-instruct"],
        "api_style": "replicate",
    },
    "azure": {
        "endpoint": "https://{resource}.openai.azure.com/openai/deployments/{deployment}/",
        "default_models": [],
        "api_style": "azure",
    },
    # Virtual providers
    "picorouter/privacy": {"class": "virtual", "route": "local_only"},
    "picorouter/free": {"class": "virtual", "route": "free_providers"},
    "picorouter/fast": {"class": "virtual", "route": "fast_providers"},
    "picorouter/sota": {"class": "virtual", "route": "sota_providers"},
}


def get_provider_info(name: str) -> Optional[dict]:
    """Get provider info by name."""
    return PROVIDERS.get(name.lower())


def list_providers() -> List:
    """List all available provider names."""
    return list(PROVIDERS.keys())


def register_provider(name: str, endpoint: str, default_models: list = None, **kwargs):
    """Register a new provider.

    Example:
        register_provider(
            "myprovider",
            "https://api.myprovider.com/v1/",
            ["my-model"]
        )
    """
    PROVIDERS[name.lower()] = {
        "endpoint": endpoint,
        "default_models": default_models or [],
        **kwargs,
    }


# =============================================================================
# Base Provider
# =============================================================================


class RateLimitError(Exception):
    """Rate limit exceeded."""

    pass


class BaseProvider:
    """Base provider class."""

    name = "base"

    def __init__(self, config: dict):
        self.config = config
        self.endpoint = config.get("endpoint")
        self.api_key = config.get("api_key")
        self.models = config.get("models", [])

    async def chat(self, messages: list, model: str = None, **kwargs) -> Dict:
        raise NotImplementedError

    async def list_models(self) -> List:
        return self.models


# =============================================================================
# Local Provider (Ollama, LM Studio)
# =============================================================================


class LocalProvider(BaseProvider):
    """Local model provider."""

    name = "local"

    def __init__(self, config: dict):
        provider = config.get("provider", "ollama")

        if provider == "lmstudio":
            self.endpoint = config.get("endpoint", "http://localhost:1234").rstrip("/")
        else:
            self.endpoint = config.get("endpoint", "http://localhost:11434").rstrip("/")

        self.provider = provider
        self.models = config.get("models", ["llama3"])

    async def chat(self, messages: list, model: str = None, **kwargs) -> Dict:
        model = model or self.models[0]

        if self.provider == "lmstudio":
            url = f"{self.endpoint}/v1/chat/completions"
            payload = {"model": model, "messages": messages, **kwargs}
        else:
            url = f"{self.endpoint}/api/chat"
            payload = {"model": model, "messages": messages, "stream": False, **kwargs}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def list_models(self) -> List:
        if self.provider == "lmstudio":
            url = f"{self.endpoint}/v1/models"
        else:
            url = f"{self.endpoint}/api/tags"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                if self.provider == "lmstudio":
                    return [m.get("id") for m in data.get("data", [])]
                else:
                    return [m.get("name") for m in data.get("models", [])]
        except Exception:
            return []


# =============================================================================
# Cloud Provider (OpenAI-compatible)
# =============================================================================


class CloudProvider(BaseProvider):
    """Cloud API provider (OpenAI-compatible)."""

    name = "cloud"

    def __init__(self, name: str, config: dict):
        self.name = name
        info = PROVIDERS.get(name, {})

        self.endpoint = config.get("base_url") or info.get("endpoint") or ""
        self.api_key = config.get("api_key") or _secrets.get_provider_key(name)
        self.models = config.get("models", []) or info.get("default_models", [])

        self.api_style = info.get("api_style", "openai")

        # Headers
        self.headers = config.get("headers", {})
        if self.api_key and "Authorization" not in self.headers:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

        if self.name == "anthropic":
            self.headers["anthropic-version"] = "2023-06-01"
            if self.api_key:
                self.headers["x-api-key"] = self.api_key

    async def chat(self, messages: list, model: str = None, **kwargs) -> Dict:
        model = model or (self.models[0] if self.models else "gpt-3.5-turbo")

        # Provider-specific handling
        if self.api_style == "anthropic":
            return await self._anthropic_chat(messages, model, **kwargs)
        elif self.api_style == "google":
            return await self._google_chat(messages, model, **kwargs)
        elif self.api_style == "replicate":
            return await self._replicate_chat(messages, model, **kwargs)
        elif self.api_style == "azure":
            return await self._azure_chat(messages, model, **kwargs)
        else:
            return await self._openai_chat(messages, model, **kwargs)

    async def _openai_chat(self, messages: list, model: str, **kwargs) -> Dict:
        """Standard OpenAI-compatible chat."""
        payload = {
            "model": model,
            "messages": messages,
            **{
                k: v
                for k, v in kwargs.items()
                if k in ["temperature", "max_tokens", "top_p", "stream", "stop"]
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    f"{self.endpoint}chat/completions",
                    json=payload,
                    headers=self.headers,
                )

                if resp.status_code == 429:
                    raise RateLimitError(f"Rate limited by {self.name}")

                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise RateLimitError(f"Rate limited by {self.name}")
                raise

    async def _anthropic_chat(self, messages: list, model: str, **kwargs) -> Dict:
        """Anthropic API."""
        system = ""
        anthropic_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content", "")
            elif msg.get("role") != "system":
                anthropic_messages.append(msg)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 1024),
        }

        if system:
            payload["system"] = system

        headers = dict(self.headers)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.endpoint}messages", json=payload, headers=headers
            )

            if resp.status_code == 429:
                raise RateLimitError(f"Rate limited by {self.name}")

            resp.raise_for_status()
            data = resp.json()

            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": data.get("content", [{"text": ""}])[0].get(
                                "text", ""
                            ),
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": data.get("usage", {}).get("input_tokens", 0)
                    + data.get("usage", {}).get("output_tokens", 0),
                },
            }

    async def _google_chat(self, messages: list, model: str, **kwargs) -> Dict:
        """Google Gemini API."""
        contents = []
        for msg in messages:
            contents.append(
                {
                    "role": "user" if msg.get("role") == "user" else "model",
                    "parts": [{"text": msg.get("content", "")}],
                }
            )

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.9),
                "maxOutputTokens": kwargs.get("max_tokens", 2048),
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.endpoint}models/{model}:generateContent",
                json=payload,
                headers=self.headers,
            )

            if resp.status_code == 429:
                raise RateLimitError(f"Rate limited by {self.name}")

            resp.raise_for_status()
            data = resp.json()

            content = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            return {
                "choices": [{"message": {"role": "assistant", "content": content}}],
                "usage": {"total_tokens": 0},
            }

    async def _replicate_chat(self, messages: list, model: str, **kwargs) -> Dict:
        """Replicate API."""
        payload = {"version": model, "input": {"messages": messages, **kwargs}}

        headers = dict(self.headers)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.endpoint}predictions", json=payload, headers=headers
            )

            if resp.status_code == 429:
                raise RateLimitError(f"Rate limited by {self.name}")

            resp.raise_for_status()
            data = resp.json()

            while data.get("status") in ["starting", "processing"]:
                await asyncio.sleep(2)
                resp = await client.get(
                    f"{self.endpoint}predictions/{data['id']}", headers=headers
                )
                data = resp.json()

            if data.get("status") == "failed":
                raise Exception(f"Replicate failed: {data.get('error')}")

            output = data.get("output", "")
            if isinstance(output, list):
                output = output[0] if output else ""

            return {
                "choices": [{"message": {"role": "assistant", "content": str(output)}}],
                "usage": {"total_tokens": 0},
            }

    async def _azure_chat(self, messages: list, model: str, **kwargs) -> Dict:
        """Azure OpenAI API."""
        payload = {
            "messages": messages,
            **{
                k: v
                for k, v in kwargs.items()
                if k in ["temperature", "max_tokens", "top_p", "stream"]
            },
        }

        headers = {"api-key": self.api_key, "Content-Type": "application/json"}

        url = self.endpoint.replace("{deployment}", model)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{url}?api-version=2024-02-15-preview", json=payload, headers=headers
            )

            if resp.status_code == 429:
                raise RateLimitError(f"Rate limited by {self.name}")

            resp.raise_for_status()
            return resp.json()

    async def list_models(self) -> List:
        return self.models


# =============================================================================
# Provider Factory
# =============================================================================


def create_provider(name: str, config: dict) -> BaseProvider:
    """Create a provider instance."""
    name = name.lower()

    # Check if virtual provider
    if name.startswith("picorouter/"):
        return VirtualProvider(name, config)

    # Check registry
    info = PROVIDERS.get(name, {})
    provider_class = info.get("class")

    if provider_class == "local":
        return LocalProvider(config)
    else:
        return CloudProvider(name, config)


# =============================================================================
# Virtual Provider (meta-routers)
# =============================================================================


class VirtualProvider(BaseProvider):
    """Virtual provider that routes to other providers."""

    name = "virtual"

    ROUTES = {
        "local_only": ["local"],
        "free_providers": ["kilo", "groq", "openrouter"],
        "fast_providers": ["groq", "kilo"],
        "sota_providers": ["openai", "anthropic", "google"],
    }

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.route_type = name.replace("picorouter/", "")

    async def chat(
        self, messages: list, model: str = None, router=None, **kwargs
    ) -> Dict:
        """Route to appropriate providers based on type."""

        if self.route_type == "privacy":
            return await self._route_privacy(messages, router, **kwargs)
        elif self.route_type == "free":
            return await self._route_free(messages, router, **kwargs)
        elif self.route_type == "fast":
            return await self._route_fast(messages, router, **kwargs)
        elif self.route_type == "sota":
            return await self._route_sota(messages, router, **kwargs)

        raise Exception(f"Unknown virtual route: {self.route_type}")

    async def _route_privacy(self, messages, router, **kwargs):
        """Route to privacy-compliant providers (ZDR).
        
        Priority:
        1. Local providers (Ollama, LM Studio) - always ZDR
        2. ZDR-tagged models from OpenRouter
        3. Fail if no ZDR model available (no non-ZDR fallback)
        """
        from picorouter.providers import get_zdr_models, refresh_zdr_cache
        
        # Priority 1: Try local providers (always ZDR)
        local = router.profile.get("local", {})
        for model in local.get("models", []):
            try:
                if await router.try_local(messages, model, **kwargs):
                    return await router.local_chat(messages, model, **kwargs)
            except Exception:
                continue
        
        # Priority 2: Try ZDR models from OpenRouter
        try:
            # Refresh cache to get latest ZDR models
            all_models = await refresh_zdr_cache(force=False)
            zdr_models = get_zdr_models()
            
            if not zdr_models:
                raise Exception("No ZDR models available from OpenRouter")
            
            # Try each ZDR model
            openrouter = router.cloud.get("openrouter")
            if openrouter:
                for model_info in zdr_models:
                    model_id = model_info["id"]
                    try:
                        return await openrouter.chat(messages, model_id, **kwargs)
                    except RateLimitError:
                        continue
                    except Exception:
                        continue
            
            raise Exception("No ZDR providers available")
            
        except Exception as e:
            # Don't fall back to non-ZDR - fail as per design decision
            raise Exception(f"No privacy-compliant providers available: {e}")

    async def _route_local_only(self, messages, router, **kwargs):
        local = router.profile.get("local", {})
        for model in local.get("models", []):
            try:
                if await router.try_local(messages, model, **kwargs):
                    return await router.local_chat(messages, model, **kwargs)
            except Exception:
                continue
        raise Exception("No local providers available")

    async def _route_free(self, messages, router, **kwargs):
        # Try local first
        local = router.profile.get("local", {})
        for model in local.get("models", []):
            try:
                if await router.try_local(messages, model, **kwargs):
                    return await router.local_chat(messages, model, **kwargs)
            except Exception:
                continue

        # Try free cloud
        for prov_name in ["kilo", "groq", "openrouter"]:
            prov = router.cloud.get(prov_name)
            if prov:
                try:
                    return await prov.chat(messages, None, **kwargs)
                except RateLimitError:
                    continue
                except Exception:
                    continue

        raise Exception("No free providers available")

    async def _route_fast(self, messages, router, **kwargs):
        for prov_name in ["groq", "kilo", "openrouter"]:
            prov = router.cloud.get(prov_name)
            if prov:
                try:
                    return await prov.chat(messages, None, **kwargs)
                except RateLimitError:
                    continue
                except Exception:
                    continue

        # Fallback to local
        local = router.profile.get("local", {})
        for model in local.get("models", []):
            try:
                if await router.try_local(messages, model, **kwargs):
                    return await router.local_chat(messages, model, **kwargs)
            except Exception:
                continue

        raise Exception("No fast providers available")

    async def _route_sota(self, messages, router, **kwargs):
        for prov_name in ["openai", "anthropic", "google"]:
            prov = router.cloud.get(prov_name)
            if prov:
                try:
                    return await prov.chat(messages, None, **kwargs)
                except RateLimitError:
                    continue
                except Exception:
                    continue

        # Fallback to any
        for prov_name, prov in router.cloud.items():
            try:
                return await prov.chat(messages, None, **kwargs)
            except Exception:
                continue

        raise Exception("No SOTA providers available")

    async def list_models(self) -> List:
        return []
# =============================================================================
# ZDR (Zero Data Retention) Model Caching
# =============================================================================

import time

ZDR_CACHE_TTL = 86400  # 24 hours in seconds

_zdr_cache = {
    "models": [],
    "timestamp": 0,
}


def _is_cache_valid() -> bool:
    """Check if ZDR cache is still valid."""
    return time.time() - _zdr_cache["timestamp"] < ZDR_CACHE_TTL


async def fetch_openrouter_models(force_refresh: bool = False) -> List[Dict]:
    """Fetch models from OpenRouter API and extract ZDR metadata.
    
    Args:
        force_refresh: If True, ignore cache and fetch fresh data
        
    Returns:
        List of model dictionaries with ZDR and pricing info
    """
    global _zdr_cache
    
    # Return cached data if valid and not forcing refresh
    if not force_refresh and _zdr_cache["models"] and _is_cache_valid():
        return _zdr_cache["models"]
    
    # Get API key
    api_key = _secrets.get_provider_key("openrouter")
    if not api_key:
        # Return cached data if available, even if expired
        if _zdr_cache["models"]:
            return _zdr_cache["models"]
        raise Exception("OpenRouter API key not configured. Run: pico router secrets set --provider openrouter --key YOUR_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            
            models = []
            for model in data.get("data", []):
                # Extract ZDR info from privacy field
                privacy = model.get("privacy", {})
                pricing = model.get("pricing", {})
                
                model_info = {
                    "id": model.get("id"),
                    "name": model.get("name"),
                    "zdr": privacy.get("zero_retention", False),
                    "price_input": float(pricing.get("prompt", 0)),
                    "price_output": float(pricing.get("completion", 0)),
                    "price_cache": float(pricing.get("cached-prompt", 0)),
                }
                models.append(model_info)
            
            # Update cache
            _zdr_cache = {
                "models": models,
                "timestamp": time.time(),
            }
            
            return models
            
        except httpx.HTTPStatusError as e:
            # Return cached data on API error
            if _zdr_cache["models"]:
                return _zdr_cache["models"]
            raise Exception(f"Failed to fetch OpenRouter models: {e}")
        except Exception as e:
            # Return cached data on any error
            if _zdr_cache["models"]:
                return _zdr_cache["models"]
            raise Exception(f"Failed to fetch OpenRouter models: {e}")


def get_zdr_models() -> List[Dict]:
    """Get cached ZDR models.
    
    Returns cached models filtered to only ZDR-capable ones.
    Does NOT refresh cache - use refresh_zdr_cache() for that.
    """
    return [m for m in _zdr_cache["models"] if m.get("zdr", False)]


def get_all_models() -> List[Dict]:
    """Get all cached models with metadata.
    
    Returns all models including ZDR status and pricing.
    """
    return _zdr_cache["models"]


async def refresh_zdr_cache(force: bool = True) -> List[Dict]:
    """Force refresh the ZDR model cache.
    
    Args:
        force: If True, always fetch fresh data from API
        
    Returns:
        List of all models with ZDR metadata
    """
    return await fetch_openrouter_models(force_refresh=force)


def get_cache_info() -> dict:
    """Get information about the ZDR cache.
    
    Returns:
        Dict with cache status, model count, ZDR count, and age
    """
    age = time.time() - _zdr_cache["timestamp"]
    return {
        "cached": len(_zdr_cache["models"]) > 0,
        "total_models": len(_zdr_cache["models"]),
        "zdr_count": len(get_zdr_models()),
        "age_seconds": age,
        "age_hours": age / 3600,
        "ttl_seconds": ZDR_CACHE_TTL,
        "ttl_hours": ZDR_CACHE_TTL / 3600,
        "expired": age >= ZDR_CACHE_TTL if _zdr_cache["timestamp"] > 0 else True,
    }
