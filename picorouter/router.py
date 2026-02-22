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
            coro = self.local.chat(messages, model, **kwargs)
            task = asyncio.create_task(coro)
            task.set_name(f"local:{model}")
            tasks.append(task)

        # Cloud providers
        for name, prov in self.cloud.items():
            for model in prov.models:
                coro = prov.chat(messages, model, **kwargs)
                task = asyncio.create_task(coro)
                task.set_name(f"{name}:{model}")
                tasks.append(task)

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

        for task in done:
            try:
                return task.result()
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


# =============================================================================
# Request Routing
# =============================================================================

def analyze_headers(headers: dict) -> dict:
    """Analyze X-PicoRouter-* headers for routing hints."""
    features = {
        "header_profile": None,
        "header_provider": None,
        "header_model": None,
        "header_local": False,
        "header_yolo": False,
    }
    
    if not headers:
        return features
    
    # Normalize headers (lowercase keys)
    h = {k.lower(): v for k, v in headers.items()}
    
    # X-PicoRouter-Profile: use specific profile
    profile = h.get("x-picorouter-profile")
    if profile:
        features["header_profile"] = profile
    
    # X-PicoRouter-Provider: force provider
    provider = h.get("x-picorouter-provider")
    if provider:
        features["header_provider"] = provider
    
    # X-PicoRouter-Model: force model
    model = h.get("x-picorouter-model")
    if model:
        features["header_model"] = model
    
    # X-PicoRouter-Local: force local only
    local = h.get("x-picorouter-local", "").lower()
    if local in ["1", "true", "yes"]:
        features["header_local"] = True
    
    # X-PicoRouter-Yolo: enable YOLO mode
    yolo = h.get("x-picorouter-yolo", "").lower()
    if yolo in ["1", "true", "yes"]:
        features["header_yolo"] = True
    
    return features


def parse_model(model: str) -> tuple:
    """Parse model string for explicit provider:model routing.
    
    Returns (provider, model) tuple. If no provider prefix, returns (None, model).
    
    Examples:
        "kilo:minimax/m2.5:free" -> ("kilo", "minimax/m2.5:free")
        "local:llama3" -> ("local", "llama3")
        "llama3" -> (None, "llama3")
    """
    if not model:
        return (None, None)
    
    if ":" in model:
        parts = model.split(":", 1)
        provider = parts[0]
        actual_model = parts[1]
        return (provider, actual_model)
    
    return (None, model)



def find_providers_with_model(profile: dict, model: str) -> list:
    """Find all providers in profile that have the given model configured.
    
    Returns list of (provider_name, provider_config) tuples.
    
    Examples:
        profile with kilo, groq, openrouter all having "minimax/m2.5:free"
        -> [("kilo", {...}), ("openrouter", {...})]
    """
    if not model:
        return []
    
    providers = profile.get("cloud", {}).get("providers", {})
    matching = []
    
    for prov_name, prov_config in providers.items():
        models = prov_config.get("models", [])
        if model in models:
            matching.append((prov_name, prov_config))
    
    return matching


async def route_with_model_fallback(router, messages: list, model: str, providers: list, **kwargs) -> Dict:
    """Try multiple providers that have the same model, with fallback on errors.
    
    Args:
        router: Router instance
        messages: Chat messages
        model: Model name to use
        providers: List of (provider_name, provider_config) tuples to try
        **kwargs: Additional parameters
    
    Returns:
        Response from first successful provider
    
    Raises:
        Exception if all providers fail
    """
    for prov_name, prov_config in providers:
        try:
            return await router.cloud_chat(messages, prov_name, model=model, **kwargs)
        except router.RateLimitError:
            # Rate limited - try next provider
            continue
        except Exception:
            # Other error - try next provider
            continue
    
    raise Exception(f"All providers failed for model {model}")


