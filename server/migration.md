# Celery to TaskIQ Migration Guide

## Executive Summary

This document outlines the migration path from Celery to TaskIQ for the Reflector project. TaskIQ is a modern, async-first distributed task queue that provides similar functionality to Celery while being designed specifically for async Python applications.

## Current Celery Usage Analysis

### Key Patterns in Use
1. **Task Decorators**: `@shared_task`, `@asynctask`, `@with_session` decorators
2. **Task Invocation**: `.delay()`, `.si()` for signatures
3. **Workflow Patterns**: `chain()`, `group()`, `chord()` for complex pipelines
4. **Scheduled Tasks**: Celery Beat with crontab and periodic schedules
5. **Session Management**: Custom `@with_session` and `@with_session_and_transcript` decorators
6. **Retry Logic**: Auto-retry with exponential backoff
7. **Redis Backend**: Using Redis for broker and result backend

### Critical Files to Migrate
- `reflector/worker/app.py` - Celery app configuration and beat schedule
- `reflector/worker/session_decorator.py` - Session management decorators
- `reflector/pipelines/main_file_pipeline.py` - File processing pipeline
- `reflector/pipelines/main_live_pipeline.py` - Live streaming pipeline (10 tasks)
- `reflector/worker/process.py` - Background processing tasks
- `reflector/worker/ics_sync.py` - Calendar sync tasks
- `reflector/worker/cleanup.py` - Cleanup tasks
- `reflector/worker/webhook.py` - Webhook notifications

## TaskIQ Architecture Mapping

### 1. Installation

```bash
# Remove Celery dependencies
uv remove celery flower

# Install TaskIQ with Redis support
uv add taskiq taskiq-redis taskiq-pipelines
```

### 2. Broker Configuration

#### Current (Celery)
```python
# reflector/worker/app.py
from celery import Celery

app = Celery(
    "reflector",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[...],
)
```

#### New (TaskIQ)
```python
# reflector/worker/broker.py
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker
from taskiq import PipelineMiddleware, SimpleRetryMiddleware

result_backend = RedisAsyncResultBackend(
    redis_url=settings.REDIS_URL,
    result_ex_time=86400,  # 24 hours
)

broker = RedisStreamBroker(
    url=settings.REDIS_URL,
    max_connection_pool_size=10,
).with_result_backend(result_backend).with_middlewares(
    PipelineMiddleware(),  # For chain/group/chord support
    SimpleRetryMiddleware(default_retry_count=3),
)

# For testing environment
if os.environ.get("ENVIRONMENT") == "pytest":
    from taskiq import InMemoryBroker
    broker = InMemoryBroker(await_inplace=True)
```

### 3. Task Definition Migration

#### Current (Celery)
```python
@shared_task
@asynctask
@with_session
async def task_pipeline_file_process(session: AsyncSession, transcript_id: str):
    pipeline = PipelineMainFile(transcript_id=transcript_id)
    await pipeline.process()
```

#### New (TaskIQ)
```python
from taskiq import TaskiqDepends
from reflector.worker.broker import broker
from reflector.worker.dependencies import get_db_session

@broker.task
async def task_pipeline_file_process(transcript_id: str):
    # Use get_session for proper test mocking
    async for session in get_session():
        pipeline = PipelineMainFile(transcript_id=transcript_id)
        await pipeline.process()
```

### 4. Session Management

#### Current Session Decorators (Keep Using These!)
```python
# reflector/worker/session_decorator.py
def with_session(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with get_session_context() as session:
            return await func(session, *args, **kwargs)
    return wrapper
```

#### Session Management Strategy

**⚠️ CRITICAL**: The key insight is to maintain consistent session management patterns:

1. **For Worker Tasks**: Continue using `@with_session` decorator pattern
2. **For FastAPI endpoints**: Use `get_session` dependency injection
3. **Never use `get_session_factory()` directly** in application code

