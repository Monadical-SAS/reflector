from typing import Optional

from fastapi import APIRouter, WebSocket

from reflector.auth.auth_jwt import JWTAuth  # type: ignore
from reflector.db.users import user_controller
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
    if len(parts) >= 2 and parts[0].lower() == "bearer":
        negotiated_subprotocol = "bearer"
        token = parts[1]

    user_id: Optional[str] = None
    if not token:
        await websocket.close(code=UNAUTHORISED)
        return

    try:
        payload = JWTAuth().verify_token(token)
        uid = payload.get("sub")  # This is the Authentik UID

        # Look up user by Authentik UID to get internal user.id
        if uid:
            user = await user_controller.get_by_uid(uid)
            if user:
                user_id = user.id
            else:
                # User not found - they may not have been synced yet
                await websocket.close(code=UNAUTHORISED)
                return
        else:
            await websocket.close(code=UNAUTHORISED)
            return
    except Exception:
        await websocket.close(code=UNAUTHORISED)
        return

    if not user_id:
        await websocket.close(code=UNAUTHORISED)
        return

    room_id = f"user:{user_id}"
    ws_manager = get_ws_manager()

    await ws_manager.add_user_to_room(
        room_id, websocket, subprotocol=negotiated_subprotocol
    )

    try:
        while True:
            await websocket.receive()
    finally:
        if room_id:
            await ws_manager.remove_user_from_room(room_id, websocket)
