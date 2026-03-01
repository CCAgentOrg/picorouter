"""PicoRouter - Storage backends for logging.

Supports:
- JSONL (file) - default
- SQLite - embedded
- Turso/LibSQL - local-first with sync
"""

import json
import sqlite3
import logging

logger = logging.getLogger(__name__)
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class StorageBackend:
    """Base storage backend."""

    def log(self, entry: dict) -> None:
        raise NotImplementedError

    def get_stats(self) -> Dict:
        raise NotImplementedError

    def get_recent(self, limit: int = 50) -> List:
        raise NotImplementedError

    def get_cost_by_key(self, key_name: str, period: str = "monthly") -> float:
        """Get total cost for a key within a time period.
        
        Args:
            key_name: Name of the key
            period: monthly, daily, or lifetime
        
        Returns:
            Total cost in USD
        """
        raise NotImplementedError

    def close(self) -> None:
        pass


class JSONLBackend(StorageBackend):
    """JSONL file backend (default)."""

    def __init__(self, log_file: str = "logs/requests.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self.stats = {
            "total_requests": 0,
            "by_provider": {},
            "by_model": {},
            "by_profile": {},
            "total_tokens": 0,
            "total_cost_usd": 0,
            "errors": 0,
        }
        self._load_stats()

    def _load_stats(self):
        """Load existing stats from log file."""
        if not self.log_file.exists():
            return

        with open(self.log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    self._update_stats(entry)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Skipping invalid log entry: {e}")
                    continue

    def _update_stats(self, entry: dict):
        self.stats["total_requests"] += 1
        for key in ["provider", "model", "profile"]:
            val = entry.get(key, "unknown")
            bucket = f"by_{key}"
            self.stats[bucket][val] = self.stats[bucket].get(val, 0) + 1

        tokens = entry.get("tokens_used", 0)
        self.stats["total_tokens"] += tokens

        prov = entry.get("provider", "unknown")
        cost = (tokens / 1_000_000) * COST_PER_MILLION.get(prov, 0.50)
        self.stats["total_cost_usd"] += cost

        if entry.get("status") == "error":
            self.stats["errors"] += 1

    def log(self, entry: dict):
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        self._update_stats(entry)

    def get_stats(self) -> Dict:
        return self.stats

    def get_recent(self, limit: int = 50) -> List:
        if not self.log_file.exists():
            return []

        entries = []
        with open(self.log_file) as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Skipping invalid log entry: {e}")
                    continue
        return entries[-limit:]


    def get_cost_by_key(self, key_name: str, period: str = "monthly") -> float:
        """Get total cost for a key within a time period."""
        if not self.log_file.exists():
            return 0.0
        
        from datetime import datetime, timedelta
        
        # Calculate time threshold
        now = datetime.now()
        if period == "daily":
            threshold = (now - timedelta(days=1)).isoformat()
        elif period == "monthly":
            threshold = (now - timedelta(days=30)).isoformat()
        else:  # lifetime
            threshold = "1970-01-01"
        
        total_cost = 0.0
        with open(self.log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    # Check if entry matches key and is within time period
                    if entry.get("key") == key_name and entry.get("timestamp", "") >= threshold:
                        total_cost += entry.get("cost_usd", 0)
                except (json.JSONDecodeError, KeyError):
                    continue
        
        return total_cost


class SQLiteBackend(StorageBackend):
    """SQLite backend (embedded)."""

    def __init__(self, db_path: str = "logs/picorouter.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_db()

    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                profile TEXT,
                key_name TEXT,
                provider TEXT,
                model TEXT,
                tokens_used INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                status TEXT,
                error TEXT,
                duration_ms INTEGER,
                prompt_tokens INTEGER,
                completion_tokens INTEGER
            );
            
            CREATE INDEX IF NOT EXISTS idx_timestamp ON requests(timestamp);
            CREATE INDEX IF NOT EXISTS idx_provider ON requests(provider);
            CREATE INDEX IF NOT EXISTS idx_key ON requests(key_name);
            
            CREATE TABLE IF NOT EXISTS keys (
                name TEXT PRIMARY KEY,
                created TEXT,
                expires TEXT,
                rate_limit INTEGER,
                total_requests INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0
            );
        """)
        self.conn.commit()

    def log(self, entry: dict):
        self.conn.execute(
            """
            INSERT INTO requests (timestamp, profile, key_name, provider, model, 
                tokens_used, cost_usd, status, error, duration_ms, 
                prompt_tokens, completion_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                entry.get("timestamp", datetime.now().isoformat()),
                entry.get("profile"),
                entry.get("key"),
                entry.get("provider"),
                entry.get("model"),
                entry.get("tokens_used", 0),
                entry.get("cost_usd", 0),
                entry.get("status"),
                entry.get("error"),
                entry.get("duration_ms"),
                entry.get("prompt_tokens"),
                entry.get("completion_tokens"),
            ),
        )
        self.conn.commit()

    def get_stats(self) -> Dict:
        cur = self.conn.cursor()

        stats = {
            "total_requests": 0,
            "by_provider": {},
            "by_model": {},
            "by_profile": {},
            "total_tokens": 0,
            "total_cost_usd": 0,
            "errors": 0,
        }

        # Total requests
        cur.execute("SELECT COUNT(*) FROM requests")
        stats["total_requests"] = cur.fetchone()[0] or 0

        # By provider
        cur.execute("SELECT provider, COUNT(*) FROM requests GROUP BY provider")
        for row in cur.fetchall():
            if row[0]:
                stats["by_provider"][row[0]] = row[1]

        # By model
        cur.execute("SELECT model, COUNT(*) FROM requests GROUP BY model")
        for row in cur.fetchall():
            if row[0]:
                stats["by_model"][row[0]] = row[1]

        # By profile
        cur.execute("SELECT profile, COUNT(*) FROM requests GROUP BY profile")
        for row in cur.fetchall():
            if row[0]:
                stats["by_profile"][row[0]] = row[1]

        # Tokens
        cur.execute("SELECT SUM(tokens_used) FROM requests")
        stats["total_tokens"] = cur.fetchone()[0] or 0

        # Cost
        cur.execute("SELECT SUM(cost_usd) FROM requests")
        stats["total_cost_usd"] = cur.fetchone()[0] or 0

        # Errors
        cur.execute("SELECT COUNT(*) FROM requests WHERE status = 'error'")
        stats["errors"] = cur.fetchone()[0] or 0

        return stats

    def get_recent(self, limit: int = 50) -> List:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT timestamp, profile, key_name, provider, model, 
                tokens_used, cost_usd, status, error
            FROM requests 
            ORDER BY id DESC 
            LIMIT ?
        """,
            (limit,),
        )

        rows = cur.fetchall()
        entries = []
        for row in rows:
            entries.append(
                {
                    "timestamp": row[0],
                    "profile": row[1],
                    "key": row[2],
                    "provider": row[3],
                    "model": row[4],
                    "tokens_used": row[5],
                    "cost_usd": row[6],
                    "status": row[7],
                    "error": row[8],
                }
            )
        return list(reversed(entries))

    def close(self):
        self.conn.close()


    def get_cost_by_key(self, key_name: str, period: str = "monthly") -> float:
        """Get total cost for a key within a time period."""
        from datetime import datetime, timedelta
        
        # Calculate time threshold
        now = datetime.now()
        if period == "daily":
            threshold = (now - timedelta(days=1)).isoformat()
        elif period == "monthly":
            threshold = (now - timedelta(days=30)).isoformat()
        else:  # lifetime
            threshold = "1970-01-01"
        
        cur = self.conn.cursor()
        cur.execute(
            """SELECT SUM(cost_usd) FROM requests 
                WHERE key_name = ? AND timestamp >= ?""",
            (key_name, threshold)
        )
        result = cur.fetchone()[0]
        return result or 0.0


class TursoBackend(SQLiteBackend):
    """Turso/LibSQL backend - local-first with sync."""

    def __init__(self, url: str = None, auth_token: str = None):
        self.url = url or "libsql://local"
        self.auth_token = auth_token

        # Use libsql client if available, else fall back to SQLite
        try:
            import libsql_client

            self._use_libsql = True
            self._client = None  # Will init on first use
        except ImportError:
            self._use_libsql = False

        # For embedded mode, use SQLite path
        if self._use_libsql and self.url.startswith("libsql://"):
            db_path = self.url.replace("libsql://", "").replace("/", "_")
            if not db_path:
                db_path = "local.db"
        else:
            db_path = "logs/turso.db"

        super().__init__(db_path)

    def sync(self):
        """Sync with Turso cloud (if configured)."""
        if not self._use_libsql:
            print("⚠️  LibSQL not installed. Run: pip install libsql")
            return

        # This would sync with Turso
        # self._client.sync()
        print("🔄 Turso sync not implemented - using local SQLite")


# Cost estimation (shared)
COST_PER_MILLION = {
    "local:ollama": 0,
    "local:lmstudio": 0,
    "kilo": 0,
    "groq": 0.18,
    "openrouter": 0,
    "openai": 0.60,
    "anthropic": 0.80,
    "google": 0.00,
    "mistral": 0.40,
    "cohere": 0.30,
    "ai21": 0.40,
    "together": 0.60,
    "deepinfra": 0.44,
    "fireworks": 0.60,
    "replicate": 0.50,
    "azure": 1.00,
    # Virtual providers
    "picorouter/privacy": 0.50,
    "picorouter/free": 0,
    "picorouter/fast": 0.18,
    "picorouter/sota": 1.00,
    "default": 0.50,
    "default": 0.50,
}


def create_backend(backend: str = "jsonl", **kwargs) -> StorageBackend:
    """Create a storage backend.

    Args:
        backend: "jsonl", "sqlite", or "turso"
        **kwargs: Backend-specific options

    Examples:
        # JSONL (default)
        create_backend("jsonl", log_file="logs/requests.jsonl")

        # SQLite
        create_backend("sqlite", db_path="logs/picorouter.db")

        # Turso
        create_backend("turso", url="libsql://my-db.turso.io", auth_token="...")
    """
    if backend == "jsonl":
        return JSONLBackend(kwargs.get("log_file", "logs/requests.jsonl"))
    elif backend == "sqlite":
        return SQLiteBackend(kwargs.get("db_path", "logs/picorouter.db"))
    elif backend == "turso":
        return TursoBackend(kwargs.get("url"), kwargs.get("auth_token"))
    else:
        return JSONLBackend()
