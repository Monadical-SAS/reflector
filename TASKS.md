# Durable Workflow Migration Tasks

This document defines atomic, isolated work items for migrating the Daily.co multitrack diarization pipeline from Celery to durable workflow orchestration using **Hatchet**.

---

## Provider Selection

```bash
# .env
DURABLE_WORKFLOW_PROVIDER=none      # Celery only (default)
DURABLE_WORKFLOW_PROVIDER=hatchet   # Use Hatchet
DURABLE_WORKFLOW_SHADOW_MODE=true   # Run both Hatchet + Celery (for comparison)
```

---

## Task Index

| ID | Title | Status |
|----|-------|--------|
| INFRA-001 | Add container to docker-compose | Done |
| INFRA-002 | Create Python client wrapper | Done |
| INFRA-003 | Add environment configuration | Done |
| TASK-001 | Create workflow definition | Done |
| TASK-002 | get_recording task | Done |
| TASK-003 | get_participants task | Done |
| TASK-004 | pad_track task | Done |
| TASK-005 | mixdown_tracks task | Done |
| TASK-006 | generate_waveform task | Done |
| TASK-007 | transcribe_track task | Done |
| TASK-008 | merge_transcripts task | Done (in process_tracks) |
| TASK-009 | detect_topics task | Done |
| TASK-010 | generate_title task | Done |
| TASK-011 | generate_summary task | Done |
| TASK-012 | finalize task | Done |
| TASK-013 | cleanup_consent task | Done |
| TASK-014 | post_zulip task | Done |
| TASK-015 | send_webhook task | Done |
| EVENT-001 | Progress WebSocket events | Done |
| INTEG-001 | Pipeline trigger integration | Done |
| SHADOW-001 | Shadow mode toggle | Done |
| TEST-001 | Integration tests | Pending |
| TEST-002 | E2E workflow test | Pending |
| CUTOVER-001 | Production cutover | Pending |
| CLEANUP-001 | Remove Celery code | Pending |

---

## File Structure

```
server/reflector/hatchet/
├── client.py                    # SDK wrapper
├── progress.py                  # WebSocket progress emission
├── run_workers.py               # Worker startup
└── workflows/
    ├── diarization_pipeline.py  # Main workflow with all tasks
    └── track_processing.py      # Child workflow (pad + transcribe)
```

---

## Remaining Work

### TEST-001: Integration Tests
- [ ] Test each task with mocked external services
- [ ] Test error handling and retries

### TEST-002: E2E Workflow Test
- [ ] Complete workflow run with real Daily.co recording
- [ ] Verify output matches Celery pipeline
- [ ] Performance comparison

### CUTOVER-001: Production Cutover
- [ ] Deploy with `DURABLE_WORKFLOW_PROVIDER=hatchet`
- [ ] Monitor for failures
- [ ] Compare results with shadow mode if needed

### CLEANUP-001: Remove Celery Code
- [ ] Remove `main_multitrack_pipeline.py`
- [ ] Remove Celery task triggers
- [ ] Update documentation

---

## Known Issues

### Hatchet
- See `HATCHET_LLM_OBSERVATIONS.md` for debugging notes
- SDK v1.21+ API changes (breaking)
- JWT token Docker networking issues
- Worker appears hung without debug mode
- Workflow replay is version-locked (use --force to run latest code)

---

## Quick Start

### Hatchet
```bash
# Start infrastructure
docker compose up -d hatchet hatchet-worker

# Workers auto-register on startup
```

### Trigger Workflow
```bash
# Set provider in .env
DURABLE_WORKFLOW_PROVIDER=hatchet

# Process a Daily.co recording via webhook or API
# The pipeline trigger automatically uses the configured provider
```
