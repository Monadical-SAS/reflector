"""Factory for creating video platform clients based on configuration."""

from typing import Optional

from reflector.settings import settings

from .base import Platform, VideoPlatformClient, VideoPlatformConfig
from .registry import get_platform_client


def get_platform_config(platform: Platform) -> VideoPlatformConfig:
    """Get configuration for a specific platform."""
    if platform == "whereby":
        if not settings.WHEREBY_API_KEY:
            raise ValueError(
                "WHEREBY_API_KEY is required when platform='whereby'. "
                "Set WHEREBY_API_KEY environment variable."
            )
        return VideoPlatformConfig(
            api_key=settings.WHEREBY_API_KEY,
            webhook_secret=settings.WHEREBY_WEBHOOK_SECRET or "",
            api_url=settings.WHEREBY_API_URL,
            s3_bucket=settings.RECORDING_STORAGE_AWS_BUCKET_NAME,
            s3_region=settings.RECORDING_STORAGE_AWS_REGION,
            aws_access_key_id=settings.AWS_WHEREBY_ACCESS_KEY_ID,
            aws_access_key_secret=settings.AWS_WHEREBY_ACCESS_KEY_SECRET,
        )
    elif platform == "daily":
        if not settings.DAILY_API_KEY:
            raise ValueError(
                "DAILY_API_KEY is required when platform='daily'. "
                "Set DAILY_API_KEY environment variable."
            )
        if not settings.DAILY_SUBDOMAIN:
            raise ValueError(
                "DAILY_SUBDOMAIN is required when platform='daily'. "
                "Set DAILY_SUBDOMAIN environment variable."
            )
        return VideoPlatformConfig(
            api_key=settings.DAILY_API_KEY,
            webhook_secret=settings.DAILY_WEBHOOK_SECRET or "",
            subdomain=settings.DAILY_SUBDOMAIN,
            s3_bucket=settings.AWS_DAILY_S3_BUCKET,
            s3_region=settings.AWS_DAILY_S3_REGION,
            aws_role_arn=settings.AWS_DAILY_ROLE_ARN,
        )
    else:
        raise ValueError(f"Unknown platform: {platform}")


def create_platform_client(platform: Platform) -> VideoPlatformClient:
    """Create a video platform client instance."""
    config = get_platform_config(platform)
    return get_platform_client(platform, config)


def get_platform_for_room(
    room_id: Optional[str] = None, room_platform: Optional[Platform] = None
) -> Platform:
    """Determine which platform to use for a room.

    Priority order (highest to lowest):
    1. DAILY_MIGRATION_ROOM_IDS - env var override for testing/migration
    2. room_platform - database persisted platform choice
    3. DEFAULT_VIDEO_PLATFORM - env var fallback
    """
    # If Daily migration is disabled, always use Whereby
    if not settings.DAILY_MIGRATION_ENABLED:
        return "whereby"

    # Highest priority: If room is in migration list, use Daily (env var override)
    if room_id and room_id in settings.DAILY_MIGRATION_ROOM_IDS:
        return "daily"

    # Second priority: Use room's persisted platform from database
    if room_platform:
        return room_platform

    # Fallback: Use default platform from env var
    return settings.DEFAULT_VIDEO_PLATFORM
