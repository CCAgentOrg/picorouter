"""PicoRouter - Router class."""

import asyncio
from typing import Dict
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

    async def chat(self, messages: list, headers: dict = None, **kwargs) -> Dict:
        """Route and execute chat request."""
        from picorouter.router import route_request

        return await route_request(self, messages, headers=headers, **kwargs)

    async def try_local(self, messages: list, model: str, **kwargs) -> bool:
        try:
            await self.local.chat(messages, model, **kwargs)
            return True
        except Exception:
            return False

    async def local_chat(self, messages: list, model: str, **kwargs) -> Dict:
        return await self.local.chat(messages, model, **kwargs)

    async def cloud_chat(self, messages: list, provider: str, **kwargs) -> Dict:
        # Handle virtual providers
        if provider.startswith("picorouter/"):
            vp = VirtualProvider(provider, {})
            return await vp.chat(messages, router=self, **kwargs)

        prov = self.cloud.get(provider)
        if not prov:
            raise Exception(f"Unknown provider: {provider}")

        model = kwargs.pop("model", None)
        return await prov.chat(messages, model, **kwargs)

    async def yolo_chat(self, messages: list, **kwargs) -> Dict:
        """Fire all, return first success."""
        tasks = []

        # Local models
        for model in self.profile.get("local", {}).get("models", []):
            tasks.append(
                self._task_wrap(
                    self.local.chat(messages, model, **kwargs), f"local:{model}"
                )
            )

        # Cloud providers
        for name, prov in self.cloud.items():
            for model in prov.models:
                tasks.append(
                    self._task_wrap(
                        prov.chat(messages, model, **kwargs), f"{name}:{model}"
                    )
                )

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


# =============================================================================
# Prompt Analysis (for tests)
# =============================================================================

import re


def analyze_prompt(prompt: str) -> Dict:
    """Analyze prompt features."""
    prompt_lower = prompt.lower()
    
    # Length checks
    short = len(prompt) < 100
    long = len(prompt) > 1000
    
    # Code detection
    code_patterns = [
        r'\bdef\s+\w+\s*\(',
        r'\bclass\s+\w+',
        r'\bimport\s+\w+',
        r'\bfrom\s+\w+\s+import',
        r'\bfunction\s+\w+\s*\(',
        r'=>\s*\{',
        r'const\s+\w+\s*=',
        r'let\s+\w+\s*=',
        r'var\s+\w+\s*=',
    ]
    contains_code = any(re.search(p, prompt) for p in code_patterns)
    
    # Reasoning detection
    reasoning_patterns = ['think step by step', 'explain why', 'reasoning', 'analyze']
    contains_reasoning = any(p in prompt_lower for p in reasoning_patterns)
    
    # Language detection
    language = None
    if re.search(r'\bdef\s+\w+\s*\(', prompt):
        language = 'python'
    elif re.search(r'\bfunction\s+\w+\s*\(|const\s+\w+\s*=|let\s+\w+\s*=', prompt):
        language = 'javascript'
    
    return {
        'short_prompt': short,
        'long_prompt': long,
        'contains_code': contains_code,
        'contains_reasoning': contains_reasoning,
        'language': language,
    }


def match_routing_rule(features: Dict, rules: list) -> Dict | None:
    """Match features against routing rules."""
    for rule in rules:
        condition = rule.get('if', '')
        
        # Handle language:xxx syntax
        if ':' in condition:
            key, value = condition.split(':', 1)
            if features.get(key) == value:
                return rule
        
        # Simple key check
        if features.get(condition):
            return rule
    
    return None
