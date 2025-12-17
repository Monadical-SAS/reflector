"""WebSocket broadcasting helpers for Hatchet workflows.

DUPLICATION NOTE: To be kept when Celery is deprecated. Currently dupes Celery logic.

Provides WebSocket broadcasting for Hatchet that matches Celery's @broadcast_to_sockets
decorator behavior. Events are broadcast to transcript rooms and user rooms.
"""

from typing import Any

from reflector.db.transcripts import Transcript, TranscriptEvent, transcripts_controller
from reflector.logger import logger
from reflector.utils.string import NonEmptyString
from reflector.ws_manager import get_ws_manager

# Events that should also be sent to user room (matches Celery behavior)
USER_ROOM_EVENTS = {"STATUS", "FINAL_TITLE", "DURATION"}


async def broadcast_event(
    transcript_id: NonEmptyString, event: TranscriptEvent
) -> None:
    """Broadcast a TranscriptEvent to WebSocket subscribers.

    Fire-and-forget: errors are logged but don't interrupt workflow execution.
    """
    logger.info(
        "[Hatchet Broadcast] Broadcasting event",
        transcript_id=transcript_id,
        event_type=event.event,
    )
    try:
        ws_manager = get_ws_manager()

        await ws_manager.send_json(
            room_id=f"ts:{transcript_id}",
            message=event.model_dump(mode="json"),
        )
        logger.info(
            "[Hatchet Broadcast] Event sent to transcript room",
            transcript_id=transcript_id,
            event_type=event.event,
        )

        if event.event in USER_ROOM_EVENTS:
            transcript = await transcripts_controller.get_by_id(transcript_id)
            if transcript and transcript.user_id:
                await ws_manager.send_json(
                    room_id=f"user:{transcript.user_id}",
                    message={
                        "event": f"TRANSCRIPT_{event.event}",
                        "data": {"id": transcript_id, **event.data},
                    },
                )
    except Exception as e:
        logger.warning(
            "[Hatchet Broadcast] Failed to broadcast event",
            error=str(e),
            transcript_id=transcript_id,
            event_type=event.event,
        )


async def set_status_and_broadcast(transcript_id: NonEmptyString, status: str) -> None:
    """Set transcript status and broadcast to WebSocket.

    Wrapper around transcripts_controller.set_status that adds WebSocket broadcasting.
    """
    event = await transcripts_controller.set_status(transcript_id, status)
    if event:
        await broadcast_event(transcript_id, event)


async def append_event_and_broadcast(
    transcript_id: NonEmptyString,
    transcript: Transcript,
    event_name: str,
    data: Any,
) -> TranscriptEvent:
    """Append event to transcript and broadcast to WebSocket.

    Wrapper around transcripts_controller.append_event that adds WebSocket broadcasting.
    """
    event = await transcripts_controller.append_event(
        transcript=transcript,
        event=event_name,
        data=data,
    )
    await broadcast_event(transcript_id, event)
    return event
