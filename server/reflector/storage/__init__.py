from .base import Storage  # noqa
from reflector.settings import settings


def get_transcripts_storage() -> Storage:
    assert settings.TRANSCRIPT_STORAGE_BACKEND
    return Storage.get_instance(
        name=settings.TRANSCRIPT_STORAGE_BACKEND,
        settings_prefix="TRANSCRIPT_STORAGE_",
    )


def get_recordings_storage() -> Storage:
    return Storage.get_instance(
        name=settings.RECORDING_STORAGE_BACKEND,
        settings_prefix="RECORDING_STORAGE_",
    )
