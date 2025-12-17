"""WebSocket broadcasting helpers for Hatchet workflows.

Provides WebSocket broadcasting for Hatchet that matches Celery's @broadcast_to_sockets
decorator behavior. Events are broadcast to transcript rooms and user rooms.
"""

from reflector.db.transcripts import TranscriptEvent
from reflector.logger import logger
from reflector.ws_manager import get_ws_manager

# Events that should also be sent to user room (matches Celery behavior)
USER_ROOM_EVENTS = {"STATUS", "FINAL_TITLE", "DURATION"}


async def broadcast_event(transcript_id: str, event: TranscriptEvent) -> None:
    """Broadcast a TranscriptEvent to WebSocket subscribers.

    Fire-and-forget: errors are logged but don't interrupt workflow execution.
    """
    try:
        ws_manager = get_ws_manager()

        # Broadcast to transcript room
        await ws_manager.send_json(
            room_id=f"ts:{transcript_id}",
            message=event.model_dump(mode="json"),
        )

        # Also broadcast to user room for certain events
        if event.event in USER_ROOM_EVENTS:
            # Deferred import to avoid circular dependency
            from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

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
            event=event.event,
        )


async def set_status_and_broadcast(transcript_id: str, status: str) -> None:
    """Set transcript status and broadcast to WebSocket.

    Wrapper around transcripts_controller.set_status that adds WebSocket broadcasting.
    """
    from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

    event = await transcripts_controller.set_status(transcript_id, status)
    if event:
        await broadcast_event(transcript_id, event)


async def append_event_and_broadcast(
    transcript_id: str,
    transcript,  # Transcript model
    event_name: str,
    data,  # Pydantic model
) -> TranscriptEvent:
    """Append event to transcript and broadcast to WebSocket.

    Wrapper around transcripts_controller.append_event that adds WebSocket broadcasting.
    """
    from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

    event = await transcripts_controller.append_event(
        transcript=transcript,
        event=event_name,
        data=data,
    )
    await broadcast_event(transcript_id, event)
    return event
