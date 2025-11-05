from typing import Optional

from reflector.settings import settings

from ..schemas.platform import WHEREBY_PLATFORM, Platform
from .base import VideoPlatformClient, VideoPlatformConfig
from .registry import get_platform_client


def get_platform_config(platform: Platform) -> VideoPlatformConfig:
    if platform == WHEREBY_PLATFORM:
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
    config = get_platform_config(platform)
    return get_platform_client(platform, config)


def get_platform(room_platform: Optional[Platform] = None) -> Platform:
    if room_platform:
        return room_platform

    return settings.DEFAULT_VIDEO_PLATFORM
