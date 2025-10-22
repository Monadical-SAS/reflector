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

    assert "WEBVTT" in result
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
