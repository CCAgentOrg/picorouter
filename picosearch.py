#!/usr/bin/env python3
"""
PicoSearch - Web Search with Multi-Provider Support + Turso Storage

Providers:
- SearXNG (local/self-hosted)
- Brave Search (API)
- Tavily (API)
- DuckDuckGo (free)

All searches logged to Turso (or JSONL fallback).
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import yaml
from pydantic import BaseModel

__version__ = "0.2.0"

# Config paths
CONFIG_PATHS = [
    Path.cwd() / "picorouter.yaml",
    Path.cwd() / "picosearch.yaml",
    Path.home() / ".picorouter.yaml",
    Path.home() / ".picosearch.yaml",
]

DEFAULT_SEARXNG = "https://ccsearxng.zeabur.app"


# === Data Models ===

class SearchResult(BaseModel):
    title: str
    url: str
    content: str = ""
    engine: str = ""


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    provider: str
    suggestions: list[str] = []


# === Turso Storage ===

class TursoStorage:
    """Turso/LibSQL storage for search logs."""
    
    def __init__(self, url: str):
        self.url = url
        self.use_turso = bool(url)
        if self.use_turso:
            self._init_db()
    
    def _init_db(self):
        """Initialize tables."""
        try:
            import libsql_client
            conn = libsql_client.connect(self.url)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    query TEXT NOT NULL,
                    provider TEXT,
                    results_count INTEGER DEFAULT 0,
                    duration_ms INTEGER DEFAULT 0,
                    error TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_timestamp ON search_logs(timestamp)
            """)
            conn.close()
        except Exception as e:
            print(f"⚠️ Turso init failed: {e}", file=sys.stderr)
            self.use_turso = False
    
    def log_search(self, query: str, provider: str, results_count: int, 
                   duration_ms: int, error: str = None):
        """Log a search to Turso or JSONL."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "provider": provider,
            "results_count": results_count,
            "duration_ms": duration_ms,
            "error": error or "",
        }
        
        if self.use_turso:
            try:
                import libsql_client
                conn = libsql_client.connect(self.url)
                conn.execute(f"""
                    INSERT INTO search_logs (timestamp, query, provider, results_count, duration_ms, error)
                    VALUES ('{entry['timestamp']}', '{entry['query']}', '{entry['provider']}',
                        {entry['results_count']}, {entry['duration_ms']}, '{entry['error']}')
                """)
                conn.close()
            except Exception as e:
                print(f"⚠️ Turso log error: {e}", file=sys.stderr)
        
        # Always write to JSONL as backup
        log_file = Path("logs/search.jsonl")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_stats(self, days: int = 30) -> dict:
        """Get search stats."""
        if self.use_turso:
            try:
                import libsql_client
                conn = libsql_client.connect(self.url)
                
                total = conn.execute("SELECT COUNT(*) as c FROM search_logs").fetchone()
                by_provider = conn.execute("""
                    SELECT provider, COUNT(*) as c, SUM(results_count) as results 
                    FROM search_logs GROUP BY provider
                """).fetchall()
                conn.close()
                
                return {
                    "total_searches": total[0] if total else 0,
                    "by_provider": {row[0]: {"count": row[1], "results": row[2]} for row in by_provider}
                }
            except:
                pass
        
        # Fallback to JSONL
        log_file = Path("logs/search.jsonl")
        if not log_file.exists():
            return {"total_searches": 0, "by_provider": {}}
        
        stats = {"total_searches": 0, "by_provider": {}}
        with open(log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    stats["total_searches"] += 1
                    prov = entry.get("provider", "unknown")
                    if prov not in stats["by_provider"]:
                        stats["by_provider"][prov] = {"count": 0, "results": 0}
                    stats["by_provider"][prov]["count"] += 1
                    stats["by_provider"][prov]["results"] += entry.get("results_count", 0)
                except:
                    continue
        return stats


# === Search Providers ===

class SearXNGProvider:
    """SearXNG search provider."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def search(self, query: str, num_results: int = 10) -> SearchResponse:
        params = {
            "q": query,
            "format": "json",
            "num_results": num_results,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    content=r.get("content", "")[:200],
                    engine=r.get("engine", "searxng"),
                )
                for r in data.get("results", [])[:num_results]
            ]
            
            return SearchResponse(
                query=query,
                results=results,
                provider="searxng",
                suggestions=data.get("suggestions", []),
            )


