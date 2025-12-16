# Hatchet Migration - LLM Debugging Observations

This document captures hard-won debugging insights from implementing the multitrack diarization pipeline with Hatchet. These observations are particularly relevant for LLM assistants working on this codebase.

## Architecture Context

- **Hatchet SDK v1.21+** uses async workers with gRPC for task polling
- Workers connect to Hatchet server via gRPC (port 7077) and trigger workflows via REST (port 8888)
- `hatchet-lite` image bundles server, engine, and database in one container
- Tasks are decorated with `@workflow.task()` (not `@hatchet.step()` as in older examples)
- Workflow input is validated via Pydantic models with `input_validator=` parameter

---

## Challenge 1: SDK Version API Breaking Changes

### Symptoms
```
AttributeError: 'V1WorkflowRunDetails' object has no attribute 'workflow_run_id'
```

### Root Cause
Hatchet SDK v1.21+ changed the response structure for workflow creation. Old examples show:
```python
result = await client.runs.aio_create(workflow_name, input_data)
return result.workflow_run_id  # OLD - doesn't work
```

### Resolution
Access the run ID through the new nested structure:
```python
result = await client.runs.aio_create(workflow_name, input_data)
return result.run.metadata.id  # NEW - SDK v1.21+
```

### Key Insight
**Don't trust documentation or examples.** Read the SDK source code or use IDE autocomplete to discover actual attribute names. The SDK evolves faster than docs.

---

## Challenge 2: Worker Appears Hung at "starting runner..."

### Symptoms
```
[INFO] Starting Hatchet workers
[INFO] Starting Hatchet worker polling...
[INFO] STARTING HATCHET...
[INFO] starting runner...
# ... nothing else, appears stuck
```

### Root Cause
Without debug mode, Hatchet SDK doesn't log:
- Workflow registration
- gRPC connection status
- Heartbeat activity
- Action listener acquisition

The worker IS working, you just can't see it.

### Resolution
Always enable debug mode during development:
```bash
HATCHET_DEBUG=true
```

With debug enabled, you'll see the actual activity:
```
[DEBUG] 'worker-name' waiting for ['workflow:task1', 'workflow:task2']
[DEBUG] starting action listener: worker-name
[DEBUG] acquired action listener: 562d00a8-8895-42a1-b65b-46f905c902f9
[DEBUG] sending heartbeat
```

### Key Insight
**Start every Hatchet debugging session with `HATCHET_DEBUG=true`.** Silent workers waste hours of debugging time.

---

## Challenge 3: Docker Networking + JWT Token URL Conflicts

### Symptoms
```
grpc._channel._InactiveRpcError: <_InactiveRpcError of RPC that terminated with:
    status = StatusCode.UNAVAILABLE
    details = "failed to connect to all addresses"
```

### Root Cause
The Hatchet API token embeds URLs:
```json
{
  "aud": "http://localhost:8889",
  "grpc_broadcast_address": "localhost:7077",
  "server_url": "http://localhost:8889"
}
```

Inside Docker containers, `localhost` refers to the container itself, not the Hatchet server.

### Resolution
Override the token-embedded URLs with environment variables:
```bash
# In .env or docker-compose environment
HATCHET_CLIENT_HOST_PORT=hatchet:7077
HATCHET_CLIENT_SERVER_URL=http://hatchet:8888
HATCHET_CLIENT_TLS_STRATEGY=none
```

### Key Insight
**The JWT token is not the final word on connection settings.** Environment variables override token-embedded URLs, which is essential for Docker networking.

---

## Challenge 4: Workflow Name Case Sensitivity

### Symptoms
```
BadRequestException: (400)
HTTP response body: errors=[APIError(description='workflow names not found: diarizationpipeline')]
```

### Root Cause
Hatchet uses the exact workflow name you define for triggering:
```python
diarization_pipeline = hatchet.workflow(
    name="DiarizationPipeline",  # Use THIS exact name to trigger
    input_validator=PipelineInput
)
```

Internally, task identifiers are lowercased (`diarizationpipeline:get_recording`), but workflow triggers must match the defined name.

### Resolution
```python
# Correct
await client.start_workflow('DiarizationPipeline', input_data)

# Wrong
await client.start_workflow('diarizationpipeline', input_data)
```

### Key Insight
**Workflow names are case-sensitive for triggering, but task refs are lowercase.** Don't conflate the two.

---

## Challenge 5: Pydantic Response Object Iteration

### Symptoms
```
AttributeError: 'tuple' object has no attribute 'participant_id'
```

### Root Cause
When API responses return Pydantic models with list fields:
```python
class MeetingParticipantsResponse(BaseModel):
    data: List[MeetingParticipant]
```

Iterating the response object directly is wrong:
```python
for p in participants:  # WRONG - iterates over model fields as tuples
```

### Resolution
Access the `.data` attribute explicitly:
```python
for p in participants.data:  # CORRECT - iterates over list items
    print(p.participant_id)
```

### Key Insight
**Pydantic models with list fields require explicit `.data` access.** The model itself is not iterable in the expected way.

---

## Challenge 6: Database Connections in Async Workers

### Symptoms
```
InterfaceError: cannot perform operation: another operation is in progress
```

### Root Cause
Similar to Conductor, Hatchet workers may inherit stale database connections. Each task runs in an async context that may not share the same event loop as cached connections.

### Resolution
Create fresh database connections per task:
```python
async def _get_fresh_db_connection():
    """Create fresh database connection for worker task."""
    import databases
    from reflector.db import _database_context
    from reflector.settings import settings

    _database_context.set(None)
    db = databases.Database(settings.DATABASE_URL)
    _database_context.set(db)
    await db.connect()
    return db

async def _close_db_connection(db):
    await db.disconnect()
    _database_context.set(None)
```

