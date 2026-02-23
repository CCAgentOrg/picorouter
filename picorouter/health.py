"""PicoRouter - Health monitoring for providers.

Features:
- Background health checks for all configured providers
- Track latency, uptime, error rates per provider
- Auto-exclude failing providers from routing
- Visual indicators: 🟢 healthy, 🟡 degraded, 🔴 down
"""

import asyncio
import httpx
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

# Health status thresholds
LATENCY_OK_MS = 2000  # < 2s = healthy
LATENCY_SLOW_MS = 5000  # < 5s = degraded, > 5s = down
ERROR_RATE_OK = 0.1  # < 10% errors = healthy
ERROR_RATE_DEGRADED = 0.5  # < 50% errors = degraded, > 50% = down
UPTIME_OK = 0.9  # > 90% uptime = healthy


@dataclass
class ProviderHealth:
    """Health status for a single provider."""

    name: str
    status: str = "unknown"  # unknown, healthy, degraded, down
    latency_ms: float = 0
    uptime: float = 1.0
    error_rate: float = 0.0
    total_checks: int = 0
    successful_checks: int = 0
    last_check: Optional[float] = None
    last_success: Optional[float] = None
    last_error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "uptime": round(self.uptime, 4),
            "error_rate": round(self.error_rate, 4),
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "last_check": datetime.fromtimestamp(self.last_check).isoformat()
            if self.last_check
            else None,
            "last_error": self.last_error,
        }

    @property
    def indicator(self) -> str:
        if self.status == "healthy":
            return "🟢"
        elif self.status == "degraded":
            return "🟡"
        elif self.status == "down":
            return "🔴"
        return "⚪"


class HealthMonitor:
    """Monitor health of all configured providers."""

    def __init__(self, check_interval: int = 60):
        """Initialize health monitor.

        Args:
            check_interval: Seconds between health checks (default 60)
        """
        self.check_interval = check_interval
        self.providers: Dict[str, ProviderHealth] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_provider(self, name: str, endpoint: str = None):
        """Register a provider for health monitoring."""
        with self._lock:
            if name not in self.providers:
                self.providers[name] = ProviderHealth(name=name)
                self.providers[name].endpoint = endpoint

    def get_health(self, name: str) -> Optional[ProviderHealth]:
        """Get health status for a provider."""
        with self._lock:
            return self.providers.get(name)

    def get_all_health(self) -> List[ProviderHealth]:
        """Get health status for all providers."""
        with self._lock:
            return list(self.providers.values())

    def get_status_summary(self) -> dict:
        """Get summary of all provider statuses."""
        with self._lock:
            healthy = sum(1 for p in self.providers.values() if p.status == "healthy")
            degraded = sum(1 for p in self.providers.values() if p.status == "degraded")
            down = sum(1 for p in self.providers.values() if p.status == "down")
            unknown = sum(1 for p in self.providers.values() if p.status == "unknown")

            return {
                "total": len(self.providers),
                "healthy": healthy,
                "degraded": degraded,
                "down": down,
                "unknown": unknown,
            }

    def is_healthy(self, name: str) -> bool:
        """Check if a provider is healthy enough for routing."""
        health = self.get_health(name)
        if not health:
            return True
        return health.status in ("healthy", "degraded", "unknown")

    async def check_provider(
        self, name: str, endpoint: str, timeout: float = 10.0
    ) -> bool:
        """Check health of a single provider.

        Returns True if provider is reachable, False otherwise.
        """
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Try to reach the provider's models endpoint
                if name in ("ollama", "lmstudio"):
                    # Local providers - check tags endpoint
                    url = (
                        f"{endpoint}/api/tags"
                        if name == "ollama"
                        else f"{endpoint}/v1/models"
                    )
                else:
                    # Cloud providers - check chat completions with minimal request
                    url = f"{endpoint}chat/completions"
                    # We can't easily test cloud providers without a valid request
                    # Just check if endpoint is reachable

                resp = await client.get(
                    url.replace("chat/completions", "") + "models"
                    if "chat/completions" in url
                    else url,
                    headers={"Authorization": "Bearer test"}
                    if name != "ollama"
                    else {},
                )
                latency = (time.time() - start) * 1000

                # Update health
                with self._lock:
                    health = self.providers.get(name)
                    if health:
                        health.total_checks += 1
                        health.successful_checks += 1
                        health.last_check = time.time()
                        health.last_success = time.time()
                        health.latency_ms = (
                            health.latency_ms * 0.7 + latency * 0.3
                        )  # Smooth
                        health.error_rate = 1 - (
                            health.successful_checks / health.total_checks
                        )
                        health.uptime = health.successful_checks / health.total_checks

                        # Determine status
                        self._update_status(health)

                return True

        except Exception as e:
            with self._lock:
                health = self.providers.get(name)
                if health:
                    health.total_checks += 1
                    health.last_check = time.time()
                    health.last_error = str(e)[:100]
                    health.error_rate = 1 - (
                        health.successful_checks / max(health.total_checks, 1)
                    )
                    health.uptime = health.successful_checks / max(
                        health.total_checks, 1
                    )

                    # Determine status
                    self._update_status(health)

            return False

    def _update_status(self, health: ProviderHealth):
        """Update health status based on metrics."""
        if health.total_checks < 3:
            health.status = "unknown"
            return

        # Check error rate first
        if health.error_rate > ERROR_RATE_DEGRADED:
            health.status = "down"
        elif health.error_rate > ERROR_RATE_OK:
            health.status = "degraded"
        # Check latency
        elif health.latency_ms > LATENCY_SLOW_MS:
            health.status = "degraded"
        elif health.latency_ms > LATENCY_OK_MS:
            health.status = "degraded"
        # Check uptime
        elif health.uptime < UPTIME_OK:
            health.status = "degraded"
        else:
            health.status = "healthy"

    async def check_all_providers(self, providers: Dict[str, dict]):
        """Check health of all configured providers."""
        from picorouter.providers import PROVIDERS

        for name, config in providers.items():
            # Get endpoint from config or registry
            info = PROVIDERS.get(name, {})
            endpoint = config.get("base_url") or info.get("endpoint")

            if endpoint:
                await self.check_provider(name, endpoint)

    def start_background_checks(self, get_providers_fn):
        """Start background health check thread.

        Args:
            get_providers_fn: Function that returns current providers dict
        """
        if self._running:
            return

        self._running = True
        self._providers_fn = get_providers_fn

        def run_loop():
            while self._running:
                try:
                    providers = self._providers_fn()
                    if providers:
                        asyncio.run(self.check_all_providers(providers))
                except Exception:
                    pass

                time.sleep(self.check_interval)

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

    def stop_background_checks(self):
        """Stop background health check thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)


# Global health monitor instance
_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor


def init_health_monitor(config: dict, profile_name: str = None) -> HealthMonitor:
    """Initialize health monitor with providers from config."""
    monitor = get_health_monitor()

    profile_name = profile_name or config.get("default_profile", "chat")
    profile = config.get("profiles", {}).get(profile_name, {})

    # Register local provider
    local = profile.get("local", {})
    if local:
        provider = local.get("provider", "ollama")
        endpoint = local.get("endpoint", "http://localhost:11434")
        monitor.register_provider(provider, endpoint)

    # Register cloud providers
    cloud_providers = profile.get("cloud", {}).get("providers", {})
    for name, cfg in cloud_providers.items():
        from picorouter.providers import PROVIDERS

        info = PROVIDERS.get(name, {})
        endpoint = cfg.get("base_url") or info.get("endpoint")
        if endpoint:
            monitor.register_provider(name, endpoint)

    return monitor
