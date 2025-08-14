import os
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest


# Pytest-docker configuration
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
    from reflector.db import engine, metadata, database  # noqa

    metadata.drop_all(bind=engine)
    metadata.create_all(bind=engine)

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
    ):
        mock_storage.return_value = dummy
        mock_get_transcripts.return_value = dummy
        yield


@pytest.fixture(scope="session")
def celery_enable_logging():
    return True


@pytest.fixture(scope="session")
def celery_config():
    with NamedTemporaryFile() as f:
        yield {
            "broker_url": "memory://",
            "result_backend": f"db+sqlite:///{f.name}",
        }


@pytest.fixture(scope="session")
def celery_includes():
    return ["reflector.pipelines.main_live_pipeline"]


@pytest.fixture(scope="session")
def fake_mp3_upload():
    with patch(
        "reflector.db.transcripts.TranscriptController.move_mp3_to_storage"
    ) as mock_move:
        mock_move.return_value = True
        yield


@pytest.fixture
async def fake_transcript_with_topics(tmpdir):
    import shutil
    from pathlib import Path

    from httpx import AsyncClient

    from reflector.app import app
    from reflector.db.transcripts import TranscriptTopic
    from reflector.processors.types import Word
    from reflector.settings import settings
    from reflector.views.transcripts import transcripts_controller

    settings.DATA_DIR = Path(tmpdir)

    # create a transcript
    ac = AsyncClient(app=app, base_url="http://test/v1")
    response = await ac.post("/transcripts", json={"name": "Test audio download"})
    assert response.status_code == 200
    tid = response.json()["id"]

    transcript = await transcripts_controller.get_by_id(tid)
    assert transcript is not None

    await transcripts_controller.update(transcript, {"status": "finished"})

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
