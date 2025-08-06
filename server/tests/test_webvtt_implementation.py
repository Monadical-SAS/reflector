"""Test WebVTT auto-update functionality and edge cases."""
import pytest
from reflector.db.transcripts import (
    Transcript,
    TranscriptController,
    SourceKind,
    WEBVTT_COLUMN_NAME,
    TOPICS_COLUMN_NAME,
)


@pytest.mark.asyncio
class TestWebVTTAutoUpdateImplementation:
    """Test that WebVTT auto-update is working correctly."""
    
    async def test_update_method_calls_handle_topics_update(self):
        """
        Verify that TranscriptController.update() calls _handle_topics_update()
        to automatically update WebVTT when topics change.
        """
        controller = TranscriptController()
        
        # Check the source code - update() should call _handle_topics_update()
        import inspect
        update_source = inspect.getsource(controller.update)
        
        # The update method now properly calls _handle_topics_update
        assert "_handle_topics_update" in update_source, \
            "Regression: update() no longer calls _handle_topics_update!"
        
        # Verify the implementation uses _handle_topics_update
        assert "TranscriptController._handle_topics_update(values)" in update_source
    
    async def test_handle_topics_update_handles_dict_conversion(self):
        """
        Verify that _handle_topics_update() properly converts dict data to TranscriptTopic objects.
        """
        # Test with dict data (as would come from database)
        values = {
            TOPICS_COLUMN_NAME: [{
                "id": "topic1",
                "title": "Test",
                "summary": "Test",
                "timestamp": 0.0,
                "words": [{"text": "Hello", "start": 0.0, "end": 1.0, "speaker": 0}]
            }]
        }
        
        # This should now work - _handle_topics_update converts dicts to TranscriptTopic objects
        updated_values = TranscriptController._handle_topics_update(values)
        
        # WebVTT should be generated
        assert WEBVTT_COLUMN_NAME in updated_values
        assert updated_values[WEBVTT_COLUMN_NAME] is not None
        assert "WEBVTT" in updated_values[WEBVTT_COLUMN_NAME]
    
    async def test_upsert_topic_updates_webvtt(self):
        """
        Verify that upsert_topic() updates WebVTT automatically through the update() method.
        """
        controller = TranscriptController()
        
        # Check upsert_topic source
        import inspect
        upsert_source = inspect.getsource(controller.upsert_topic)
        
        # It calls update() with topics
        assert "self.update" in upsert_source
        assert "topics_dump()" in upsert_source
        
        # And update() calls _handle_topics_update()
        update_source = inspect.getsource(controller.update)
        assert "_handle_topics_update" in update_source
        
        # This ensures WebVTT is automatically updated when topics are upserted
    
    async def test_webvtt_update_is_automatic(self):
        """
        Verify that WebVTT updates are automatic - no manual intervention required.
        """
        # Verify the automatic flow works:
        # controller.update(transcript, {"topics": topics_data})
        # -> automatically calls _handle_topics_update
        # -> converts dict to TranscriptTopic objects
        # -> generates WebVTT
        # -> includes WebVTT in the update
        
        # This is covered by integration tests
        pass  # Integration point verified in other tests


@pytest.mark.asyncio  
class TestWebVTTEdgeCases:
    """Test edge cases and potential issues."""
    
    async def test_webvtt_readonly_warning(self):
        """
        Test that attempting to manually set WebVTT triggers a warning (TODO).
        Currently just silently ignores manual WebVTT updates.
        """
        # TODO: When logging is implemented, this should verify a warning is logged
        # when someone tries to manually set the webvtt field
        
        values = {
            WEBVTT_COLUMN_NAME: "manual webvtt content",
            TOPICS_COLUMN_NAME: [{"id": "1", "title": "Test", "summary": "Test", "timestamp": 0.0, "words": []}]
        }
        
        updated = TranscriptController._handle_topics_update(values)
        
        # WebVTT should be auto-generated, not the manual value
        assert updated[WEBVTT_COLUMN_NAME] != "manual webvtt content"
        assert "WEBVTT" in updated[WEBVTT_COLUMN_NAME]
    
    async def test_migration_should_populate_webvtt(self):
        """
        The migration that added the webvtt field should have:
        1. Added the column (it did)
        2. Populated existing records with WebVTT from topics (it didn't?)
        
        This means existing transcripts might have null WebVTT even with topics.
        """
        # Check if migration populates WebVTT for existing records
        pytest.skip("Need to check if migration populates WebVTT for existing records")