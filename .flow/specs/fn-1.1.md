# Task 1: WebSocket Endpoint Skeleton

**File:** `server/reflector/views/transcripts_chat.py`
**Lines:** ~30
**Dependencies:** None

## Objective
Create basic WebSocket endpoint with auth and connection handling.

## Implementation
```python
from typing import Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
import reflector.auth as auth
from reflector.db.transcripts import transcripts_controller

router = APIRouter()

@router.websocket("/transcripts/{transcript_id}/chat")
async def transcript_chat_websocket(
    transcript_id: str,
    websocket: WebSocket,
    user: Optional[auth.UserInfo] = Depends(auth.current_user_optional),
):
    # 1. Auth check
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id
    )

    # 2. Accept connection
    await websocket.accept()

    try:
        # 3. Basic message loop (stub)
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        pass
```

## Validation
- [ ] Endpoint accessible at `ws://localhost:1250/v1/transcripts/{id}/chat`
- [ ] Auth check executes (404 if transcript not found)
- [ ] Connection accepts
- [ ] Echo messages back to client
- [ ] Disconnect handled gracefully

## Notes
- Test with `websocat` or browser WebSocket client
- Don't add LLM yet, just echo
