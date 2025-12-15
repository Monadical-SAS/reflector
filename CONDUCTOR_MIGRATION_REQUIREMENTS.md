# Conductor Migration Requirements: Daily.co Multitrack Pipeline

## Executive Summary

Migrate the Daily.co multitrack diarization pipeline from a monolithic Celery task to a decomposed Conductor workflow, enabling visual progress tracking, granular retries, and operational observability.

---

## Business Value

### 1. Visibility: Where Are We Now? (UX, DevEx)

**Current State**: Users see only three states: `idle` → `processing` → `ended/error`. A 10-minute pipeline appears frozen with no feedback.

**Target State**: Real-time visibility into which step is executing:
- "Transcribing track 2 of 3"
- "Generating summary (step 8 of 9)"
- Visual DAG in admin UI showing completed/in-progress/pending nodes

**Business Impact**:
- Reduced support tickets ("is it stuck?")
- Engineers can instantly identify bottlenecks
- Users have confidence the system is working

### 2. Progress Tracking: What's Left? (UX, DevEx)

**Current State**: No indication of remaining work. A failure at step 8 gives same error as failure at step 1.

**Target State**:
- Progress percentage based on completed steps
- Clear step enumeration (e.g., "Step 5/9: Transcription")
- Frontend receives structured progress events with step metadata

**Business Impact**:
- Users can estimate completion time
- Frontend can render meaningful progress bars
- Error messages include context ("Failed during summary generation")

### 3. Audit Trail & Profiling (DevEx, Ops)

**Current State**: Logs scattered across Celery workers. No unified view of a single recording's journey. Resource consumption unknown per step.

**Target State**:
- Single workflow ID traces entire recording lifecycle
- Per-step execution times recorded
- Resource consumption (GPU seconds, LLM tokens) attributable to specific steps
- Conductor UI provides complete audit history

**Business Impact**:
- Debugging: "Recording X failed at step Y after Z seconds"
- Cost attribution: "Transcription costs $X, summarization costs $Y"
- Performance optimization: identify slowest steps

### 4. Clear Event Dictionary (DevEx)

**Current State**: Frontend receives WebSocket events (`TRANSCRIPT`, `TOPIC`, `FINAL_TITLE`, etc.) but mapping to pipeline phases is implicit. Adding new events requires tracing through Python code.

**Target State**:
- Each Conductor task explicitly defines its output events
- Event schema documented alongside task definition
- Frontend developers can reference task→event mapping directly

**Business Impact**:
- Faster frontend development
- Reduced miscommunication between backend/frontend teams
- Self-documenting pipeline

### 5. Restart Without Reprocessing (UX, DevEx)

**Current State**: Any failure restarts the entire pipeline. A timeout during summary generation re-runs transcription (wasting GPU costs).

**Target State**:
- Failures resume from last successful step
- Completed work is checkpointed (e.g., transcription results stored before summary)
- Manual retry triggers only failed step, not entire workflow

**Business Impact**:
- Reduced GPU/LLM costs on retries
- Faster recovery from transient failures
- Users don't wait for re-transcription on summary failures

### 6. Per-Step Timeouts (UX, DevEx)

**Current State**: Single task timeout for entire pipeline. A hung GPU call blocks everything. Killing the task loses all progress.

**Target State**:
- Each step has independent timeout (e.g., transcription: 5min, LLM: 30s)
- Timeout kills only the hung step
- Pipeline can retry just that step or fail gracefully

**Business Impact**:
- Faster detection of stuck external services
- Reduced blast radius from hung calls
- More granular SLAs per operation type

### 7. Native Retries with Backoff (DevEx, UX)

**Current State**: Celery retry logic is per-task, not per-external-call. Custom retry wrappers needed for each API call.

**Target State**:
- Conductor provides native retry policies per task
- Exponential backoff configured declaratively
- Retry state visible in UI (attempt 2/5)

**Business Impact**:
- Reduced boilerplate code
- Consistent retry behavior across all external calls
- Visibility into retry attempts for debugging

---

## Current Architecture

### Daily.co Multitrack Pipeline Flow

