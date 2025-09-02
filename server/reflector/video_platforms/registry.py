from typing import Dict, Type

from .base import VideoPlatformClient, VideoPlatformConfig

# Registry of available video platforms
_PLATFORMS: Dict[str, Type[VideoPlatformClient]] = {}


def register_platform(name: str, client_class: Type[VideoPlatformClient]):
    """Register a video platform implementation."""
    _PLATFORMS[name.lower()] = client_class


def get_platform_client(
    platform: str, config: VideoPlatformConfig
) -> VideoPlatformClient:
    """Get a video platform client instance."""
    platform_lower = platform.lower()
    if platform_lower not in _PLATFORMS:
        raise ValueError(f"Unknown video platform: {platform}")

    client_class = _PLATFORMS[platform_lower]
    return client_class(config)


def get_available_platforms() -> list[str]:
    """Get list of available platform names."""
    return list(_PLATFORMS.keys())


# Auto-register built-in platforms
def _register_builtin_platforms():
    from .jitsi import JitsiClient
    from .whereby import WherebyClient

    register_platform("jitsi", JitsiClient)
    register_platform("whereby", WherebyClient)


_register_builtin_platforms()
