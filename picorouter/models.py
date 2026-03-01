"""PicoRouter - Model discovery from models.dev."""

import json
import httpx
import re
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# models.dev API endpoint
MODELS_DEV_URL = "https://models.dev/api"


async def fetch_models_dev_models() -> List[dict]:
    """Fetch all models from models.dev with improved parsing."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get("https://models.dev/")
            resp.raise_for_status()

            text = resp.text
            models = []

            # Try multiple parsing strategies
            # Strategy 1: Look for table-like patterns with pipe separators
            lines = text.split("\n")
            for line in lines:
                # Skip obviously non-data lines
                if not line or line.strip().startswith("#"):
                    continue

                # Try pipe-separated format: Provider | Model | ...
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2:
                        provider = parts[0].strip()
                        model = parts[1].strip()

                        # Skip headers and empty values
                        if (
                            provider
                            and model
                            and provider not in ["Provider", ""]
                            and model not in ["Model", ""]
                        ):
                            models.append(
                                {
                                    "provider": provider,
                                    "model": model,
                                    "source": "models.dev",
                                }
                            )

                # Try regex for model names (fallback)
                # Look for patterns like: "provider/model" or "provider: model"
                elif re.search(r"^([a-zA-Z0-9_-]+)\s*[/:]\s*([a-zA-Z0-9_/.-]+)", line):
                    match = re.search(
                        r"^([a-zA-Z0-9_-]+)\s*[/:]\s*([a-zA-Z0-9_/.-]+)", line
                    )
                    if match:
                        models.append(
                            {
                                "provider": match.group(1),
                                "model": match.group(2),
                                "source": "models.dev",
                            }
                        )

            logger.debug(f"Parsed {len(models)} models from models.dev")
            return models[:500]

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching models.dev: {e}")
            return []
        except httpx.RequestError as e:
            logger.warning(f"Network error fetching models.dev: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching models.dev: {e}")
            return []


async def search_models(
    free: bool = False,
    context_min: int = 0,
    provider: str = None,
    max_results: int = 20,
) -> list:
    """Search models from models.dev with filters."""
    models = await fetch_models_dev_models()

    if not models:
        return []

    filtered = []
    for m in models:
        # Provider filtering
        if provider and m.get("provider", "").lower() != provider.lower():
            continue

        # Free filtering - heuristic based on provider
        if free:
            free_providers = ["kilo", "groq", "openrouter", "free"]
            if m.get("provider", "").lower() not in free_providers:
                continue

        filtered.append(m)

    return filtered[:max_results]


def format_model_list(models: list) -> str:
    """Format model list for display."""
    if not models:
        return "No models found."

    lines = ["📋 Available Models", "=" * 40]

    # Group by provider
    by_provider = {}
    for m in models:
        prov = m.get("provider", "unknown")
        if prov not in by_provider:
            by_provider[prov] = []
        by_provider[prov].append(m.get("model", ""))

    for prov, model_list in sorted(by_provider.items()):
        lines.append(f"\n🔹 {prov}")
        for model in model_list[:5]:
            lines.append(f"   • {model}")
        if len(model_list) > 5:
            lines.append(f"   ... and {len(model_list) - 5} more")

    return "\n".join(lines)


def generate_config_from_models(models: list) -> str:
    """Generate YAML config from models."""
    if not models:
        return "# No models available"

    lines = ["# PicoRouter config generated from models.dev", "", "profiles:"]

    # Group by provider
    by_provider = {}
    for m in models:
        prov = m.get("provider", "unknown")
        if prov not in by_provider:
            by_provider[prov] = []
        by_provider[prov].append(m.get("model", ""))

    # Generate profile for each provider
    for prov, model_list in sorted(by_provider.items()):
        prov_key = prov.lower().replace(".", "").replace(" ", "")
        lines.append(f"  {prov_key}:")
        lines.append(f"    cloud:")
        lines.append(f"      providers:")
        lines.append(f"        {prov}:")
        lines.append(f"          models:")
        for model in model_list[:3]:  # Max 3 models per provider
            lines.append(f"            - {model}")

    lines.append("")
    lines.append("default_profile: chat")

    return "\n".join(lines)


# CLI integration
def models_cli(args):
    """CLI for model discovery."""
    import asyncio

    async def run():
        if args.command == "search":
            models = await search_models(
                free=args.free,
                context_min=args.context,
                provider=args.provider,
                max_results=args.limit,
            )
            print(format_model_list(models))

        elif args.command == "sync":
            print("🔄 Fetching models from models.dev...")
            models = await fetch_models_dev_models()
            print(f"📥 Found {len(models)} models")

            if args.output:
                config = generate_config_from_models(models)
                with open(args.output, "w") as f:
                    f.write(config)
                print(f"✅ Config written to {args.output}")
            else:
                print("\n" + format_model_list(models))

        elif args.command == "providers":
            models = await fetch_models_dev_models()
            providers = set(m.get("provider", "") for m in models)
            print("🏢 Available Providers:")
            for p in sorted(providers):
                print(f"   • {p}")
        
        elif args.command == "list":
            from picorouter.providers import (
                get_zdr_models,
                get_all_models,
                refresh_zdr_cache,
                get_cache_info,
            )
            
            # Refresh if requested
            if args.refresh:
                print("🔄 Refreshing ZDR model cache...")
                try:
                    all_models = await refresh_zdr_cache(force=True)
                except Exception as e:
                    print(f"⚠️  Error refreshing cache: {e}")
                    all_models = get_all_models()
            else:
                all_models = get_all_models()
            
            # Filter by ZDR if requested
            if args.zdr:
                models = get_zdr_models()
                title = "🔒 ZDR (Privacy) Models"
            else:
                models = all_models
                title = "📋 All Cached Models"
            
            # Output as JSON if requested
            if args.json:
                import json
                print(json.dumps(models, indent=2))
                return
            
            # Format as table
            cache_info = get_cache_info()
            print(f"\n{title}")
            print("=" * 60)
            
            if not models:
                print("No models found.")
                if not args.zdr:
                    print("\n💡 Try: picorouter models list --zdr --refresh")
                return
            
            # Print cache info
            if cache_info["cached"]:
                age = cache_info["age_hours"]
                status = "fresh" if not cache_info["expired"] else "expired"
                print(f"📦 Cache: {cache_info['total_models']} models, {cache_info['zdr_count']} ZDR | {age:.1f}h old ({status})")
            else:
                print(f"📦 Cache: {cache_info['total_models']} models, {cache_info['zdr_count']} ZDR | Not loaded")
            print()
            
            # Print models in table format
            print(f"{'Model ID':<45} {'ZDR':>5} {'$/M Input':>10}")
            print("-" * 60)
            for m in models[:50]:  # Limit display
                zdr = "✅" if m.get("zdr") else "❌"
                price = m.get("price_input", 0)
                print(f"{m.get('id', 'unknown'):<45} {zdr:>5} {price:>10.2f}")
            
            if len(models) > 50:
                print(f"... and {len(models) - 50} more")
            models = await fetch_models_dev_models()
            providers = set(m.get("provider", "") for m in models)
            print("🏢 Available Providers:")
            for p in sorted(providers):
                print(f"   • {p}")

    asyncio.run(run())
