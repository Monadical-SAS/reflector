# Task 2: WebVTT Context Generation

**File:** `server/reflector/views/transcripts_chat.py` (modify)
**Lines:** ~15
**Dependencies:** Task 1

## Objective
Generate WebVTT transcript context on connection.

## Implementation
```python
from reflector.utils.transcript_formats import topics_to_webvtt_named
from reflector.views.transcripts import _get_is_multitrack

# Add after websocket.accept():
# Get WebVTT context
is_multitrack = await _get_is_multitrack(transcript)
webvtt = topics_to_webvtt_named(
    transcript.topics,
    transcript.participants,
    is_multitrack
)

# Truncate if needed
webvtt_truncated = webvtt[:15000] if len(webvtt) > 15000 else webvtt

# Send to client for verification
await websocket.send_json({
    "type": "context",
    "webvtt": webvtt_truncated,
    "truncated": len(webvtt) > 15000
})
```

## Validation
- [ ] WebVTT generated on connection
- [ ] Truncated to 15k chars if needed
- [ ] Client receives context message
- [ ] Format matches WebVTT spec (timestamps, speaker names)

## Notes
- Log if truncation occurs
- Keep echo functionality for testing
