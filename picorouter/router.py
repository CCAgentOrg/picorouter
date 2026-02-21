"""PicoRouter - Router class."""

import asyncio
from picorouter.providers import (
    LocalProvider,
    CloudProvider,
    VirtualProvider,
    create_provider,
    RateLimitError,
)


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
        # Handle virtual providers
        if provider.startswith("picorouter/"):
            vp = VirtualProvider(provider, {})
            return await vp.chat(messages, router=self, **kwargs)
        
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
