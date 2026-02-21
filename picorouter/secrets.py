"""PicoRouter - Secrets management with multiple backends.

Supports:
- Environment variables (default)
- .env file
- vaultwarden (self-hosted Bitwarden)
- Encrypted local file
"""

import json
import os
import subprocess
import base64
import hashlib
from pathlib import Path
from typing import Optional, List, Dict

# Provider API key env var mapping
PROVIDER_KEYS = {
    "kilo": "KILO_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
    "ai21": "AI21_API_KEY",
    "together": "TOGETHER_API_KEY",
    "replicate": "REPLICATE_API_KEY",
    "deepinfra": "DEEPINFRA_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "anyscale": "ANYSCALE_API_KEY",
    "azure": "AZURE_API_KEY",
    "picorouter": "PICOROUTER_API_KEY",  # PicoRouter's own key
}


class SecretsBackend:
    """Base secrets backend."""

    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    def set(self, key: str, value: str) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def list_keys(self) -> List[str]:
        raise NotImplementedError


class EnvBackend(SecretsBackend):
    """Environment variables backend (default)."""

    def get(self, key: str) -> Optional[str]:
        return os.getenv(key)

    def set(self, key: str, value: str) -> None:
        os.environ[key] = value

    def delete(self, key: str) -> None:
        os.environ.pop(key, None)

    def list_keys(self) -> List[str]:
        return [k for k in os.environ if k.endswith("_API_KEY")]


