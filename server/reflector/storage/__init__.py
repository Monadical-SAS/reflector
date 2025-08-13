from .base import Storage  # noqa
from reflector.settings import settings


def get_transcripts_storage() -> Storage:
    assert settings.TRANSCRIPT_STORAGE_BACKEND
    return Storage.get_instance(
        name=settings.TRANSCRIPT_STORAGE_BACKEND,
        settings_prefix="TRANSCRIPT_STORAGE_",
    )
