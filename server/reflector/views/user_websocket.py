from typing import Optional

from fastapi import APIRouter, WebSocket

from reflector.auth.auth_jwt import JWTAuth  # type: ignore
from reflector.ws_manager import get_ws_manager

router = APIRouter()


@router.websocket("/events")
async def user_events_websocket(websocket: WebSocket):
    # Optional token via query param (browser WS can't send auth headers)
    token = websocket.query_params.get("token")
    user_id: Optional[str] = None
    if token:
        try:
            payload = JWTAuth().verify_token(token)
            user_id = payload.get("sub")
        except Exception:
            user_id = None

    # Subscribe to user-specific room if available
    room_id = f"user:{user_id}" if user_id else None
    ws_manager = get_ws_manager()

    # Only accept here if we are NOT using the shared manager (which accepts itself)
    if not room_id:
        await websocket.accept()
    else:
        await ws_manager.add_user_to_room(room_id, websocket)

    try:
        while True:
            await websocket.receive()
    finally:
        if room_id:
            await ws_manager.remove_user_from_room(room_id, websocket)
