"""PicoRouter - API Key management."""

import hashlib
import secrets
import os
from datetime import datetime
from typing import Optional


def hash_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def generate_key() -> str:
    """Generate a random API key."""
    return f"pico_{secrets.token_urlsafe(24)}"


class KeyManager:
    """Manage multiple API keys with capabilities."""
    
    def __init__(self, keys_config: dict = None):
        self.keys = keys_config or {}
    
    def validate_key(self, key: str) -> Optional[dict]:
        """Validate key and return its capabilities."""
        if not key:
            return None
        
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        for name, info in self.keys.items():
            stored_hash = info.get("hash", "")
            if key_hash.startswith(stored_hash[:16]) or stored_hash == key_hash[:16]:
                # Check expiration
                if info.get("expires"):
                    exp = datetime.fromisoformat(info["expires"])
                    if datetime.now() > exp:
                        return None
                return {
                    "name": name,
                    "capabilities": info.get("capabilities", {}),
                    "rate_limit": info.get("rate_limit"),
                    "profiles": info.get("profiles", []),
                    "readonly": info.get("readonly", False)
                }
        
        return None
    
    def add_key(
        self, 
        name: str, 
        rate_limit: int = None,
        profiles: list = None,
        expires: str = None,
        readonly: bool = False
    ) -> str:
        """Add a new key and return it."""
        key = generate_key()
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        
        self.keys[name] = {
            "hash": key_hash,
            "rate_limit": rate_limit,
            "profiles": profiles or ["chat"],
            "expires": expires,
            "readonly": readonly,
            "capabilities": {
                "chat": not readonly,
                "models": True,
                "stats": True,
                "logs": not readonly
            },
            "created": datetime.now().isoformat()
        }
        
        return key
    
    def remove_key(self, name: str) -> bool:
        """Remove a key by name."""
        if name in self.keys:
            del self.keys[name]
            return True
        return False
    
    def list_keys(self) -> list:
        """List keys (without showing the actual key)."""
        return [
            {
                "name": name,
                "profiles": info.get("profiles", []),
                "rate_limit": info.get("rate_limit"),
                "expires": info.get("expires"),
                "readonly": info.get("readonly", False),
                "created": info.get("created")
            }
            for name, info in self.keys.items()
        ]
    
    def get_config(self) -> dict:
        """Get keys config for saving."""
        return self.keys
    
    @staticmethod
    def from_config(config: dict) -> "KeyManager":
        """Create KeyManager from config."""
        return KeyManager(config.get("keys", {}))