```
Daily webhook (recording.ready-to-download)     Polling (every 3 min)
              │                                        │
              ▼                                        ▼
         _handle_recording_ready()              poll_daily_recordings()
              │                                        │
              └──────────────┬─────────────────────────┘
                             ▼
              process_multitrack_recording.delay()     ← Celery task #1
                             │
                  ├── Daily API: GET /recordings/{id}
                  ├── Daily API: GET /meetings/{mtgSessionId}/participants
                  ├── DB: Create recording + transcript
                             │
                             ▼
              task_pipeline_multitrack_process.delay() ← Celery task #2 (MONOLITH)
                             │
                             │   ┌─────────────────────────────────────────────────┐
                             │   │  pipeline.process() - ALL PHASES INSIDE HERE   │
                             │   │                                                 │
                             │   │  Phase 2: Track Padding (N tracks, sequential) │
                             │   │  Phase 3: Mixdown → S3 upload                  │
                             │   │  Phase 4: Waveform generation                  │
                             │   │  Phase 5: Transcription (N GPU calls, serial!) │
                             │   │  Phase 6: Topic Detection (C LLM calls)        │
                             │   │  Phase 7a: Title Generation (1 LLM call)       │
                             │   │  Phase 7b: Summary Generation (2+2M LLM calls) │
                             │   │  Phase 8: Finalize status                      │
                             │   └─────────────────────────────────────────────────┘
                             │
                             ▼
              chain(cleanup → zulip → webhook).delay() ← Celery chain (3 tasks)
```

### Problem: Monolithic `pipeline.process()`

The heavy lifting happens inside a single Python function call. Celery only sees:
- Task started
- Task succeeded/failed

It cannot see or control the 8 internal phases.

---

## Target Architecture

### Decomposed Conductor Workflow

```
                        ┌─────────────────────┐
                        │   get_recording     │  ← Daily API
                        │   get_participants  │
                        └──────────┬──────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
          ┌──────────┐       ┌──────────┐       ┌──────────┐
          │ pad_tk_0 │       │ pad_tk_1 │       │ pad_tk_N │  ← FORK (parallel)
          └────┬─────┘       └────┬─────┘       └────┬─────┘
                └──────────────────┼──────────────────┘
                                   ▼
                        ┌─────────────────────┐
                        │   mixdown_tracks    │  ← PyAV → S3
                        └──────────┬──────────┘
                                   │
                        ┌──────────┴──────────┐
                        ▼                     ▼
                ┌───────────────┐     ┌───────────────┐
                │generate_wave  │     │  (continue)   │  ← waveform parallel with transcription setup
                └───────────────┘     └───────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
          ┌────────────┐    ┌────────────┐    ┌────────────┐
          │transcribe_0│    │transcribe_1│    │transcribe_N│  ← FORK (parallel GPU!)
          └─────┬──────┘    └─────┬──────┘    └─────┬──────┘
                └──────────────────┼──────────────────┘
                                   ▼
                        ┌─────────────────────┐
                        │  merge_transcripts  │
                        └──────────┬──────────┘
                                   │
                        ┌──────────┴──────────┐
                        ▼                     ▼
                ┌───────────────┐     ┌───────────────┐
                │detect_topics  │     │     (or)      │  ← topic detection
                └───────┬───────┘     └───────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
   ┌─────────────┐              ┌─────────────┐
   │generate_title│              │gen_summary │  ← FORK (parallel LLM)
   └──────┬──────┘              └──────┬──────┘
          └──────────────┬─────────────┘
                         ▼
                ┌─────────────────────┐
                │      finalize       │
                └──────────┬──────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │ consent  │──▶│  zulip   │──▶│ webhook  │  ← sequential chain
     └──────────┘   └──────────┘   └──────────┘
```

### Key Improvements

| Aspect | Current (Celery) | Target (Conductor) |
|--------|------------------|-------------------|
| Transcription parallelism | Serial (N × 30s) | Parallel (max 30s) |
| Failure granularity | Restart all | Retry failed step only |
| Progress visibility | None | Per-step status in UI |
| Timeout control | Entire pipeline | Per-step timeouts |
| Audit trail | Scattered logs | Unified workflow history |

---

## Scope of Work

### Module 1: Conductor Infrastructure Setup

