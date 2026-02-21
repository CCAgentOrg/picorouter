"""PicoRouter - Provider compatibility layer.

Import from picorouter.providers:
    from picorouter.providers import Router, CloudProvider, LocalProvider
"""

# Re-export from providers package
from picorouter.providers import (
    PROVIDERS,
    get_provider_info,
    list_providers,
    register_provider,
    create_provider,
    BaseProvider,
    CloudProvider,
    LocalProvider,
    VirtualProvider,
    RateLimitError,
)

# For backwards compatibility
class Router:
    """Router compatibility - import from picorouter.router instead."""
    pass
