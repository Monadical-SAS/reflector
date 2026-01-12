# Task 4: Register WebSocket Route

**File:** `server/reflector/app.py` (modify)
**Lines:** ~3
**Dependencies:** Task 3

## Objective
Register chat router in FastAPI app.

## Implementation
```python
# Add import
from reflector.views.transcripts_chat import router as transcripts_chat_router

# Add to route registration section
app.include_router(transcripts_chat_router, prefix="/v1", tags=["transcripts"])
```

## Validation
- [ ] Route appears in OpenAPI docs at `/docs`
- [ ] WebSocket endpoint accessible from frontend
- [ ] No import errors
