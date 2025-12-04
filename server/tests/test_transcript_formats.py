"""Tests for transcript format conversion functionality."""

import pytest

from reflector.db.transcripts import TranscriptParticipant, TranscriptTopic
from reflector.processors.types import Word
from reflector.utils.transcript_formats import (
    format_timestamp_mmss,
    get_speaker_name,
    topics_to_webvtt_named,
    transcript_to_json_segments,
    transcript_to_text,
    transcript_to_text_timestamped,
)


@pytest.mark.asyncio
async def test_get_speaker_name_with_participants():
    """Test speaker name resolution with participants list."""
    participants = [
        TranscriptParticipant(id="1", speaker=0, name="John Smith"),
        TranscriptParticipant(id="2", speaker=1, name="Jane Doe"),
    ]

    assert get_speaker_name(0, participants) == "John Smith"
    assert get_speaker_name(1, participants) == "Jane Doe"
    assert get_speaker_name(2, participants) == "Speaker 2"


@pytest.mark.asyncio
async def test_get_speaker_name_without_participants():
    """Test speaker name resolution without participants list."""
    assert get_speaker_name(0, None) == "Speaker 0"
    assert get_speaker_name(1, None) == "Speaker 1"
    assert get_speaker_name(5, []) == "Speaker 5"


@pytest.mark.asyncio
async def test_format_timestamp_mmss():
    """Test timestamp formatting to MM:SS."""
    assert format_timestamp_mmss(0) == "00:00"
    assert format_timestamp_mmss(5) == "00:05"
    assert format_timestamp_mmss(65) == "01:05"
    assert format_timestamp_mmss(125.7) == "02:05"
    assert format_timestamp_mmss(3661) == "61:01"


@pytest.mark.asyncio
async def test_transcript_to_text():
    """Test plain text format conversion."""
    topics = [
        TranscriptTopic(
            id="1",
            title="Topic 1",
            summary="Summary 1",
            timestamp=0.0,
            words=[
                Word(text="Hello", start=0.0, end=1.0, speaker=0),
                Word(text=" world.", start=1.0, end=2.0, speaker=0),
            ],
        ),
        TranscriptTopic(
            id="2",
            title="Topic 2",
            summary="Summary 2",
            timestamp=2.0,
            words=[
                Word(text="How", start=2.0, end=3.0, speaker=1),
                Word(text=" are", start=3.0, end=4.0, speaker=1),
                Word(text=" you?", start=4.0, end=5.0, speaker=1),
            ],
        ),
    ]

    participants = [
        TranscriptParticipant(id="1", speaker=0, name="John Smith"),
        TranscriptParticipant(id="2", speaker=1, name="Jane Doe"),
    ]

    result = transcript_to_text(topics, participants)
    lines = result.split("\n")

    assert len(lines) == 2
    assert lines[0] == "John Smith: Hello world."
    assert lines[1] == "Jane Doe: How are you?"


@pytest.mark.asyncio
async def test_transcript_to_text_timestamped():
    """Test timestamped text format conversion."""
    topics = [
        TranscriptTopic(
            id="1",
            title="Topic 1",
            summary="Summary 1",
            timestamp=0.0,
            words=[
                Word(text="Hello", start=0.0, end=1.0, speaker=0),
                Word(text=" world.", start=1.0, end=2.0, speaker=0),
            ],
        ),
        TranscriptTopic(
            id="2",
            title="Topic 2",
            summary="Summary 2",
            timestamp=65.0,
            words=[
                Word(text="How", start=65.0, end=66.0, speaker=1),
                Word(text=" are", start=66.0, end=67.0, speaker=1),
                Word(text=" you?", start=67.0, end=68.0, speaker=1),
            ],
        ),
    ]

    participants = [
        TranscriptParticipant(id="1", speaker=0, name="John Smith"),
        TranscriptParticipant(id="2", speaker=1, name="Jane Doe"),
    ]

    result = transcript_to_text_timestamped(topics, participants)
    lines = result.split("\n")

    assert len(lines) == 2
    assert lines[0] == "[00:00] John Smith: Hello world."
    assert lines[1] == "[01:05] Jane Doe: How are you?"


@pytest.mark.asyncio
async def test_topics_to_webvtt_named():
    """Test WebVTT format conversion with participant names."""
    topics = [
        TranscriptTopic(
            id="1",
            title="Topic 1",
            summary="Summary 1",
            timestamp=0.0,
            words=[
                Word(text="Hello", start=0.0, end=1.0, speaker=0),
                Word(text=" world.", start=1.0, end=2.0, speaker=0),
            ],
        ),
    ]

    participants = [
        TranscriptParticipant(id="1", speaker=0, name="John Smith"),
    ]

    result = topics_to_webvtt_named(topics, participants)

    assert result.startswith("WEBVTT")
    assert "<v John Smith>" in result
    assert "00:00:00.000 --> 00:00:02.000" in result
    assert "Hello world." in result


