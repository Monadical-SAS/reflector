"""
Celery tasks for consuming Jitsi events from Redis queues.
"""

import json
from datetime import datetime
from typing import Any, Dict

import redis
import structlog
from sqlalchemy.orm import Session

from reflector.database import get_db_sync
from reflector.models import Meeting, Transcript
from reflector.settings import settings
from reflector.worker.app import app

logger = structlog.get_logger(__name__)


class JitsiEventProcessor:
    """Process Jitsi events from Redis queues."""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST or "redis",
            port=settings.REDIS_PORT or 6379,
            decode_responses=True,
        )
        self.participants = {}  # room_name -> {jid: participant_info}
        self.speaker_stats = {}  # room_name -> {jid: stats}

    def process_participant_joined(self, data: Dict[str, Any], db: Session):
        """Track participant joining a room."""
        room_name = data["room_name"]
        participant = {
            "jid": data["participant_jid"],
            "nick": data["participant_nick"],
            "id": data["participant_id"],
            "is_moderator": data.get("is_moderator", False),
            "joined_at": datetime.now(),
        }

        if room_name not in self.participants:
            self.participants[room_name] = {}

        self.participants[room_name][participant["jid"]] = participant

        logger.info(
            "Participant joined",
            room=room_name,
            participant=participant["nick"],
            total_participants=len(self.participants[room_name]),
        )

        # Update meeting in database if exists
        meeting = (
            db.query(Meeting)
            .filter(
                Meeting.room_name == room_name,
                Meeting.status.in_(["active", "pending"]),
            )
            .first()
        )

        if meeting:
            # Store participant info in meeting metadata
            metadata = meeting.metadata or {}
            if "participants" not in metadata:
                metadata["participants"] = []

            metadata["participants"].append(
                {
                    "id": participant["id"],
                    "name": participant["nick"],
                    "joined_at": participant["joined_at"].isoformat(),
                    "is_moderator": participant["is_moderator"],
                }
            )

            meeting.metadata = metadata
            db.commit()

    def process_participant_left(self, data: Dict[str, Any], db: Session):
        """Track participant leaving a room."""
        room_name = data["room_name"]
        participant_jid = data["participant_jid"]

        if room_name in self.participants:
            if participant_jid in self.participants[room_name]:
                participant = self.participants[room_name][participant_jid]
                participant["left_at"] = datetime.now()

                logger.info(
                    "Participant left",
                    room=room_name,
                    participant=participant["nick"],
                    duration=(
                        participant["left_at"] - participant["joined_at"]
                    ).total_seconds(),
                )

                # Update meeting in database
                meeting = (
                    db.query(Meeting)
                    .filter(
                        Meeting.room_name == room_name,
                        Meeting.status.in_(["active", "pending"]),
                    )
                    .first()
                )

                if meeting and meeting.metadata and "participants" in meeting.metadata:
                    for p in meeting.metadata["participants"]:
                        if p["id"] == participant["id"]:
                            p["left_at"] = participant["left_at"].isoformat()
                            break
                    db.commit()

    def process_speaker_stats(self, data: Dict[str, Any], db: Session):
        """Update speaker statistics."""
        room_name = data["room_jid"].split("@")[0]
        self.speaker_stats[room_name] = data["stats"]

        logger.debug(
            "Speaker stats updated", room=room_name, speakers=len(data["stats"])
        )

    def process_recording_completed(self, data: Dict[str, Any], db: Session):
        """Process completed recording with all metadata."""
        room_name = data["room_name"]
        meeting_url = data["meeting_url"]
        recording_path = data["recording_path"]
        recording_file = data["recording_file"]

        logger.info(
            "Recording completed", room=room_name, url=meeting_url, path=recording_path
        )

        # Get participant data for this room
        participants = self.participants.get(room_name, {})
        speaker_stats = self.speaker_stats.get(room_name, {})

        # Create transcript record with full metadata
        transcript = Transcript(
            title=f"Recording: {room_name}",
            source_url=meeting_url,
            metadata={
                "jitsi": {
                    "room_name": room_name,
                    "meeting_url": meeting_url,
                    "recording_path": recording_path,
                    "participants": [
                        {
                            "id": p["id"],
                            "name": p["nick"],
                            "joined_at": p["joined_at"].isoformat(),
                            "left_at": p.get("left_at", datetime.now()).isoformat(),
                            "is_moderator": p["is_moderator"],
                            "speaking_time": speaker_stats.get(p["jid"], {}).get(
                                "total_time", 0
                            ),
                        }
                        for p in participants.values()
                    ],
                    "speaker_stats": speaker_stats,
                }
            },
            status="pending",
        )
        db.add(transcript)
        db.commit()

        # Trigger processing pipeline
        from reflector.pipelines.main_transcript_pipeline import TranscriptMainPipeline

        pipeline = TranscriptMainPipeline()
        pipeline.create(transcript.id, recording_file)

        # Clean up room data
        self.participants.pop(room_name, None)
        self.speaker_stats.pop(room_name, None)

        logger.info(
            "Transcript created",
            transcript_id=transcript.id,
            participants=len(participants),
            has_speaker_stats=bool(speaker_stats),
        )


processor = JitsiEventProcessor()


@app.task(name="reflector.worker.jitsi_events.process_jitsi_events")
def process_jitsi_events():
    """
    Process Jitsi events from Redis queue.
    This should be called periodically by Celery Beat.
    """
    db = next(get_db_sync())
    processed = 0

    try:
        # Process up to 100 events per run
        for _ in range(100):
            # Pop event from queue (blocking with 1 second timeout)
            event_data = processor.redis_client.brpop(
                ["jitsi:events:queue", "jitsi:recordings:queue"], timeout=1
            )

            if not event_data:
                break

            queue_name, event_json = event_data
            event = json.loads(event_json)

            event_type = event["type"]
            data = event["data"]

            logger.debug(f"Processing event: {event_type}")

            # Route to appropriate processor
            if event_type == "participant_joined":
                processor.process_participant_joined(data, db)
            elif event_type == "participant_left":
                processor.process_participant_left(data, db)
            elif event_type == "speaker_stats_update":
                processor.process_speaker_stats(data, db)
            elif event_type == "recording_completed":
                processor.process_recording_completed(data, db)
            else:
                logger.warning(f"Unknown event type: {event_type}")

            processed += 1

        if processed > 0:
            logger.info(f"Processed {processed} Jitsi events")

    except Exception as e:
        logger.error(f"Error processing Jitsi events: {e}")
        raise
    finally:
        db.close()

    return processed


@app.task(name="reflector.worker.jitsi_events.consume_jitsi_stream")
def consume_jitsi_stream():
    """
    Alternative: Use Redis Streams for more reliable event processing.
    Redis Streams provide better guarantees and consumer groups.
    """
    db = next(get_db_sync())

    try:
        # Read from stream with consumer group
        events = processor.redis_client.xreadgroup(
            "reflector-consumers",
            "worker-1",
            {"jitsi:events": ">"},
            count=10,
            block=1000,
        )

        for stream_name, messages in events:
            for message_id, data in messages:
                event = json.loads(data[b"event"])
                # Process event...

                # Acknowledge message
                processor.redis_client.xack(
                    stream_name, "reflector-consumers", message_id
                )

    except Exception as e:
        logger.error(f"Error consuming stream: {e}")
        raise
    finally:
        db.close()
