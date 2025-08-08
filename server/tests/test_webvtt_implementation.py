"""Test WebVTT auto-update functionality and edge cases."""
import pytest
from reflector.db.transcripts import (
    Transcript,
    TranscriptController,
    SourceKind,
    "topics",
)


@pytest.mark.asyncio
class TestWebVTTAutoUpdateImplementation:

    async def test_handle_topics_update_handles_dict_conversion(self):
        """
        Verify that _handle_topics_update() properly converts dict data to TranscriptTopic objects.
        """
        values = {
            "topics": [{
                "id": "topic1",
                "title": "Test",
                "summary": "Test",
                "timestamp": 0.0,
                "words": [{"text": "Hello", "start": 0.0, "end": 1.0, "speaker": 0}]
            }]
        }
        
        updated_values = TranscriptController._handle_topics_update(values)
        
        assert "webvtt" in updated_values
        assert updated_values["webvtt"] is not None
        assert "WEBVTT" in updated_values["webvtt"]
    
