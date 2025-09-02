"""Factory for creating video platform clients based on configuration."""

from typing import Optional

from reflector.settings import settings

from .base import VideoPlatformClient, VideoPlatformConfig
from .registry import get_platform_client


def get_platform_config(platform: str) -> VideoPlatformConfig:
    """Get configuration for a specific platform."""
    if platform == "whereby":
        return VideoPlatformConfig(
            api_key=settings.WHEREBY_API_KEY or "",
            webhook_secret=settings.WHEREBY_WEBHOOK_SECRET or "",
            api_url=settings.WHEREBY_API_URL,
            aws_access_key_id=settings.AWS_WHEREBY_ACCESS_KEY_ID,
            aws_access_key_secret=settings.AWS_WHEREBY_ACCESS_KEY_SECRET,
        )
    elif platform == "jitsi":
        return VideoPlatformConfig(
            api_key="",  # Jitsi uses JWT, no API key
            webhook_secret=settings.JITSI_WEBHOOK_SECRET or "",
            api_url=f"https://{settings.JITSI_DOMAIN}",
        )
    else:
        raise ValueError(f"Unknown platform: {platform}")


def create_platform_client(platform: str) -> VideoPlatformClient:
    """Create a video platform client instance."""
    config = get_platform_config(platform)
    return get_platform_client(platform, config)


def get_platform_for_room(room_id: Optional[str] = None) -> str:
    """Determine which platform to use for a room based on feature flags."""
    # For now, default to whereby since we don't have feature flags yet
    return "whereby"