**Files to Create/Modify:**
- `docker-compose.yml` - Add Conductor server container
- `server/reflector/conductor/` - New module for Conductor client
- Environment configuration for Conductor URL

**Tasks:**
- [ ] Add `conductoross/conductor-standalone:3.15.0` to docker-compose
- [ ] Create Conductor client wrapper (Python `conductor-python` SDK)
- [ ] Configure health checks and service dependencies
- [ ] Document Conductor UI access (port 8127)

### Module 2: Task Decomposition - Worker Definitions

**Files to Create:**
- `server/reflector/conductor/workers/` directory with:
  - `get_recording.py` - Daily API recording fetch
  - `get_participants.py` - Daily API participant fetch
  - `pad_track.py` - Single track padding (PyAV)
  - `mixdown_tracks.py` - Multi-track mixdown
  - `generate_waveform.py` - Waveform generation
  - `transcribe_track.py` - Single track GPU transcription
  - `merge_transcripts.py` - Combine transcriptions
  - `detect_topics.py` - LLM topic detection
  - `generate_title.py` - LLM title generation
  - `generate_summary.py` - LLM summary generation
  - `finalize.py` - Status update and cleanup
  - `cleanup_consent.py` - Consent check
  - `post_zulip.py` - Zulip notification
  - `send_webhook.py` - External webhook
  - `generate_dynamic_fork_tasks.py` - Helper for FORK_JOIN_DYNAMIC task generation

**Reference Files (Current Implementation):**
- `server/reflector/pipelines/main_multitrack_pipeline.py`
- `server/reflector/worker/process.py`
- `server/reflector/worker/webhook.py`

**Key Considerations:**
- Each worker receives input from previous step via Conductor
- Workers must be idempotent (same input → same output)
- State serialization between steps (JSON-compatible types)

### Module 3: Workflow Definition

**Files to Create:**
- `server/reflector/conductor/workflows/diarization_pipeline.json`
- `server/reflector/conductor/workflows/register.py` - Registration script

**Workflow Structure:**
```json
{
  "name": "daily_diarization_pipeline",
  "version": 1,
  "tasks": [
    {"name": "get_recording", "type": "SIMPLE"},
    {"name": "get_participants", "type": "SIMPLE"},
    {
      "name": "fork_padding",
      "type": "FORK_JOIN_DYNAMIC",
      "dynamicForkTasksParam": "track_keys"
    },
    {"name": "mixdown_tracks", "type": "SIMPLE"},
    {"name": "generate_waveform", "type": "SIMPLE"},
    {
      "name": "fork_transcription",
      "type": "FORK_JOIN_DYNAMIC",
      "dynamicForkTasksParam": "padded_urls"
    },
    {"name": "merge_transcripts", "type": "SIMPLE"},
    {"name": "detect_topics", "type": "SIMPLE"},
    {
      "name": "fork_generation",
      "type": "FORK_JOIN",
      "forkTasks": [["generate_title"], ["generate_summary"]]
    },
    {"name": "finalize", "type": "SIMPLE"},
    {"name": "cleanup_consent", "type": "SIMPLE"},
    {"name": "post_zulip", "type": "SIMPLE"},
    {"name": "send_webhook", "type": "SIMPLE"}
  ]
}
```

**Key Considerations:**
- Dynamic FORK for variable number of tracks (N)
- Timeout configuration per task type
- Retry policies with exponential backoff

### Module 4: Pipeline Trigger Migration

**Files to Modify:**
- `server/reflector/worker/process.py`

**Changes:**
- Replace `task_pipeline_multitrack_process.delay()` with Conductor workflow start
- Store workflow ID on Recording for status tracking
- Handle Conductor API errors
- Keep `process_multitrack_recording` as-is (creates DB entities before workflow)

**Note:** Both webhook AND polling entry points converge at `process_multitrack_recording`,
which then calls `task_pipeline_multitrack_process.delay()`. By modifying this single call site,
we capture both entry paths without duplicating integration logic.

### Module 5: Task Definition Registration

**Files to Create:**
- `server/reflector/conductor/tasks/definitions.py`

**Task Definitions with Timeouts:**

