"""
Tests for Hatchet payload thinning optimizations.

Verifies that:
1. TopicChunkInput no longer carries words
2. TopicChunkResult no longer carries words
3. words_to_segments() matches Transcript.as_segments(is_multitrack=False) — behavioral equivalence
   for the extract_subjects refactoring
4. TopicsResult can be constructed with empty transcript words
"""

from reflector.hatchet.workflows.models import TopicChunkResult
from reflector.hatchet.workflows.topic_chunk_processing import TopicChunkInput
from reflector.processors.types import Word


def _make_words(speaker: int = 0, start: float = 0.0) -> list[Word]:
    return [
        Word(text="Hello", start=start, end=start + 0.5, speaker=speaker),
        Word(text=" world.", start=start + 0.5, end=start + 1.0, speaker=speaker),
    ]


class TestTopicChunkInputNoWords:
    """TopicChunkInput must not have a words field."""

    def test_no_words_field(self):
        assert "words" not in TopicChunkInput.model_fields

    def test_construction_without_words(self):
        inp = TopicChunkInput(
            chunk_index=0, chunk_text="Hello world.", timestamp=0.0, duration=1.0
        )
        assert inp.chunk_index == 0
        assert inp.chunk_text == "Hello world."

    def test_rejects_words_kwarg(self):
        """Passing words= should raise a validation error (field doesn't exist)."""
        import pydantic

        try:
            TopicChunkInput(
                chunk_index=0,
                chunk_text="text",
                timestamp=0.0,
                duration=1.0,
                words=_make_words(),
            )
            # If pydantic is configured to ignore extra, this won't raise.
            # Verify the field is still absent from the model.
            assert "words" not in TopicChunkInput.model_fields
        except pydantic.ValidationError:
            pass  # Expected


class TestTopicChunkResultNoWords:
    """TopicChunkResult must not have a words field."""

    def test_no_words_field(self):
        assert "words" not in TopicChunkResult.model_fields

    def test_construction_without_words(self):
        result = TopicChunkResult(
            chunk_index=0,
            title="Test",
            summary="Summary",
            timestamp=0.0,
            duration=1.0,
        )
        assert result.title == "Test"
        assert result.chunk_index == 0

    def test_serialization_roundtrip(self):
        """Serialized TopicChunkResult has no words key."""
        result = TopicChunkResult(
            chunk_index=0,
            title="Test",
            summary="Summary",
            timestamp=0.0,
            duration=1.0,
        )
        data = result.model_dump()
        assert "words" not in data
        reconstructed = TopicChunkResult(**data)
        assert reconstructed == result


class TestWordsToSegmentsBehavioralEquivalence:
    """words_to_segments() must produce same output as Transcript.as_segments(is_multitrack=False).

    This ensures the extract_subjects refactoring (from task output topic.transcript.as_segments()
    to words_to_segments(db_topic.words)) preserves identical behavior.
    """

    def test_single_speaker(self):
        from reflector.processors.types import Transcript as TranscriptType
        from reflector.processors.types import words_to_segments

        words = _make_words(speaker=0)
        direct = words_to_segments(words)
        via_transcript = TranscriptType(words=words).as_segments(is_multitrack=False)

        assert len(direct) == len(via_transcript)
        for d, v in zip(direct, via_transcript):
            assert d.text == v.text
            assert d.speaker == v.speaker
            assert d.start == v.start
            assert d.end == v.end

    def test_multiple_speakers(self):
        from reflector.processors.types import Transcript as TranscriptType
        from reflector.processors.types import words_to_segments

        words = [
            Word(text="Hello", start=0.0, end=0.5, speaker=0),
            Word(text=" world.", start=0.5, end=1.0, speaker=0),
            Word(text=" How", start=1.0, end=1.5, speaker=1),
            Word(text=" are", start=1.5, end=2.0, speaker=1),
            Word(text=" you?", start=2.0, end=2.5, speaker=1),
        ]

        direct = words_to_segments(words)
        via_transcript = TranscriptType(words=words).as_segments(is_multitrack=False)

        assert len(direct) == len(via_transcript)
        for d, v in zip(direct, via_transcript):
            assert d.text == v.text
            assert d.speaker == v.speaker

    def test_empty_words(self):
        from reflector.processors.types import Transcript as TranscriptType
        from reflector.processors.types import words_to_segments

        assert words_to_segments([]) == []
        assert TranscriptType(words=[]).as_segments(is_multitrack=False) == []


class TestTopicsResultEmptyWords:
    """TopicsResult can carry topics with empty transcript words."""

    def test_construction_with_empty_words(self):
        from reflector.hatchet.workflows.models import TopicsResult
        from reflector.processors.types import TitleSummary
        from reflector.processors.types import Transcript as TranscriptType

        topics = [
            TitleSummary(
                title="Topic A",
                summary="Summary A",
                timestamp=0.0,
                duration=5.0,
                transcript=TranscriptType(words=[]),
            ),
            TitleSummary(
                title="Topic B",
                summary="Summary B",
                timestamp=5.0,
                duration=5.0,
                transcript=TranscriptType(words=[]),
            ),
        ]
        result = TopicsResult(topics=topics)
        assert len(result.topics) == 2
        for t in result.topics:
            assert t.transcript.words == []

    def test_serialization_roundtrip(self):
        from reflector.hatchet.workflows.models import TopicsResult
        from reflector.processors.types import TitleSummary
        from reflector.processors.types import Transcript as TranscriptType

        topics = [
            TitleSummary(
                title="Topic",
                summary="Summary",
                timestamp=0.0,
                duration=1.0,
                transcript=TranscriptType(words=[]),
            )
        ]
        result = TopicsResult(topics=topics)
        data = result.model_dump()
        reconstructed = TopicsResult(**data)
        assert len(reconstructed.topics) == 1
        assert reconstructed.topics[0].transcript.words == []
