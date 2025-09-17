import json
import tempfile
from pathlib import Path

from reflector.jibri_events import (
    JitsiEventParser,
    ParticipantJoinedEvent,
    RoomCreatedEvent,
)


def test_parse_room_created_event():
    parser = JitsiEventParser()
    event_data = {
        "type": "room_created",
        "timestamp": 1234567890,
        "room_name": "TestRoom",
        "room_jid": "testroom@conference.meet.jitsi",
        "meeting_url": "https://meet.jitsi/TestRoom",
    }

    event = parser.parse_event(event_data)

    assert isinstance(event, RoomCreatedEvent)
    assert event.room_name == "TestRoom"
    assert event.meeting_url == "https://meet.jitsi/TestRoom"


def test_parse_participant_joined_event():
    parser = JitsiEventParser()
    event_data = {
        "type": "participant_joined",
        "timestamp": 1234567891,
        "room_name": "TestRoom",
        "participant": {
            "jid": "user1@meet.jitsi/resource",
            "nick": "John Doe",
            "id": "user1@meet.jitsi",
            "is_moderator": False,
        },
    }

    event = parser.parse_event(event_data)

    assert isinstance(event, ParticipantJoinedEvent)
    assert event.participant.nick == "John Doe"
    assert event.participant.is_moderator is False


def test_parse_unknown_event_returns_none():
    parser = JitsiEventParser()
    event_data = {"type": "unknown_event", "timestamp": 1234567890}

    event = parser.parse_event(event_data)
    assert event is None


def test_parse_events_file_with_complete_session():
    parser = JitsiEventParser()

    with tempfile.TemporaryDirectory() as tmpdir:
        events_file = Path(tmpdir) / "events.jsonl"

        events = [
            {
                "type": "room_created",
                "timestamp": 1234567890,
                "room_name": "TestRoom",
                "room_jid": "testroom@conference.meet.jitsi",
                "meeting_url": "https://meet.jitsi/TestRoom",
            },
            {
                "type": "participant_joined",
                "timestamp": 1234567892,
                "room_name": "TestRoom",
                "participant": {
                    "jid": "user1@meet.jitsi/resource",
                    "nick": "John Doe",
                    "id": "user1@meet.jitsi",
                    "is_moderator": False,
                },
            },
            {
                "type": "speaker_active",
                "timestamp": 1234567895,
                "room_name": "TestRoom",
                "speaker_jid": "user1@meet.jitsi",
                "speaker_nick": "John Doe",
                "duration": 10,
            },
            {
                "type": "participant_left",
                "timestamp": 1234567920,
                "room_name": "TestRoom",
                "participant": {
                    "jid": "user1@meet.jitsi/resource",
                    "duration_seconds": 28,
                },
            },
        ]

        with open(events_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        metadata = parser.parse_events_file(tmpdir)

        assert metadata["room"]["name"] == "TestRoom"
        assert metadata["room"]["meeting_url"] == "https://meet.jitsi/TestRoom"
        assert len(metadata["participants"]) == 1
        assert metadata["event_count"] == 4


def test_parse_events_file_missing_file():
    parser = JitsiEventParser()

    with tempfile.TemporaryDirectory() as tmpdir:
        metadata = parser.parse_events_file(tmpdir)

        assert metadata["room"]["name"] == ""
        assert len(metadata["participants"]) == 0
        assert metadata["event_count"] == 0
