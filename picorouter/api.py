"""PicoRouter - HTTP API server."""

import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from picorouter.providers import Router


class APIHandler(BaseHTTPRequestHandler):
    router: Router = None
    
    def log_message(self, fmt, *args):
        pass  # Silence default logging
    
    def send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
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
                        limit = int(q.split("limit=")[1].split("&")[0])
                except:
                    pass
            self.send_json({"logs": self.router.logger.get_recent(limit)})
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def handle_models(self):
        models = []
        for m in self.router.profile.get("local", {}).get("models", []):
            models.append({"id": f"local:{m}", "object": "model", "created": 0, "owned_by": "local"})
        for name, prov in self.router.cloud.items():
            for m in prov.models:
                models.append({"id": f"{name}:{m}", "object": "model", "created": 0, "owned_by": name})
        self.send_json({"object": "list", "data": models})
    
    def do_POST(self):
        if self.path not in ["/v1/chat/completions", "/v1/completions"]:
            self.send_json({"error": "Not found"}, 404)
            return
        
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return
        
        if self.path == "/v1/chat/completions":
            self.handle_chat(data)
        else:
            self.send_json({"error": "Not implemented"}, 501)
    
    def handle_chat(self, data: dict):
        messages = data.get("messages", [])
        model = data.get("model", "")
        
        kwargs = {k: v for k, v in data.items() 
                  if k in ["temperature", "max_tokens", "top_p", "stream"]}
        
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
            self.router.logger.log({
                "timestamp": datetime.now().isoformat(),
                "profile": self.router.profile_name,
                "provider": "failed",
                "model": model or "auto",
                "status": "error",
                "error": str(e)[:200]
            })
            self.send_json({"error": str(e)}, 500)


def run_server(router: Router, host: str = "0.0.0.0", port: int = 8080):
    """Run the HTTP server."""
    APIHandler.router = router
    server = HTTPServer((host, port), APIHandler)
    print(f"🚀 PicoRouter on http://{host}:{port}")
    print(f"   Endpoint: http://{host}:{port}/v1")
    server.serve_forever()
