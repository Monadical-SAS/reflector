"""
Transcripts chat API
====================

WebSocket endpoint for bidirectional chat with LLM about transcript content.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

import reflector.auth as auth
from reflector.db.recordings import recordings_controller
from reflector.db.transcripts import transcripts_controller
from reflector.utils.transcript_formats import topics_to_webvtt_named

router = APIRouter()


async def _get_is_multitrack(transcript) -> bool:
    """Detect if transcript is from multitrack recording."""
    if not transcript.recording_id:
        return False
    recording = await recordings_controller.get_by_id(transcript.recording_id)
    return recording is not None and recording.is_multitrack


@router.websocket("/transcripts/{transcript_id}/chat")
async def transcript_chat_websocket(
    transcript_id: str,
    websocket: WebSocket,
    user: Optional[auth.UserInfo] = Depends(auth.current_user_optional),
):
    """WebSocket endpoint for chatting with LLM about transcript content."""
    # 1. Auth check
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # 2. Accept connection
    await websocket.accept()

    # 3. Generate WebVTT context
    is_multitrack = await _get_is_multitrack(transcript)
    webvtt = topics_to_webvtt_named(
        transcript.topics, transcript.participants, is_multitrack
    )

    try:
        # 4. Message loop
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "get_context":
                # Return WebVTT context
                await websocket.send_json({"type": "context", "webvtt": webvtt})
            else:
                # Echo for now (backward compatibility)
                await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        pass
