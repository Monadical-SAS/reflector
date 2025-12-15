# Conductor OSS Migration - LLM Debugging Observations

This document captures hard-won debugging insights from migrating the multitrack diarization pipeline from Celery to Conductor OSS. These observations are particularly relevant for LLM assistants working on this codebase.

## Architecture Context

- **Conductor Python SDK** uses multiprocessing: 1 parent process spawns 15 `TaskRunner` subprocesses
- Each task type gets its own subprocess that polls Conductor server
- Workers are identified by container hostname (e.g., `595f5ddc9711`)
- Shadow mode (`CONDUCTOR_SHADOW_MODE=true`) runs both Celery and Conductor in parallel

---

## Challenge 1: Ghost Workers - Multiple Containers Polling Same Tasks

### Symptoms
- Tasks complete but with wrong/empty output
- Worker logs show no execution for a task that API shows as COMPLETED
- `workerId` in Conductor API doesn't match expected container

### Root Cause
Multiple containers may be running Conductor workers:
- `reflector-conductor-worker-1` (dedicated worker)
- `reflector-server-1` (if shadow mode enabled or worker code imported)

### Debugging Steps
```bash
# 1. Get the mystery worker ID from Conductor API
curl -s "http://localhost:8180/api/workflow/{id}" | jq '.tasks[] | {ref: .referenceTaskName, workerId}'

# 2. Find which container has that hostname
docker ps -a | grep {workerId}
# or
docker ps -a --format "{{.ID}} {{.Names}}" | grep {first-12-chars}

# 3. Check that container's code version
docker exec {container} cat /app/reflector/conductor/workers/{worker}.py | head -50
```

### Resolution
Restart ALL containers that might be polling Conductor tasks:
```bash
docker compose restart conductor-worker server
```

### Key Insight
**Always verify `workerId` matches your expected container.** In distributed worker setups, know ALL containers that poll for tasks.

---

## Challenge 2: Multiprocessing + AsyncIO + Database Conflicts

### Symptoms
```
InterfaceError: cannot perform operation: another operation is in progress
RuntimeError: Task <Task pending...> running at /app/.../worker.py
```

### Root Cause
Conductor Python SDK forks subprocesses. When subprocess calls `asyncio.run()`:
1. New event loop is created
2. But `get_database()` returns cached connection from parent process context
3. Parent's connection is incompatible with child's event loop

### Resolution
Reset context and create fresh connection in each subprocess:
```python
async def _process():
    import databases
    from reflector.db import _database_context
    from reflector.settings import settings

    # Reset context var - don't inherit from parent
    _database_context.set(None)
    db = databases.Database(settings.DATABASE_URL)
    _database_context.set(db)
    await db.connect()

    # ... rest of async code
```

### Key Insight
**Any singleton/cached resource (DB connections, S3 clients, HTTP sessions) must be recreated AFTER fork.** Never trust inherited state in multiprocessing workers.

### TODO: The Real Problem with get_database()

**Current solution is a hack.** The issue runs deeper than multiprocessing fork:

#### What's Actually Happening
1. Each Conductor subprocess calls `asyncio.run(_process())` repeatedly for each task
2. First `asyncio.run()`: creates DB connection, stores in ContextVar
3. First task completes, `asyncio.run()` exits, **event loop destroyed**
4. **But**: ContextVar still holds the connection reference (ContextVars persist across `asyncio.run()` calls)
5. Second `asyncio.run()`: Creates a **new event loop**
6. Code tries to use the **old connection** (from ContextVar) with the **new event loop**
7. Error: "another operation is in progress"

**Root issue**: `get_database()` as a global singleton is incompatible with repeated `asyncio.run()` calls in the same process.

#### Option 1: Explicit Connection Lifecycle (cleanest)
```python
async def _process():
    import databases
    from reflector.settings import settings

    # Don't use get_database() - create explicit connection
    db = databases.Database(settings.DATABASE_URL)

    try:
        await db.connect()

        # Problem: transcripts_controller.get_by_id() uses get_database() internally
        # Would need to refactor controllers to accept db parameter
        # e.g., await transcripts_controller.get_by_id(transcript_id, db=db)

    finally:
        await db.disconnect()
```

**Pros**: Clean separation, explicit lifecycle
**Cons**: Requires refactoring all controller methods to accept `db` parameter

#### Option 2: Reset ContextVar Properly (pragmatic)
```python
async def _process():
    from reflector.db import _database_context, get_database

    # Ensure fresh connection per task
    old_db = _database_context.get()
    if old_db and old_db.is_connected:
        await old_db.disconnect()
    _database_context.set(None)

    # Now get_database() will create fresh connection
    db = get_database()
    await db.connect()

    try:
        # ... work ...
    finally:
        await db.disconnect()
        _database_context.set(None)
```

**Pros**: Works with existing controller code
**Cons**: Still manipulating globals, cleanup needed in every worker

#### Option 3: Fix get_database() Itself (best long-term)
```python
# In reflector/db/__init__.py
def get_database() -> databases.Database:
    """Get database instance for current event loop"""
    import asyncio

    db = _database_context.get()

    # Check if connection is valid for current event loop
    if db is not None:
        try:
            loop = asyncio.get_running_loop()
            # If connection's event loop differs, it's stale
            if db._connection and hasattr(db._connection, '_loop'):
                if db._connection._loop != loop:
                    # Stale connection from old event loop
                    db = None
        except RuntimeError:
            # No running loop
            pass

    if db is None:
        db = databases.Database(settings.DATABASE_URL)
        _database_context.set(db)

    return db
```