@pytest.mark.asyncio
async def test_transcript_to_json_segments():
    """Test JSON segments format conversion."""
    topics = [
        TranscriptTopic(
            id="1",
            title="Topic 1",
            summary="Summary 1",
            timestamp=0.0,
            words=[
                Word(text="Hello", start=0.0, end=1.0, speaker=0),
                Word(text=" world.", start=1.0, end=2.0, speaker=0),
            ],
        ),
        TranscriptTopic(
            id="2",
            title="Topic 2",
            summary="Summary 2",
            timestamp=2.0,
            words=[
                Word(text="How", start=2.0, end=3.0, speaker=1),
                Word(text=" are", start=3.0, end=4.0, speaker=1),
                Word(text=" you?", start=4.0, end=5.0, speaker=1),
            ],
        ),
    ]

    participants = [
        TranscriptParticipant(id="1", speaker=0, name="John Smith"),
        TranscriptParticipant(id="2", speaker=1, name="Jane Doe"),
    ]

    result = transcript_to_json_segments(topics, participants)

    assert len(result) == 2
    assert result[0].speaker == 0
    assert result[0].speaker_name == "John Smith"
    assert result[0].text == "Hello world."
    assert result[0].start == 0.0
    assert result[0].end == 2.0

    assert result[1].speaker == 1
    assert result[1].speaker_name == "Jane Doe"
    assert result[1].text == "How are you?"
    assert result[1].start == 2.0
    assert result[1].end == 5.0


@pytest.mark.asyncio
async def test_transcript_formats_with_empty_topics():
    """Test format conversion with empty topics list."""
    topics = []
    participants = []

    assert transcript_to_text(topics, participants) == ""
    assert transcript_to_text_timestamped(topics, participants) == ""
    assert "WEBVTT" in topics_to_webvtt_named(topics, participants)
    assert transcript_to_json_segments(topics, participants) == []


@pytest.mark.asyncio
async def test_transcript_formats_with_empty_words():
    """Test format conversion with topics containing no words."""
    topics = [
        TranscriptTopic(
            id="1",
            title="Topic 1",
            summary="Summary 1",
            timestamp=0.0,
            words=[],
        ),
    ]
    participants = []

    assert transcript_to_text(topics, participants) == ""
    assert transcript_to_text_timestamped(topics, participants) == ""
    assert "WEBVTT" in topics_to_webvtt_named(topics, participants)
    assert transcript_to_json_segments(topics, participants) == []


@pytest.mark.asyncio
async def test_transcript_formats_with_multiple_speakers():
    """Test format conversion with multiple speaker changes."""
    topics = [
        TranscriptTopic(
            id="1",
            title="Topic 1",
            summary="Summary 1",
            timestamp=0.0,
            words=[
                Word(text="Hello", start=0.0, end=1.0, speaker=0),
                Word(text=" there.", start=1.0, end=2.0, speaker=0),
                Word(text="Hi", start=2.0, end=3.0, speaker=1),
                Word(text=" back.", start=3.0, end=4.0, speaker=1),
                Word(text="Good", start=4.0, end=5.0, speaker=0),
                Word(text=" morning.", start=5.0, end=6.0, speaker=0),
            ],
        ),
    ]

    participants = [
        TranscriptParticipant(id="1", speaker=0, name="Alice"),
        TranscriptParticipant(id="2", speaker=1, name="Bob"),
    ]

    text_result = transcript_to_text(topics, participants)
    lines = text_result.split("\n")
    assert len(lines) == 3
    assert "Alice: Hello there." in lines[0]
    assert "Bob: Hi back." in lines[1]
    assert "Alice: Good morning." in lines[2]

    json_result = transcript_to_json_segments(topics, participants)
    assert len(json_result) == 3
    assert json_result[0].speaker_name == "Alice"
    assert json_result[1].speaker_name == "Bob"
    assert json_result[2].speaker_name == "Alice"


