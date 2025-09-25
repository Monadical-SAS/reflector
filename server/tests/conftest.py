import asyncio
import os
import sys
from unittest.mock import patch

import pytest


@pytest.fixture(scope="session")
def event_loop():
    if sys.platform.startswith("win") and sys.version_info[:2] >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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
def postgres_service(docker_ip, docker_services):
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

    docker_services.wait_until_responsive(timeout=30.0, pause=0.1, check=is_responsive)

    return {
        "host": docker_ip,
        "port": port,
        "dbname": "reflector_test",
        "user": "test_user",
        "password": "test_password",
    }


@pytest.fixture(scope="session")
def _database_url(postgres_service):
    db_config = postgres_service
    DATABASE_URL = (
        f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    )

    # Override settings
    from reflector.settings import settings

    settings.DATABASE_URL = DATABASE_URL

    return DATABASE_URL


@pytest.fixture(scope="session")
def init_database():
    from reflector.db import Base

    return Base.metadata.create_all


@pytest.fixture
def dummy_processors():
    with (
        patch(
            "reflector.processors.transcript_topic_detector.TranscriptTopicDetectorProcessor.get_topic"
        ) as mock_topic,
        patch(
            "reflector.processors.transcript_final_title.TranscriptFinalTitleProcessor.get_title"
        ) as mock_title,
        patch(
            "reflector.processors.transcript_final_summary.TranscriptFinalSummaryProcessor.get_long_summary"
        ) as mock_long_summary,
        patch(
            "reflector.processors.transcript_final_summary.TranscriptFinalSummaryProcessor.get_short_summary"
        ) as mock_short_summary,
    ):
        from reflector.processors.transcript_topic_detector import TopicResponse

        mock_topic.return_value = TopicResponse(
            title="LLM TITLE", summary="LLM SUMMARY"
        )
        mock_title.return_value = "LLM Title"
        mock_long_summary.return_value = "LLM LONG SUMMARY"
        mock_short_summary.return_value = "LLM SHORT SUMMARY"
        yield (
            mock_topic,
            mock_title,
            mock_long_summary,
            mock_short_summary,
        )  # noqa


@pytest.fixture
async def whisper_transcript():
    from reflector.processors.audio_transcript_whisper import (
        AudioTranscriptWhisperProcessor,
    )

    with patch(
        "reflector.processors.audio_transcript_auto"
        ".AudioTranscriptAutoProcessor.__new__"
    ) as mock_audio:
        mock_audio.return_value = AudioTranscriptWhisperProcessor()
        yield


@pytest.fixture
async def dummy_transcript():
    from reflector.processors.audio_transcript import AudioTranscriptProcessor
    from reflector.processors.types import AudioFile, Transcript, Word

    class TestAudioTranscriptProcessor(AudioTranscriptProcessor):
        _time_idx = 0

        async def _transcript(self, data: AudioFile):
            i = self._time_idx
            self._time_idx += 2
            return Transcript(
                text="Hello world.",
                words=[
                    Word(start=i, end=i + 1, text="Hello", speaker=0),
                    Word(start=i + 1, end=i + 2, text=" world.", speaker=0),
                ],
            )

    with patch(
        "reflector.processors.audio_transcript_auto"
        ".AudioTranscriptAutoProcessor.__new__"
    ) as mock_audio:
        mock_audio.return_value = TestAudioTranscriptProcessor()
        yield


@pytest.fixture
async def dummy_diarization():
    from reflector.processors.audio_diarization import AudioDiarizationProcessor

    class TestAudioDiarizationProcessor(AudioDiarizationProcessor):
        _time_idx = 0

        async def _diarize(self, data):
            i = self._time_idx
            self._time_idx += 2
            return [
                {"start": i, "end": i + 1, "speaker": 0},
                {"start": i + 1, "end": i + 2, "speaker": 1},
            ]

    with patch(
        "reflector.processors.audio_diarization_auto"
        ".AudioDiarizationAutoProcessor.__new__"
    ) as mock_audio:
        mock_audio.return_value = TestAudioDiarizationProcessor()
        yield


