"""PicoRouter - Provider implementations."""

import asyncio
import os
import httpx
from picorouter.secrets import SecretsManager, PROVIDER_KEYS

# Initialize secrets manager
_secrets = SecretsManager()

# All supported provider endpoints
PROVIDER_ENDPOINTS = {
    # Free / Low-cost
    "kilo": "https://api.kilo.ai/api/openrouter/",
    "groq": "https://api.groq.com/openai/",
    "openrouter": "https://openrouter.ai/api/v1/",
    
    # Major providers
    "openai": "https://api.openai.com/v1/",
    "anthropic": "https://api.anthropic.com/v1/",
    "google": "https://generativelanguage.googleapis.com/v1beta/",
    "mistral": "https://api.mistral.ai/v1/",
    "cohere": "https://api.cohere.ai/v1/",
    "ai21": "https://api.ai21.com/v1/",
    
    # Aggregators / Specialized
    "together": "https://api.together.ai/v1/",
    "replicate": "https://api.replicate.com/v1/",
    "deepinfra": "https://api.deepinfra.com/v1/openai/v1/",
    "fireworks": "https://api.fireworks.ai/v1/",
    "anyscale": "https://api.endpoints.anyscale.com/v1/",
    "azure": "https://{resource}.openai.azure.com/openai/deployments/{deployment}/",
    
    # Local (handled separately)
    "ollama": None,
    "lmstudio": None,
}

# Default models per provider
DEFAULT_MODELS = {
    "kilo": ["minimax/m2.5:free"],
    "groq": ["llama-3.1-70b-versatile"],
    "openrouter": ["openrouter/free"],
    "openai": ["gpt-4o-mini"],
    "anthropic": ["claude-3-haiku-20240307"],
    "google": ["gemini-1.5-flash"],
    "mistral": ["mistral-small-latest"],
    "cohere": ["command-r-plus"],
    "ai21": ["jamba-1.5-mini"],
    "together": ["meta-llama/Llama-3-70b-chat-hf"],
    "replicate": ["llama-3-70b-instruct"],
    "deepinfra": ["meta-llama/Llama-3-70b-instruct"],
    "fireworks": ["llama-v3-70b-instruct"],
    "anyscale": ["meta-llama/Llama-3-70b-Instruct"],
}


class RateLimitError(Exception):
    """Rate limit exceeded."""
    pass


class LocalProvider:
    """Local model provider (Ollama, LM Studio)."""
    
    def __init__(self, config: dict):
        provider = config.get("provider", "ollama")
        
        if provider == "lmstudio":
            self.endpoint = config.get("endpoint", "http://localhost:1234").rstrip('/')
        else:  # ollama default
            self.endpoint = config.get("endpoint", "http://localhost:11434").rstrip('/')
        
        self.provider = provider
    
    async def chat(self, messages: list, model: str = None, **kwargs) -> dict:
        model = model or "llama3"
        
        if self.provider == "lmstudio":
            url = f"{self.endpoint}/v1/chat/completions"
            payload = {"model": model, "messages": messages, **kwargs}
        else:  # ollama
            url = f"{self.endpoint}/api/chat"
            payload = {"model": model, "messages": messages, **kwargs}
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    
    async def list_models(self) -> list:
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


