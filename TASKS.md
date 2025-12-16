# Durable Workflow Migration Tasks

This document defines atomic, isolated work items for migrating the Daily.co multitrack diarization pipeline from Celery to durable workflow orchestration. Supports both **Conductor** and **Hatchet** via `DURABLE_WORKFLOW_PROVIDER` env var.

---

## Provider Selection

```bash
# .env
DURABLE_WORKFLOW_PROVIDER=none      # Celery only (default)
DURABLE_WORKFLOW_PROVIDER=conductor # Use Conductor
DURABLE_WORKFLOW_PROVIDER=hatchet   # Use Hatchet
DURABLE_WORKFLOW_SHADOW_MODE=true   # Run both provider + Celery (for comparison)
```

---

## Task Index

| ID | Title | Status | Conductor | Hatchet |
|----|-------|--------|-----------|---------|
| INFRA-001 | Add container to docker-compose | Done | ✓ | ✓ |
| INFRA-002 | Create Python client wrapper | Done | ✓ | ✓ |
| INFRA-003 | Add environment configuration | Done | ✓ | ✓ |
| TASK-001 | Create task definitions/workflow | Done | ✓ JSON | ✓ Python |
| TASK-002 | get_recording worker | Done | ✓ | ✓ |
| TASK-003 | get_participants worker | Done | ✓ | ✓ |
| TASK-004 | pad_track worker | Done | ✓ | ✓ |
| TASK-005 | mixdown_tracks worker | Done | ✓ | ✓ |
| TASK-006 | generate_waveform worker | Done | ✓ | ✓ |
| TASK-007 | transcribe_track worker | Done | ✓ | ✓ |
| TASK-008 | merge_transcripts worker | Done | ✓ | ✓ (in process_tracks) |
| TASK-009 | detect_topics worker | Done | ✓ | ✓ |
| TASK-010 | generate_title worker | Done | ✓ | ✓ |
| TASK-011 | generate_summary worker | Done | ✓ | ✓ |
| TASK-012 | finalize worker | Done | ✓ | ✓ |
| TASK-013 | cleanup_consent worker | Done | ✓ | ✓ |
| TASK-014 | post_zulip worker | Done | ✓ | ✓ |
| TASK-015 | send_webhook worker | Done | ✓ | ✓ |
| EVENT-001 | Progress WebSocket events | Done | ✓ | ✓ |
| INTEG-001 | Pipeline trigger integration | Done | ✓ | ✓ |
| SHADOW-001 | Shadow mode toggle | Done | ✓ | ✓ |
| TEST-001 | Integration tests | Pending | - | - |
| TEST-002 | E2E workflow test | Pending | - | - |
| CUTOVER-001 | Production cutover | Pending | - | - |
| CLEANUP-001 | Remove Celery code | Pending | - | - |

---

## Architecture Differences

| Aspect | Conductor | Hatchet |
|--------|-----------|---------|
| Worker model | Multiprocessing (fork) | Async (single process) |
| Task communication | REST polling | gRPC streaming |
| Workflow definition | JSON files | Python decorators |
| Child workflows | FORK_JOIN_DYNAMIC + JOIN task | `aio_run()` returns directly |
| Task definitions | Separate worker files | Embedded in workflow |
| Debug logging | Limited | Excellent with `HATCHET_DEBUG=true` |

---

## File Structure

### Conductor
```
server/reflector/conductor/
├── client.py                    # SDK wrapper
├── progress.py                  # WebSocket progress emission
├── run_workers.py               # Worker startup
├── shadow_compare.py            # Shadow mode comparison
├── tasks/
│   ├── definitions.py           # Task definitions with timeouts
│   └── register.py              # Registration script
├── workers/
│   ├── get_recording.py
│   ├── get_participants.py
│   ├── pad_track.py
│   ├── mixdown_tracks.py
│   ├── generate_waveform.py
│   ├── transcribe_track.py
│   ├── merge_transcripts.py
│   ├── detect_topics.py
│   ├── generate_title.py
│   ├── generate_summary.py
│   ├── finalize.py
│   ├── cleanup_consent.py
│   ├── post_zulip.py
│   ├── send_webhook.py
│   └── generate_dynamic_fork_tasks.py
└── workflows/
    └── register.py
```

### Hatchet
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
- [ ] Test each worker with mocked external services
- [ ] Test error handling and retries
- [ ] Test both Conductor and Hatchet paths

### TEST-002: E2E Workflow Test
- [ ] Complete workflow run with real Daily.co recording
- [ ] Verify output matches Celery pipeline
- [ ] Performance comparison

### CUTOVER-001: Production Cutover
- [ ] Deploy with `DURABLE_WORKFLOW_PROVIDER=conductor` or `hatchet`
- [ ] Monitor for failures
- [ ] Compare results with shadow mode if needed

### CLEANUP-001: Remove Celery Code
- [ ] Remove `main_multitrack_pipeline.py`
- [ ] Remove Celery task triggers
- [ ] Update documentation

---

## Known Issues

### Conductor
- See `CONDUCTOR_LLM_OBSERVATIONS.md` for debugging notes
- Ghost workers issue (multiple containers polling)
- Multiprocessing + AsyncIO conflicts

### Hatchet
- See `HATCHET_LLM_OBSERVATIONS.md` for debugging notes
- SDK v1.21+ API changes (breaking)
- JWT token Docker networking issues
- Worker appears hung without debug mode

---

## Quick Start

### Conductor
```bash
# Start infrastructure
docker compose up -d conductor conductor-worker

# Register workflow
docker compose exec conductor-worker uv run python -m reflector.conductor.workflows.register
```

### Hatchet
```bash
# Start infrastructure
docker compose up -d hatchet hatchet-worker

# Workers auto-register on startup
```

### Trigger Workflow
```bash
# Set provider in .env
DURABLE_WORKFLOW_PROVIDER=hatchet  # or conductor

# Process a Daily.co recording via webhook or API
# The pipeline trigger automatically uses the configured provider
```
