# Task 3: LLM Streaming Integration

**File:** `server/reflector/views/transcripts_chat.py` (modify)
**Lines:** ~35
**Dependencies:** Task 2

## Objective
Integrate LLM streaming with conversation management.

## Implementation
```python
from llama_index.core import Settings
from reflector.llm import LLM
from reflector.settings import settings

# After WebVTT generation:
# Configure LLM
llm = LLM(settings=settings, temperature=0.7)

# System message
system_msg = f"""You are analyzing this meeting transcript (WebVTT):

{webvtt_truncated}

Answer questions about content, speakers, timeline. Include timestamps when relevant."""

# Conversation history
conversation_history = [{"role": "system", "content": system_msg}]

# Replace echo loop with:
try:
    while True:
        data = await websocket.receive_json()
        if data["type"] != "message":
            continue

        # Add user message
        user_msg = {"role": "user", "content": data["text"]}
        conversation_history.append(user_msg)

        # Stream LLM response
        assistant_msg = ""
        async for chunk in Settings.llm.astream_chat(conversation_history):
            token = chunk.delta
            await websocket.send_json({"type": "token", "text": token})
            assistant_msg += token

        # Save assistant response
        conversation_history.append({"role": "assistant", "content": assistant_msg})
        await websocket.send_json({"type": "done"})

except WebSocketDisconnect:
    pass
except Exception as e:
    await websocket.send_json({"type": "error", "message": str(e)})
```

## Validation
- [ ] LLM responds to user messages
- [ ] Tokens stream incrementally
- [ ] Conversation history maintained
- [ ] `done` message sent after completion
- [ ] Errors caught and sent to client

## Notes
- Test with: "What was discussed?"
- Verify timestamps appear in responses
