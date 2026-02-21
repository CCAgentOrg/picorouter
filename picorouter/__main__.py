#!/usr/bin/env python3
"""PicoRouter - Minimal AI Model Router.

Usage:
    python picorouter.py serve [--profile NAME] [--host HOST] [--port PORT]
    python picorouter.py chat -m "message"
    python picorouter.py config --example
    python picorouter.py logs [-s] [-n COUNT]
    python picorouter.py key add [--name NAME] [--rate-limit N] [--profiles p1,p2]
    python picorouter.py key list
    python picorouter.py key remove NAME
"""

import argparse
import asyncio
import sys

from picorouter.config import load_config, find_config, generate_example, save_config
from picorouter.providers import Router
from picorouter.logger import Logger
from picorouter.api import run_server
from picorouter.keys import KeyManager
from picorouter.tailscale import get_all_ips, is_tailscale_running, print_network_info, get_tailscale_ip


def resolve_host(host: str) -> str:
    """Resolve host alias to IP address."""
    host = host.lower().strip()
    
    if host in ["0.0.0.0", "all", "*"]:
        return "0.0.0.0"
    
    if host in ["127.0.0.1", "localhost"]:
        return "127.0.0.1"
    
    # Tailscale
    if host == "tailscale":
        ts_ip = get_tailscale_ip()
        if ts_ip:
            return ts_ip
        print("⚠️  Tailscale not detected. Using 0.0.0.0")
        return "0.0.0.0"
    
    # LAN
    if host == "lan":
        ips = get_all_ips()
        if ips.get("lan"):
            return ips["lan"]
        print("⚠️  No LAN IP found. Using 0.0.0.0")
        return "0.0.0.0"
    
    # Assume it's already an IP
    return host


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
    
    # Keys
    if input("\n🔑 Add API keys now? (y/n) [n]: ").strip().lower() == 'y':
        config["keys"] = {}
        km = KeyManager()
        while True:
            name = input("  Key name (or Enter to done): ").strip()
            if not name:
                break
            rate = input(f"  Rate limit for {name} (req/min, empty for default): ").strip()
            rate = int(rate) if rate else 60
            profiles = input(f"  Allowed profiles (comma, empty for all): ").strip()
            profiles = [p.strip() for p in profiles.split(",")] if profiles else ["chat", "coding", "yolo"]
            
            key = km.add_key(name, rate_limit=rate, profiles=profiles)
            print(f"  ✅ Key '{name}': {key}")
        
        config["keys"] = km.get_config()
    
    return config


