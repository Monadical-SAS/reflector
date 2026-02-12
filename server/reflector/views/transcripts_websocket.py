"""
Transcripts websocket API
=========================

"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

import reflector.auth as auth
from reflector.db.transcripts import transcripts_controller
from reflector.ws_events import TranscriptWsEvent
from reflector.ws_manager import get_ws_manager

router = APIRouter()


@router.get(
    "/transcripts/{transcript_id}/events",
    response_model=TranscriptWsEvent,
    summary="Transcript WebSocket event schema",
    description="Stub exposing the discriminated union of all transcript-level WS events for OpenAPI type generation. Real events are delivered over the WebSocket at the same path.",
)
async def transcript_get_websocket_events(transcript_id: str):
    pass


@router.websocket("/transcripts/{transcript_id}/events")
async def transcript_events_websocket(
    transcript_id: str,
    websocket: WebSocket,
):
    _, negotiated_subprotocol = auth.parse_ws_bearer_token(websocket)
    user = await auth.current_user_ws_optional(websocket)
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # connect to websocket manager
    # use ts:transcript_id as room id
    room_id = f"ts:{transcript_id}"
    ws_manager = get_ws_manager()
    await ws_manager.add_user_to_room(
        room_id, websocket, subprotocol=negotiated_subprotocol
    )

    try:
        # on first connection, send all events only to the current user
        for event in transcript.events:
            # for now, do not send TRANSCRIPT or STATUS options - theses are live event
            # not necessary to be sent to the client; but keep the rest
            name = event.event
            if name in ("TRANSCRIPT", "STATUS"):
                continue
            await websocket.send_json(event.model_dump(mode="json"))

        # XXX if transcript is final (locked=True and status=ended)
        # XXX send a final event to the client and close the connection

        # endless loop to wait for new events
        # we do not have command system now,
        while True:
            await websocket.receive()
    except (RuntimeError, WebSocketDisconnect):
        await ws_manager.remove_user_from_room(room_id, websocket)
