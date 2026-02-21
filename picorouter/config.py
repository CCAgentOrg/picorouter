"""PicoRouter - Configuration."""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field

CONFIG_PATHS = [
    Path.cwd() / "picorouter.yaml",
    Path.home() / ".picorouter.yaml",
    Path.home() / ".config" / "picorouter.yaml",
]


def load_config(path: str = None) -> dict:
    """Load configuration from file."""
    if path:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    
    for p in CONFIG_PATHS:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    
    return {}


def find_config() -> str | None:
    """Find config file path."""
    for p in CONFIG_PATHS:
        if p.exists():
            return str(p)
    return None


def generate_example() -> dict:
    """Generate example configuration."""
    return {
        "profiles": {
            "chat": {
                "local": {"provider": "ollama", "endpoint": "http://localhost:11434", "models": ["llama3"]},
                "cloud": {
                    "providers": {
                        "kilo": {"models": ["minimax/m2.5:free"]},
                        "openrouter": {"models": ["openrouter/free"]}
                    }
                },
                "routing": [{"if": "short_prompt", "use_local": True}],
                "yolo": False
            },
            "coding": {
                "local": {"provider": "ollama", "endpoint": "http://localhost:11434", "models": ["codellama"]},
                "cloud": {"providers": {"kilo": {"models": ["minimax/m2.5:free"]}}},
                "routing": [{"if": "contains_code", "use_local": True}],
                "yolo": False
            },
            "yolo": {
                "local": {"provider": "ollama", "endpoint": "http://localhost:11434", "models": ["llama3", "codellama"]},
                "cloud": {
                    "providers": {
                        "kilo": {"models": ["minimax/m2.5:free", "giga-potato"]},
                        "groq": {"models": ["llama-3.1-70b-versatile"]},
                        "openrouter": {"models": ["openrouter/free"]}
                    }
                },
                "yolo": True
            }
        },
        "default_profile": "chat",
        "server": {"host": "0.0.0.0", "port": 8080}
    }


def save_config(config: dict, path: str = "picorouter.yaml"):
    """Save configuration to file."""
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
