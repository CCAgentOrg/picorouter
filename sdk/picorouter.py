# PicoRouter SDK
# Python client library

import requests
from typing import Optional


class PicoRouter:
    """Python SDK for PicoRouter."""
    
    def __init__(
        self, 
        base_url: str = "http://localhost:8080",
        api_key: str = None,
        timeout: int = 120
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
    
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.base_url}{endpoint}"
        resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp.json()
    
    # === Chat ===
    
    def chat(
        self,
        messages: list,
        model: str = None,
        profile: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> dict:
        """Send chat request."""
        payload = {
            "messages": messages,
            "temperature": temperature,
        }
        if model:
            payload["model"] = model
        if profile:
            payload["profile"] = profile
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        payload.update({k: v for k, v in kwargs.items() 
                       if k in ["top_p", "stream", "stop"]})
        
        return self._request("POST", "/v1/chat/completions", json=payload)
    
    def chat_simple(self, message: str, **kwargs) -> str:
        """Simple chat with single message."""
        return self.chat([{"role": "user", "content": message}], **kwargs)
    
    # === Models ===
    
    def models(self) -> list:
        """List available models."""
        return self._request("GET", "/v1/models")["data"]
    
    # === Stats & Logs ===
    
    def stats(self) -> dict:
        """Get usage statistics."""
        return self._request("GET", "/stats")
    
    def logs(self, limit: int = 50) -> list:
        """Get recent logs."""
        return self._request("GET", f"/logs?limit={limit}")["logs"]
    
    # === Health ===
    
    def health(self) -> bool:
        """Check if server is healthy."""
        try:
            return self._request("GET", "/health")["status"] == "ok"
        except:
            return False


# === Convenience ===

def chat(
    message: str,
    base_url: str = "http://localhost:8080",
    api_key: str = None,
    **kwargs
) -> str:
    """Quick chat function."""
    client = PicoRouter(base_url, api_key)
    return client.chat_simple(message, **kwargs)
