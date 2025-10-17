from typing import Dict, Type

from .base import Platform, VideoPlatformClient, VideoPlatformConfig

# Registry of available video platforms
_PLATFORMS: Dict[Platform, Type[VideoPlatformClient]] = {}


def register_platform(name: Platform, client_class: Type[VideoPlatformClient]):
    """Register a video platform implementation."""
    _PLATFORMS[name] = client_class


def get_platform_client(
    platform: Platform, config: VideoPlatformConfig
) -> VideoPlatformClient:
    """Get a video platform client instance."""
    if platform not in _PLATFORMS:
        raise ValueError(f"Unknown video platform: {platform}")

    client_class = _PLATFORMS[platform]
    return client_class(config)


def get_available_platforms() -> list[Platform]:
    """Get list of available platform names."""
    return list(_PLATFORMS.keys())


# Auto-register built-in platforms
def _register_builtin_platforms():
    from .daily import DailyClient  # noqa: PLC0415
    from .whereby import WherebyClient  # noqa: PLC0415

    register_platform("whereby", WherebyClient)
    register_platform("daily", DailyClient)


_register_builtin_platforms()