@pytest.mark.asyncio
async def test_transcript_formats_with_overlapping_speakers_multitrack():
    """Test format conversion for multitrack recordings with truly interleaved words.

    Multitrack recordings have words from different speakers sorted by start time,
    causing frequent speaker alternation. This tests the sentence-based segmentation
    that groups each speaker's words into complete sentences.
    """
    # Real multitrack data: words sorted by start time, speakers interleave
    # Alice says: "Hello there." (0.0-1.0)
    # Bob says: "I'm good." (0.5-1.5)
    # When sorted by time, words interleave: Hello, I'm, there., good.
    topics = [
        TranscriptTopic(
            id="1",
            title="Topic 1",
            summary="Summary 1",
            timestamp=0.0,
            words=[
                Word(text="Hello ", start=0.0, end=0.5, speaker=0),
                Word(text="I'm ", start=0.5, end=0.8, speaker=1),
                Word(text="there.", start=0.5, end=1.0, speaker=0),
                Word(text="good.", start=1.0, end=1.5, speaker=1),
            ],
        ),
    ]

    participants = [
        TranscriptParticipant(id="1", speaker=0, name="Alice"),
        TranscriptParticipant(id="2", speaker=1, name="Bob"),
    ]

    # With is_multitrack=True, should produce 2 segments (one per speaker sentence)
    # not 4 segments (one per speaker change)
    webvtt_result = topics_to_webvtt_named(topics, participants, is_multitrack=True)
    expected_webvtt = """WEBVTT

00:00:00.000 --> 00:00:01.000
<v Alice>Hello there.

00:00:00.500 --> 00:00:01.500
<v Bob>I'm good.
"""
    assert webvtt_result == expected_webvtt

    text_result = transcript_to_text(topics, participants, is_multitrack=True)
    lines = text_result.split("\n")
    assert len(lines) == 2
    assert "Alice: Hello there." in lines[0]
    assert "Bob: I'm good." in lines[1]

    timestamped_result = transcript_to_text_timestamped(
        topics, participants, is_multitrack=True
    )
    timestamped_lines = timestamped_result.split("\n")
    assert len(timestamped_lines) == 2
    assert "[00:00] Alice: Hello there." in timestamped_lines[0]
    assert "[00:00] Bob: I'm good." in timestamped_lines[1]

    segments = transcript_to_json_segments(topics, participants, is_multitrack=True)
    assert len(segments) == 2
    assert segments[0].speaker_name == "Alice"
    assert segments[0].text == "Hello there."
    assert segments[1].speaker_name == "Bob"
    assert segments[1].text == "I'm good."


@pytest.mark.asyncio
async def test_api_transcript_format_text(client):
    """Test GET /transcripts/{id} with transcript_format=text."""
    response = await client.post("/transcripts", json={"name": "Test transcript"})
    assert response.status_code == 200
    tid = response.json()["id"]

    from reflector.db.transcripts import (
        TranscriptParticipant,
        TranscriptTopic,
        transcripts_controller,
    )
    from reflector.processors.types import Word

    transcript = await transcripts_controller.get_by_id(tid)

    await transcripts_controller.update(
        transcript,
        {
            "participants": [
                TranscriptParticipant(
                    id="1", speaker=0, name="John Smith"
                ).model_dump(),
                TranscriptParticipant(id="2", speaker=1, name="Jane Doe").model_dump(),
            ]
        },
    )

    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Summary 1",
            timestamp=0,
            words=[
                Word(text="Hello", start=0, end=1, speaker=0),
                Word(text=" world.", start=1, end=2, speaker=0),
            ],
        ),
    )

    response = await client.get(f"/transcripts/{tid}?transcript_format=text")
    assert response.status_code == 200
    data = response.json()

    assert data["transcript_format"] == "text"
    assert "transcript" in data
    assert "John Smith: Hello world." in data["transcript"]