class BraveProvider:
    """Brave Search API provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
    
    async def search(self, query: str, num_results: int = 10) -> SearchResponse:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": num_results}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    content=r.get("description", ""),
                    engine="brave",
                )
                for r in data.get("web", {}).get("results", [])[:num_results]
            ]
            
            return SearchResponse(
                query=query,
                results=results,
                provider="brave",
                suggestions=data.get("mixed", {}).get("queries", {}).get("query_strings", []),
            )


class DuckDuckGoProvider:
    """DuckDuckGo Lite (free) provider."""
    
    def __init__(self):
        self.base_url = "https://lite.duckduckgo.com/lite/"
    
    async def search(self, query: str, num_results: int = 10) -> SearchResponse:
        params = {"q": query}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Parse HTML results (simple regex approach)
            import re
            html = response.text
            
            results = []
            # Match result blocks
            results_match = re.findall(r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.+?)</a>.*?<a class="result__snippet"[^>]*>(.+?)</a>', html, re.DOTALL)
            
            for url, title, content in results_match[:num_results]:
                results.append(SearchResult(
                    title=title.replace("<br>", " ").strip(),
                    url=url,
                    content=content.replace("<br>", " ").strip()[:200],
                    engine="duckduckgo",
                ))
            
            return SearchResponse(
                query=query,
                results=results,
                provider="duckduckgo",
            )


# === Router ===

class PicoSearch:
    """Multi-provider search router with Turso storage."""
    
    def __init__(self, config: dict = None):
        config = config or {}
        
        # Storage
        db_config = config.get("database", {})
        turso_url = db_config.get("turso_url")
        self.storage = TursoStorage(turso_url)
        
        # Providers (priority order)
        search_config = config.get("search", {})
        
        # SearXNG (local/self-hosted) - always try first
        searxng_url = search_config.get("searxng_url", DEFAULT_SEARXNG)
        self.providers = [SearXNGProvider(searxng_url)]
        
        # Brave API
        brave_key = search_config.get("brave_api_key") or os.getenv("BRAVE_API_KEY")
        if brave_key:
            self.providers.append(BraveProvider(brave_key))
        
        # DuckDuckGo (free fallback)
        self.providers.append(DuckDuckGoProvider())
        
        self.default_provider = "searxng"
    
    async def search(self, query: str, provider: str = None, num_results: int = 10) -> SearchResponse:
        """Search with fallback through providers."""
        import time
        start = time.time()
        
        providers_to_try = []
        
        if provider:
            # Use specified provider
            for p in self.providers:
                if p.__class__.__name__.lower().replace("provider", "") == provider.lower():
                    providers_to_try = [p]
                    break
            if not providers_to_try:
                providers_to_try = self.providers
        else:
            # Try in priority order
            providers_to_try = self.providers
        
        last_error = None
        for p in providers_to_try:
            try:
                result = await p.search(query, num_results)
                duration_ms = int((time.time() - start) * 1000)
                
                # Log success
                self.storage.log_search(
                    query=query,
                    provider=result.provider,
                    results_count=len(result.results),
                    duration_ms=duration_ms,
                )
                
                return result
            except Exception as e:
                last_error = e
                print(f"⚠️ {p.__class__.__name__} failed: {e}", file=sys.stderr)
                continue
        
        # All failed
        duration_ms = int((time.time() - start) * 1000)
        self.storage.log_search(
            query=query,
            provider="failed",
            results_count=0,
            duration_ms=duration_ms,
            error=str(last_error),
        )
        
        raise Exception(f"All search providers failed: {last_error}")
    
    def get_stats(self) -> dict:
        """Get search statistics."""
        return self.storage.get_stats()


# === MCP Server ===

def create_mcp_server(picosearch: PicoSearch):
    """Create MCP server for PicoSearch."""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    import asyncio
    
    server = Server("picosearch")
    
    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="search",
                description="Search the web. Tries SearXNG first (your instance), then falls back to Brave/DuckDuckGo.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "provider": {"type": "string", "description": "Specific provider: searxng, brave, duckduckgo"},
                        "num_results": {"type": "number", "default": 10},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="search_stats",
                description="Get search usage statistics",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "search":
            result = await picosearch.search(
                query=arguments["query"],
                provider=arguments.get("provider"),
                num_results=arguments.get("num_results", 10),
            )
            
            response = f"🔍 **{result.query}** (via {result.provider})\n\n"
            for i, r in enumerate(result.results, 1):
                response += f"**{i}. {r.title}**\n"
                response += f"   {r.content[:150]}...\n"
                response += f"   🔗 {r.url}\n\n"
            
            if result.suggestions:
                response += f"💡 Suggestions: {', '.join(result.suggestions)}"
            
            return [TextContent(type="text", text=response)]
        
        elif name == "search_stats":
            stats = picosearch.get_stats()
            response = "📊 Search Stats\n" + "=" * 30 + "\n"
            response += f"Total Searches: {stats['total_searches']}\n\nBy Provider:\n"
            for prov, data in stats.get("by_provider", {}).items():
                response += f"  {prov}: {data['count']} searches, {data['results']} results\n"
            return [TextContent(type="text", text=response)]
    
    return server


# === CLI ===

def load_config() -> dict:
    """Load config from files."""
    for path in CONFIG_PATHS:
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}
    return {}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PicoSearch - Multi-Provider Web Search")
    parser.add_argument("--config", "-c", help="Config file")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--provider", "-p", help="Specific provider")
    parser.add_argument("--num-results", "-n", type=int, default=10)
    parser.add_argument("--stats", "-s", action="store_true", help="Show stats")
    parser.add_argument("--mcp", action="store_true", help="Run as MCP server")
    args = parser.parse_args()
    
    # Load config
    config = {}
    if args.config:
        with open(args.config) as f:
            config = yaml.safe_load(f) or {}
    else:
        config = load_config()
    
    picosearch = PicoSearch(config)
    
    if args.mcp:
        # Run as MCP server
        server = create_mcp_server(picosearch)
        print("🔍 PicoSearch MCP Server running...")
        print(f"   Default: SearXNG → Brave → DuckDuckGo")
        print(f"   Storage: {'Turso' if picosearch.storage.use_turso else 'JSONL'}")
        
        async def run():
            async with stdio_server() as (read, write):
                await server.run(read, write, server.create_initialization_options())
        
        asyncio.run(run())
    
    elif args.query:
        # CLI search
        async def do_search():
            result = await picosearch.search(
                query=args.query,
                provider=args.provider,
                num_results=args.num_results,
            )
            print(f"\n🔍 Results for: {result.query} (via {result.provider})\n")
            for i, r in enumerate(result.results, 1):
                print(f"{i}. {r.title}")
                print(f"   {r.content[:100]}...")
                print(f"   {r.url}\n")
        
        asyncio.run(do_search())
    
    elif args.stats:
        # Show stats
        stats = picosearch.get_stats()
        print("\n📊 Search Stats")
        print("=" * 40)
        print(f"Total Searches: {stats['total_searches']}\nBy Provider:")
        for prov, data in stats.get("by_provider", {}).items():
            print(f"  {prov}: {data['count']} searches, {data['results']} results")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
