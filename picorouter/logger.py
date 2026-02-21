"""PicoRouter - Request logging."""

import json
from pathlib import Path
from datetime import datetime

COST_PER_MILLION = {
    "local:ollama": 0, "local:lmstudio": 0,
    "kilo": 0, "groq": 0.18, "openrouter": 0, "default": 0.50
}


class Logger:
    """Request logger with JSONL + stats."""
    
    def __init__(self, log_file: str = "logs/requests.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            "total_requests": 0, "by_provider": {}, "by_model": {},
            "by_profile": {}, "total_tokens": 0, "total_cost_usd": 0, "errors": 0
        }
    
    def log(self, entry: dict):
        # Write JSONL
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        # Update stats
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
    
    def get_stats(self) -> dict:
        return self.stats
    
    def get_recent(self, limit: int = 50) -> list:
        if not self.log_file.exists():
            return []
        
        entries = []
        with open(self.log_file) as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except:
                    continue
        return entries[-limit:]
