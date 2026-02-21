#!/usr/bin/env python3
"""PicoRouter - Minimal AI Model Router.

Usage:
    python picorouter.py serve [--profile NAME] [--host HOST] [--port PORT]
    python picorouter.py chat -m "message"
    python picorouter.py config --example
    python picorouter.py logs [-s] [-n COUNT]
"""

import argparse
import asyncio
import sys

from picorouter.config import load_config, find_config, generate_example, save_config
from picorouter.providers import Router
from picorouter.logger import Logger
from picorouter.api import run_server


def create_config_interactive():
    """Interactive config creator."""
    print("🧩 PicoRouter Config")
    print("=" * 20)
    
    config = {"profiles": {}, "server": {"host": "0.0.0.0", "port": 8080}}
    
    # Default profile
    profile = {}
    local = input("Local provider (ollama/lmstudio) [ollama]: ").strip() or "ollama"
    endpoint = input("Local endpoint [http://localhost:11434]: ").strip() or "http://localhost:11434"
    models = input("Local models (comma) [llama3]: ").strip() or "llama3"
    
    profile["local"] = {
        "provider": local,
        "endpoint": endpoint,
        "models": [m.strip() for m in models.split(",")]
    }
    
    # Cloud providers
    print("\n☁️  Cloud Providers")
    profile["cloud"] = {"providers": {}}
    
    add_kilo = input("Add Kilo.ai? (y/n) [y]: ").strip().lower() != 'n'
    if add_kilo:
        profile["cloud"]["providers"]["kilo"] = {"models": ["minimax/m2.5:free"]}
    
    add_groq = input("Add Groq? (y/n) [y]: ").strip().lower() != 'n'
    if add_groq:
        profile["cloud"]["providers"]["groq"] = {"models": ["llama-3.1-70b-versatile"]}
    
    add_openrouter = input("Add OpenRouter? (y/n) [y]: ").strip().lower() != 'n'
    if add_openrouter:
        profile["cloud"]["providers"]["openrouter"] = {"models": ["openrouter/free"]}
    
    # YOLO mode
    profile["yolo"] = input("Enable YOLO mode? (y/n) [n]: ").strip().lower() == 'y'
    
    config["profiles"]["default"] = profile
    config["default_profile"] = "default"
    
    return config


def main():
    parser = argparse.ArgumentParser(description="PicoRouter - Minimal AI Model Router")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Serve
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--profile", "-p", default="chat")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", "-P", type=int, default=8080)
    
    # Chat
    chat_parser = subparsers.add_parser("chat", help="Chat")
    chat_parser.add_argument("--message", "-m", required=True)
    
    # Config
    config_parser = subparsers.add_parser("config", help="Config")
    config_parser.add_argument("--example", "-e", action="store_true")
    config_parser.add_argument("--output", "-o")
    
    # Logs
    logs_parser = subparsers.add_parser("logs", help="View logs")
    logs_parser.add_argument("--stats", "-s", action="store_true")
    logs_parser.add_argument("--limit", "-n", type=int, default=20)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "config":
        if args.example:
            cfg = generate_example()
        else:
            cfg = create_config_interactive()
        
        path = args.output or "picorouter.yaml"
        save_config(cfg, path)
        print(f"✅ Config saved to {path}")
        return
    
    # Load config
    config = load_config()
    if not config:
        print("❌ No config. Run: python picorouter.py config --example")
        sys.exit(1)
    
    # Initialize
    profile_name = getattr(args, "profile", None)
    router = Router(config, profile_name)
    router.logger = Logger()
    
    if args.command == "serve":
        print(f"📋 Profile: {router.profile_name}")
        run_server(router, args.host, args.port)
    
    elif args.command == "chat":
        messages = [{"role": "user", "content": args.message}]
        
        async def run():
            result = await router.chat(messages)
            print(f"\n🤖 {result.get('message', {}).get('content', '')}")
        
        asyncio.run(run())
    
    elif args.command == "logs":
        if args.stats:
            stats = router.logger.get_stats()
            print("\n📊 Stats")
            print(f"  Requests: {stats['total_requests']}")
            print(f"  Tokens:   {stats['total_tokens']}")
            print(f"  Cost:     ${stats['total_cost_usd']:.4f}")
            print(f"  Errors:   {stats['errors']}")
        else:
            logs = router.logger.get_recent(args.limit)
            for log in logs:
                ts = log.get("timestamp", "")[:19]
                status = "✓" if log.get("status") == "success" else "✗"
                print(f"{status} {ts} | {log.get('provider', '?')[:12]} | {log.get('tokens_used', 0)} tokens")


if __name__ == "__main__":
    main()
