import os
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

from reflector.schemas.platform import WHEREBY_PLATFORM


@pytest.fixture(scope="session", autouse=True)
def register_mock_platform():
    from mocks.mock_platform import MockPlatformClient

    from reflector.video_platforms.registry import register_platform

    register_platform(WHEREBY_PLATFORM, MockPlatformClient)
    yield


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

    docker_services.wait_until_responsive(timeout=30.0, pause=0.1, check=is_responsive)

    # Return connection parameters
    return {
        "host": docker_ip,
        "port": port,
        "dbname": "reflector_test",
        "user": "test_user",
        "password": "test_password",
    }


@pytest.fixture(scope="function", autouse=True)
@pytest.mark.asyncio
async def setup_database(postgres_service):
    from reflector.db import engine, metadata, get_database  # noqa

    metadata.drop_all(bind=engine)
    metadata.create_all(bind=engine)
    database = get_database()

    try:
        await database.connect()
        yield
    finally:
        await database.disconnect()


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


@pytest.fixture
def test_settings():
    """Provide isolated settings for tests to avoid modifying global settings"""
    from reflector.settings import Settings

    return Settings()


@pytest.fixture(scope="session")
def celery_enable_logging():
    return True


@pytest.fixture(scope="session")
def celery_config():
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = os.environ.get("REDIS_PORT", "6379")
    # Use db 2 to avoid conflicts with main app
    redis_url = f"redis://{redis_host}:{redis_port}/2"
    yield {
        "broker_url": redis_url,
        "result_backend": redis_url,
    }


@pytest.fixture(scope="session")
def celery_includes():
    return [
        "reflector.pipelines.main_live_pipeline",
        "reflector.pipelines.main_file_pipeline",
    ]


@pytest.fixture
async def client():
    from httpx import AsyncClient

    from reflector.app import app

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def ws_manager_in_memory(monkeypatch):
    """Replace Redis-based WS manager with an in-memory implementation for tests."""
    import asyncio
    import json

    from reflector.ws_manager import WebsocketManager

    class _InMemorySubscriber:
        def __init__(self, queue: asyncio.Queue):
            self.queue = queue

        async def get_message(
            self, ignore_subscribe_messages: bool = True, timeout: float | None = None
        ):
            wait_timeout = timeout if timeout is not None else 0.05
            try:
                return await asyncio.wait_for(self.queue.get(), timeout=wait_timeout)
            except Exception:
                return None

    class InMemoryPubSubManager:
        def __init__(self):
            self.queues: dict[str, asyncio.Queue] = {}
            self.connected = False

        async def connect(self) -> None:
            self.connected = True

        async def disconnect(self) -> None:
            self.connected = False

        async def send_json(self, room_id: str, message: dict) -> None:
            if room_id not in self.queues:
                self.queues[room_id] = asyncio.Queue()
            payload = json.dumps(message).encode("utf-8")
            await self.queues[room_id].put(
                {"channel": room_id.encode("utf-8"), "data": payload}
            )

        async def subscribe(self, room_id: str):
            if room_id not in self.queues:
                self.queues[room_id] = asyncio.Queue()
            return _InMemorySubscriber(self.queues[room_id])

        async def unsubscribe(self, room_id: str) -> None:
            # keep queue for potential later resubscribe within same test
            pass

    pubsub = InMemoryPubSubManager()
    ws_manager = WebsocketManager(pubsub_client=pubsub)

    def _get_ws_manager():
        return ws_manager

    # Patch all places that imported get_ws_manager at import time
    monkeypatch.setattr("reflector.ws_manager.get_ws_manager", _get_ws_manager)
    monkeypatch.setattr(
        "reflector.pipelines.main_live_pipeline.get_ws_manager", _get_ws_manager
    )
    monkeypatch.setattr(
        "reflector.views.transcripts_websocket.get_ws_manager", _get_ws_manager
    )
    monkeypatch.setattr(
        "reflector.views.user_websocket.get_ws_manager", _get_ws_manager
    )
    monkeypatch.setattr("reflector.views.transcripts.get_ws_manager", _get_ws_manager)

    # Websocket auth: avoid OAuth2 on websocket dependencies; allow anonymous
    import reflector.auth as auth

    # Ensure FastAPI uses our override for routes that captured the original callable
    from reflector.app import app as fastapi_app

    try:
        fastapi_app.dependency_overrides[auth.current_user_optional] = lambda: None
    except Exception:
        pass

    # Stub Redis cache used by profanity filter to avoid external Redis
    from reflector import redis_cache as rc

    class _FakeRedis:
        def __init__(self):
            self._data = {}

        def get(self, key):
            value = self._data.get(key)
            if value is None:
                return None
            if isinstance(value, bytes):
                return value
            return str(value).encode("utf-8")

        def setex(self, key, duration, value):
            # ignore duration for tests
            if isinstance(value, bytes):
                self._data[key] = value
            else:
                self._data[key] = str(value).encode("utf-8")

    fake_redises: dict[int, _FakeRedis] = {}

    def _get_redis_client(db=0):
        if db not in fake_redises:
            fake_redises[db] = _FakeRedis()
        return fake_redises[db]

    monkeypatch.setattr(rc, "get_redis_client", _get_redis_client)

    yield


@pytest.fixture
@pytest.mark.asyncio
async def authenticated_client():
    async with authenticated_client_ctx():
        yield


@pytest.fixture
@pytest.mark.asyncio
async def authenticated_client2():
    async with authenticated_client2_ctx():
        yield


@asynccontextmanager
async def authenticated_client_ctx():
    from reflector.app import app
    from reflector.auth import current_user, current_user_optional

    app.dependency_overrides[current_user] = lambda: {
        "sub": "randomuserid",
        "email": "test@mail.com",
    }
    app.dependency_overrides[current_user_optional] = lambda: {
        "sub": "randomuserid",
        "email": "test@mail.com",
    }
    yield
    del app.dependency_overrides[current_user]
    del app.dependency_overrides[current_user_optional]


@asynccontextmanager
async def authenticated_client2_ctx():
    from reflector.app import app
    from reflector.auth import current_user, current_user_optional

    app.dependency_overrides[current_user] = lambda: {
        "sub": "randomuserid2",
        "email": "test@mail.com",
    }
    app.dependency_overrides[current_user_optional] = lambda: {
        "sub": "randomuserid2",
        "email": "test@mail.com",
    }
    yield
    del app.dependency_overrides[current_user]
    del app.dependency_overrides[current_user_optional]


@pytest.fixture(scope="session")
def fake_mp3_upload():
    with patch(
        "reflector.db.transcripts.TranscriptController.move_mp3_to_storage"
    ) as mock_move:
        mock_move.return_value = True
        yield


@pytest.fixture(autouse=True)
def reset_hatchet_client():
    """Reset HatchetClientManager singleton before and after each test.

    This ensures test isolation - each test starts with a fresh client state.
    The fixture is autouse=True so it applies to all tests automatically.
    """
    from reflector.hatchet.client import HatchetClientManager

    # Reset before test
    HatchetClientManager.reset()
    yield
    # Reset after test to clean up
    HatchetClientManager.reset()


@pytest.fixture
async def fake_transcript_with_topics(tmpdir, client):
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

    transcript = await transcripts_controller.get_by_id(tid)
    assert transcript is not None

    await transcripts_controller.update(transcript, {"status": "ended"})

    # manually copy a file at the expected location
    audio_filename = transcript.audio_mp3_filename
    path = Path(__file__).parent / "records" / "test_mathieu_hello.mp3"
    audio_filename.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, audio_filename)

    # create some topics
    await transcripts_controller.upsert_topic(
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
