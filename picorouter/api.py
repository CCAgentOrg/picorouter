"""PicoRouter - HTTP API server."""

import json
import os
import time
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from picorouter.router import Router
from picorouter.keys import KeyManager
from picorouter.web_settings import get_settings_html
from picorouter.config import load_config, save_config, find_config

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter with thread-safety."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # key_name -> [(timestamp)]
        self._lock = threading.Lock()

    def is_allowed(self, key_name: str, limit: int = None) -> bool:
        limit = limit or self.requests_per_minute
        now = time.time()
        minute_ago = now - 60

        with self._lock:
            # Clean old entries
            if key_name in self.requests:
                self.requests[key_name] = [
                    t for t in self.requests[key_name] if t > minute_ago
                ]

            count = len(self.requests.get(key_name, []))

            if count >= limit:
                return False

            self.requests.setdefault(key_name, []).append(now)
            return True


class APIHandler(BaseHTTPRequestHandler):
    router: Router = None
    key_manager: KeyManager = None
    rate_limiter: RateLimiter = None

    # Current authenticated key's capabilities
    _auth: dict = None

    def log_message(self, fmt, *args):
        pass  # Silence default logging

    def send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_error_json(self, status: int, message: str):
        """Send error without internal details."""
        self.send_json({"error": message}, status)

    def authenticate(self) -> bool:
        """Authenticate request using API key."""
        auth_header = self.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            # No auth - check if required
            if self.key_manager and self.key_manager.keys:
                self.send_error_json(401, "API key required")
                return False
            return True  # No keys configured, allow

        token = auth_header[7:]

        if not self.key_manager:
            # No key manager - accept any key for backward compat
            return True

        auth = self.key_manager.validate_key(token)
        if not auth:
            self.send_error_json(401, "Invalid API key")
            return False

        self._auth = auth
        return True

    def check_capability(self, cap: str) -> bool:
        """Check if authenticated key has capability."""
        if not self._auth:
            return True  # No auth, allow all

        caps = self._auth.get("capabilities", {})
        return caps.get(cap, False)

    def check_profile(self, profile: str) -> bool:
        """Check if key is allowed to use profile."""
        if not self._auth:
            return True  # No auth, allow all

        allowed = self._auth.get("profiles", [])
        return profile in allowed or "*" in allowed

    def check_rate_limit(self) -> bool:
        """Check rate limit for authenticated key."""
        if not self.rate_limiter:
            return True

        key_name = self._auth.get("name", "anonymous") if self._auth else "anonymous"
        limit = self._auth.get("rate_limit") if self._auth else None

        return self.rate_limiter.is_allowed(key_name, limit)


    def check_budget(self) -> bool:
        """Check if key has remaining budget."""
        if not self._auth:
            return True  # No auth = no budget limit
        
        budget = self._auth.get("budget")
        if budget is None:
            return True  # No budget set = unlimited
        
        key_name = self._auth.get("name")
        budget_period = self._auth.get("budget_period", "monthly")
        
        # Get current spend from logger storage
        if hasattr(self.router, 'logger') and self.router.logger:
            current_spend = self.router.logger.storage.get_cost_by_key(key_name, budget_period)
            remaining = budget - current_spend
            
            if remaining <= 0:
                self.send_error_json(402, f"Budget exceeded: ${current_spend:.2f}/${budget:.2f} {budget_period}")
                return False
        
        return True

    def do_GET(self):
        if not self.authenticate():
            return

        if not self.check_rate_limit():
            self.send_error_json(429, "Rate limit exceeded")
            return

        if self.path == "/v1/models":
            if not self.check_capability("models"):
                self.send_error_json(403, "Capability not allowed")
                return
            self.handle_models()
        elif self.path == "/health":
            self.send_json({"status": "ok"})
        elif self.path == "/stats":
            if not self.check_capability("stats"):
                self.send_error_json(403, "Capability not allowed")
                return
            self.send_json(self.router.logger.get_stats())
        elif self.path == "/logs":
            if not self.check_capability("logs"):
                self.send_error_json(403, "Capability not allowed")
                return
            limit = 50
            if "?" in self.path:
                try:
                    q = self.path.split("?")[1]
                    if "limit=" in q:
                        limit = min(
                            max(int(q.split("limit=")[1].split("&")[0]), 1), 100
                        )
                except (ValueError, IndexError) as e:
                    logger.debug(f"Invalid limit parameter in query string: {e}")
                    limit = 50
            self.send_json({"logs": self.router.logger.get_recent(limit)})
        elif self.path == "/settings" or self.path == "/settings/":
            self.send_html(get_settings_html())
        elif self.path == "/settings/config":
            self.handle_settings_config()
        elif self.path.startswith("/settings/keys"):
            self.handle_settings_keys()
        elif self.path == "/v1/providers":
            self.handle_providers()
        else:
            self.send_error_json(404, "Not found")

    def do_POST(self):
        # Settings endpoints don't require auth/rate_limit/budget
        is_settings = self.path.startswith("/settings/")
        
        if not is_settings:
            if not self.authenticate():
                return

            if not self.check_rate_limit():
                self.send_error_json(429, "Rate limit exceeded")
                return

            # Check budget before processing request
            if not self.check_budget():
                return  # check_budget() sends error response

        # Handle settings endpoints
        if self.path == "/settings/config":
            self.handle_settings_config()
            return
        elif self.path == "/settings/keys" or self.path.startswith("/settings/keys/"):
            self.handle_settings_keys()
            return
        elif self.path not in ["/v1/chat/completions", "/v1/completions"]:
            self.send_error_json(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))

        # Limit request size (1MB max)
        if length > 1_000_000:
            self.send_error_json(413, "Request too large")
            return

        body = self.rfile.read(length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error_json(400, "Invalid JSON")
            return

        if self.path == "/v1/chat/completions":
            self.handle_chat(data)
        else:
            self.send_error_json(501, "Not implemented")

    def handle_models(self):
        models = []
        for m in self.router.profile.get("local", {}).get("models", []):
            models.append(
                {
                    "id": f"local:{m}",
                    "object": "model",
                    "created": 0,
                    "owned_by": "local",
                }
            )
        for name, prov in self.router.cloud.items():
            for m in prov.models:
                models.append(
                    {
                        "id": f"{name}:{m}",
                        "object": "model",
                        "created": 0,
                        "owned_by": name,
                    }
                )
        self.send_json({"object": "list", "data": models})

    def handle_chat(self, data: dict):
        if not self.check_capability("chat"):
            self.send_error_json(403, "Chat not allowed")
            return

        # Check profile access
        profile = data.get("profile", self.router.profile_name)
        if not self.check_profile(profile):
            self.send_error_json(403, f"Profile '{profile}' not allowed")
            return

        # Validate messages
        messages = data.get("messages", [])
        if not messages:
            self.send_error_json(400, "messages is required")
            return

        if not isinstance(messages, list):
            self.send_error_json(400, "messages must be an array")
            return

        # Limit messages count
        if len(messages) > 50:
            self.send_error_json(400, "Too many messages (max 50)")
            return

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                self.send_error_json(400, f"messages[{i}] must be an object")
                return
            if "role" not in msg:
                self.send_error_json(400, f"messages[{i}].role is required")
                return
            if "content" not in msg:
                self.send_error_json(400, f"messages[{i}].content is required")
                return
            if msg["role"] not in ["system", "user", "assistant"]:
                self.send_error_json(
                    400, f"messages[{i}].role must be 'system', 'user', or 'assistant'"
                )
                return
            content = str(msg["content"])
            if len(content) > 100000:
                self.send_error_json(
                    400, f"messages[{i}].content too long (max 100000 characters)"
                )
                return

        model = data.get("model", "")

        # Whitelist allowed parameters (including model for explicit routing)
        allowed = {"temperature", "max_tokens", "top_p", "stream", "stop", "profile", "model"}
        kwargs = {k: v for k, v in data.items() if k in allowed}

        if "temperature" in kwargs:
            try:
                temp = float(kwargs["temperature"])
                if not (0.0 <= temp <= 2.0):
                    self.send_error_json(400, "temperature must be between 0.0 and 2.0")
                    return
            except (ValueError, TypeError):
                self.send_error_json(400, "temperature must be a number")
                return

        if "top_p" in kwargs:
            try:
                top_p_val = float(kwargs["top_p"])
                if not (0.0 <= top_p_val <= 1.0):
                    self.send_error_json(400, "top_p must be between 0.0 and 1.0")
                    return
            except (ValueError, TypeError):
                self.send_error_json(400, "top_p must be a number")
                return

        if "max_tokens" in kwargs:
            try:
                max_t = int(kwargs["max_tokens"])
                if max_t < 1 or max_t > 32000:
                    self.send_error_json(
                        400, "max_tokens must be integer between 1 and 32000"
                    )
                    return
            except (ValueError, TypeError):
                self.send_error_json(400, "max_tokens must be an integer")
                return

        if model:
            if not isinstance(model, str):
                self.send_error_json(400, "model must be a string")
                return
            if len(model) > 200:
                self.send_error_json(400, "model name too long (max 200 characters)")
                return

        # Validate message structure
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                self.send_error_json(400, f"messages[{i}] must be an object")
                return
            if "role" not in msg:
                self.send_error_json(400, f"messages[{i}].role is required")
                return
            if "content" not in msg:
                self.send_error_json(400, f"messages[{i}].content is required")
                return
            if msg["role"] not in ["system", "user", "assistant"]:
                self.send_error_json(
                    400, f"messages[{i}].role must be 'system', 'user', or 'assistant'"
                )
                return
            # Limit content length per message
            content = str(msg["content"])
            if len(content) > 100000:
                self.send_error_json(
                    400, f"messages[{i}].content too long (max 100000 characters)"
                )
                return



        # Validate temperature
        if "temperature" in kwargs:
            try:
                temp = float(kwargs["temperature"])
                if not (0.0 <= temp <= 2.0):
                    self.send_error_json(400, "temperature must be between 0.0 and 2.0")
                    return
            except (ValueError, TypeError):
                self.send_error_json(400, "temperature must be a number")
                return

        # Validate top_p
        if "top_p" in kwargs:
            try:
                top_p_val = float(kwargs["top_p"])
                if not (0.0 <= top_p_val <= 1.0):
                    self.send_error_json(400, "top_p must be between 0.0 and 1.0")
                    return
            except (ValueError, TypeError):
                self.send_error_json(400, "top_p must be a number")
                return

        # Validate max_tokens
        if "max_tokens" in kwargs:
            try:
                max_t = int(kwargs["max_tokens"])
                if max_t < 1 or max_t > 32000:
                    self.send_error_json(
                        400, "max_tokens must be integer between 1 and 32000"
                    )
                    return
            except (ValueError, TypeError):
                self.send_error_json(400, "max_tokens must be an integer")
                return

        # Sanitize model parameter
        if model:
            if not isinstance(model, str):
                self.send_error_json(400, "model must be a string")
                return
            if len(model) > 200:
                self.send_error_json(400, "model name too long (max 200 characters)")
                return

        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Pass headers for intelligent routing
            result = loop.run_until_complete(
                self.router.chat(
                    messages, headers=self.headers, profile=profile, **kwargs
                )
            )
            loop.close()

            content = result.get("message", {}).get("content", "")

            response = {
                "id": f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": model or "unknown",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": result.get("usage", {}),
            }

            self.router.logger.log(
                {
                    "timestamp": datetime.now().isoformat(),
                    "profile": profile,
                    "key": self._auth.get("name", "anonymous")
                    if self._auth
                    else "none",
                    "provider": "unknown",
                    "model": model or "auto",
                    "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                    "status": "success",
                }
            )

            self.send_json(response)

        except Exception as e:
            self.router.logger.log(
                {
                    "timestamp": datetime.now().isoformat(),
                    "profile": profile,
                    "key": self._auth.get("name", "anonymous")
                    if self._auth
                    else "none",
                    "provider": "failed",
                    "model": model or "auto",
                    "status": "error",
                    "error": "Request failed",
                }
            )
            self.send_error_json(500, "Request failed")

    def handle_settings_config(self):
        """Handle GET/PUT for /settings/config"""
        if self.command == "GET":
            # Return current config (without sensitive data)
            config = {}
            if hasattr(self.router, 'config') and self.router.config:
                config = self.router.config.copy()
            self.send_json(config)
        elif self.command == "POST":
            # Update config
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                new_config = json.loads(body)
                from picorouter.config import save_config, find_config
                config_path = find_config()
                if config_path:
                    save_config(new_config, config_path)
                    self.router.config = new_config
                    self.send_json({"status": "ok"})
                else:
                    self.send_error_json(404, "No config file found")
            except json.JSONDecodeError:
                self.send_error_json(400, "Invalid JSON")
            except Exception as e:
                self.send_error_json(500, str(e))
        else:
            self.send_error_json(405, "Method not allowed")

    def handle_settings_keys(self):
        """Handle GET/POST/DELETE for /settings/keys"""
        from picorouter.keys import KeyManager
        from picorouter.config import save_config, find_config
        
        config_path = find_config()
        if not config_path:
            self.send_error_json(404, "No config file found")
            return
        
        # Load current config
        from picorouter.config import load_config
        config = load_config()
        km = KeyManager.from_config(config)
        
        # Parse path for DELETE
        key_name = None
        if self.path.startswith("/settings/keys/"):
            key_name = self.path.split("/settings/keys/")[1]
        
        if self.command == "GET":
            # Return keys info (without hashes)
            keys_info = {}
            for name, info in km.keys.items():
                keys_info[name] = {
                    "profiles": info.get("profiles", []),
                    "rate_limit": info.get("rate_limit"),
                    "expires": info.get("expires"),
                    "readonly": info.get("readonly", False),
                    "budget": info.get("budget"),
                    "budget_period": info.get("budget_period", "monthly"),
                    "created": info.get("created"),
                }
            self.send_json(keys_info)
        elif self.command == "POST":
            # Add new key
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                name = data.get("name")
                if not name:
                    self.send_error_json(400, "Key name required")
                    return
                
                rate_limit = data.get("rate_limit", 60)
                profiles = data.get("profiles", ["chat", "coding", "yolo"])
                if isinstance(profiles, str):
                    profiles = [p.strip() for p in profiles.split(",")]
                readonly = data.get("readonly", False)
                expires = data.get("expires")
                budget = data.get("budget")
                budget_period = data.get("budget_period", "monthly")
                
                key = km.add_key(
                    name,
                    rate_limit=rate_limit,
                    profiles=profiles,
                    readonly=readonly,
                    expires=expires,
                    budget=budget,
                    budget_period=budget_period,
                )
                config["keys"] = km.get_config()
                save_config(config, config_path)
                self.send_json({"key": key, "name": name})
            except json.JSONDecodeError:
                self.send_error_json(400, "Invalid JSON")
            except Exception as e:
                self.send_error_json(500, str(e))
        elif self.command == "DELETE" and key_name:
            # Delete key
            if km.remove_key(key_name):
                config["keys"] = km.get_config()
                save_config(config, config_path)
                self.send_json({"status": "ok"})
            else:
                self.send_error_json(404, "Key not found")
        else:
            self.send_error_json(405, "Method not allowed")


def run_server(
    router: Router, host: str = "0.0.0.0", port: int = 8080, rate_limit: int = 60
):
    """Run the HTTP server."""
    from picorouter.tailscale import get_tailscale_ip, is_tailscale_running

    APIHandler.router = router

    # Initialize key manager from config
    config = router.config
    APIHandler.key_manager = KeyManager.from_config(config)

    # Initialize rate limiter
    APIHandler.rate_limiter = RateLimiter(rate_limit) if rate_limit > 0 else None

    server = HTTPServer((host, port), APIHandler)

    print(f"🚀 PicoRouter on http://{host}:{port}")

    # Show URLs
    urls = [f"http://{host}:{port}/v1"]

    # Add Tailscale URL if available
    if is_tailscale_running():
        ts_ip = get_tailscale_ip()
        if ts_ip:
            urls.append(f"http://{ts_ip}:{port}/v1 (Tailscale)")

    print(f"   Endpoints:")
    for url in urls:
        print(f"     • {url}")

    if APIHandler.key_manager.keys:
        print(f"   🔑 Keys: {len(APIHandler.key_manager.keys)} configured")
    else:
        print("   ⚠️  No API keys configured (open access)")

    if APIHandler.rate_limiter:
        print(f"   ⚡ Rate limit: {rate_limit}/min (global)")

    server.serve_forever()