@pytest.mark.asyncio
async def test_api_transcript_format_text_timestamped(client):
    """Test GET /transcripts/{id} with transcript_format=text-timestamped."""
    response = await client.post("/transcripts", json={"name": "Test transcript"})
    assert response.status_code == 200
    tid = response.json()["id"]

    from reflector.db.transcripts import (
        TranscriptParticipant,
        TranscriptTopic,
        transcripts_controller,
    )
    from reflector.processors.types import Word

    transcript = await transcripts_controller.get_by_id(tid)

    await transcripts_controller.update(
        transcript,
        {
            "participants": [
                TranscriptParticipant(
                    id="1", speaker=0, name="John Smith"
                ).model_dump(),
            ]
        },
    )

    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Summary 1",
            timestamp=0,
            words=[
                Word(text="Hello", start=65, end=66, speaker=0),
                Word(text=" world.", start=66, end=67, speaker=0),
            ],
        ),
    )

    response = await client.get(
        f"/transcripts/{tid}?transcript_format=text-timestamped"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["transcript_format"] == "text-timestamped"
    assert "transcript" in data
    assert "[01:05] John Smith: Hello world." in data["transcript"]


@pytest.mark.asyncio
async def test_api_transcript_format_webvtt_named(client):
    """Test GET /transcripts/{id} with transcript_format=webvtt-named."""
    response = await client.post("/transcripts", json={"name": "Test transcript"})
    assert response.status_code == 200
    tid = response.json()["id"]

    from reflector.db.transcripts import (
        TranscriptParticipant,
        TranscriptTopic,
        transcripts_controller,
    )
    from reflector.processors.types import Word

    transcript = await transcripts_controller.get_by_id(tid)

    await transcripts_controller.update(
        transcript,
        {
            "participants": [
                TranscriptParticipant(
                    id="1", speaker=0, name="John Smith"
                ).model_dump(),
            ]
        },
    )

    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Summary 1",
            timestamp=0,
            words=[
                Word(text="Hello", start=0, end=1, speaker=0),
                Word(text=" world.", start=1, end=2, speaker=0),
            ],
        ),
    )

    response = await client.get(f"/transcripts/{tid}?transcript_format=webvtt-named")
    assert response.status_code == 200
    data = response.json()

    assert data["transcript_format"] == "webvtt-named"
    assert "transcript" in data
    assert "WEBVTT" in data["transcript"]
    assert "<v John Smith>" in data["transcript"]


@pytest.mark.asyncio
async def test_api_transcript_format_json(client):
    """Test GET /transcripts/{id} with transcript_format=json."""
    response = await client.post("/transcripts", json={"name": "Test transcript"})
    assert response.status_code == 200
    tid = response.json()["id"]

    from reflector.db.transcripts import (
        TranscriptParticipant,
        TranscriptTopic,
        transcripts_controller,
    )
    from reflector.processors.types import Word

    transcript = await transcripts_controller.get_by_id(tid)

    await transcripts_controller.update(
        transcript,
        {
            "participants": [
                TranscriptParticipant(
                    id="1", speaker=0, name="John Smith"
                ).model_dump(),
            ]
        },
    )

    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Summary 1",
            timestamp=0,
            words=[
                Word(text="Hello", start=0, end=1, speaker=0),
                Word(text=" world.", start=1, end=2, speaker=0),
            ],
        ),
    )

    response = await client.get(f"/transcripts/{tid}?transcript_format=json")
    assert response.status_code == 200
    data = response.json()

    assert data["transcript_format"] == "json"
    assert "transcript" in data
    assert isinstance(data["transcript"], list)
    assert len(data["transcript"]) == 1
    assert data["transcript"][0]["speaker"] == 0
    assert data["transcript"][0]["speaker_name"] == "John Smith"
    assert data["transcript"][0]["text"] == "Hello world."


@pytest.mark.asyncio
async def test_api_transcript_format_default_is_text(client):
    """Test GET /transcripts/{id} defaults to text format."""
    response = await client.post("/transcripts", json={"name": "Test transcript"})
    assert response.status_code == 200
    tid = response.json()["id"]

    from reflector.db.transcripts import TranscriptTopic, transcripts_controller
    from reflector.processors.types import Word

    transcript = await transcripts_controller.get_by_id(tid)

    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Summary 1",
            timestamp=0,
            words=[
                Word(text="Hello", start=0, end=1, speaker=0),
            ],
        ),
    )

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    data = response.json()

    assert data["transcript_format"] == "text"
    assert "transcript" in data