```python
# APPROACH 1: Simple migration keeping decorator pattern
from reflector.worker.session_decorator import with_session

@taskiq_broker.task
@with_session
async def task_pipeline_file_process(session, *, transcript_id: str):
    # Session is provided by decorator, just like Celery version
    transcript = await transcripts_controller.get_by_id(session, transcript_id)
    pipeline = PipelineMainFile(transcript_id=transcript_id)
    await pipeline.process()

# APPROACH 2: For test compatibility without decorator
from reflector.db import get_session

@taskiq_broker.task
async def task_pipeline_file_process(transcript_id: str):
    # Use get_session which is mocked in tests
    async for session in get_session():
        transcript = await transcripts_controller.get_by_id(session, transcript_id)
        pipeline = PipelineMainFile(transcript_id=transcript_id)
        await pipeline.process()

# APPROACH 3: Future - TaskIQ dependency injection (after full migration)
from taskiq import TaskiqDepends

async def get_session_context():
    """Context manager version of get_session for consistency"""
    async for session in get_session():
        yield session

@taskiq_broker.task
async def task_pipeline_file_process(
    transcript_id: str,
    session: AsyncSession = TaskiqDepends(get_session_context)
):
    transcript = await transcripts_controller.get_by_id(session, transcript_id)
    pipeline = PipelineMainFile(transcript_id=transcript_id)
    await pipeline.process()
```

**Key Points:**
- `@with_session` decorator works with TaskIQ tasks (remove `@asynctask`, keep `@with_session`)
- For testing: `get_session()` from `reflector.db` is properly mocked
- Never call `get_session_factory()` directly - always use the abstractions

### 5. Task Invocation

#### Current (Celery)
```python
# Simple async execution
task_pipeline_file_process.delay(transcript_id=transcript.id)

# With signature for chaining
task_cleanup_consent.si(transcript_id=transcript_id)
```

#### New (TaskIQ)
```python
# Simple async execution
await task_pipeline_file_process.kiq(transcript_id=transcript.id)

# With kicker for advanced configuration
await task_cleanup_consent.kicker().with_labels(
    priority="high"
).kiq(transcript_id=transcript_id)
```

### 6. Workflow Patterns (Chain, Group, Chord)

#### Current (Celery)
```python
from celery import chain, group, chord

# Chain example
post_chain = chain(
    task_cleanup_consent.si(transcript_id=transcript_id),
    task_pipeline_post_to_zulip.si(transcript_id=transcript_id),
    task_send_webhook_if_needed.si(transcript_id=transcript_id),
)

# Chord example (parallel + callback)
chain = chord(
    group(chain_mp3_and_diarize, chain_title_preview),
    chain_final_summaries,
) | task_pipeline_post_to_zulip.si(transcript_id=transcript_id)
```

#### New (TaskIQ with Pipelines)
```python
from taskiq_pipelines import Pipeline
from taskiq import gather

# Chain example using Pipeline
post_pipeline = (
    Pipeline(broker, task_cleanup_consent)
    .call_next(task_pipeline_post_to_zulip, transcript_id=transcript_id)
    .call_next(task_send_webhook_if_needed, transcript_id=transcript_id)
)
await post_pipeline.kiq(transcript_id=transcript_id)

# Parallel execution with gather
results = await gather([
    chain_mp3_and_diarize.kiq(transcript_id),
    chain_title_preview.kiq(transcript_id),
])

# Then execute callback
await chain_final_summaries.kiq(transcript_id, results)
await task_pipeline_post_to_zulip.kiq(transcript_id)
```

### 7. Scheduled Tasks (Celery Beat → TaskIQ Scheduler)

#### Current (Celery Beat)
```python
# reflector/worker/app.py
app.conf.beat_schedule = {
    "process_messages": {
        "task": "reflector.worker.process.process_messages",
        "schedule": float(settings.SQS_POLLING_TIMEOUT_SECONDS),
    },
    "reprocess_failed_recordings": {
        "task": "reflector.worker.process.reprocess_failed_recordings",
        "schedule": crontab(hour=5, minute=0),
    },
}
```

#### New (TaskIQ Scheduler)
```python
# reflector/worker/scheduler.py
from taskiq import TaskiqScheduler
from taskiq_redis import ListRedisScheduleSource

schedule_source = ListRedisScheduleSource(settings.REDIS_URL)

# Define scheduled tasks with decorators
@broker.task(
    schedule=[
        {
            "cron": f"*/{int(settings.SQS_POLLING_TIMEOUT_SECONDS)} * * * * *"
        }
    ]
)
async def process_messages():
    # Task implementation
    pass

@broker.task(
    schedule=[{"cron": "0 5 * * *"}]  # Daily at 5 AM
)
async def reprocess_failed_recordings():
    # Task implementation
    pass

# Initialize scheduler
scheduler = TaskiqScheduler(broker, sources=[schedule_source])

# Run scheduler (separate process)
# taskiq scheduler reflector.worker.scheduler:scheduler
```

