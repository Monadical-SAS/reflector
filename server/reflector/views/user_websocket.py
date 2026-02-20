from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import reflector.auth as auth
from reflector.ws_events import UserWsEvent
from reflector.ws_manager import get_ws_manager

router = APIRouter()


@router.get(
    "/events",
    response_model=UserWsEvent,
    summary="User WebSocket event schema",
    description="Stub exposing the discriminated union of all user-level WS events for OpenAPI type generation. Real events are delivered over the WebSocket at the same path.",
)
async def user_get_websocket_events():
    pass


# Close code for unauthorized WebSocket connections
UNAUTHORISED = 4401


@router.websocket("/events")
async def user_events_websocket(websocket: WebSocket):
    token, negotiated_subprotocol = auth.parse_ws_bearer_token(websocket)

    if not token:
        await websocket.close(code=UNAUTHORISED)
        return

    try:
        user = await auth.current_user_ws_optional(websocket)
    except Exception:
        await websocket.close(code=UNAUTHORISED)
        return

    if not user:
        await websocket.close(code=UNAUTHORISED)
        return

    user_id: Optional[str] = user.sub if hasattr(user, "sub") else user["sub"]

    room_id = f"user:{user_id}"
    ws_manager = get_ws_manager()

    await ws_manager.add_user_to_room(
        room_id, websocket, subprotocol=negotiated_subprotocol
    )

    try:
        while True:
            await websocket.receive()
    except (RuntimeError, WebSocketDisconnect):
        pass
    finally:
        if room_id:
            await ws_manager.remove_user_from_room(room_id, websocket)