@pytest.fixture
async def dummy_file_transcript():
    from reflector.processors.file_transcript import FileTranscriptProcessor
    from reflector.processors.types import Transcript, Word

    class TestFileTranscriptProcessor(FileTranscriptProcessor):
        async def _transcript(self, data):
            return Transcript(
                text="Hello world. How are you today?",
                words=[
                    Word(start=0.0, end=0.5, text="Hello", speaker=0),
                    Word(start=0.5, end=0.6, text=" ", speaker=0),
                    Word(start=0.6, end=1.0, text="world", speaker=0),
                    Word(start=1.0, end=1.1, text=".", speaker=0),
                    Word(start=1.1, end=1.2, text=" ", speaker=0),
                    Word(start=1.2, end=1.5, text="How", speaker=0),
                    Word(start=1.5, end=1.6, text=" ", speaker=0),
                    Word(start=1.6, end=1.8, text="are", speaker=0),
                    Word(start=1.8, end=1.9, text=" ", speaker=0),
                    Word(start=1.9, end=2.1, text="you", speaker=0),
                    Word(start=2.1, end=2.2, text=" ", speaker=0),
                    Word(start=2.2, end=2.5, text="today", speaker=0),
                    Word(start=2.5, end=2.6, text="?", speaker=0),
                ],
            )

    with patch(
        "reflector.processors.file_transcript_auto.FileTranscriptAutoProcessor.__new__"
    ) as mock_auto:
        mock_auto.return_value = TestFileTranscriptProcessor()
        yield


@pytest.fixture
async def dummy_file_diarization():
    from reflector.processors.file_diarization import (
        FileDiarizationOutput,
        FileDiarizationProcessor,
    )
    from reflector.processors.types import DiarizationSegment

    class TestFileDiarizationProcessor(FileDiarizationProcessor):
        async def _diarize(self, data):
            return FileDiarizationOutput(
                diarization=[
                    DiarizationSegment(start=0.0, end=1.1, speaker=0),
                    DiarizationSegment(start=1.2, end=2.6, speaker=1),
                ]
            )

    with patch(
        "reflector.processors.file_diarization_auto.FileDiarizationAutoProcessor.__new__"
    ) as mock_auto:
        mock_auto.return_value = TestFileDiarizationProcessor()
        yield


@pytest.fixture
async def dummy_transcript_translator():
    from reflector.processors.transcript_translator import TranscriptTranslatorProcessor

    class TestTranscriptTranslatorProcessor(TranscriptTranslatorProcessor):
        async def _translate(self, text: str) -> str:
            source_language = self.get_pref("audio:source_language", "en")
            target_language = self.get_pref("audio:target_language", "en")
            return f"{source_language}:{target_language}:{text}"

    def mock_new(cls, *args, **kwargs):
        return TestTranscriptTranslatorProcessor(*args, **kwargs)

    with patch(
        "reflector.processors.transcript_translator_auto"
        ".TranscriptTranslatorAutoProcessor.__new__",
        mock_new,
    ):
        yield


@pytest.fixture
async def dummy_llm():
    from reflector.llm import LLM

    class TestLLM(LLM):
        def __init__(self):
            self.model_name = "DUMMY MODEL"
            self.llm_tokenizer = "DUMMY TOKENIZER"

    # LLM doesn't have get_instance anymore, mocking constructor instead
    with patch("reflector.llm.LLM") as mock_llm:
        mock_llm.return_value = TestLLM()
        yield


@pytest.fixture
async def dummy_storage():
    from reflector.storage.base import Storage

    class DummyStorage(Storage):
        async def _put_file(self, *args, **kwargs):
            pass

        async def _delete_file(self, *args, **kwargs):
            pass

        async def _get_file_url(self, *args, **kwargs):
            return "http://fake_server/audio.mp3"

        async def _get_file(self, *args, **kwargs):
            from pathlib import Path

            test_mp3 = Path(__file__).parent / "records" / "test_mathieu_hello.mp3"
            return test_mp3.read_bytes()

    dummy = DummyStorage()
    with (
        patch("reflector.storage.base.Storage.get_instance") as mock_storage,
        patch("reflector.storage.get_transcripts_storage") as mock_get_transcripts,
        patch(
            "reflector.pipelines.main_file_pipeline.get_transcripts_storage"
        ) as mock_get_transcripts2,
    ):
        mock_storage.return_value = dummy
        mock_get_transcripts.return_value = dummy
        mock_get_transcripts2.return_value = dummy
        yield


# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
# from sqlalchemy.orm import sessionmaker


# @pytest.fixture()
# async def db_connection(sqla_engine):
#     connection = await sqla_engine.connect()
#     try:
#         yield connection
#     finally:
#         await connection.close()


# @pytest.fixture()
# async def db_session_maker(db_connection):
#     Session = async_sessionmaker(
#         db_connection,
#         expire_on_commit=False,
#         class_=AsyncSession,
#     )
#     yield Session


# @pytest.fixture()
# async def db_session(db_session_maker, db_connection):
#     """
#     Fixture that returns a SQLAlchemy session with a SAVEPOINT, and the rollback to it
#     after the test completes.
#     """
#     session = db_session_maker(
#         bind=db_connection,
#         join_transaction_mode="create_savepoint",
#     )

#     try:
#         yield session
#     finally:
#         await session.close()


# @pytest.fixture(autouse=True)
# async def ensure_db_session_in_app(db_connection, db_session_maker):
#     async def mock_get_session():
#         session = db_session_maker(
#             bind=db_connection, join_transaction_mode="create_savepoint"
#         )

#         try:
#             yield session
#         finally:
#             await session.close()

#     with patch("reflector.db._get_session", side_effect=mock_get_session):
#         yield


@pytest.fixture(autouse=True)
async def ensure_db_session_in_app(db_session):
    async def mock_get_session():
        yield db_session

    with patch("reflector.db._get_session", side_effect=mock_get_session):
        yield


@pytest.fixture
async def client(db_session):
    from httpx import AsyncClient

    from reflector.app import app

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        yield ac


@pytest.fixture(scope="session")
def fake_mp3_upload():
    with patch(
        "reflector.db.transcripts.TranscriptController.move_mp3_to_storage"
    ) as mock_move:
        mock_move.return_value = True
        yield


@pytest.fixture
async def taskiq_broker():
    from reflector.worker.app import taskiq_broker

    await taskiq_broker.startup()

    try:
        yield taskiq_broker
    finally:
        await taskiq_broker.shutdown()


@pytest.fixture
async def fake_transcript_with_topics(tmpdir, client, db_session):
    import shutil
    from pathlib import Path

    from reflector.db.transcripts import TranscriptTopic
    from reflector.processors.types import Word
    from reflector.settings import settings
    from reflector.views.transcripts import transcripts_controller

    settings.DATA_DIR = Path(tmpdir)

    # create a transcript
    response = await client.post("/transcripts", json={"name": "Test audio download"})
    assert response.status_code == 200
    tid = response.json()["id"]

    transcript = await transcripts_controller.get_by_id(db_session, tid)
    assert transcript is not None

    await transcripts_controller.update(db_session, transcript, {"status": "ended"})

    # manually copy a file at the expected location
    audio_filename = transcript.audio_mp3_filename
    path = Path(__file__).parent / "records" / "test_mathieu_hello.mp3"
    audio_filename.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, audio_filename)

    # create some topics
    await transcripts_controller.upsert_topic(
        db_session,
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Topic 1 summary",
            timestamp=0,
            transcript="Hello world",
            words=[
                Word(text="Hello", start=0, end=1, speaker=0),
                Word(text="world", start=1, end=2, speaker=0),
            ],
        ),
    )
    await transcripts_controller.upsert_topic(
        db_session,
        transcript,
        TranscriptTopic(
            title="Topic 2",
            summary="Topic 2 summary",
            timestamp=2,
            transcript="Hello world",
            words=[
                Word(text="Hello", start=2, end=3, speaker=0),
                Word(text="world", start=3, end=4, speaker=0),
            ],
        ),
    )

    yield transcript
