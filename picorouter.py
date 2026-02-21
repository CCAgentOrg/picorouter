#!/usr/bin/env python3
"""
PicoRouter - Minimal AI Model Router

Local-first with intelligent cloud fallback.
OpenAI-compatible API server.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
import yaml
import httpx

__version__ = "0.1.0"
__author__ = "CashlessConsumer"

# Configuration paths
CONFIG_PATHS = [
    Path.cwd() / "picorouter.yaml",
    Path.home() / ".picorouter.yaml",
    Path.home() / ".config" / "picorouter.yaml",
]


@dataclass
class ProviderConfig:
    name: str
    api_key: str = ""
    base_url: str = ""
    models: list = field(default_factory=list)
    enabled: bool = True


@dataclass
class LocalConfig:
    provider: str = "ollama"
    endpoint: str = "http://localhost:11434"
    models: list = field(default_factory=list)


@dataclass
class RoutingRule:
    condition: str  # contains_code, short_prompt, etc.
    use_local: bool = True
    models: list = field(default_factory=list)
    providers: list = field(default_factory=list)


@dataclass
class Profile:
    name: str
    local: LocalConfig = field(default_factory=LocalConfig)
    cloud: dict = field(default_factory=dict)  # provider_name -> config
    routing: list = field(default_factory=list)
    yolo: bool = False


@dataclass
class Config:
    profiles: dict = field(default_factory=dict)
    default_profile: str = "default"
    providers: dict = field(default_factory=dict)
    server: dict = field(default_factory=lambda: {"host": "0.0.0.0", "port": 8080})


class PromptAnalyzer:
    """Analyzes prompts to determine routing rules."""
    
    CODE_PATTERNS = [
        r'def\s+\w+',  # Python function
        r'class\s+\w+',  # Class definition
        r'function\s+\w+',  # JS function
        r'const\s+\w+\s*=',  # JS variable
        r'let\s+\w+\s*=',  # JS variable
        r'import\s+',  # Import statement
        r'from\s+\w+\s+import',  # Python import
        r'```',  # Code block
        r'if\s*\(',  # If statement
        r'for\s*\(',  # For loop
        r'while\s*\(',  # While loop
        r'return\s+',  # Return statement
    ]
    
    REASONING_PATTERNS = [
        r'think\s+step\s*by\s*step',
        r'explain\s+your\s+reasoning',
        r'why\s+is\s+',
        r'how\s+does\s+',
        r'prove\s+that',
        r'derive\s+',
    ]
    
    @classmethod
    def analyze(cls, prompt: str) -> dict:
        """Analyze prompt and return detected features."""
        features = {
            "contains_code": False,
            "contains_reasoning": False,
            "short_prompt": len(prompt) < 200,
            "long_prompt": len(prompt) > 2000,
            "has_image": False,
            "language": "en",
        }
        
        # Check for code patterns
        for pattern in cls.CODE_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                features["contains_code"] = True
                break
        
        # Check for reasoning patterns
        for pattern in cls.REASONING_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                features["contains_reasoning"] = True
                break
        
        # Language detection (simple)
        non_ascii = sum(1 for c in prompt if ord(c) > 127)
        if non_ascii / max(len(prompt), 1) > 0.3:
            # Could add more sophisticated detection
            features["language"] = "other"
        
        return features


class LocalProvider:
    """Handles local model providers (Ollama, LM Studio)."""
    
    def __init__(self, config: LocalConfig):
        self.config = config
        self.endpoint = config.endpoint.rstrip('/')
        
    async def chat(self, messages: list, model: str = None, **kwargs) -> dict:
        """Send chat request to local provider."""
        model = model or self.config.models[0] if self.config.models else "llama3"
        
        url = f"{self.endpoint}/api/chat"
        
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Local provider error: {e}")
    
    async def list_models(self) -> list:
        """List available local models."""
        url = f"{self.endpoint}/api/tags"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return [m.get("name", m.get("id")) for m in data.get("models", [])]
            except httpx.HTTPError:
                return self.config.models  # Fallback to configured models
    
    def is_available(self) -> bool:
        """Check if local provider is running."""
        try:
            import requests
            response = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False


class CloudProvider:
    """Handles cloud API providers."""
    
    PROVIDER_ENDPOINTS = {
        "kilo": "https://api.kilo.ai/api/openrouter/",
        "groq": "https://api.groq.com/openai/",
        "openrouter": "https://openrouter.ai/api/v1/",
        "huggingface": "https://api-inference.huggingface.co/",
    }
    
    def __init__(self, name: str, config: ProviderConfig, api_key: str = None):
        self.name = name
        self.config = config
        self.api_key = api_key or config.api_key
        self.base_url = config.base_url or self.PROVIDER_ENDPOINTS.get(name, "")
        
    async def chat(self, messages: list, model: str = None, **kwargs) -> dict:
        """Send chat request to cloud provider."""
        model = model or config.models[0] if self.config.models else "gpt-3.5-turbo"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        if self.name == "openrouter":
            headers["HTTP-Referer"] = "https://picorouter.local"
        
        url = f"{self.base_url}chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise RateLimitError(f"Rate limited by {self.name}")
                raise Exception(f"Cloud provider error: {e}")
            except httpx.HTTPError as e:
                raise Exception(f"Cloud provider error: {e}")
    
    async def list_models(self) -> list:
        """List available models from provider."""
        if self.name == "openrouter":
            url = f"{self.base_url}models"
        elif self.name == "groq":
            url = f"{self.base_url}models"
        else:
            return self.config.models
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return [m.get("id") for m in data.get("data", [])]
            except:
                return self.config.models


class RateLimitError(Exception):
    """Raised when a provider returns 429."""
    pass


class PicoRouter:
    """Main router class."""
    
    def __init__(self, config: Config = None, profile_name: str = None):
        self.config = config or self.load_config()
        self.profile_name = profile_name or self.config.default_profile
        self.profile = self.config.profiles.get(self.profile_name, Profile(name="default"))
        
        # Initialize providers
        self.local = LocalProvider(self.profile.local)
        self.cloud_providers = {}
        
        for provider_name, provider_config in self.profile.cloud.items():
            api_key = os.environ.get(f"{provider_name.upper()}_API_KEY")
            self.cloud_providers[provider_name] = CloudProvider(
                provider_name, provider_config, api_key
            )
    
    @classmethod
    def load_config(cls, path: str = None) -> Config:
        """Load configuration from file."""
        config_path = path or cls.find_config()
        
        if not config_path:
            # Return default config
            return Config()
        
        with open(config_path) as f:
            data = yaml.safe_load(f)
        
        # Parse config
        config = Config()
        config.providers = data.get("providers", {})
        config.default_profile = data.get("default_profile", "default")
        
        # Parse profiles
        for name, profile_data in data.get("profiles", {}).items():
            local_data = profile_data.get("local", {})
            local = LocalConfig(
                provider=local_data.get("provider", "ollama"),
                endpoint=local_data.get("endpoint", "http://localhost:11434"),
                models=local_data.get("models", []),
            )
            
            # Parse cloud providers
            cloud = {}
            for provider_name, provider_data in profile_data.get("cloud", {}).get("providers", {}).items():
                if isinstance(provider_data, dict):
                    cloud[provider_name] = ProviderConfig(
                        name=provider_name,
                        models=provider_data.get("models", []),
                        api_key=provider_data.get("api_key", ""),
                        base_url=provider_data.get("base_url", ""),
                    )
            
            # Parse routing rules
            routing = []
            for rule_data in profile_data.get("routing", []):
                routing.append(RoutingRule(
                    condition=rule_data.get("if", ""),
                    use_local=rule_data.get("use_local", True),
                    models=rule_data.get("models", []),
                    providers=rule_data.get("providers", []),
                ))
            
            config.profiles[name] = Profile(
                name=name,
                local=local,
                cloud=cloud,
                routing=routing,
                yolo=profile_data.get("yolo", False),
            )
        
        return config
    
    @classmethod
    def find_config(cls) -> str:
        """Find config file in standard locations."""
        for path in CONFIG_PATHS:
            if path.exists():
                return str(path)
        return None
    
    def analyze_prompt(self, messages: list) -> dict:
        """Analyze messages to determine routing."""
        # Combine all text from messages
        full_prompt = ""
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                if isinstance(content, str):
                    full_prompt += content + " "
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            full_prompt += item.get("text", "") + " "
                        elif isinstance(item, str):
                            full_prompt += item + " "
        
        return PromptAnalyzer.analyze(full_prompt)
    
    def match_routing_rule(self, features: dict) -> RoutingRule:
        """Match prompt features to routing rules."""
        for rule in self.profile.routing:
            condition = rule.condition
            
            if condition == "contains_code" and features.get("contains_code"):
                return rule
            elif condition == "contains_reasoning" and features.get("contains_reasoning"):
                return rule
            elif condition == "short_prompt" and features.get("short_prompt"):
                return rule
            elif condition == "long_prompt" and features.get("long_prompt"):
                return rule
            elif condition.startswith("language:") and features.get("language"):
                lang = condition.split(":")[1]
                if features.get("language") == lang:
                    return rule
        
        return None
    
    async def chat(self, messages: list, **kwargs) -> dict:
        """Route chat request to appropriate provider."""
        features = self.analyze_prompt(messages)
        matched_rule = self.match_routing_rule(features)
        
        # YOLO mode: fire all at once
        if self.profile.yolo:
            return await self._yolo_chat(messages, **kwargs)
        
        # Seamless mode: try local first, then cloud
        # Try local if rule says use_local or no rule matched
        if not matched_rule or matched_rule.use_local:
            for model in self.profile.local.models:
                try:
                    if await self._try_local(messages, model, **kwargs):
                        return await self.local.chat(messages, model, **kwargs)
                except Exception as e:
                    print(f"Local model {model} failed: {e}", file=sys.stderr)
                    continue
        
        # Try cloud providers
        if matched_rule and matched_rule.providers:
            providers = matched_rule.providers
        else:
            providers = list(self.profile.cloud.keys())
        
        for provider_name in providers:
            provider = self.cloud_providers.get(provider_name)
            if not provider:
                continue
            
            try:
                return await provider.chat(messages, **kwargs)
            except RateLimitError:
                print(f"Provider {provider_name} rate limited, trying next...", file=sys.stderr)
                continue
            except Exception as e:
                print(f"Provider {provider_name} error: {e}", file=sys.stderr)
                continue
        
        raise Exception("All providers failed")
    
    async def _try_local(self, messages: list, model: str, **kwargs) -> bool:
        """Check if local model works."""
        try:
            await self.local.chat(messages, model, **kwargs)
            return True
        except:
            return False
    
    async def _yolo_chat(self, messages: list, **kwargs) -> dict:
        """YOLO mode: fire all providers, take first success."""
        tasks = []
        
        # Local models
        for model in self.profile.local.models:
            tasks.append(self._task_with_name(
                self.local.chat(messages, model, **kwargs),
                f"local:{model}"
            ))
        
        # Cloud providers
        for provider_name, provider in self.cloud_providers.items():
            for model in provider.config.models:
                tasks.append(self._task_with_name(
                    provider.chat(messages, model, **kwargs),
                    f"{provider_name}:{model}"
                ))
        
        # Wait for first success
        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending
        for task in pending:
            task.cancel()
        
        # Get result
        for task in done:
            try:
                result = await task
                name = task.get_name()
                print(f"YOLO: {name} succeeded", file=sys.stderr)
                return result
            except Exception as e:
                print(f"YOLO: {task.get_name()} failed: {e}", file=sys.stderr)
                continue
        
        raise Exception("YOLO: All providers failed")
    
    @staticmethod
    async def _task_with_name(coro, name):
        """Wrap coroutine with name for identification."""
        task = asyncio.create_task(coro)
        task.set_name(name)
        return task


class APIHandler(BaseHTTPRequestHandler):
    """HTTP handler for OpenAI-compatible API."""
    
    router: PicoRouter = None
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def send_json(self, data: dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/v1/models":
            self._handle_models()
        elif self.path == "/health":
            self.send_json({"status": "ok"})
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return
        
        if self.path == "/v1/chat/completions":
            self._handle_chat_completions(data)
        elif self.path == "/v1/completions":
            self._handle_completions(data)
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def _handle_models(self):
        """Return available models."""
        models = []
        
        # Local models
        for model in self.router.profile.local.models:
            models.append({
                "id": f"local:{model}",
                "object": "model",
                "created": 0,
                "owned_by": "local",
            })
        
        # Cloud models
        for provider_name, provider in self.router.cloud_providers.items():
            for model in provider.config.models:
                models.append({
                    "id": f"{provider_name}:{model}",
                    "object": "model",
                    "created": 0,
                    "owned_by": provider_name,
                })
        
        self.send_json({"object": "list", "data": models})
    
    def _handle_chat_completions(self, data: dict):
        """Handle chat completions request."""
        messages = data.get("messages", [])
        model = data.get("model", "")
        
        # Extract kwargs
        kwargs = {}
        for key in ["temperature", "max_tokens", "top_p", "stream"]:
            if key in data:
                kwargs[key] = data[key]
        
        # Run async
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.router.chat(messages, **kwargs)
            )
            loop.close()
            
            # Convert to OpenAI format
            response = {
                "id": f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": model or "unknown",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.get("message", {}).get("content", ""),
                    },
                    "finish_reason": "stop",
                }],
            }
            
            self.send_json(response)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def _handle_completions(self, data: dict):
        """Handle text completions request."""
        # Simple implementation - could expand
        prompt = data.get("prompt", "")
        messages = [{"role": "user", "content": prompt}]
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.router.chat(messages))
            loop.close()
            
            response = {
                "id": f"cmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "object": "text_completion",
                "created": int(datetime.now().timestamp()),
                "choices": [{
                    "text": result.get("message", {}).get("content", ""),
                    "index": 0,
                    "finish_reason": "stop",
                }],
            }
            
            self.send_json(response)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)


def create_config_interactive() -> dict:
    """Interactive TUI for config creation."""
    print("═" * 50)
    print("  PicoRouter Configuration Generator")
    print("═" * 50)
    print()
    
    config = {"profiles": {}, "providers": {}}
    
    # Default profile
    print("📋 Creating default profile...")
    profile = create_profile_interactive("default")
    config["profiles"]["default"] = profile
    
    # Add more profiles?
    while True:
        add_more = input("\n➕ Add another profile? (y/n): ").strip().lower()
        if add_more != 'y':
            break
        
        name = input("   Profile name: ").strip()
        if name:
            config["profiles"][name] = create_profile_interactive(name)
    
    # Server config
    print("\n🌐 Server Configuration")
    config["server"] = {
        "host": input("   Host [0.0.0.0]: ").strip() or "0.0.0.0",
        "port": int(input("   Port [8080]: ").strip() or "8080"),
    }
    
    config["default_profile"] = input("\n� default profile name [default]: ").strip() or "default"
    
    return config


def create_profile_interactive(name: str) -> dict:
    """Create a single profile interactively."""
    print(f"\n── Profile: {name} ──")
    
    profile = {
        "local": {
            "provider": input(f"   Local provider (ollama/lmstudio) [ollama]: ").strip() or "ollama",
            "endpoint": input(f"   Endpoint [http://localhost:11434]: ").strip() or "http://localhost:11434",
            "models": input(f"   Models (comma-separated) [llama3,mistral]: ").strip() or "llama3,mistral",
        },
        "cloud": {"providers": {}},
        "routing": [],
        "yolo": False,
    }
    profile["local"]["models"] = [m.strip() for m in profile["local"]["models"].split(",")]
    
    # Cloud providers
    print("\n☁️  Cloud Providers")
    available_providers = ["kilo", "groq", "openrouter", "huggingface"]
    for p in available_providers:
        add = input(f"   Add {p}? (y/n): ").strip().lower()
        if add == 'y':
            api_key = input(f"      API Key (or press enter to use env {p.upper()}_API_KEY): ").strip()
            models = input(f"      Models (comma-separated): ").strip()
            
            provider_config = {}
            if api_key:
                provider_config["api_key"] = api_key
            if models:
                provider_config["models"] = [m.strip() for m in models.split(",")]
            
            profile["cloud"]["providers"][p] = provider_config
    
    # YOLO mode
    yolo = input("\n⚡ Enable YOLO mode? (y/n): ").strip().lower()
    profile["yolo"] = yolo == 'y'
    
    # Routing rules
    print("\n🔀 Routing Rules")
    rules = [
        ("contains_code", "Route code prompts to coder models"),
        ("contains_reasoning", "Route reasoning prompts to thinking models"),
        ("short_prompt", "Route short prompts to fast models"),
        ("long_prompt", "Route long prompts to models with large context"),
    ]
    
    for rule_type, description in rules:
        add = input(f"   Add rule: {description}? (y/n): ").strip().lower()
        if add == 'y':
            use_local = input(f"      Use local models? (y/n): ").strip().lower() == 'y'
            models = input(f"      Preferred models (comma-separated): ").strip()
            
            rule = {
                "if": rule_type,
                "use_local": use_local,
            }
            if models:
                rule["models"] = [m.strip() for m in models.split(",")]
            
            profile["routing"].append(rule)
    
    return profile


def generate_example_config() -> dict:
    """Generate example configuration with popular providers."""
    return {
        "profiles": {
            "coding": {
                "local": {
                    "provider": "ollama",
                    "endpoint": "http://localhost:11434",
                    "models": ["codellama", "llama3", "mistral"],
                },
                "cloud": {
                    "providers": {
                        "kilo": {
                            "models": ["minimax/m2.5:free", "z-ai/glm-5:free"],
                        },
                        "groq": {
                            "models": ["llama-3.1-70b-versatile"],
                        },
                    }
                },
                "routing": [
                    {"if": "contains_code", "use_local": True, "models": ["codellama"]},
                    {"if": "short_prompt", "use_local": True, "models": ["llama3"]},
                ],
                "yolo": False,
            },
            "chat": {
                "local": {
                    "provider": "ollama",
                    "endpoint": "http://localhost:11434",
                    "models": ["llama3", "mistral"],
                },
                "cloud": {
                    "providers": {
                        "kilo": {
                            "models": ["minimax/m2.5:free"],
                        },
                        "openrouter": {
                            "models": ["openrouter/free"],
                        },
                    }
                },
                "routing": [
                    {"if": "short_prompt", "use_local": True},
                ],
                "yolo": False,
            },
            "yolo": {
                "local": {
                    "provider": "ollama",
                    "endpoint": "http://localhost:11434",
                    "models": ["llama3", "codellama", "mistral"],
                },
                "cloud": {
                    "providers": {
                        "kilo": {"models": ["minimax/m2.5:free", "giga-potato"]},
                        "groq": {"models": ["llama-3.1-70b-versatile", "mixtral-8x7b-32768"]},
                        "openrouter": {"models": ["openrouter/free", "anthropic/claude-3-haiku"]},
                    }
                },
                "yolo": True,
            },
        },
        "default_profile": "chat",
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
        },
    }


def save_config(config: dict, path: str = None):
    """Save configuration to file."""
    path = path or "picorouter.yaml"
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"\n✅ Config saved to {path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PicoRouter - Minimal AI Model Router")
    parser.add_argument("--config", "-c", help="Config file path")
    parser.add_argument("--profile", "-p", help="Profile to use")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Generate config")
    config_parser.add_argument("--output", "-o", help="Output file")
    config_parser.add_argument("--example", "-e", help="Generate example config", action="store_true")
    
    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Chat interactively")
    chat_parser.add_argument("--message", "-m", required=True, help="Message to send")
    
    args = parser.parse_args()
    
    if args.command == "config":
        if args.example:
            config = generate_example_config()
        else:
            config = create_config_interactive()
        
        save_config(config, args.output)
        print("\n📝 Add your API keys as environment variables:")
        print("   export KILO_API_KEY=\"sk-...\"")
        print("   export GROQ_API_KEY=\"gsk_...\"")
        print("   export OPENROUTER_API_KEY=\"sk-or-...\"")
    
    elif args.command == "serve":
        router = PicoRouter(profile_name=args.profile)
        
        # Setup handler
        APIHandler.router = router
        
        host = args.host
        port = args.port
        
        server = HTTPServer((host, port), APIHandler)
        print(f"🚀 PicoRouter server running on http://{host}:{port}")
        print(f"📡 Endpoint: http://{host}:{port}/v1")
        print(f"📋 Profiles: {list(router.config.profiles.keys())}")
        print(f"🔀 Current: {router.profile_name}")
        print(f"\n💡 Point your LLM app to: http://localhost:{port}/v1")
        print("\nPress Ctrl+C to stop\n")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            server.shutdown()
    
    elif args.command == "chat":
        router = PicoRouter(profile_name=args.profile)
        
        messages = [{"role": "user", "content": args.message}]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(router.chat(messages))
            content = result.get("message", {}).get("content", "")
            print(f"\n🤖 {content}")
        finally:
            loop.close()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
