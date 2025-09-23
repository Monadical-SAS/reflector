"""Integration tests for WebVTT auto-update functionality in Transcript model."""

import pytest
from sqlalchemy import select

from reflector.db.base import TranscriptModel
from reflector.db.transcripts import (
    SourceKind,
    TranscriptController,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.processors.types import Word


@pytest.mark.asyncio
class TestWebVTTAutoUpdate:
    """Test that WebVTT field auto-updates when Transcript is created or modified."""

    async def test_webvtt_not_updated_on_transcript_creation_without_topics(
        self, session
    ):
        """WebVTT should be None when creating transcript without topics."""
        # Using global transcripts_controller

        transcript = await transcripts_controller.add(
            session,
            name="Test Transcript",
            source_kind=SourceKind.FILE,
        )

        try:
            result = await db_session.execute(
                select(TranscriptModel).where(TranscriptModel.id == transcript.id)
            )
            row = result.scalar_one_or_none()

            assert row is not None
            assert row.webvtt is None
        finally:
            await transcripts_controller.remove_by_id(session, transcript.id)

    async def test_webvtt_updated_on_upsert_topic(self, db_db_session):
        """WebVTT should update when upserting topics via upsert_topic method."""
        # Using global transcripts_controller

        transcript = await transcripts_controller.add(
            session,
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
                ],
            )

            await transcripts_controller.upsert_topic(session, transcript, topic)

            result = await db_session.execute(
                select(TranscriptModel).where(TranscriptModel.id == transcript.id)
            )
            row = result.scalar_one_or_none()

            assert row is not None
            webvtt = row.webvtt

            assert webvtt is not None
            assert "WEBVTT" in webvtt
            assert "Hello world" in webvtt
            assert "<v Speaker0>" in webvtt

        finally:
            await transcripts_controller.remove_by_id(session, transcript.id)

    async def test_webvtt_updated_on_direct_topics_update(self, db_db_session):
        """WebVTT should update when updating topics field directly."""
        # Using global transcripts_controller

        transcript = await transcripts_controller.add(
            session,
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
                    ],
                }
            ]

            await transcripts_controller.update(
                session, transcript, {"topics": topics_data}
            )

            # Fetch from DB
            result = await db_session.execute(
                select(TranscriptModel).where(TranscriptModel.id == transcript.id)
            )
            row = result.scalar_one_or_none()

            assert row is not None
            webvtt = row.webvtt

            assert webvtt is not None
            assert "WEBVTT" in webvtt
            assert "First sentence" in webvtt

        finally:
            await transcripts_controller.remove_by_id(session, transcript.id)

    async def test_webvtt_updated_manually_with_handle_topics_update(
        self, db_db_session
    ):
        """Test that _handle_topics_update works when called manually."""
        # Using global transcripts_controller

        transcript = await transcripts_controller.add(
            session,
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
                ],
            )

            transcript.upsert_topic(topic1)

            values = {"topics": transcript.topics_dump()}

            await transcripts_controller.update(session, transcript, values)

            # Fetch from DB
            result = await db_session.execute(
                select(TranscriptModel).where(TranscriptModel.id == transcript.id)
            )
            row = result.scalar_one_or_none()

            assert row is not None
            webvtt = row.webvtt

            assert webvtt is not None
            assert "WEBVTT" in webvtt
            assert "Manual test" in webvtt
            assert "<v Speaker0>" in webvtt

        finally:
            await transcripts_controller.remove_by_id(session, transcript.id)

    async def test_webvtt_update_with_non_sequential_topics_fails(self, db_db_session):
        """Test that non-sequential topics raise assertion error."""
        # Using global transcripts_controller

        transcript = await transcripts_controller.add(
            session,
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
                ],
            )

            transcript.upsert_topic(topic1)
            values = {"topics": transcript.topics_dump()}

            with pytest.raises(AssertionError) as exc_info:
                TranscriptController._handle_topics_update(values)

            assert "Words are not in sequence" in str(exc_info.value)

        finally:
            await transcripts_controller.remove_by_id(session, transcript.id)

    async def test_multiple_speakers_in_webvtt(self, db_db_session):
        """Test WebVTT generation with multiple speakers."""
        # Using global transcripts_controller

        transcript = await transcripts_controller.add(
            session,
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
                ],
            )

            transcript.upsert_topic(topic)
            values = {"topics": transcript.topics_dump()}

            await transcripts_controller.update(session, transcript, values)

            # Fetch from DB
            result = await db_session.execute(
                select(TranscriptModel).where(TranscriptModel.id == transcript.id)
            )
            row = result.scalar_one_or_none()

            assert row is not None
            webvtt = row.webvtt

            assert webvtt is not None
            assert "<v Speaker0>" in webvtt
            assert "<v Speaker1>" in webvtt
            assert "Hello" in webvtt
            assert "Hi" in webvtt
            assert "Goodbye" in webvtt

        finally:
            await transcripts_controller.remove_by_id(session, transcript.id)
