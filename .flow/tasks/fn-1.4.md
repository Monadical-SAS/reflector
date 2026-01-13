# fn-1.4 Register WebSocket route

## Description
TBD

## Acceptance
- [ ] TBD

## Done summary
- Registered transcripts_chat_router in FastAPI app (server/reflector/app.py:94)
- WebSocket route `/v1/transcripts/{id}/chat` now available
- Imports transcripts_chat router module (line 21)
- Routes registered with /v1 prefix for API versioning

This completes the backend WebSocket route registration. The endpoint is now accessible at `ws://localhost:1250/v1/transcripts/{transcript_id}/chat` and integrates with existing auth infrastructure.
## Evidence
- Commits: b461ebb488cdff46c585207adb894baf50ac36b0
- Tests:
- PRs: