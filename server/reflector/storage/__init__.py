from .base import Storage  # noqa


def get_transcripts_storage() -> Storage:
    from reflector.settings import settings

    return Storage.get_instance(
        name=settings.TRANSCRIPT_STORAGE_BACKEND,
        settings_prefix="TRANSCRIPT_STORAGE_",
    )
