import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def settings_configuration():
    # theses settings are linked to monadical for pytest-recording
    # if a fork is done, they have to provide their own url when cassettes needs to be updated
    # modal api keys has to be defined by the user
    from reflector.settings import settings

    settings.TRANSCRIPT_BACKEND = "modal"
    settings.TRANSCRIPT_URL = (
        "https://monadical-sas--reflector-transcriber-parakeet-web.modal.run"
    )
    settings.DIARIZATION_BACKEND = "modal"
    settings.DIARIZATION_URL = "https://monadical-sas--reflector-diarizer-web.modal.run"


@pytest.fixture(scope="module")
def vcr_config():
    """VCR configuration to filter sensitive headers"""
    return {
        "filter_headers": [("authorization", "DUMMY_API_KEY")],
    }


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    return os.path.join(str(pytestconfig.rootdir), "tests", "docker-compose.test.yml")


@pytest.fixture(scope="session")
def docker_ip():
    """Get Docker IP address for test services"""
    # For most Docker setups, localhost works
    return "127.0.0.1"


# Only register docker_services dependent fixtures if docker plugin is available
try:
    import pytest_docker  # noqa: F401

    @pytest.fixture(scope="session")
    def postgres_service(docker_ip, docker_services):
        """Ensure that PostgreSQL service is up and responsive."""
        port = docker_services.port_for("postgres_test", 5432)

        def is_responsive():
            try:
                import psycopg2

                conn = psycopg2.connect(
                    host=docker_ip,
                    port=port,
                    dbname="reflector_test",
                    user="test_user",
                    password="test_password",
                )
                conn.close()
                return True
            except Exception:
                return False

        docker_services.wait_until_responsive(
            timeout=30.0, pause=0.1, check=is_responsive
        )

        # Return connection parameters
        return {
            "host": docker_ip,
            "port": port,
            "database": "reflector_test",
            "user": "test_user",
            "password": "test_password",
        }
except ImportError:
    # Docker plugin not available, provide a dummy fixture
    @pytest.fixture(scope="session")
    def postgres_service(docker_ip):
        """Dummy postgres service when docker plugin is not available"""
        return {
            "host": docker_ip,
            "port": 15432,  # Default test postgres port
            "database": "reflector_test",
            "user": "test_user",
            "password": "test_password",
        }


@pytest.fixture(scope="session", autouse=True)
async def setup_database(postgres_service):
    """Setup database and run migrations"""
    from sqlalchemy.ext.asyncio import create_async_engine

    from reflector.db import Base

    # Build database URL from connection params
    db_config = postgres_service
    DATABASE_URL = (
        f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )

    # Override settings
    from reflector.settings import settings

    settings.DATABASE_URL = DATABASE_URL

    # Create engine and tables
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        # Drop all tables first to ensure clean state
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def session(setup_database):
    """Provide a transactional database session for tests"""
    from reflector.db import get_session_factory

    async with get_session_factory()() as session:
        yield session
        await session.rollback()


@pytest.fixture
def fake_mp3_upload(tmp_path):
    """Create a temporary MP3 file for upload testing"""
    mp3_file = tmp_path / "test.mp3"
    # Create a minimal valid MP3 file (ID3v2 header + minimal frame)
    mp3_data = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff\xfb" + b"\x00" * 100
    mp3_file.write_bytes(mp3_data)
    return mp3_file


@pytest.fixture
def dummy_transcript():
    """Mock transcript processor response"""
    from reflector.processors.types import Transcript, Word

    return Transcript(
        text="Hello world this is a test",
        words=[
            Word(word="Hello", start=0.0, end=0.5, speaker=0),
            Word(word="world", start=0.5, end=1.0, speaker=0),
            Word(word="this", start=1.0, end=1.5, speaker=0),
            Word(word="is", start=1.5, end=1.8, speaker=0),
            Word(word="a", start=1.8, end=2.0, speaker=0),
            Word(word="test", start=2.0, end=2.5, speaker=0),
        ],
    )


@pytest.fixture
def dummy_transcript_translator():
    """Mock transcript translation"""
    return "Hola mundo esto es una prueba"


