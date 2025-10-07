from typing import Optional

from fastapi import APIRouter, WebSocket

from reflector.auth.auth_jwt import JWTAuth  # type: ignore
from reflector.ws_manager import get_ws_manager

router = APIRouter()

# Close code for unauthorized WebSocket connections
UNAUTHORISED = 4401


@router.websocket("/events")
async def user_events_websocket(websocket: WebSocket):
    # Browser can't send Authorization header for WS; use subprotocol: ["bearer", token]
    raw_subprotocol = websocket.headers.get("sec-websocket-protocol") or ""
    parts = [p.strip() for p in raw_subprotocol.split(",") if p.strip()]
    token: Optional[str] = None
    negotiated_subprotocol: Optional[str] = None
    if len(parts) >= 2 and parts[0] == "bearer":
        negotiated_subprotocol = "bearer"
        token = parts[1]

    user_id: Optional[str] = None
    if token:
        try:
            payload = JWTAuth().verify_token(token)
            user_id = payload.get("sub")
        except Exception:
            await websocket.close(code=UNAUTHORISED)
            return
    else:
        # No auth provided: close with 4401 Unauthorized
        await websocket.close(code=UNAUTHORISED)
        return

    # Subscribe to user-specific room if available
    room_id = f"user:{user_id}" if user_id else None
    ws_manager = get_ws_manager()

    # Only accept here if we are NOT using the shared manager (which accepts itself)
    if not room_id:
        await websocket.close(code=UNAUTHORISED)
        return
    else:
        await ws_manager.add_user_to_room(
            room_id, websocket, subprotocol=negotiated_subprotocol
        )

    try:
        while True:
            await websocket.receive()
    finally:
        if room_id:
            await ws_manager.remove_user_from_room(room_id, websocket)
