"""PicoRouter - Request logging with pluggable backends."""

from picorouter.storage import create_backend, COST_PER_MILLION, StorageBackend


class Logger:
    """Request logger with swappable storage backends."""
    
    def __init__(
        self, 
        backend: str = "jsonl",
        log_file: str = "logs/requests.jsonl",
        db_path: str = "logs/picorouter.db",
        turso_url: str = None,
        turso_token: str = None
    ):
        # Create storage backend
        if backend == "jsonl":
            self.storage = create_backend("jsonl", log_file=log_file)
        elif backend == "sqlite":
            self.storage = create_backend("sqlite", db_path=db_path)
        elif backend == "turso":
            self.storage = create_backend("turso", url=turso_url, auth_token=turso_token)
        else:
            self.storage = create_backend("jsonl", log_file=log_file)
        
        self._cost_per_million = COST_PER_MILLION
    
    def log(self, entry: dict):
        # Calculate cost
        tokens = entry.get("tokens_used", 0)
        prov = entry.get("provider", "unknown")
        cost = (tokens / 1_000_000) * self._cost_per_million.get(prov, 0.50)
        entry["cost_usd"] = cost
        
        self.storage.log(entry)
    
    def get_stats(self) -> dict:
        return self.storage.get_stats()
    
    def get_recent(self, limit: int = 50) -> list:
        return self.storage.get_recent(limit)
    
    def close(self):
        self.storage.close()