@pytest.fixture
def dummy_diarization():
    """Mock diarization processor response"""
    from reflector.processors.types import DiarizationOutput, DiarizationSegment

    return DiarizationOutput(
        diarization=[
            DiarizationSegment(speaker=0, start=0.0, end=1.0),
            DiarizationSegment(speaker=1, start=1.0, end=2.5),
        ]
    )


@pytest.fixture
def dummy_file_transcript():
    """Mock file transcript processor response"""
    from reflector.processors.types import Transcript, Word

    return Transcript(
        text="This is a complete file transcript with multiple speakers",
        words=[
            Word(word="This", start=0.0, end=0.5, speaker=0),
            Word(word="is", start=0.5, end=0.8, speaker=0),
            Word(word="a", start=0.8, end=1.0, speaker=0),
            Word(word="complete", start=1.0, end=1.5, speaker=1),
            Word(word="file", start=1.5, end=1.8, speaker=1),
            Word(word="transcript", start=1.8, end=2.3, speaker=1),
            Word(word="with", start=2.3, end=2.5, speaker=0),
            Word(word="multiple", start=2.5, end=3.0, speaker=0),
            Word(word="speakers", start=3.0, end=3.5, speaker=0),
        ],
    )


@pytest.fixture
def dummy_file_diarization():
    """Mock file diarization processor response"""
    from reflector.processors.types import DiarizationOutput, DiarizationSegment

    return DiarizationOutput(
        diarization=[
            DiarizationSegment(speaker=0, start=0.0, end=1.0),
            DiarizationSegment(speaker=1, start=1.0, end=2.3),
            DiarizationSegment(speaker=0, start=2.3, end=3.5),
        ]
    )


@pytest.fixture
def fake_transcript_with_topics():
    """Create a transcript with topics for testing"""
    from reflector.db.transcripts import TranscriptTopic
    from reflector.processors.types import Word

    topics = [
        TranscriptTopic(
            id="topic1",
            title="Introduction",
            summary="Opening remarks and introductions",
            timestamp=0.0,
            duration=30.0,
            words=[
                Word(word="Hello", start=0.0, end=0.5, speaker=0),
                Word(word="everyone", start=0.5, end=1.0, speaker=0),
            ],
        ),
        TranscriptTopic(
            id="topic2",
            title="Main Discussion",
            summary="Core topics and key points",
            timestamp=30.0,
            duration=60.0,
            words=[
                Word(word="Let's", start=30.0, end=30.3, speaker=1),
                Word(word="discuss", start=30.3, end=30.8, speaker=1),
                Word(word="the", start=30.8, end=31.0, speaker=1),
                Word(word="agenda", start=31.0, end=31.5, speaker=1),
            ],
        ),
    ]
    return topics


@pytest.fixture
def dummy_processors(
    dummy_transcript,
    dummy_transcript_translator,
    dummy_diarization,
    dummy_file_transcript,
    dummy_file_diarization,
):
    """Mock all processor responses"""
    return {
        "transcript": dummy_transcript,
        "translator": dummy_transcript_translator,
        "diarization": dummy_diarization,
        "file_transcript": dummy_file_transcript,
        "file_diarization": dummy_file_diarization,
    }


@pytest.fixture
def dummy_storage():
    """Mock storage backend"""
    from unittest.mock import AsyncMock

    storage = AsyncMock()
    storage.get_file_url.return_value = "https://example.com/test-audio.mp3"
    storage.put_file.return_value = None
    storage.delete_file.return_value = None
    return storage


@pytest.fixture
def dummy_llm():
    """Mock LLM responses"""
    return {
        "title": "Test Meeting Title",
        "summary": "This is a test meeting summary with key discussion points.",
        "short_summary": "Brief test summary.",
    }


@pytest.fixture
def whisper_transcript():
    """Mock Whisper API response format"""
    return {
        "text": "Hello world this is a test",
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "Hello world this is a test",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5},
                    {"word": "world", "start": 0.5, "end": 1.0},
                    {"word": "this", "start": 1.0, "end": 1.5},
                    {"word": "is", "start": 1.5, "end": 1.8},
                    {"word": "a", "start": 1.8, "end": 2.0},
                    {"word": "test", "start": 2.0, "end": 2.5},
                ],
            }
        ],
        "language": "en",
    }
