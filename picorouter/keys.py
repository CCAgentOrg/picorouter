"""PicoRouter - API Key management."""

import hashlib
import secrets
import os
from datetime import datetime
from typing import Optional, List, Dict


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
                    "readonly": info.get("readonly", False),
                    "budget": info.get("budget"),  # Monthly budget limit in USD
                    "budget_period": info.get("budget_period", "monthly")  # monthly, daily, lifetime
                }
        
        return None
    
    def add_key(
        self, 
        name: str, 
        rate_limit: int = None,
        profiles: list = None,
        expires: str = None,
        readonly: bool = False,
        budget: float = None,
        budget_period: str = "monthly"
    ) -> str:
        """Add a new key and return it.
        
        Args:
            name: Key name
            rate_limit: Requests per minute
            profiles: Allowed profiles
            expires: Expiration date (ISO format)
            readonly: Read-only key
            budget: Budget limit in USD (None = unlimited)
            budget_period: monthly, daily, or lifetime
        """
        key = generate_key()
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        
        self.keys[name] = {
            "hash": key_hash,
            "rate_limit": rate_limit,
            "profiles": profiles or ["chat"],
            "expires": expires,
            "readonly": readonly,
            "budget": budget,
            "budget_period": budget_period,
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
    
    def list_keys(self) -> List:
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
    
    def get_config(self) -> Dict:
        """Get keys config for saving."""
        return self.keys
    
    @staticmethod
    def from_config(config: dict) -> "KeyManager":
        """Create KeyManager from config."""
        return KeyManager(config.get("keys", {}))

    def check_budget(self, key_name: str, get_cost_func) -> tuple:
        """Check if key has remaining budget.
        
        Args:
            key_name: Name of the key to check
            get_cost_func: Function to get current spend (key_name, period) -> float
        
        Returns:
            (allowed: bool, message: str, remaining: float)
        """
        key_info = self.keys.get(key_name, {})
        budget = key_info.get("budget")
        
        # No budget set = unlimited
        if budget is None:
            return (True, "unlimited", None)
        
        budget_period = key_info.get("budget_period", "monthly")
        
        # Get current spend
        current_spend = get_cost_func(key_name, budget_period)
        remaining = budget - current_spend
        
        if remaining <= 0:
            return (False, f"Budget exceeded: ${current_spend:.2f}/${budget:.2f} {budget_period}", 0)
        
        return (True, f"${remaining:.2f} remaining", remaining)
