from typing import Dict, Type

from ..schemas.platform import Platform
from .base import VideoPlatformClient, VideoPlatformConfig

_PLATFORMS: Dict[Platform, Type[VideoPlatformClient]] = {}


def register_platform(name: Platform, client_class: Type[VideoPlatformClient]):
    _PLATFORMS[name] = client_class


def get_platform_client(
    platform: Platform, config: VideoPlatformConfig
) -> VideoPlatformClient:
    if platform not in _PLATFORMS:
        raise ValueError(f"Unknown video platform: {platform}")

    client_class = _PLATFORMS[platform]
    return client_class(config)


def get_available_platforms() -> list[Platform]:
    return list(_PLATFORMS.keys())


def _register_builtin_platforms():
    from .daily import DailyClient  # noqa: PLC0415
    from .whereby import WherebyClient  # noqa: PLC0415

    register_platform("whereby", WherebyClient)
    register_platform("daily", DailyClient)


_register_builtin_platforms()