def main():
    parser = argparse.ArgumentParser(description="PicoRouter - Minimal AI Model Router")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Serve
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--profile", "-p", default="chat")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host: localhost, all, tailscale, lan, or IP")
    serve_parser.add_argument("--port", "-P", type=int, default=8080)
    serve_parser.add_argument("--rate-limit", "-r", type=int, default=60, help="Requests per minute (0 to disable)")
    serve_parser.add_argument("--show-ips", "-i", action="store_true", help="Show available network IPs")
    
    # Chat
    chat_parser = subparsers.add_parser("chat", help="Chat")
    chat_parser.add_argument("--message", "-m", required=True)
    chat_parser.add_argument("--profile", "-p", default="chat")
    
    # Config
    config_parser = subparsers.add_parser("config", help="Config")
    config_parser.add_argument("--example", "-e", action="store_true")
    config_parser.add_argument("--output", "-o")
    
    # Logs
    logs_parser = subparsers.add_parser("logs", help="View logs")
    logs_parser.add_argument("--stats", "-s", action="store_true")
    logs_parser.add_argument("--limit", "-n", type=int, default=20)
    
    # Key management
    key_parser = subparsers.add_parser("key", help="API Key management")
    key_subparsers = key_parser.add_subparsers(dest="key_command")
    
    key_add = key_subparsers.add_parser("add", help="Add new API key")
    key_add.add_argument("--name", "-n", required=True, help="Key name")
    key_add.add_argument("--rate-limit", "-r", type=int, default=60, help="Requests per minute")
    key_add.add_argument("--profiles", "-p", help="Allowed profiles (comma-separated)")
    key_add.add_argument("--readonly", action="store_true", help="Read-only key (chat disabled)")
    key_add.add_argument("--expires", help="Expiration date (ISO format)")
    
    key_list = key_subparsers.add_parser("list", help="List API keys")
    key_remove = key_subparsers.add_parser("remove", help="Remove API key")
    key_remove.add_argument("name", help="Key name to remove")
    
    # Secrets management
    secrets_parser = subparsers.add_parser("secrets", help="Provider API key management")
    secrets_parser.add_argument("--backend", "-b", default=None, help="Backend: env, dotenv, vaultwarden, encrypted")
    secrets_subparsers = secrets_parser.add_subparsers(dest="secrets_command")
    
    secrets_list = secrets_subparsers.add_parser("list", help="List configured provider keys")
    secrets_set = secrets_subparsers.add_parser("set", help="Set provider API key")
    secrets_set.add_argument("--provider", "-p", required=True, help="Provider name")
    secrets_set.add_argument("--key", "-k", required=True, help="API key value")
    secrets_show = secrets_subparsers.add_parser("show", help="Show available backends")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Key management commands
    if args.command == "key":
        config_path = find_config()
        if not config_path:
            print("❌ No config found. Run: python picorouter.py config --example")
            sys.exit(1)
        
        config = load_config()
        km = KeyManager.from_config(config)
        
        if args.key_command == "add":
            profiles = args.profiles.split(",") if args.profiles else ["chat", "coding", "yolo"]
            profiles = [p.strip() for p in profiles]
            key = km.add_key(
                args.name,
                rate_limit=args.rate_limit,
                profiles=profiles,
                readonly=args.readonly,
                expires=args.expires
            )
            config["keys"] = km.get_config()
            save_config(config, config_path)
            print(f"✅ Added key '{args.name}': {key}")
            print(f"   Rate limit: {args.rate_limit}/min")
            print(f"   Profiles: {profiles}")
        
        elif args.key_command == "list":
            keys = km.list_keys()
            if not keys:
                print("📝 No API keys configured")
            else:
                print("🔑 Configured API Keys:")
                for k in keys:
                    print(f"   • {k['name']}")
                    print(f"     Profiles: {k['profiles']}")
                    print(f"     Rate limit: {k['rate_limit']}/min")
                    print(f"     Readonly: {k['readonly']}")
                    if k.get('expires'):
                        print(f"     Expires: {k['expires']}")
                    print()
        
        elif args.key_command == "remove":
            if km.remove_key(args.name):
                config["keys"] = km.get_config()
                save_config(config, config_path)
                print(f"✅ Removed key '{args.name}'")
            else:
                print(f"❌ Key '{args.name}' not found")
        
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
    
    # Initialize logger with storage config
    storage_cfg = config.get("storage", {})
    router.logger = Logger(
        backend=storage_cfg.get("backend", "jsonl"),
        log_file=storage_cfg.get("log_file", "logs/requests.jsonl"),
        db_path=storage_cfg.get("db_path", "logs/picorouter.db"),
        turso_url=storage_cfg.get("turso_url"),
        turso_token=storage_cfg.get("turso_token")
    )
    router.config = config  # Store for key manager
    
    if args.command == "serve":
        # Show network info if requested
        if getattr(args, "show_ips", False):
            print_network_info()
        
        # Resolve host
        host = resolve_host(args.host)
        
        print(f"📋 Profile: {router.profile_name}")
        run_server(router, host, args.port, args.rate_limit)
    
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
                key = log.get("key", "")
                print(f"{status} {ts} | {key[:10]} | {log.get('provider', '?')[:12]} | {log.get('tokens_used', 0)} tokens")
    
    elif args.command == "secrets":
        from picorouter.secrets import SecretsManager
        sm = SecretsManager(args.backend)
        
        if args.secrets_command == "list":
            print("🔐 Configured provider keys:")
            for p in sm.list_providers():
                status = "✅" if p["configured"] else "❌"
                hint = p["key_hint"] or ""
                print(f"  {status} {p['provider']:12} {hint}")
        
        elif args.secrets_command == "set":
            sm.set_provider_key(args.provider, args.key)
            print(f"✅ Set {args.provider} API key")
        
        elif args.secrets_command == "show":
            print("🔐 Available backends:")
            print("  env        - Environment variables (default)")
            print("  dotenv     - .env file")
            print("  vaultwarden - Self-hosted Bitwarden")
            print("  encrypted  - Encrypted local file")
            print()
            print("Set backend:")
            print("  export PICOROUTER_SECRETS_BACKEND=dotenv")
        
        else:
            secrets_parser.print_help()
    
    elif args.command == "models":
        from picorouter.models import models_cli
        models_cli(args)
    
    # Models (discovery from models.dev)
    models_parser = subparsers.add_parser("models", help="Model discovery from models.dev")
    models_subparsers = models_parser.add_subparsers(dest="models_command")
    
    models_search = models_subparsers.add_parser("search", help="Search models")
    models_search.add_argument("--free", action="store_true", help="Free models only")
    models_search.add_argument("--context", type=int, default=0, help="Min context length")
    models_search.add_argument("--provider", "-p", help="Filter by provider")
    models_search.add_argument("--limit", "-n", type=int, default=20, help="Max results")
    
    models_sync = models_subparsers.add_parser("sync", help="Sync models to config")
    models_sync.add_argument("--output", "-o", help="Output file for config")
    
    models_providers = models_subparsers.add_parser("providers", help="List available providers")


if __name__ == "__main__":
    main()
