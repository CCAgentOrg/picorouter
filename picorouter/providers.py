"""PicoRouter - Provider implementations."""

import asyncio
import os
import httpx
from dataclasses import dataclass

PROVIDER_ENDPOINTS = {
    "kilo": "https://api.kilo.ai/api/openrouter/",
    "groq": "https://api.groq.com/openai/",
    "openrouter": "https://openrouter.ai/api/v1/",
}


class RateLimitError(Exception):
    """Rate limit exceeded."""
    pass


class LocalProvider:
    """Local model provider (Ollama, LM Studio)."""
    
    def __init__(self, config: dict):
        self.endpoint = config.get("endpoint", "http://localhost:11434").rstrip('/')
    
    async def chat(self, messages: list, model: str = None, **kwargs) -> dict:
        model = model or "llama3"
        url = f"{self.endpoint}/api/chat"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json={"model": model, "messages": messages, **kwargs})
            resp.raise_for_status()
            return resp.json()
    
    async def list_models(self) -> list:
        url = f"{self.endpoint}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                return [m.get("name") for m in data.get("models", [])]
        except Exception:
            return []


class CloudProvider:
    """Cloud API provider."""
    
    def __init__(self, name: str, config: dict):
        self.name = name
        self.base_url = config.get("base_url") or PROVIDER_ENDPOINTS.get(name, "")
        self.api_key = config.get("api_key") or os.getenv(f"{name.upper()}_API_KEY", "")
        self.models = config.get("models", [])
    
    async def chat(self, messages: list, model: str = None, **kwargs) -> dict:
        model = model or (self.models[0] if self.models else "gpt-3.5-turbo")
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # OpenAI-compatible format
        payload = {
            "model": model,
            "messages": messages,
            **{k: v for k, v in kwargs.items() if k in ["temperature", "max_tokens", "top_p", "stream"]}
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
        for name, cfg in self.profile.get("cloud", {}).get("providers", {}).items():
            self.cloud[name] = CloudProvider(name, cfg)
    
    async def chat(self, messages: list, **kwargs) -> dict:
        """Route and execute chat request."""
        from picorouter.router import route_request
        return await route_request(self, messages, **kwargs)
    
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
