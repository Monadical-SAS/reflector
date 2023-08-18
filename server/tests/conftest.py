import pytest


@pytest.fixture(scope="function", autouse=True)
@pytest.mark.asyncio
async def setup_database():
    from reflector.settings import settings
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile() as f:
        settings.DATABASE_URL = f"sqlite:///{f.name}"
        from reflector.db import engine, metadata

        metadata.create_all(bind=engine)

        yield
