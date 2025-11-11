from .base import Storage  # noqa
from reflector.settings import settings


def get_transcripts_storage() -> Storage:
    """
    Get storage for processed transcript files (master credentials).

    Also use this for ALL our file operations with bucket override:
        master = get_transcripts_storage()
        master.delete_file(key, bucket=recording.bucket_name)
    """
    assert settings.TRANSCRIPT_STORAGE_BACKEND
    return Storage.get_instance(
        name=settings.TRANSCRIPT_STORAGE_BACKEND,
        settings_prefix="TRANSCRIPT_STORAGE_",
    )


def get_whereby_storage() -> Storage:
    """
    Get storage config for Whereby (for passing to Whereby API).

    Usage:
        whereby_storage = get_whereby_storage()
        key_id, secret = whereby_storage.key_credentials
        whereby_api.create_meeting(
            bucket=whereby_storage.bucket_name,
            access_key_id=key_id,
            secret=secret,
        )

    Do NOT use for our file operations - use get_transcripts_storage() instead.
    """
    # Fail fast if platform-specific config missing
    if not settings.WHEREBY_STORAGE_AWS_BUCKET_NAME:
        raise ValueError(
            "WHEREBY_STORAGE_AWS_BUCKET_NAME required for Whereby with AWS storage"
        )

    return Storage.get_instance(
        name="aws",
        settings_prefix="WHEREBY_STORAGE_",
    )


def get_dailyco_storage() -> Storage:
    """
    Get storage config for Daily.co (for passing to Daily API).

    Usage:
        daily_storage = get_dailyco_storage()
        daily_api.create_meeting(
            bucket=daily_storage.bucket_name,
            region=daily_storage.region,
            role_arn=daily_storage.role_credential,
        )

    Do NOT use for our file operations - use get_transcripts_storage() instead.
    """
    # Fail fast if platform-specific config missing
    if not settings.DAILYCO_STORAGE_AWS_BUCKET_NAME:
        raise ValueError(
            "DAILYCO_STORAGE_AWS_BUCKET_NAME required for Daily.co with AWS storage"
        )

    return Storage.get_instance(
        name="aws",
        settings_prefix="DAILYCO_STORAGE_",
    )
