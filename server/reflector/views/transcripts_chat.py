"""
Transcripts chat API
====================

WebSocket endpoint for bidirectional chat with LLM about transcript content.
"""

from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from llama_index.core import Settings
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from reflector.auth.auth_jwt import JWTAuth
from reflector.db.recordings import recordings_controller
from reflector.db.transcripts import transcripts_controller
from reflector.db.users import user_controller
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
):
    """WebSocket endpoint for chatting with LLM about transcript content."""
    # 1. Auth check (optional) - extract token from WebSocket subprotocol header
    # Browser can't send Authorization header for WS; use subprotocol: ["bearer", token]
    raw_subprotocol = websocket.headers.get("sec-websocket-protocol") or ""
    parts = [p.strip() for p in raw_subprotocol.split(",") if p.strip()]
    token: Optional[str] = None
    negotiated_subprotocol: Optional[str] = None
    if len(parts) >= 2 and parts[0].lower() == "bearer":
        negotiated_subprotocol = "bearer"
        token = parts[1]

    user_id: Optional[str] = None
    if token:
        try:
            payload = JWTAuth().verify_token(token)
            authentik_uid = payload.get("sub")

            if authentik_uid:
                user = await user_controller.get_by_authentik_uid(authentik_uid)
                if user:
                    user_id = user.id
        except Exception:
            # Auth failed - continue as anonymous
            pass

    # Get transcript (respects user_id for private transcripts)
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    if not transcript:
        await websocket.close(code=1008)  # Policy violation (not found/unauthorized)
        return

    # 2. Accept connection (with negotiated subprotocol if present)
    await websocket.accept(subprotocol=negotiated_subprotocol)

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
            chat_stream = await Settings.llm.astream_chat(conversation_history)
            async for chunk in chat_stream:
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
