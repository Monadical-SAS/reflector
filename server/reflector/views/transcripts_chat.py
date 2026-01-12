"""
Transcripts chat API
====================

WebSocket endpoint for bidirectional chat with LLM about transcript content.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from llama_index.core import Settings
from llama_index.core.base.llms.types import ChatMessage, MessageRole

import reflector.auth as auth
from reflector.db.recordings import recordings_controller
from reflector.db.transcripts import transcripts_controller
from reflector.llm import LLM
from reflector.settings import settings
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

    # Truncate if needed (15k char limit for POC)
    webvtt_truncated = webvtt[:15000] if len(webvtt) > 15000 else webvtt

    # 4. Configure LLM
    llm = LLM(settings=settings, temperature=0.7)

    # 5. System message with transcript context
    system_msg = f"""You are analyzing this meeting transcript (WebVTT):

{webvtt_truncated}

Answer questions about content, speakers, timeline. Include timestamps when relevant."""

    # 6. Conversation history
    conversation_history = [ChatMessage(role=MessageRole.SYSTEM, content=system_msg)]

    try:
        # 7. Message loop
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "get_context":
                # Return WebVTT context (for debugging/testing)
                await websocket.send_json({"type": "context", "webvtt": webvtt})
                continue

            if data.get("type") != "message":
                # Echo unknown types for backward compatibility
                await websocket.send_json({"type": "echo", "data": data})
                continue

            # Add user message to history
            user_msg = ChatMessage(role=MessageRole.USER, content=data.get("text", ""))
            conversation_history.append(user_msg)

            # Stream LLM response
            assistant_msg = ""
            async for chunk in Settings.llm.astream_chat(conversation_history):
                token = chunk.delta or ""
                if token:
                    await websocket.send_json({"type": "token", "text": token})
                    assistant_msg += token

            # Save assistant response to history
            conversation_history.append(
                ChatMessage(role=MessageRole.ASSISTANT, content=assistant_msg)
            )
            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