### 8. Retry Configuration

#### Current (Celery)
```python
@shared_task(
    bind=True,
    max_retries=30,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=3600,
)
async def task_send_webhook_if_needed(self, ...):
    try:
        # Task logic
    except Exception as exc:
        raise self.retry(exc=exc)
```

#### New (TaskIQ)
```python
from taskiq.middlewares import SimpleRetryMiddleware

# Global middleware configuration (1:1 with Celery defaults)
broker = broker.with_middlewares(
    SimpleRetryMiddleware(default_retry_count=3),
)

# For specific tasks with custom retry logic:
@broker.task(retry_on_error=True, max_retries=30)
async def task_send_webhook_if_needed(...):
    # Task logic - exceptions auto-retry
    pass
```

## Testing Migration

### Current Pytest Setup (Celery)
```python
# tests/conftest.py
@pytest.fixture(scope="session")
def celery_config():
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
    }

@pytest.mark.usefixtures("celery_session_app")
@pytest.mark.usefixtures("celery_session_worker")
async def test_task():
    pass
```

### New Pytest Setup (TaskIQ)
```python
# tests/conftest.py
import pytest
from taskiq import InMemoryBroker
from reflector.worker.broker import broker

@pytest.fixture(scope="function", autouse=True)
async def setup_taskiq_broker():
    """Replace broker with InMemoryBroker for testing"""
    original_broker = broker
    test_broker = InMemoryBroker(await_inplace=True)

    # Copy task registrations
    for task_name, task in original_broker._tasks.items():
        test_broker.register_task(task.original_function, task_name=task_name)

    yield test_broker
    await test_broker.shutdown()

@pytest.fixture
async def taskiq_with_db_session(db_session):
    """Setup TaskIQ with database session"""
    from reflector.worker.broker import broker
    broker.add_dependency_context({
        AsyncSession: db_session
    })
    yield
    broker.custom_dependency_context = {}

# Test example
@pytest.mark.anyio
async def test_task(taskiq_with_db_session):
    result = await task_pipeline_file_process("transcript-id")
    assert result is not None
```

## Migration Steps

### Phase 1: Setup (Week 1)
1. **Install TaskIQ packages**
   ```bash
   uv add taskiq taskiq-redis taskiq-pipelines
   ```

2. **Create new broker configuration**
   - Create `reflector/worker/broker.py` with TaskIQ broker setup
   - Create `reflector/worker/dependencies.py` for dependency injection

3. **Update settings**
   - Keep existing Redis configuration
   - Add TaskIQ-specific settings if needed

### Phase 2: Parallel Running (Week 2-3)
1. **Migrate simple tasks first**
   - Start with `cleanup.py` (1 task)
   - Move to `webhook.py` (1 task)
   - Test thoroughly in isolation

2. **Setup dual-mode operation**
   - Keep Celery tasks running
   - Add TaskIQ versions alongside
   - Use feature flags to switch between them

### Phase 3: Complex Tasks (Week 3-4)
1. **Migrate pipeline tasks**
   - Convert `main_file_pipeline.py`
   - Convert `main_live_pipeline.py` (most complex with 10 tasks)
   - Ensure chain/group/chord patterns work

2. **Migrate scheduled tasks**
   - Setup TaskIQ scheduler
   - Convert beat schedule to TaskIQ schedules
   - Test cron patterns

### Phase 4: Testing & Validation (Week 4-5)
1. **Update test suite**
   - Replace Celery fixtures with TaskIQ fixtures
   - Update all test files
   - Ensure coverage remains the same

2. **Performance testing**
   - Compare task execution times
   - Monitor Redis memory usage
   - Test under load

### Phase 5: Cutover (Week 5-6)
1. **Final migration**
   - Remove Celery dependencies
   - Update deployment scripts
   - Update documentation

2. **Monitoring**
   - Setup TaskIQ monitoring (if available)
   - Create health checks
   - Document operational procedures

## Key Differences to Note

### Advantages of TaskIQ
1. **Native async support** - No need for `@asynctask` wrapper
2. **Dependency injection** - Cleaner than decorators for session management
3. **Type hints** - Better IDE support and autocompletion
4. **Modern Python** - Designed for Python 3.7+
5. **Simpler testing** - InMemoryBroker makes testing easier

### Potential Challenges
1. **Less mature ecosystem** - Fewer third-party integrations
2. **Documentation** - Less comprehensive than Celery
3. **Monitoring tools** - No Flower equivalent (may need custom solution)
4. **Community support** - Smaller community than Celery

