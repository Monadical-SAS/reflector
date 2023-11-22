from unittest.mock import patch
from tempfile import NamedTemporaryFile

import pytest


@pytest.fixture(scope="function", autouse=True)
@pytest.mark.asyncio
async def setup_database():
    from reflector.settings import settings

    with NamedTemporaryFile() as f:
        settings.DATABASE_URL = f"sqlite:///{f.name}"
        from reflector.db import engine, metadata

        metadata.create_all(bind=engine)

        yield


@pytest.fixture
def dummy_processors():
    with patch(
        "reflector.processors.transcript_topic_detector.TranscriptTopicDetectorProcessor.get_topic"
    ) as mock_topic, patch(
        "reflector.processors.transcript_final_title.TranscriptFinalTitleProcessor.get_title"
    ) as mock_title, patch(
        "reflector.processors.transcript_final_long_summary.TranscriptFinalLongSummaryProcessor.get_long_summary"
    ) as mock_long_summary, patch(
        "reflector.processors.transcript_final_short_summary.TranscriptFinalShortSummaryProcessor.get_short_summary"
    ) as mock_short_summary, patch(
        "reflector.processors.transcript_translator.TranscriptTranslatorProcessor.get_translation"
    ) as mock_translate:
        mock_topic.return_value = {"title": "LLM TITLE", "summary": "LLM SUMMARY"}
        mock_title.return_value = {"title": "LLM TITLE"}
        mock_long_summary.return_value = "LLM LONG SUMMARY"
        mock_short_summary.return_value = {"short_summary": "LLM SHORT SUMMARY"}
        mock_translate.return_value = "Bonjour le monde"
        yield mock_translate, mock_topic, mock_title, mock_long_summary, mock_short_summary  # noqa


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
async def dummy_llm():
    from reflector.llm.base import LLM

    class TestLLM(LLM):
        def __init__(self):
            self.model_name = "DUMMY MODEL"
            self.llm_tokenizer = "DUMMY TOKENIZER"

    with patch("reflector.llm.base.LLM.get_instance") as mock_llm:
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

    with patch("reflector.storage.base.Storage.get_instance") as mock_storage:
        mock_storage.return_value = DummyStorage()
        yield


@pytest.fixture
def nltk():
    with patch("reflector.llm.base.LLM.ensure_nltk") as mock_nltk:
        mock_nltk.return_value = "NLTK PACKAGE"
        yield


@pytest.fixture
def ensure_casing():
    with patch("reflector.llm.base.LLM.ensure_casing") as mock_casing:
        mock_casing.return_value = "LLM TITLE"
        yield


@pytest.fixture
def sentence_tokenize():
    with patch(
        "reflector.processors.TranscriptFinalLongSummaryProcessor.sentence_tokenize"
    ) as mock_sent_tokenize:
        mock_sent_tokenize.return_value = ["LLM LONG SUMMARY"]
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
def fake_mp3_upload():
    with patch(
        "reflector.db.transcripts.TranscriptController.move_mp3_to_storage"
    ) as mock_move:
        mock_move.return_value = True
        yield