@pytest.mark.asyncio
async def test_api_topics_endpoint_multitrack_segmentation(client):
    """Test GET /transcripts/{id}/topics uses sentence-based segmentation for multitrack.

    This tests the fix for TASKS2.md - ensuring /topics endpoints correctly detect
    multitrack recordings and use sentence-based segmentation instead of fragmenting
    on every speaker change.
    """
    from datetime import datetime, timezone

    from reflector.db.recordings import Recording, recordings_controller
    from reflector.db.transcripts import (
        TranscriptParticipant,
        TranscriptTopic,
        transcripts_controller,
    )
    from reflector.processors.types import Word

    # Create a multitrack recording (has track_keys)
    recording = Recording(
        bucket_name="test-bucket",
        object_key="test-key",
        recorded_at=datetime.now(timezone.utc),
        track_keys=["track1.webm", "track2.webm"],  # This makes it multitrack
    )
    await recordings_controller.create(recording)

    # Create transcript linked to the recording
    transcript = await transcripts_controller.add(
        name="Multitrack Test",
        source_kind="file",
        recording_id=recording.id,
    )

    await transcripts_controller.update(
        transcript,
        {
            "participants": [
                TranscriptParticipant(id="1", speaker=0, name="Alice").model_dump(),
                TranscriptParticipant(id="2", speaker=1, name="Bob").model_dump(),
            ]
        },
    )

    # Add interleaved words (as they appear in real multitrack data)
    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Summary 1",
            timestamp=0,
            words=[
                Word(text="Hello ", start=0.0, end=0.5, speaker=0),
                Word(text="I'm ", start=0.5, end=0.8, speaker=1),
                Word(text="there.", start=0.5, end=1.0, speaker=0),
                Word(text="good.", start=1.0, end=1.5, speaker=1),
            ],
        ),
    )

    # Test /topics endpoint
    response = await client.get(f"/transcripts/{transcript.id}/topics")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    topic = data[0]

    # Key assertion: multitrack should produce 2 segments (one per speaker sentence)
    # Not 4 segments (one per speaker change)
    assert len(topic["segments"]) == 2

    # Check content
    segment_texts = [s["text"] for s in topic["segments"]]
    assert "Hello there." in segment_texts
    assert "I'm good." in segment_texts


@pytest.mark.asyncio
async def test_api_topics_endpoint_non_multitrack_segmentation(client):
    """Test GET /transcripts/{id}/topics uses default segmentation for non-multitrack.

    Ensures backward compatibility - transcripts without multitrack recordings
    should continue using the default speaker-change-based segmentation.
    """
    from reflector.db.transcripts import (
        TranscriptParticipant,
        TranscriptTopic,
        transcripts_controller,
    )
    from reflector.processors.types import Word

    # Create transcript WITHOUT recording (defaulted as not multitrack) TODO better heuristic
    response = await client.post("/transcripts", json={"name": "Test transcript"})
    assert response.status_code == 200
    tid = response.json()["id"]

    transcript = await transcripts_controller.get_by_id(tid)

    await transcripts_controller.update(
        transcript,
        {
            "participants": [
                TranscriptParticipant(id="1", speaker=0, name="Alice").model_dump(),
                TranscriptParticipant(id="2", speaker=1, name="Bob").model_dump(),
            ]
        },
    )

    # Add interleaved words
    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Summary 1",
            timestamp=0,
            words=[
                Word(text="Hello ", start=0.0, end=0.5, speaker=0),
                Word(text="I'm ", start=0.5, end=0.8, speaker=1),
                Word(text="there.", start=0.5, end=1.0, speaker=0),
                Word(text="good.", start=1.0, end=1.5, speaker=1),
            ],
        ),
    )

    # Test /topics endpoint
    response = await client.get(f"/transcripts/{tid}/topics")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    topic = data[0]

    # Non-multitrack: should produce 4 segments (one per speaker change)
    assert len(topic["segments"]) == 4


@pytest.mark.asyncio
async def test_api_topics_with_words_endpoint_multitrack(client):
    """Test GET /transcripts/{id}/topics/with-words uses multitrack segmentation."""
    from datetime import datetime, timezone

    from reflector.db.recordings import Recording, recordings_controller
    from reflector.db.transcripts import (
        TranscriptParticipant,
        TranscriptTopic,
        transcripts_controller,
    )
    from reflector.processors.types import Word

    # Create multitrack recording
    recording = Recording(
        bucket_name="test-bucket",
        object_key="test-key-2",
        recorded_at=datetime.now(timezone.utc),
        track_keys=["track1.webm", "track2.webm"],
    )
    await recordings_controller.create(recording)

    transcript = await transcripts_controller.add(
        name="Multitrack Test 2",
        source_kind="file",
        recording_id=recording.id,
    )

    await transcripts_controller.update(
        transcript,
        {
            "participants": [
                TranscriptParticipant(id="1", speaker=0, name="Alice").model_dump(),
                TranscriptParticipant(id="2", speaker=1, name="Bob").model_dump(),
            ]
        },
    )

    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Summary 1",
            timestamp=0,
            words=[
                Word(text="Hello ", start=0.0, end=0.5, speaker=0),
                Word(text="I'm ", start=0.5, end=0.8, speaker=1),
                Word(text="there.", start=0.5, end=1.0, speaker=0),
                Word(text="good.", start=1.0, end=1.5, speaker=1),
            ],
        ),
    )

    response = await client.get(f"/transcripts/{transcript.id}/topics/with-words")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    topic = data[0]

    # Should have 2 segments (multitrack sentence-based)
    assert len(topic["segments"]) == 2
    # Should also have words field
    assert "words" in topic
    assert len(topic["words"]) == 4
