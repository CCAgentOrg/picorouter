#!/usr/bin/env python3
"""
PicoSearch MCP Server

Wraps SearXNG instance as an MCP tool for AI assistants.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
import yaml
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

__version__ = "0.1.0"

# Config paths
CONFIG_PATHS = [
    Path.cwd() / "picorouter.yaml",
    Path.cwd() / "mcpsearch.yaml",
    Path.home() / ".picorouter.yaml",
    Path.home() / ".mcpsearch.yaml",
]

# Default SearXNG instance
DEFAULT_SEARXNG = "https://ccsearxng.zeabur.app"


class SearchLogger:
    """Simple search request logger - supports Turso."""
    
    def __init__(self, turso_url: str = None):
        self.turso_url = turso_url
        self.use_turso = bool(turso_url)
        
        if self.use_turso:
            self._init_turso()
        else:
            self.log_file = Path("logs/search.jsonl")
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            "total_searches": 0,
            "total_results": 0,
            "errors": 0,
        }
    
    def _init_turso(self):
        """Initialize Turso database."""
        try:
            import libsql_client
            self._turso_exec("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    query TEXT,
                    results_count INTEGER DEFAULT 0,
                    error TEXT
                )
            """)
        except Exception as e:
            print(f"Turso init failed: {e}, using JSONL", file=sys.stderr)
            self.use_turso = False
            self.log_file = Path("logs/search.jsonl")
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _turso_exec(self, sql: str):
        """Execute SQL on Turso."""
        if not self.use_turso:
            return
        try:
            import libsql_client
            conn = libsql_client.connect(self.turso_url)
            conn.execute(sql)
            conn.close()
        except Exception as e:
            print(f"Turso error: {e}", file=sys.stderr)
    
    def log(self, query: str, results_count: int, error: str = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "results_count": results_count,
            "error": error,
        }
        
        if self.use_turso:
            self._turso_exec(f"""
                INSERT INTO search_logs (timestamp, query, results_count, error)
                VALUES ('{entry['timestamp']}', '{entry['query']}', 
                    {entry['results_count']}, '{entry.get('error', '')}')
            """)
        else:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        
        self.stats["total_searches"] += 1
        if error:
            self.stats["errors"] += 1
        else:
            self.stats["total_results"] += results_count
    
    def get_stats(self):
        return self.stats


class SearXNGClient:
    """SearXNG API client."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or DEFAULT_SEARXNG
    
    async def search(self, query: str, engines: list = None, categories: list = None, 
                    language: str = "en", num_results: int = 10) -> dict:
        """Search using SearXNG."""
        
        params = {
            "q": query,
            "format": "json",
            "lang": language,
            "num_results": num_results,
        }
        
        if engines:
            params["engines"] = ",".join(engines)
        if categories:
            params["categories"] = ",".join(categories)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.base_url}/search", params=params)
                response.raise_for_status()
                data = response.json()
                
                # Parse results
                results = []
                for result in data.get("results", [])[:num_results]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", "")[:200],
                        "engine": result.get("engine", ""),
                    })
                
                return {
                    "query": query,
                    "results": results,
                    "number_of_results": data.get("number_of_results", len(results)),
                    "infoboxes": data.get("infoboxes", []),
                    "suggestions": data.get("suggestions", []),
                }
                
            except httpx.HTTPError as e:
                raise Exception(f"SearXNG search failed: {e}")


# Initialize
search_logger = SearchLogger()
searxng_client = None

# Create MCP server
server = Server("picorouter-search")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search",
            description="Search the web using SearXNG. Returns title, URL, and snippet for each result.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "num_results": {
                        "type": "number",
                        "description": "Number of results to return (default: 10)",
                        "default": 10
                    },
                    "language": {
                        "type": "string", 
                        "description": "Language code (default: en)",
                        "default": "en"
                    },
                    "engines": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific search engines to use"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_stats",
            description="Get search usage statistics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    
    global searxng_client
    
    if name == "search":
        query = arguments.get("query", "")
        num_results = arguments.get("num_results", 10)
        language = arguments.get("language", "en")
        engines = arguments.get("engines")
        
        try:
            if not searxng_client:
                # Load config
                base_url = DEFAULT_SEARXNG
                turso_url = None
                for config_path in CONFIG_PATHS:
                    if config_path.exists():
                        with open(config_path) as f:
                            config = yaml.safe_load(f)
                            base_url = config.get("search", {}).get("searxng_url", DEFAULT_SEARXNG)
                            turso_url = config.get("database", {}).get("turso_url")
                            break
                searxng_client = SearXNGClient(base_url)
                
                # Re-init logger with Turso if configured
                if turso_url:
                    global search_logger
                    search_logger = SearchLogger(turso_url)
            
            result = await searxng_client.search(
                query, engines=engines, language=language, num_results=num_results
            )
            
            # Log the search
            search_logger.log(query, len(result.get("results", [])))
            
            # Format response
            response = f"🔍 Search results for: **{query}**\n\n"
            
            for i, r in enumerate(result.get("results", []), 1):
                response += f"**{i}. {r['title']}**\n"
                response += f"   {r['content'][:150]}...\n"
                response += f"   🔗 {r['url']}\n\n"
            
            if result.get("suggestions"):
                response += f"💡 Suggestions: {', '.join(result['suggestions'])}"
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            search_logger.log(query, 0, str(e))
            return [TextContent(type="text", text=f"❌ Search error: {e}")]
    
    elif name == "search_stats":
        stats = search_logger.get_stats()
        response = "📊 Search Stats\n"
        response += "=" * 30 + "\n"
        response += f"Total Searches: {stats['total_searches']}\n"
        response += f"Total Results: {stats['total_results']}\n"
        response += f"Errors: {stats['errors']}\n"
        return [TextContent(type="text", text=response)]
    
    return [TextContent(type="text", text="Unknown tool")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    print("🔍 PicoSearch MCP Server running...")
    print(f"   Default SearXNG: {DEFAULT_SEARXNG}")
    print("   Config: picorouter.yaml or mcpsearch.yaml")
    asyncio.run(main())
