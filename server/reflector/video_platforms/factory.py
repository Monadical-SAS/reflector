from reflector.settings import settings
from reflector.storage import get_dailyco_storage, get_whereby_storage

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
        whereby_storage = get_whereby_storage()
        key_id, secret = whereby_storage.key_credentials
        return VideoPlatformConfig(
            api_key=settings.WHEREBY_API_KEY,
            webhook_secret=settings.WHEREBY_WEBHOOK_SECRET or "",
            api_url=settings.WHEREBY_API_URL,
            s3_bucket=whereby_storage.bucket_name,
            s3_region=whereby_storage.region,
            aws_access_key_id=key_id,
            aws_access_key_secret=secret,
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
        daily_storage = get_dailyco_storage()
        return VideoPlatformConfig(
            api_key=settings.DAILY_API_KEY,
            webhook_secret=settings.DAILY_WEBHOOK_SECRET or "",
            subdomain=settings.DAILY_SUBDOMAIN,
            s3_bucket=daily_storage.bucket_name,
            s3_region=daily_storage.region,
            aws_role_arn=daily_storage.role_credential,
        )
    else:
        raise ValueError(f"Unknown platform: {platform}")


def create_platform_client(platform: Platform) -> VideoPlatformClient:
    config = get_platform_config(platform)
    return get_platform_client(platform, config)