class DotEnvBackend(SecretsBackend):
    """.env file backend."""

    def __init__(self, path: str = None):
        self.path = path or ".env"
        self._load()

    def _load(self):
        self.data = {}
        if Path(self.path).exists():
            with open(self.path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        self.data[k.strip()] = v.strip().strip('"').strip("'")

    def _save(self):
        with open(self.path, "w") as f:
            f.write("# PicoRouter secrets\n")
            for k, v in self.data.items():
                f.write(f'{k}="{v}"\n')

    def get(self, key: str) -> Optional[str]:
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        self.data.pop(key, None)
        self._save()

    def list_keys(self) -> List[str]:
        return list(self.data.keys())


class VaultwardenBackend(SecretsBackend):
    """vaultwarden (self-hosted Bitwarden) backend."""

    def __init__(self, session_token: str = None, url: str = None):
        self.url = url or os.getenv("VAULTWARDEN_URL", "http://localhost:8000")
        self.token = session_token or os.getenv("VAULTWARDEN_TOKEN")
        self._org_id = os.getenv("VAULTWARDEN_ORG_ID")

    def _run(self, args: list) -> dict:
        """Run bw CLI command."""
        if not self.token:
            raise Exception("vaultwarden token not set (VAULTWARDEN_TOKEN)")

        env = os.environ.copy()
        env["BW_SESSION"] = self.token

        result = subprocess.run(["bw"] + args, capture_output=True, text=True, env=env)

        if result.returncode != 0:
            raise Exception(f"vaultwarden error: {result.stderr}")

        return json.loads(result.stdout) if result.stdout else {}

    def get(self, key: str) -> Optional[str]:
        try:
            # Search for item
            items = self._run(["list", "items", "--search", key])
            for item in items:
                if item.get("name") == key:
                    # Get password field
                    for field in item.get("fields", []):
                        if field.get("name") == "value":
                            return field.get("value")
                    # Fallback to password
                    return item.get("login", {}).get("password")
            return None
        except Exception:
            return None

    def set(self, key: str, value: str) -> None:
        # Create or update item
        # Note: Requires bw CLI and unlocked vault
        print(f"⚠️  vaultwarden: use 'bw encode' to store: {key}={value[:10]}...")

    def delete(self, key: str) -> None:
        try:
            # Search for item first to get its ID
            items = self._run(["list", "items", "--search", key])
            for item in items:
                if item.get("name") == key:
                    item_id = item.get("id")
                    if item_id:
                        self._run(["delete", "item", item_id])
                        return
        except Exception as e:
            raise Exception(f"vaultwarden: failed to delete key '{key}': {e}")

    def list_keys(self) -> List[str]:
        try:
            items = self._run(["list", "items"])
            return [i.get("name") for i in items if i.get("name")]
        except Exception:
            return []


class EncryptedFileBackend(SecretsBackend):
    """Simple encrypted file backend."""

    def __init__(self, path: str = None, password: str = None):
        self.path = path or os.path.expanduser("~/.picorouter/secrets.json")
        self.password = password or os.getenv("PICOROUTER_SECRETS_PASSWORD")

        if not self.password:
            # Try to read from keyring or prompt
            self.password = self._get_password()

        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _get_password(self) -> str:
        # Try keyring first
        try:
            import keyring

            return keyring.get_password("picorouter", "secrets")
        except Exception:
            pass

        # Fallback to env
        return os.getenv("PICOROUTER_SECRETS_PASSWORD", "")

    def _encrypt(self, data: str) -> str:
        """Simple XOR + base64 (not crypto-secure, but obfuscated)."""
        key = hashlib.sha256(self.password.encode()).digest()
        encrypted = bytes(
            a ^ b
            for a, b in zip(
                data.encode(), (key * ((len(data) // len(key)) + 1))[: len(data)]
            )
        )
        return base64.b64encode(encrypted).decode()

    def _decrypt(self, data: str) -> str:
        """Decrypt XOR + base64."""
        key = hashlib.sha256(self.password.encode()).digest()
        decrypted = bytes(
            a ^ b
            for a, b in zip(
                base64.b64decode(data),
                (key * ((len(base64.b64decode(data)) // len(key)) + 1))[
                    : len(base64.b64decode(data))
                ],
            )
        )
        return decrypted.decode()

    def _load(self):
        self.data = {}
        if Path(self.path).exists():
            try:
                with open(self.path) as f:
                    encrypted = f.read()
                    if encrypted:
                        self.data = json.loads(self._decrypt(encrypted))
            except Exception:
                pass

    def _save(self):
        with open(self.path, "w") as f:
            f.write(self._encrypt(json.dumps(self.data)))

    def get(self, key: str) -> Optional[str]:
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        self.data.pop(key, None)
        self._save()

    def list_keys(self) -> List[str]:
        return list(self.data.keys())


class SecretsManager:
    """Unified secrets manager with backend selection."""

    def __init__(self, backend: str = None):
        self.backend_name = backend or os.getenv("PICOROUTER_SECRETS_BACKEND", "env")
        self.backend = self._init_backend()

    def _init_backend(self) -> SecretsBackend:
        if self.backend_name == "env":
            return EnvBackend()
        elif self.backend_name == "dotenv":
            return DotEnvBackend()
        elif self.backend_name == "vaultwarden":
            return VaultwardenBackend()
        elif self.backend_name == "encrypted":
            return EncryptedFileBackend()
        else:
            return EnvBackend()

    def get_provider_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider."""
        env_var = PROVIDER_KEYS.get(provider.lower())
        if not env_var:
            return None

        # Check backend first
        key = self.backend.get(env_var)
        if key:
            return key

        # Fallback to env
        return os.getenv(env_var)

    def set_provider_key(self, provider: str, value: str) -> None:
        """Set API key for a provider."""
        env_var = PROVIDER_KEYS.get(provider.lower())
        if env_var:
            self.backend.set(env_var, value)
            os.environ[env_var] = value

    def get(self, key: str) -> Optional[str]:
        return self.backend.get(key)

    def set(self, key: str, value: str) -> None:
        self.backend.set(key, value)

    def list_providers(self) -> List[dict]:
        """List all providers and their key status."""
        results = []
        for provider, env_var in PROVIDER_KEYS.items():
            key = self.get(env_var)
            results.append(
                {
                    "provider": provider,
                    "env_var": env_var,
                    "configured": bool(key),
                    "key_hint": key[:8] + "..." if key else None,
                }
            )
        return results


def init_secrets(backend: str = None) -> SecretsManager:
    """Initialize secrets manager."""
    return SecretsManager(backend)


# CLI helpers
def secrets_cli(args):
    """CLI for secrets management."""
    sm = SecretsManager(args.backend)

    if args.command == "list":
        print("🔐 Configured provider keys:")
        for p in sm.list_providers():
            status = "✅" if p["configured"] else "❌"
            hint = p["key_hint"] or ""
            print(f"  {status} {p['provider']:12} {hint}")

    elif args.command == "set":
        if not args.key or not args.value:
            print("Usage: secrets set <KEY> <VALUE>")
            return
        sm.set(args.key, args.value)
        print(f"✅ Set {args.key}")

    elif args.command == "get":
        val = sm.get(args.key)
        if val:
            print(f"{args.key}={val}")
        else:
            print(f"Key not found: {args.key}")

    elif args.command == "show":
        print("🔐 Available backends:")
        print("  env        - Environment variables (default)")
        print("  dotenv     - .env file")
        print("  vaultwarden - Self-hosted Bitwarden")
        print("  encrypted  - Encrypted local file")
        print()
        print(f"Current: {args.backend or 'env'}")
        print()
        print("Usage:")
        print("  export PICOROUTER_SECRETS_BACKEND=dotenv")
        print("  export PICOROUTER_SECRETS_BACKEND=vaultwarden")