## Command Line Changes

### Current (Celery)
```bash
# Start worker
celery -A reflector.worker.app worker --loglevel=info

# Start beat scheduler
celery -A reflector.worker.app beat
```

### New (TaskIQ)
```bash
# Start worker
taskiq worker reflector.worker.broker:broker

# Start scheduler
taskiq scheduler reflector.worker.scheduler:scheduler

# With custom settings
taskiq worker reflector.worker.broker:broker --workers 4 --log-level INFO
```

## Rollback Plan

If issues arise during migration:

1. **Keep Celery code in version control** - Tag the last Celery version
2. **Maintain dual broker setup** - Can switch back via environment variable
3. **Database compatibility** - No schema changes required
4. **Redis compatibility** - Both use Redis, easy to switch back

## Success Criteria

1. ✅ All tasks migrated and functioning
2. ✅ Test coverage maintained at current levels
3. ✅ Performance equal or better than Celery
4. ✅ Scheduled tasks running reliably
5. ✅ Error handling and retries working correctly
6. ✅ WebSocket notifications still functioning
7. ✅ Pipeline processing maintaining same behavior

## Monitoring & Operations

### Health Checks
```python
# reflector/worker/healthcheck.py
@broker.task
async def healthcheck_ping():
    """TaskIQ health check task"""
    return {"status": "healthy", "timestamp": datetime.now()}
```

### Metrics Collection
- Task execution times
- Success/failure rates
- Queue depths
- Worker utilization

## Key Implementation Points - MUST READ

### Critical Changes Required

1. **Session Management in Tasks**
   - ✅ **VERIFIED**: Tasks MUST use `get_session()` from `reflector.db` for test compatibility
   - ❌ Do NOT use `get_session_factory()` directly in tasks - it bypasses test mocks
   - ✅ The test database session IS properly shared when using `get_session()`

2. **Task Invocation Changes**
   - Replace `.delay()` with `await .kiq()`
   - All task invocations become async/await
   - No need to commit sessions before task invocation (controllers handle this)

3. **Broker Configuration**
   - TaskIQ broker must be initialized in `worker/app.py`
   - Use `InMemoryBroker(await_inplace=True)` for testing
   - Use `RedisStreamBroker` for production

4. **Test Setup Requirements**
   - Set `os.environ["ENVIRONMENT"] = "pytest"` at top of test files
   - Add TaskIQ broker fixture to test functions
   - Keep Celery fixtures for now (dual-mode operation)

5. **Import Pattern Changes**
   ```python
   # Each file needs both imports during migration
   from reflector.pipelines.main_file_pipeline import (
       task_pipeline_file_process,        # Celery version
       task_pipeline_file_process_taskiq, # TaskIQ version
   )
   ```

6. **Decorator Changes**
   - Remove `@asynctask` - TaskIQ is async-native
   - **Keep `@with_session`** - it works with TaskIQ tasks!
   - Remove `@shared_task` from TaskIQ version
   - Keep `@shared_task` on Celery version for backward compatibility

## Verified POC Results

✅ **Database transactions work correctly** across test and TaskIQ tasks
✅ **Tasks execute immediately** in tests with `InMemoryBroker(await_inplace=True)`
✅ **Session mocking works** when using `get_session()` properly
✅ **"OK" output confirmed** - TaskIQ task executes and accesses test data

## Conclusion

The migration from Celery to TaskIQ is feasible and offers several advantages for an async-first codebase like Reflector. The key challenges will be:

1. Migrating complex pipeline patterns (chain/chord)
2. Ensuring scheduled task reliability
3. **SOLVED**: Maintaining session management patterns - use `get_session()`
4. Updating the test suite

The phased approach allows for gradual migration with minimal risk. The ability to run both systems in parallel provides a safety net during the transition period.

## Appendix: Quick Reference

| Celery | TaskIQ |
|--------|--------|
| `@shared_task` | `@broker.task` |
| `.delay()` | `.kiq()` |
| `.apply_async()` | `.kicker().kiq()` |
| `chain()` | `Pipeline()` |
| `group()` | `gather()` |
| `chord()` | `gather() + callback` |
| `@task.retry()` | `retry_on_error=True` |
| Celery Beat | TaskIQ Scheduler |
| `celery worker` | `taskiq worker` |
| Flower | Custom monitoring needed |