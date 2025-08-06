"""Integration tests for WebVTT auto-update functionality in Transcript model."""
import pytest
from datetime import datetime, timezone
from reflector.db.transcripts import (
    Transcript, 
    TranscriptController,
    TranscriptTopic,
    SourceKind,
    WEBVTT_COLUMN_NAME,
    TOPICS_COLUMN_NAME,
    transcripts
)
from reflector.processors.types import Word
from reflector.db import database
import json


@pytest.mark.asyncio
class TestWebVTTAutoUpdate:
    """Test that WebVTT field auto-updates when Transcript is created or modified."""
    
    async def test_webvtt_not_updated_on_transcript_creation_without_topics(self):
        """WebVTT should be None when creating transcript without topics."""
        controller = TranscriptController()
        
        transcript = await controller.add(
            name="Test Transcript",
            source_kind=SourceKind.FILE,
        )
        
        try:
            result = await database.fetch_one(
                transcripts.select().where(transcripts.c.id == transcript.id)
            )
            
            assert result is not None
            assert result[WEBVTT_COLUMN_NAME] is None
        finally:
            await controller.remove_by_id(transcript.id)
    
    async def test_webvtt_updated_on_upsert_topic(self):
        """WebVTT should update when upserting topics via upsert_topic method."""
        controller = TranscriptController()
        
        transcript = await controller.add(
            name="Test Transcript",
            source_kind=SourceKind.FILE,
        )
        
        try:
            topic = TranscriptTopic(
                id="topic1",
                title="Test Topic",
                summary="Test summary",
                timestamp=0.0,
                words=[
                    Word(text="Hello", start=0.0, end=0.5, speaker=0),
                    Word(text=" world", start=0.5, end=1.0, speaker=0),
                ]
            )
            
            await controller.upsert_topic(transcript, topic)
            
            result = await database.fetch_one(
                transcripts.select().where(transcripts.c.id == transcript.id)
            )
            
            assert result is not None
            webvtt = result[WEBVTT_COLUMN_NAME]
            
            assert webvtt is not None
            assert "WEBVTT" in webvtt
            assert "Hello world" in webvtt
            assert "<v Speaker0>" in webvtt
            
        finally:
            await controller.remove_by_id(transcript.id)
    
    async def test_webvtt_updated_on_direct_topics_update(self):
        """WebVTT should update when updating topics field directly."""
        controller = TranscriptController()
        
        transcript = await controller.add(
            name="Test Transcript", 
            source_kind=SourceKind.FILE,
        )
        
        try:
            topics_data = [
                {
                    "id": "topic1",
                    "title": "First Topic",
                    "summary": "First sentence test",
                    "timestamp": 0.0,
                    "words": [
                        {"text": "First", "start": 0.0, "end": 0.5, "speaker": 0},
                        {"text": " sentence", "start": 0.5, "end": 1.0, "speaker": 0},
                    ]
                }
            ]
            
            await controller.update(
                transcript,
                {TOPICS_COLUMN_NAME: topics_data}
            )
            
            # Fetch from DB
            result = await database.fetch_one(
                transcripts.select().where(transcripts.c.id == transcript.id)
            )
            
            assert result is not None
            webvtt = result[WEBVTT_COLUMN_NAME]
            
            assert webvtt is not None
            assert "WEBVTT" in webvtt
            assert "First sentence" in webvtt
            
        finally:
            await controller.remove_by_id(transcript.id)
    
    async def test_webvtt_updated_manually_with_handle_topics_update(self):
        """Test that _handle_topics_update works when called manually."""
        controller = TranscriptController()
        
        transcript = await controller.add(
            name="Test Transcript",
            source_kind=SourceKind.FILE,
        )
        
        try:
            topic1 = TranscriptTopic(
                id="topic1",
                title="Topic 1",
                summary="Manual test",
                timestamp=0.0,
                words=[
                    Word(text="Manual", start=0.0, end=0.5, speaker=0),
                    Word(text=" test", start=0.5, end=1.0, speaker=0),
                ]
            )
            
            transcript.upsert_topic(topic1)
            
            values = {TOPICS_COLUMN_NAME: transcript.topics_dump()}
            
            await controller.update(transcript, values)
            
            # Fetch from DB
            result = await database.fetch_one(
                transcripts.select().where(transcripts.c.id == transcript.id)
            )
            
            assert result is not None
            webvtt = result[WEBVTT_COLUMN_NAME]
            
            assert webvtt is not None
            assert "WEBVTT" in webvtt
            assert "Manual test" in webvtt
            assert "<v Speaker0>" in webvtt
            
        finally:
            await controller.remove_by_id(transcript.id)
    
    async def test_webvtt_update_with_non_sequential_topics_fails(self):
        """Test that non-sequential topics raise assertion error."""
        controller = TranscriptController()
        
        transcript = await controller.add(
            name="Test Transcript",
            source_kind=SourceKind.FILE,
        )
        
        try:
            topic1 = TranscriptTopic(
                id="topic1", 
                title="Bad Topic",
                summary="Bad order test",
                timestamp=1.0,
                words=[
                    Word(text="Second", start=2.0, end=2.5, speaker=0),
                    Word(text="First", start=1.0, end=1.5, speaker=0),
                ]
            )
            
            transcript.upsert_topic(topic1)
            values = {TOPICS_COLUMN_NAME: transcript.topics_dump()}
            
            with pytest.raises(AssertionError) as exc_info:
                TranscriptController._handle_topics_update(values)
            
            assert "Words are not in sequence" in str(exc_info.value)
            
        finally:
            await controller.remove_by_id(transcript.id)
    
    async def test_multiple_speakers_in_webvtt(self):
        """Test WebVTT generation with multiple speakers."""
        controller = TranscriptController()
        
        transcript = await controller.add(
            name="Test Transcript",
            source_kind=SourceKind.FILE,
        )
        
        try:
            topic = TranscriptTopic(
                id="topic1",
                title="Multi Speaker",
                summary="Multi speaker test",
                timestamp=0.0,
                words=[
                    Word(text="Hello", start=0.0, end=0.5, speaker=0),
                    Word(text="Hi", start=1.0, end=1.5, speaker=1),
                    Word(text="Goodbye", start=2.0, end=2.5, speaker=0),
                ]
            )
            
            transcript.upsert_topic(topic)
            values = {TOPICS_COLUMN_NAME: transcript.topics_dump()}
            
            await controller.update(transcript, values)
            
            # Fetch from DB
            result = await database.fetch_one(
                transcripts.select().where(transcripts.c.id == transcript.id)
            )
            
            assert result is not None
            webvtt = result[WEBVTT_COLUMN_NAME]
            
            assert webvtt is not None
            assert "<v Speaker0>" in webvtt
            assert "<v Speaker1>" in webvtt
            assert "Hello" in webvtt
            assert "Hi" in webvtt
            assert "Goodbye" in webvtt
            
        finally:
            await controller.remove_by_id(transcript.id)