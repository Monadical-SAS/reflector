from .base import Storage  # noqa

def get_storage() -> Storage:
    from reflector.settings import settings
    return Storage.get_instance(
        name=settings.TRANSCRIPT_STORAGE_BACKEND,
    )
