"""PicoRouter - Configuration with pluggable backends.

Supports:
- YAML file (default)
- SQLite (local DB)
- Turso/LibSQL (syncs)
"""

import os
import yaml
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

CONFIG_PATHS = [
    Path.cwd() / "picorouter.yaml",
    Path.home() / ".picorouter.yaml",
    Path.home() / ".config" / "picorouter.yaml",
]


class ConfigBackend:
    """Base config backend."""
    
    def load(self) -> dict:
        raise NotImplementedError
    
    def save(self, config: dict) -> None:
        raise NotImplementedError
    
    def watch(self, callback) -> None:
        """Watch for changes (optional)."""
        pass


class FileBackend(ConfigBackend):
    """YAML file backend (default)."""
    
    def __init__(self, path: str = None):
        self.path = path or self._find_path()
    
    def _find_path(self) -> str | None:
        for p in CONFIG_PATHS:
            if p.exists():
                return str(p)
        return str(CONFIG_PATHS[0])
    
    def load(self) -> dict:
        if not Path(self.path).exists():
            return {}
        with open(self.path) as f:
            return yaml.safe_load(f) or {}
    
    def save(self, config: dict) -> None:
        with open(self.path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)


class SQLiteConfigBackend(ConfigBackend):
    """SQLite config backend."""
    
    def __init__(self, db_path: str = "logs/picorouter.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_db()
    
    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated TEXT
            );
            
            CREATE TABLE IF NOT EXISTS routing_rules (
                id INTEGER PRIMARY KEY,
                profile TEXT NOT NULL,
                condition TEXT,
                use_local INTEGER,
                providers TEXT,
                model TEXT
            );
            
            CREATE TABLE IF NOT EXISTS profiles (
                name TEXT PRIMARY KEY,
                config TEXT,
                updated TEXT
            );
        """)
        self.conn.commit()
    
    def load(self) -> dict:
        cur = self.conn.cursor()
        
        # Load config rows
        config = {}
        cur.execute("SELECT key, value FROM config")
        for key, value in cur.fetchall():
            try:
                config[key] = json.loads(value)
            except:
                config[key] = value
        
        # Load profiles
        if "profiles" not in config:
            config["profiles"] = {}
        cur.execute("SELECT name, config FROM profiles")
        for name, cfg in cur.fetchall():
            if cfg:
                config["profiles"][name] = json.loads(cfg)
        
        return config
    
    def save(self, config: dict) -> None:
        cur = self.conn.cursor()
        
        # Save top-level config
        for key, value in config.items():
            if key == "profiles":
                continue  # Handle separately
            cur.execute(
                "INSERT OR REPLACE INTO config (key, value, updated) VALUES (?, ?, ?)",
                (key, json.dumps(value), datetime.now().isoformat())
            )
        
        # Save profiles
        for name, profile_cfg in config.get("profiles", {}).items():
            cur.execute(
                "INSERT OR REPLACE INTO profiles (name, config, updated) VALUES (?, ?, ?)",
                (name, json.dumps(profile_cfg), datetime.now().isoformat())
            )
        
        self.conn.commit()
    
    def close(self):
        self.conn.close()


class TursoConfigBackend(SQLiteConfigBackend):
    """Turso/LibSQL config backend - same as SQLite but with sync."""
    
    def __init__(self, url: str = None, auth_token: str = None, db_path: str = "logs/config.db"):
        super().__init__(db_path)
        self.turso_url = url
        self.auth_token = auth_token
    
    def sync(self):
        """Sync with Turso cloud."""
        # Would use libsql_client.sync() here
        print("🔄 Turso sync not implemented")


# Factory
def create_config_backend(backend: str = "file", **kwargs) -> ConfigBackend:
    """Create a config backend.
    
    Args:
        backend: "file", "sqlite", or "turso"
    """
    if backend == "file":
        return FileBackend(kwargs.get("path"))
    elif backend == "sqlite":
        return SQLiteConfigBackend(kwargs.get("db_path", "logs/picorouter.db"))
    elif backend == "turso":
        return TursoConfigBackend(
            kwargs.get("url"),
            kwargs.get("auth_token"),
            kwargs.get("db_path", "logs/config.db")
        )
    else:
        return FileBackend()


# Legacy API (backward compatible)
def load_config(path: str = None) -> dict:
    """Load configuration (legacy)."""
    if path:
        return FileBackend(path).load()
    
    # Try file first
    cfg = FileBackend().load()
    if cfg:
        return cfg
    
    # Try env-based backend
    backend = os.getenv("PICOROUTER_CONFIG_BACKEND", "file")
    if backend != "file":
        return create_config_backend(backend).load()
    
    return {}


def find_config() -> str | None:
    """Find config file path (legacy)."""
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
                        "kilo": {"models": ["minimax/m2.5:free"]},
                        "groq": {"models": ["llama-3.1-70b-versatile"]},
                        "openrouter": {"models": ["openrouter/free"]}
                    }
                },
                "yolo": True
            }
        },
        "default_profile": "chat",
        "server": {"host": "0.0.0.0", "port": 8080},
        "storage": {
            "backend": "jsonl",
            "log_file": "logs/requests.jsonl"
        },
        "config": {
            "backend": "file"  # file, sqlite, turso
        }
    }


def save_config(config: dict, path: str = "picorouter.yaml"):
    """Save configuration to file (legacy)."""
    backend = config.get("config", {}).get("backend", "file")
    
    if backend == "file":
        FileBackend(path).save(config)
    else:
        create_config_backend(backend).save(config)