| Task | Timeout | Response Timeout | Retry Count |
|------|---------|------------------|-------------|
| get_recording | 60s | 30s | 3 |
| get_participants | 60s | 30s | 3 |
| pad_track | 300s | 120s | 3 |
| mixdown_tracks | 600s | 300s | 3 |
| generate_waveform | 120s | 60s | 3 |
| transcribe_track | 1800s | 900s | 3 |
| merge_transcripts | 60s | 30s | 3 |
| detect_topics | 300s | 120s | 3 |
| generate_title | 60s | 30s | 3 |
| generate_summary | 300s | 120s | 3 |
| finalize | 60s | 30s | 3 |
| cleanup_consent | 60s | 30s | 3 |
| post_zulip | 60s | 30s | 5 |
| send_webhook | 60s | 30s | 30 |
| generate_dynamic_fork_tasks | 30s | 15s | 3 |

### Module 6: Frontend Integration

**WebSocket Events (Already Defined):**

Events continue to be broadcast as today. No change to event structure.

| Event | Triggered By Task | Payload |
|-------|-------------------|---------|
| STATUS | finalize | `{value: "processing"\|"ended"\|"error"}` |
| DURATION | mixdown_tracks | `{duration: float}` |
| WAVEFORM | generate_waveform | `{waveform: float[]}` |
| TRANSCRIPT | merge_transcripts | `{text: string, translation: string\|null}` |
| TOPIC | detect_topics | `{id, title, summary, timestamp, duration}` |
| FINAL_TITLE | generate_title | `{title: string}` |
| FINAL_LONG_SUMMARY | generate_summary | `{long_summary: string}` |
| FINAL_SHORT_SUMMARY | generate_summary | `{short_summary: string}` |

**New: Progress Events**

Add new event type for granular progress:

```python
# PipelineProgressEvent
{
    "event": "PIPELINE_PROGRESS",
    "data": {
        "workflow_id": str,
        "current_step": str,
        "step_index": int,
        "total_steps": int,
        "step_status": "pending" | "in_progress" | "completed" | "failed"
    }
}
```

### Module 7: State Management & Checkpointing

**Current State Storage:**
- `transcript.status` - High-level status
- `transcript.events[]` - Append-only event log
- `transcript.topics[]` - Topic results
- `transcript.title`, `transcript.long_summary`, etc.

**Conductor State Storage:**
- Workflow execution state in Conductor database
- Per-task input/output in Conductor

**Checkpointing Strategy:**
1. Each task reads required state from DB (not previous task output for large data)
2. Each task writes results to DB before returning
3. Task output contains references (IDs, URLs) not large payloads
4. On retry, task can check DB for existing results (idempotency)

---

## Data Flow Between Tasks

### Input/Output Contracts

```
get_recording
  Input:  { recording_id: string }
  Output: { id, mtg_session_id, room_name, duration }

get_participants
  Input:  { mtg_session_id: string }
  Output: { participants: [{participant_id, user_name}] }

pad_track
  Input:  { track_index: number, s3_key: string }
  Output: { padded_url: string, size: number }

mixdown_tracks
  Input:  { padded_urls: string[] }
  Output: { audio_key: string, duration: number }

generate_waveform
  Input:  { audio_key: string }
  Output: { waveform: number[] }

transcribe_track
  Input:  { track_index: number, audio_url: string }
  Output: { words: Word[] }

merge_transcripts
  Input:  { transcripts: Word[][] }
  Output: { all_words: Word[], word_count: number }

detect_topics
  Input:  { words: Word[] }
  Output: { topics: Topic[] }

generate_title
  Input:  { topics: Topic[] }
  Output: { title: string }

generate_summary
  Input:  { words: Word[], topics: Topic[] }
  Output: { summary: string, short_summary: string }

finalize
  Input:  { recording_id, title, summary, duration }
  Output: { status: "COMPLETED" }
```

---

## External API Calls Summary

### Per-Step External Dependencies

