"""Factory for creating video platform clients based on configuration."""

from typing import Optional

from reflector.settings import settings

from .base import Platform, VideoPlatformClient, VideoPlatformConfig
from .registry import get_platform_client


def get_platform_config(platform: Platform) -> VideoPlatformConfig:
    """Get configuration for a specific platform."""
    if platform == "whereby":
        return VideoPlatformConfig(
            api_key=settings.WHEREBY_API_KEY or "",
            webhook_secret=settings.WHEREBY_WEBHOOK_SECRET or "",
            api_url=settings.WHEREBY_API_URL,
            s3_bucket=settings.AWS_WHEREBY_S3_BUCKET,
            aws_access_key_id=settings.AWS_WHEREBY_ACCESS_KEY_ID,
            aws_access_key_secret=settings.AWS_WHEREBY_ACCESS_KEY_SECRET,
        )
    elif platform == "dailyco":
        return VideoPlatformConfig(
            api_key=settings.DAILYCO_API_KEY or "",
            webhook_secret=settings.DAILYCO_WEBHOOK_SECRET or "",
            subdomain=settings.DAILYCO_SUBDOMAIN,
            s3_bucket=settings.AWS_DAILYCO_S3_BUCKET,
            s3_region=settings.AWS_DAILYCO_S3_REGION,
            aws_role_arn=settings.AWS_DAILYCO_ROLE_ARN,
        )
    else:
        raise ValueError(f"Unknown platform: {platform}")


def create_platform_client(platform: Platform) -> VideoPlatformClient:
    """Create a video platform client instance."""
    config = get_platform_config(platform)
    return get_platform_client(platform, config)


def get_platform_for_room(room_id: Optional[str] = None) -> Platform:
    """Determine which platform to use for a room based on feature flags."""
    # If Daily.co migration is disabled, always use Whereby
    if not settings.DAILYCO_MIGRATION_ENABLED:
        return "whereby"

    # If a specific room is in the migration list, use Daily.co
    if room_id and room_id in settings.DAILYCO_MIGRATION_ROOM_IDS:
        return "dailyco"

    # Otherwise use the default platform
    return settings.DEFAULT_VIDEO_PLATFORM
