"""
Transcripts websocket API
=========================

"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

import reflector.auth as auth
from reflector.db.transcripts import transcripts_controller
from reflector.ws_manager import get_ws_manager

router = APIRouter()


@router.get("/transcripts/{transcript_id}/events")
async def transcript_get_websocket_events(transcript_id: str):
    pass


@router.websocket("/transcripts/{transcript_id}/events")
async def transcript_events_websocket(
    transcript_id: str,
    websocket: WebSocket,
    user: Optional[auth.UserInfo] = Depends(auth.current_user_optional),
):
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
    await ws_manager.add_user_to_room(room_id, websocket)

    try:
        # on first connection, send all events only to the current user
        # Find the last DAG_STATUS to send after other historical events
        last_dag_status = None
        for event in transcript.events:
            name = event.event
            if name in ("TRANSCRIPT", "STATUS"):
                continue
            if name == "DAG_STATUS":
                last_dag_status = event
                continue
            await websocket.send_json(event.model_dump(mode="json"))
        # Send only the most recent DAG_STATUS so reconnecting clients get current state
        if last_dag_status is not None:
            await websocket.send_json(last_dag_status.model_dump(mode="json"))

        # XXX if transcript is final (locked=True and status=ended)
        # XXX send a final event to the client and close the connection

        # endless loop to wait for new events
        # we do not have command system now,
        while True:
            await websocket.receive()
    except (RuntimeError, WebSocketDisconnect):
        await ws_manager.remove_user_from_room(room_id, websocket)