class CloudProvider:
    """Cloud API provider."""
    
    def __init__(self, name: str, config: dict):
        self.name = name
        self.base_url = config.get("base_url") or PROVIDER_ENDPOINTS.get(name, "")
        
        # Get API key from secrets manager
        self.api_key = config.get("api_key") or _secrets.get_provider_key(name)
        
        self.models = config.get("models", []) or DEFAULT_MODELS.get(name, [])
        
        # Provider-specific headers
        self.headers = config.get("headers", {})
        if name == "anthropic":
            self.headers["anthropic-version"] = self.headers.get("anthropic-version", "2023-06-01")
        
        if self.api_key and "Authorization" not in self.headers:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        if name == "anthropic" and self.api_key:
            self.headers["x-api-key"] = self.api_key
    
    async def chat(self, messages: list, model: str = None, **kwargs) -> dict:
        model = model or (self.models[0] if self.models else "gpt-3.5-turbo")
        
        # Build headers
        headers = dict(self.headers)
        
        # Anthropic uses different format
        if self.name == "anthropic":
            return await self._anthropic_chat(messages, model, **kwargs)
        
        # Google AI
        if self.name == "google":
            return await self._google_chat(messages, model, **kwargs)
        
        # Replicate
        if self.name == "replicate":
            return await self._replicate_chat(messages, model, **kwargs)
        
        # Azure
        if self.name == "azure":
            return await self._azure_chat(messages, model, **kwargs)
        
        # Standard OpenAI-compatible
        payload = {
            "model": model,
            "messages": messages,
            **{k: v for k, v in kwargs.items() 
               if k in ["temperature", "max_tokens", "top_p", "stream", "stop"]}
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}chat/completions",
                    json=payload,
                    headers=headers
                )
                
                if resp.status_code == 429:
                    raise RateLimitError(f"Rate limited by {self.name}")
                
                resp.raise_for_status()
                return resp.json()
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise RateLimitError(f"Rate limited by {self.name}")
                raise
    
    async def _anthropic_chat(self, messages: list, model: str, **kwargs) -> dict:
        """Anthropic-specific chat."""
        # Convert messages to Anthropic format
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
        
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        
        headers = dict(self.headers)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}messages",
                json=payload,
                headers=headers
            )
            
            if resp.status_code == 429:
                raise RateLimitError(f"Rate limited by {self.name}")
            
            resp.raise_for_status()
            data = resp.json()
            
            # Convert to OpenAI format
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": data.get("content", [{"text": ""}])[0].get("text", "")
                    }
                }],
                "usage": {
                    "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
                }
            }
    
    async def _google_chat(self, messages: list, model: str, **kwargs) -> dict:
        """Google AI (Gemini) specific chat."""
        # Convert to Gemini format
        contents = []
        for msg in messages:
            contents.append({
                "role": "user" if msg.get("role") == "user" else "model",
                "parts": [{"text": msg.get("content", "")}]
            })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.9),
                "maxOutputTokens": kwargs.get("max_tokens", 2048),
            }
        }
        
        headers = dict(self.headers)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}models/{model}:generateContent",
                json=payload,
                headers=headers
            )
            
            if resp.status_code == 429:
                raise RateLimitError(f"Rate limited by {self.name}")
            
            resp.raise_for_status()
            data = resp.json()
            
            # Convert to OpenAI format
            content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            return {
                "choices": [{
                    "message": {"role": "assistant", "content": content}
                }],
                "usage": {"total_tokens": 0}
            }
    
    async def _replicate_chat(self, messages: list, model: str, **kwargs) -> dict:
        """Replicate specific chat."""
        # Replicate is different - uses prediction API
        payload = {
            "version": model,
            "input": {
                "messages": messages,
                **kwargs
            }
        }
        
        headers = dict(self.headers)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Start prediction
            resp = await client.post(
                f"{self.base_url}predictions",
                json=payload,
                headers=headers
            )
            
            if resp.status_code == 429:
                raise RateLimitError(f"Rate limited by {self.name}")
            
            resp.raise_for_status()
            data = resp.json()
            
            # Poll for result
            while data.get("status") in ["starting", "processing"]:
                await asyncio.sleep(2)
                resp = await client.get(
                    f"{self.base_url}predictions/{data['id']}",
                    headers=headers
                )
                data = resp.json()
            
            if data.get("status") == "failed":
                raise Exception(f"Replicate failed: {data.get('error')}")
            
            output = data.get("output", "")
            if isinstance(output, list):
                output = output[0] if output else ""
            
            return {
                "choices": [{
                    "message": {"role": "assistant", "content": str(output)}
                }],
                "usage": {"total_tokens": 0}
            }
    
    async def _azure_chat(self, messages: list, model: str, **kwargs) -> dict:
        """Azure OpenAI specific chat."""
        # Azure uses deployment name as model
        payload = {
            "messages": messages,
            **{k: v for k, v in kwargs.items() 
               if k in ["temperature", "max_tokens", "top_p", "stream"]}
        }
        
        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        
        # Azure URL template: https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version=2024-02-15-preview
        url = self.base_url.replace("{deployment}", model)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{url}?api-version=2024-02-15-preview",
                json=payload,
                headers=headers
            )
            
            if resp.status_code == 429:
                raise RateLimitError(f"Rate limited by {self.name}")
            
            resp.raise_for_status()
            return resp.json()
    
    async def list_models(self) -> list:
        return self.models


class Router:
    """Main router class."""
    
    RateLimitError = RateLimitError
    
    def __init__(self, config: dict, profile_name: str = None):
        self.config = config
        self.profile_name = profile_name or config.get("default_profile", "chat")
        self.profile = config.get("profiles", {}).get(self.profile_name, {})
        
        # Initialize local provider
        local_cfg = self.profile.get("local", {})
        self.local = LocalProvider(local_cfg)
        
        # Initialize cloud providers
        self.cloud = {}
        cloud_providers = self.profile.get("cloud", {}).get("providers", {})
        for name, cfg in cloud_providers.items():
            self.cloud[name] = CloudProvider(name, cfg)
    
    async def chat(self, messages: list, headers: dict = None, **kwargs) -> dict:
        """Route and execute chat request."""
        from picorouter.router import route_request
        return await route_request(self, messages, headers=headers, **kwargs)
    
    async def try_local(self, messages: list, model: str, **kwargs) -> bool:
        try:
            await self.local.chat(messages, model, **kwargs)
            return True
        except Exception:
            return False
    
    async def local_chat(self, messages: list, model: str, **kwargs) -> dict:
        return await self.local.chat(messages, model, **kwargs)
    
    async def cloud_chat(self, messages: list, provider: str, **kwargs) -> dict:
        prov = self.cloud.get(provider)
        if not prov:
            raise Exception(f"Unknown provider: {provider}")
        
        model = kwargs.pop("model", None)
        return await prov.chat(messages, model, **kwargs)
    
    async def yolo_chat(self, messages: list, **kwargs) -> dict:
        """Fire all, return first success."""
        tasks = []
        
        # Local models
        for model in self.profile.get("local", {}).get("models", []):
            tasks.append(self._task_wrap(self.local.chat(messages, model, **kwargs), f"local:{model}"))
        
        # Cloud providers
        for name, prov in self.cloud.items():
            for model in prov.models:
                tasks.append(self._task_wrap(prov.chat(messages, model, **kwargs), f"{name}:{model}"))
        
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        for task in pending:
            task.cancel()
        
        for task in done:
            try:
                return await task.result()
            except Exception:
                continue
        
        raise Exception("All providers failed")
    
    @staticmethod
    async def _task_wrap(coro, name):
        task = asyncio.create_task(coro)
        task.set_name(name)
        return task