async def route_request(router, messages: list, headers: dict = None, **kwargs) -> Dict:
    """Route request based on profile, headers, and prompt analysis."""
    # Get model from kwargs (passed from API)
    user_model = kwargs.pop("model", None)
    
    # Parse model for explicit provider:model routing
    explicit_provider, explicit_model = parse_model(user_model) if user_model else (None, None)
    
    # Analyze headers for routing hints
    header_features = analyze_headers(headers or {})
    
    # Determine profile to use
    profile = router.profile
    profile_name = router.profile_name
    
    # Header can override profile
    if header_features.get("header_profile"):
        profile_name = header_features["header_profile"]
        if profile_name in router.config.get("profiles", {}):
            profile = router.config["profiles"][profile_name]
    
    # Get prompt from messages
    prompt = ""
    for msg in messages:
        if isinstance(msg, dict) and msg.get("content"):
            prompt += msg.get("content", "")
    
    # Analyze prompt content
    features = analyze_prompt(prompt)
    matched = match_routing_rule(features, profile.get("routing", []))
    
    # YOLO mode - from profile or headers
    yolo = profile.get("yolo") or header_features.get("header_yolo")
    if yolo:
        return await router.yolo_chat(messages, **kwargs)
    
    # === EXPLICIT ROUTING (highest priority) ===
    # 1. Explicit provider:model from model parameter
    if explicit_provider:
        if explicit_provider == "local":
            # Route to local provider
            model = explicit_model or profile.get("local", {}).get("models", [None])[0]
            if model:
                try:
                    return await router.local_chat(messages, model, **kwargs)
                except Exception:
                    pass  # Fall through to other providers
        else:
            # Route to specific cloud provider
            try:
                return await router.cloud_chat(messages, explicit_provider, model=explicit_model, **kwargs)
            except Exception:
                pass  # Fall through
    
    # 1b. Auto-fallback: model-only (no provider prefix) - find all providers with this model
    if not explicit_provider and explicit_model:
        # Find all providers that have this model
        providers_with_model = find_providers_with_model(profile, explicit_model)
        if providers_with_model:
            # Try each provider with fallback on 429
            try:
                return await route_with_model_fallback(router, messages, explicit_model, providers_with_model, **kwargs)
            except Exception:
                pass  # Fall through to profile-based routing
    # 2. Header-based explicit routing
    if header_features.get("header_provider"):
        prov = header_features["header_provider"]
        model = header_features.get("header_model")
        try:
            if prov == "local" or prov == "ollama":
                return await router.local_chat(messages, model or profile.get("local", {}).get("models", [None])[0], **kwargs)
            return await router.cloud_chat(messages, prov, model=model, **kwargs)
        except Exception:
            pass  # Fall through
    
    # 3. Header: force local only
    if header_features.get("header_local"):
        local_models = profile.get("local", {}).get("models", [])
        for model in local_models:
            try:
                if await router.try_local(messages, model, **kwargs):
                    return await router.local_chat(messages, model, **kwargs)
            except Exception:
                continue
        raise Exception("Local providers failed")
    
    # === PROFILE-BASED ROUTING ===
    # Try local first (default behavior)
    local = profile.get("local", {})
    if not matched or matched.get("use_local"):
        local_models = local.get("models", [])
        # If matched rule specifies models, use those
        if matched and matched.get("models"):
            local_models = matched.get("models")
        
        for model in local_models:
            try:
                if await router.try_local(messages, model, **kwargs):
                    return await router.local_chat(messages, model, **kwargs)
            except Exception:
                continue
    
    # Try cloud providers
    providers = profile.get("cloud", {}).get("providers", {})
    if matched and matched.get("providers"):
        # Filter to only matched providers
        providers = {k: v for k, v in providers.items() if k in matched.get("providers", [])}
    
    for prov_name, prov_config in providers.items():
        prov_models = prov_config.get("models", [])
        for model in prov_models:
            try:
                return await router.cloud_chat(messages, prov_name, model=model, **kwargs)
            except router.RateLimitError:
                continue
            except Exception:
                continue
    
    raise Exception("All providers failed")
