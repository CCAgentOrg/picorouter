"""PicoRouter - Core routing logic."""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

CODE_PATTERNS = [
    r'def\s+\w+', r'class\s+\w+', r'function\s+\w+',
    r'const\s+\w+\s*=', r'let\s+\w+\s*=',
    r'import\s+', r'from\s+\w+\s+import', r'```',
    r'if\s*\(', r'for\s*\(', r'while\s*\(', r'return\s+',
]

REASONING_PATTERNS = [
    r'think\s+step\s*by\s*step', r'explain\s+your\s+reasoning',
    r'why\s+is\s+', r'how\s+does\s+', r'prove\s+that', r'derive\s+',
]

LANGUAGE_PATTERNS = {
    'python': [r'def\s+\w+\s*\(', r'import\s+\w+', r'class\s+\w+:'],
    'javascript': [r'function\s+\w+', r'const\s+\w+\s*=', r'let\s+\w+\s*='],
    'rust': [r'fn\s+\w+', r'let\s+mut', r'use\s+\w+::'],
}


def analyze_prompt(prompt: str) -> dict:
    """Analyze prompt and return detected features."""
    features = {
        "contains_code": False,
        "contains_reasoning": False,
        "short_prompt": len(prompt) < 200,
        "long_prompt": len(prompt) > 2000,
        "language": None,
    }
    
    for pattern in CODE_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            features["contains_code"] = True
            break
    
    for pattern in REASONING_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            features["contains_reasoning"] = True
            break
    
    for lang, patterns in LANGUAGE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, prompt):
                features["language"] = lang
                break
    
    return features


def match_routing_rule(features: dict, routing: list) -> dict | None:
    """Match prompt features to routing rules."""
    for rule in routing:
        cond = rule.get("condition", rule.get("if", ""))
        
        if cond == "contains_code" and features.get("contains_code"):
            return rule
        elif cond == "contains_reasoning" and features.get("contains_reasoning"):
            return rule
        elif cond == "short_prompt" and features.get("short_prompt"):
            return rule
        elif cond == "long_prompt" and features.get("long_prompt"):
            return rule
        elif cond.startswith("language:") and features.get("language"):
            lang = cond.split(":")[1]
            if features.get("language") == lang:
                return rule
    
    return None


async def route_request(router, messages: list, **kwargs):
    """Route request based on profile and prompt analysis."""
    profile = router.profile
    features = analyze_prompt(messages)
    matched = match_routing_rule(features, profile.get("routing", []))
    
    # YOLO mode - fire all
    if profile.get("yolo"):
        return await router.yolo_chat(messages, **kwargs)
    
    # Try local first
    local = profile.get("local", {})
    if not matched or matched.get("use_local"):
        for model in local.get("models", []):
            try:
                if await router.try_local(messages, model, **kwargs):
                    return await router.local_chat(messages, model, **kwargs)
            except Exception:
                continue
    
    # Try cloud
    providers = matched.get("providers", []) if matched else list(profile.get("cloud", {}).keys())
    for prov in providers:
        try:
            return await router.cloud_chat(messages, prov, **kwargs)
        except router.RateLimitError:
            continue
        except Exception:
            continue
    
    raise Exception("All providers failed")
