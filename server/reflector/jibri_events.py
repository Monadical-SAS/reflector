import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel
from typing_extensions import TypedDict


class ParticipantInfo(BaseModel):
    jid: str
    nick: str
    id: str
    is_moderator: bool = False


class ParticipantLeftInfo(BaseModel):
    jid: str
    nick: Optional[str] = None
    duration_seconds: Optional[int] = None


class RoomCreatedEvent(BaseModel):
    type: Literal["room_created"]
    timestamp: int
    room_name: str
    room_jid: str
    meeting_url: str


class RecordingStartedEvent(BaseModel):
    type: Literal["recording_started"]
    timestamp: int
    room_name: str
    session_id: str
    jibri_jid: str


class RecordingStoppedEvent(BaseModel):
    type: Literal["recording_stopped"]
    timestamp: int
    room_name: str
    session_id: str
    meeting_url: str


class ParticipantJoinedEvent(BaseModel):
    type: Literal["participant_joined"]
    timestamp: int
    room_name: str
    participant: ParticipantInfo


class ParticipantLeftEvent(BaseModel):
    type: Literal["participant_left"]
    timestamp: int
    room_name: str
    participant: ParticipantLeftInfo


class SpeakerActiveEvent(BaseModel):
    type: Literal["speaker_active"]
    timestamp: int
    room_name: str
    speaker_jid: str
    speaker_nick: str
    duration: int


class DominantSpeakerChangedEvent(BaseModel):
    type: Literal["dominant_speaker_changed"]
    timestamp: int
    room_name: str
    previous: str
    current: str


JitsiEvent = Union[
    RoomCreatedEvent,
    RecordingStartedEvent,
    RecordingStoppedEvent,
    ParticipantJoinedEvent,
    ParticipantLeftEvent,
    SpeakerActiveEvent,
    DominantSpeakerChangedEvent,
]


class RoomInfo(TypedDict):
    name: str
    jid: str
    created_at: int
    meeting_url: str
    recording_stopped_at: Optional[int]


class ParticipantData(TypedDict):
    jid: str
    nick: str
    id: str
    is_moderator: bool
    joined_at: int
    left_at: Optional[int]
    duration: Optional[int]
    events: List[str]


class SpeakerStats(TypedDict):
    total_time: int
    nick: str


class ParsedMetadata(TypedDict):
    room: RoomInfo
    participants: List[ParticipantData]
    speaker_stats: Dict[str, SpeakerStats]
    event_count: int


class JitsiEventParser:
    def parse_event(self, event_data: Dict[str, Any]) -> Optional[JitsiEvent]:
        event_type = event_data.get("type")

        try:
            if event_type == "room_created":
                return RoomCreatedEvent(**event_data)
            elif event_type == "recording_started":
                return RecordingStartedEvent(**event_data)
            elif event_type == "recording_stopped":
                return RecordingStoppedEvent(**event_data)
            elif event_type == "participant_joined":
                return ParticipantJoinedEvent(**event_data)
            elif event_type == "participant_left":
                return ParticipantLeftEvent(**event_data)
            elif event_type == "speaker_active":
                return SpeakerActiveEvent(**event_data)
            elif event_type == "dominant_speaker_changed":
                return DominantSpeakerChangedEvent(**event_data)
            else:
                return None
        except Exception:
            return None

    def parse_events_file(self, recording_path: str) -> ParsedMetadata:
        events_file = Path(recording_path) / "events.jsonl"

        room_info: RoomInfo = {
            "name": "",
            "jid": "",
            "created_at": 0,
            "meeting_url": "",
            "recording_stopped_at": None,
        }

        if not events_file.exists():
            return ParsedMetadata(
                room=room_info, participants=[], speaker_stats={}, event_count=0
            )

        events: List[JitsiEvent] = []
        participants: Dict[str, ParticipantData] = {}
        speaker_stats: Dict[str, SpeakerStats] = {}

        with open(events_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    event_data = json.loads(line)
                    event = self.parse_event(event_data)

                    if event is None:
                        continue

                    events.append(event)

                    if isinstance(event, RoomCreatedEvent):
                        room_info = {
                            "name": event.room_name,
                            "jid": event.room_jid,
                            "created_at": event.timestamp,
                            "meeting_url": event.meeting_url,
                            "recording_stopped_at": None,
                        }

                    elif isinstance(event, ParticipantJoinedEvent):
                        participants[event.participant.id] = {
                            "jid": event.participant.jid,
                            "nick": event.participant.nick,
                            "id": event.participant.id,
                            "is_moderator": event.participant.is_moderator,
                            "joined_at": event.timestamp,
                            "left_at": None,
                            "duration": None,
                            "events": ["joined"],
                        }

                    elif isinstance(event, ParticipantLeftEvent):
                        participant_id = event.participant.jid.split("/")[0]
                        if participant_id in participants:
                            participants[participant_id]["left_at"] = event.timestamp
                            participants[participant_id]["duration"] = (
                                event.participant.duration_seconds
                            )
                            participants[participant_id]["events"].append("left")

                    elif isinstance(event, SpeakerActiveEvent):
                        if event.speaker_jid not in speaker_stats:
                            speaker_stats[event.speaker_jid] = {
                                "total_time": 0,
                                "nick": event.speaker_nick,
                            }
                        speaker_stats[event.speaker_jid]["total_time"] += event.duration

                    elif isinstance(event, RecordingStoppedEvent):
                        room_info["recording_stopped_at"] = event.timestamp
                        room_info["meeting_url"] = event.meeting_url

                except (json.JSONDecodeError, Exception):
                    continue

        return ParsedMetadata(
            room=room_info,
            participants=list(participants.values()),
            speaker_stats=speaker_stats,
            event_count=len(events),
        )
