from unittest.mock import patch

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
    ) as mock_short_summary:
        mock_topic.return_value = {"title": "LLM TITLE", "summary": "LLM SUMMARY"}
        mock_title.return_value = {"title": "LLM TITLE"}
        mock_long_summary.return_value = "LLM LONG SUMMARY"
        mock_short_summary.return_value = {"short_summary": "LLM SHORT SUMMARY"}

        yield mock_topic, mock_title, mock_long_summary, mock_short_summary


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
def nltk():
    with patch("reflector.llm.base.LLM.ensure_nltk") as mock_nltk:
        mock_nltk.return_value = "NLTK PACKAGE"
        yield


@pytest.fixture
def ensure_casing():
    with patch("reflector.llm.base.LLM.ensure_casing") as mock_casing:
        mock_casing.return_value = "LLM TITLE"
        yield