**Pros**: Fixes root cause, no changes needed in workers
**Cons**: Relies on implementation details of `databases` library

#### Recommendation
- **Short-term**: Option 2 (explicit cleanup in workers that need DB)
- **Long-term**: Option 1 (refactor to dependency injection) is the only architecturally clean solution

---

## Challenge 3: Type Mismatches Across Serialization Boundary

### Symptoms
```
ValidationError: 1 validation error for TranscriptTopic
transcript
  Input should be a valid string [type=string_type, input_value={'translation': None, 'words': [...]}]
```

### Root Cause
Conductor JSON-serializes all task inputs/outputs. Complex Pydantic models get serialized to dicts:
- `TitleSummary.transcript: Transcript` becomes `{"translation": null, "words": [...]}`
- Next task expects `TranscriptTopic.transcript: str`

### Resolution
Explicitly reconstruct types when deserializing:
```python
from reflector.processors.types import TitleSummary, Transcript as TranscriptType, Word

def normalize_topic(t):
    topic = dict(t)
    transcript_data = topic.get("transcript")
    if isinstance(transcript_data, dict):
        words_list = transcript_data.get("words", [])
        word_objects = [Word(**w) for w in words_list]
        topic["transcript"] = TranscriptType(
            words=word_objects,
            translation=transcript_data.get("translation")
        )
    return topic

topic_objects = [TitleSummary(**normalize_topic(t)) for t in topics]
```

### Key Insight
**Conductor task I/O is always JSON.** Design workers to handle dict inputs and reconstruct domain objects explicitly.

---

## Challenge 4: Conductor Health Check Failures

### Symptoms
```
dependency failed to start: container reflector-conductor-1 is unhealthy
```

### Root Cause
Conductor OSS standalone container health endpoint can be slow/flaky, especially during startup or under load.

### Resolution
Bypass docker-compose health check dependency:
```bash
# Instead of: docker compose up -d conductor-worker
docker start reflector-conductor-worker-1
```

### Key Insight
For development, consider removing `depends_on.condition: service_healthy` or increasing health check timeout.

---

## Challenge 5: JOIN Task Output Format

### Symptoms
`merge_transcripts` receives data but outputs `word_count: 0`

### Root Cause
FORK_JOIN_DYNAMIC's JOIN task outputs a **dict keyed by task reference names**, not an array:
```json
{
  "transcribe_track_0": {"words": [...], "track_index": 0},
  "transcribe_track_1": {"words": [...], "track_index": 1}
}
```

### Resolution
Handle both dict and array inputs:
```python
transcripts = task.input_data.get("transcripts", [])

# Handle JOIN output (dict with task refs as keys)
if isinstance(transcripts, dict):
    transcripts = list(transcripts.values())

for t in transcripts:
    if isinstance(t, dict) and "words" in t:
        all_words.extend(t["words"])
```

### Key Insight
**JOIN task output structure differs from FORK input.** Always log input types during debugging.

---

## Debugging Workflow

### 1. Add DEBUG Prints with Flush
Multiprocessing buffers stdout. Force immediate output:
```python
import sys
print("[DEBUG] worker entered", flush=True)
sys.stdout.flush()
```

### 2. Test Worker Functions Directly
Bypass Conductor entirely to verify logic:
```bash
docker compose exec conductor-worker uv run python -c "
from reflector.conductor.workers.merge_transcripts import merge_transcripts
from conductor.client.http.models import Task

mock_task = Task()
mock_task.input_data = {'transcripts': {...}, 'transcript_id': 'test'}
result = merge_transcripts(mock_task)
print(result.output_data)
"
```

### 3. Check Task Timing
Suspiciously fast completion (e.g., 10ms) indicates:
- Cached result from previous run
- Wrong worker processed it
- Task completed without actual execution

```bash
curl -s "http://localhost:8180/api/workflow/{id}" | \
  jq '.tasks[] | {ref: .referenceTaskName, duration: (.endTime - .startTime)}'
```

### 4. Verify Container Code Version
```bash
docker compose exec conductor-worker cat /app/reflector/conductor/workers/{file}.py | head -50
```

### 5. Use Conductor Retry API
Retry from specific failed task without re-running entire workflow:
```bash
curl -X POST "http://localhost:8180/api/workflow/{id}/retry"
```

---

## Common Gotchas Summary

| Issue | Signal | Fix |
|-------|--------|-----|
| Wrong worker | `workerId` mismatch | Restart all worker containers |
| DB conflict | "another operation in progress" | Fresh DB connection per subprocess |
| Type mismatch | Pydantic validation error | Reconstruct objects from dicts |
| No logs | Task completes but no output | Check if different container processed |
| 0 results | JOIN output format | Convert dict.values() to list |
| Health check | Compose dependency fails | Use `docker start` directly |

---

## Files Most Likely to Need Conductor-Specific Handling

- `server/reflector/conductor/workers/*.py` - All workers need multiprocessing-safe patterns
- `server/reflector/db/__init__.py` - Database singleton, needs context reset
- `server/reflector/conductor/workflows/*.json` - Workflow definitions, check input/output mappings