### Key Insight
**Cached singletons (DB, HTTP clients) are unsafe in workflow workers.** Always create fresh connections.

---

## Challenge 7: Child Workflow Fan-out Pattern

### Symptoms
Child workflows spawn but parent doesn't wait for completion, or results aren't collected.

### Root Cause
Hatchet child workflows need explicit spawning and result collection:
```python
# Spawning children
child_runs = await asyncio.gather(*[
    child_workflow.aio_run(child_input)
    for child_input in inputs
])

# Results are returned directly from aio_run()
```

### Resolution
Use `aio_run()` for child workflows and `asyncio.gather()` for parallelism:
```python
@parent_workflow.task(parents=[setup_task])
async def process_tracks(input: ParentInput, ctx: Context) -> dict:
    child_coroutines = [
        track_workflow.aio_run(TrackInput(track_index=i, ...))
        for i in range(len(input.tracks))
    ]

    results = await asyncio.gather(*child_coroutines, return_exceptions=True)

    # Handle failures
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Track {i} failed: {result}")

    return {"track_results": [r for r in results if not isinstance(r, Exception)]}
```

### Key Insight
**Child workflows in Hatchet return results directly.** No need to poll for completion like in Conductor.

---

## Challenge 8: Workflow Replay and Code Updates

### Symptoms
After fixing a bug in workflow code, clicking "Replay Event" in Hatchet UI still shows the old error/behavior.

### Root Cause
Hatchet replay creates a **new workflow instance** with the latest registered workflow version. However, the worker must be restarted to register the new code version. Without restart, the worker is still running the old Python module in memory.

From [Hatchet docs](https://github.com/hatchet-dev/hatchet/blob/059a4e562cd7feb5cc5728c14b04974decd72400/frontend/v0-docs/pages/home/features/retries/manual.mdx):
> "To retry a failed step, simply click on the step in the run details view and then click the 'Replay Event' button. This will create a new instance of the workflow, starting from the failed step, and using the same input data as the original run."

### Resolution
**Required steps to see code changes in replayed workflows:**

1. **Edit the code** - make your changes to workflow files
2. **Restart the worker** - registers new workflow version:
   ```bash
   docker compose restart hatchet-worker
   ```
3. **Replay in Hatchet UI** - click "Replay Event" on failed step
4. **Verify new code runs** - check logs for your changes

**For CLI-based reprocessing:**
```bash
# Default: replays existing workflow with latest code (after worker restart)
docker compose exec server uv run -m reflector.tools.process_transcript <transcript_id>

# Force: cancels old workflow and starts fresh
docker compose exec server uv run -m reflector.tools.process_transcript <transcript_id> --force
```

### Key Insight
**Replay uses updated code, but ONLY after worker restart.** Python module caching means the worker process must be restarted to pick up code changes. Simply rebuilding the container is not enough if the worker process is still running old bytecode.

---

## Debugging Workflow

### 1. Enable Debug Mode First
```bash
HATCHET_DEBUG=true
```

### 2. Verify Worker Registration
Look for this in debug logs:
```
[DEBUG] 'worker-name' waiting for ['workflow:task1', 'workflow:task2', ...]
[DEBUG] acquired action listener: {uuid}
```

### 3. Test Workflow Trigger Separately
```python
docker exec server uv run python -c "
from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.workflows.diarization_pipeline import PipelineInput
import asyncio

async def test():
    input_data = PipelineInput(
        transcript_id='test',
        recording_id=None,
        room_name='test-room',
        bucket_name='bucket',
        tracks=[],
    )
    run_id = await HatchetClientManager.start_workflow(
        'DiarizationPipeline',
        input_data.model_dump()
    )
    print(f'Triggered: {run_id}')

asyncio.run(test())
"
```

### 4. Check Hatchet Server Logs
```bash
docker logs reflector-hatchet-1 --tail 50
```

Look for `WRN` entries indicating API errors or connection issues.

### 5. Verify gRPC Connectivity
```python
docker exec worker python -c "
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('hatchet', 7077))
print(f'gRPC port 7077: {\"reachable\" if result == 0 else \"blocked\"}')"
```

### 6. Force Container Rebuild
Volume mounts may cache old bytecode:
```bash
docker compose up -d --build --force-recreate hatchet-worker
```

---

## Common Gotchas Summary

| Issue | Signal | Fix |
|-------|--------|-----|
| SDK API changed | `AttributeError` on result | Check SDK source for actual attributes |
| Worker appears stuck | Only "starting runner..." | Enable `HATCHET_DEBUG=true` |
| Can't connect from Docker | gRPC unavailable | Set `HATCHET_CLIENT_HOST_PORT` and `_SERVER_URL` |
| Workflow not found | 400 Bad Request | Use exact case-sensitive workflow name |
| Tuple iteration error | `'tuple' has no attribute` | Access `.data` on Pydantic response models |
| DB conflicts | "another operation in progress" | Fresh DB connection per task |
| Old code running | Fixed code but same error | Restart worker: `docker compose restart hatchet-worker` |
| Replay shows old behavior | Code changed but replay unchanged | Restart worker, then replay in UI |

---

## Files Most Likely to Need Hatchet-Specific Handling

- `server/reflector/hatchet/workflows/*.py` - Workflow and task definitions
- `server/reflector/hatchet/client.py` - Client wrapper, SDK version compatibility
- `server/reflector/hatchet/run_workers.py` - Worker startup and registration
- `server/reflector/hatchet/progress.py` - Progress emission for UI updates
- `docker-compose.yml` - Hatchet infrastructure services
