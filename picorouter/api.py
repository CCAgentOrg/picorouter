"""PicoRouter - HTTP API server."""

import json
import os
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from picorouter.providers import Router


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # ip -> [(timestamp, count)]
    
    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        if ip in self.requests:
            self.requests[ip] = [t for t in self.requests[ip] if t > minute_ago]
        
        count = len(self.requests.get(ip, []))
        
        if count >= self.requests_per_minute:
            return False
        
        self.requests.setdefault(ip, []).append(now)
        return True


class APIHandler(BaseHTTPRequestHandler):
    router: Router = None
    rate_limiter: RateLimiter = None
    api_key: str = None
    
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
    
    def check_auth(self) -> bool:
        """Check API key if configured."""
        if not self.api_key:
            return True  # No auth configured
        
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token == self.api_key:
                return True
        
        return False
    
    def check_rate_limit(self) -> bool:
        """Check rate limit."""
        if not self.rate_limiter:
            return True
        
        ip = self.client_address[0]
        return self.rate_limiter.is_allowed(ip)
    
    def do_GET(self):
        # Auth check for protected endpoints
        if self.path in ["/stats", "/logs"]:
            if not self.check_auth():
                self.send_error_json(401, "Unauthorized")
                return
        
        # Rate limit check
        if not self.check_rate_limit():
            self.send_error_json(429, "Rate limit exceeded")
            return
        
        if self.path == "/v1/models":
            self.handle_models()
        elif self.path == "/health":
            self.send_json({"status": "ok"})
        elif self.path == "/stats":
            self.send_json(self.router.logger.get_stats())
        elif self.path == "/logs":
            limit = 50
            if "?" in self.path:
                try:
                    q = self.path.split("?")[1]
                    if "limit=" in q:
                        limit = min(max(int(q.split("limit=")[1].split("&")[0]), 1), 100)
                except:
                    limit = 50
            self.send_json({"logs": self.router.logger.get_recent(limit)})
        else:
            self.send_error_json(404, "Not found")
    
    def do_POST(self):
        # Rate limit check
        if not self.check_rate_limit():
            self.send_error_json(429, "Rate limit exceeded")
            return
        
        if self.path not in ["/v1/chat/completions", "/v1/completions"]:
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
            models.append({"id": f"local:{m}", "object": "model", "created": 0, "owned_by": "local"})
        for name, prov in self.router.cloud.items():
            for m in prov.models:
                models.append({"id": f"{name}:{m}", "object": "model", "created": 0, "owned_by": name})
        self.send_json({"object": "list", "data": models})
    
    def handle_chat(self, data: dict):
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
        
        model = data.get("model", "")
        
        # Whitelist allowed parameters
        allowed = {"temperature", "max_tokens", "top_p", "stream", "stop"}
        kwargs = {k: v for k, v in data.items() if k in allowed}
        
        # Validate numeric params
        if "max_tokens" in kwargs:
            if not isinstance(kwargs["max_tokens"], int) or kwargs["max_tokens"] > 32000:
                self.send_error_json(400, "max_tokens must be integer <= 32000")
                return
        
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.router.chat(messages, **kwargs))
            loop.close()
            
            content = result.get("message", {}).get("content", "")
            
            response = {
                "id": f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": model or "unknown",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop"
                }],
                "usage": result.get("usage", {})
            }
            
            self.router.logger.log({
                "timestamp": datetime.now().isoformat(),
                "profile": self.router.profile_name,
                "provider": "unknown",
                "model": model or "auto",
                "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                "status": "success"
            })
            
            self.send_json(response)
            
        except Exception as e:
            # Log full error server-side only
            self.router.logger.log({
                "timestamp": datetime.now().isoformat(),
                "profile": self.router.profile_name,
                "provider": "failed",
                "model": model or "auto",
                "status": "error",
                "error": "Request failed"
            })
            # Send generic error to client
            self.send_error_json(500, "Request failed")


def run_server(
    router: Router, 
    host: str = "0.0.0.0", 
    port: int = 8080,
    api_key: str = None,
    rate_limit: int = 60
):
    """Run the HTTP server."""
    APIHandler.router = router
    APIHandler.rate_limiter = RateLimiter(rate_limit) if rate_limit > 0 else None
    APIHandler.api_key = api_key or os.getenv("PICOROUTER_API_KEY")
    
    server = HTTPServer((host, port), APIHandler)
    print(f"🚀 PicoRouter on http://{host}:{port}")
    print(f"   Endpoint: http://{host}:{port}/v1")
    
    if APIHandler.api_key:
        print("   🔐 API Key: enabled")
    if APIHandler.rate_limiter:
        print(f"   ⚡ Rate limit: {rate_limit}/min")
    
    server.serve_forever()