| Task | External Service | Calls | Notes |
|------|------------------|-------|-------|
| get_recording | Daily.co API | 1 | GET /recordings/{id} |
| get_participants | Daily.co API | 1 | GET /meetings/{id}/participants |
| pad_track | S3 | 2 | presign read + PUT padded |
| mixdown_tracks | S3 | 1 | PUT audio.mp3 |
| transcribe_track | Modal.com GPU | 1 | POST /transcriptions |
| detect_topics | LLM (OpenAI) | C | C = ceil(words/300) |
| generate_title | LLM (OpenAI) | 1 | - |
| generate_summary | LLM (OpenAI) | 2+2M | M = subjects (max 6) |
| post_zulip | Zulip API | 1 | POST or PATCH |
| send_webhook | External | 1 | Customer webhook URL |

### Cost Attribution Enabled

With decomposed tasks, costs can be attributed:
- **GPU costs**: Sum of `transcribe_track` durations
- **LLM costs**: Sum of `detect_topics` + `generate_title` + `generate_summary` token usage
- **S3 costs**: Bytes uploaded by `pad_track` + `mixdown_tracks`

---

## Idempotency Requirements

### By Task

| Task | Idempotent? | Strategy |
|------|-------------|----------|
| get_recording | ✅ | Read-only API call |
| get_participants | ✅ | Read-only API call |
| pad_track | ⚠️ | Overwrite same S3 key |
| mixdown_tracks | ⚠️ | Overwrite same S3 key |
| generate_waveform | ✅ | Deterministic from audio |
| transcribe_track | ❌ | Cache by hash(audio_url) |
| detect_topics | ❌ | Cache by hash(words) |
| generate_title | ❌ | Cache by hash(topic_titles) |
| generate_summary | ❌ | Cache by hash(words+topics) |
| finalize | ✅ | Upsert status |
| cleanup_consent | ✅ | Idempotent deletes |
| post_zulip | ⚠️ | Use message_id for updates |
| send_webhook | ⚠️ | Receiver's responsibility |

### Caching Strategy for LLM/GPU Calls

```python
class TaskCache:
    async def get(self, input_hash: str) -> Optional[Output]: ...
    async def set(self, input_hash: str, output: Output) -> None: ...

# Before calling external service:
cached = await cache.get(hash(input))
if cached:
    return cached

result = await external_service.call(input)
await cache.set(hash(input), result)
return result
```

---

## Migration Strategy

### Phase 1: Infrastructure (No Behavior Change)
- Add Conductor container to docker-compose
- Create Conductor client library
- Verify Conductor UI accessible

### Phase 2: Parallel Implementation
- Implement all worker tasks
- Register workflow definition
- Test with synthetic recordings

### Phase 3: Shadow Mode
- Trigger both Celery and Conductor pipelines
- Compare results for consistency
- Monitor Conductor execution in UI

### Phase 4: Cutover
- Disable Celery pipeline trigger
- Enable Conductor-only execution
- Monitor error rates and performance

### Phase 5: Cleanup
- Remove Celery task definitions
- Remove old pipeline code
- Update documentation

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Conductor server downtime | Health checks, failover to Celery (Phase 3) |
| Worker serialization issues | Extensive testing with real data |
| Performance regression | Benchmark parallel vs serial transcription |
| Data loss on migration | Shadow mode comparison (Phase 3) |
| Learning curve for team | Documentation, Conductor UI training |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Pipeline visibility | 3 states | 14+ steps visible |
| Transcription latency (N tracks) | N × 30s | ~30s (parallel) |
| Retry granularity | Entire pipeline | Single step |
| Cost attribution | None | Per-step breakdown |
| Debug time for failures | ~30 min | ~5 min (UI trace) |

---

## Appendix: Conductor Mock Implementation

A working Python mock demonstrating the target workflow structure is available at:
`docs/conductor-pipeline-mock/`

To run:
```bash
cd docs/conductor-pipeline-mock
docker compose up --build
./test_workflow.sh
```

UI: http://localhost:8127

This mock validates:
- Workflow definition structure
- FORK_JOIN parallelism
- Worker task patterns
- Conductor SDK usage

---

## References

- Diarization Pipeline Diagram: `DIARIZATION_PIPELINE_DIAGRAM.md`
- Current Celery Implementation: `server/reflector/pipelines/main_multitrack_pipeline.py`
- Conductor OSS Documentation: https://conductor-oss.github.io/conductor/
- Conductor Python SDK: https://github.com/conductor-sdk/conductor-python
