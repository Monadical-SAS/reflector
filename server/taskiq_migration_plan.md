# TaskIQ Migration Implementation Plan

## Phase 1: Core Infrastructure Setup

### 1.1 Create TaskIQ Broker Configuration
- [ ] Create `reflector/worker/taskiq_broker.py` with broker setup
- [ ] Configure Redis broker with proper connection pooling
- [ ] Add retry middleware for 1:1 parity with Celery
- [ ] Setup test/production environment detection

### 1.2 Session Management Utilities
- [ ] Create `get_session_context()` function in `reflector/db.py`
- [ ] Ensure `@with_session` decorator works with TaskIQ
- [ ] Verify test mocking works with new session approach

## Phase 2: Simple Task Migration (Start Small)

### 2.1 Migrate Single Tasks First
- [ ] `reflector/worker/cleanup.py` - 1 task, simple logic
- [ ] `reflector/worker/webhook.py` - 1 task with retry logic
- [ ] Test each migrated task individually

### 2.2 Create Dual-Mode Tasks
- [ ] Keep Celery version with `@shared_task`
- [ ] Add TaskIQ version without `@asynctask`
- [ ] Use feature flag to switch between versions

## Phase 3: Complex Pipeline Migration

### 3.1 File Processing Pipeline
- [ ] Migrate `task_pipeline_file_process` completely
- [ ] Handle all sub-tasks in the pipeline
- [ ] Migrate chain/group/chord patterns to TaskIQ

### 3.2 Live Processing Pipeline
- [ ] Migrate all 10 tasks in `main_live_pipeline.py`
- [ ] Convert complex chord patterns
- [ ] Ensure WebSocket notifications still work

## Phase 4: Scheduled Tasks Migration

### 4.1 Convert Celery Beat to TaskIQ Scheduler
- [ ] Create `reflector/worker/scheduler.py`
- [ ] Migrate all scheduled tasks
- [ ] Setup TaskIQ scheduler service

## Phase 5: Testing Infrastructure

### 5.1 Update Test Fixtures
- [ ] Create TaskIQ test fixtures in `conftest.py`
- [ ] Ensure dual-mode testing (both Celery and TaskIQ)
- [ ] Verify all existing tests pass

### 5.2 Migration-Specific Tests
- [ ] Test session management across tasks
- [ ] Test retry logic parity
- [ ] Test scheduled task execution

## Phase 6: Deployment & Monitoring

### 6.1 Update Deployment Scripts
- [ ] Update Docker configurations
- [ ] Create TaskIQ worker startup scripts
- [ ] Setup health checks for TaskIQ

### 6.2 Monitoring Setup
- [ ] Create TaskIQ metrics collection
- [ ] Setup alerting for failed tasks
- [ ] Create migration rollback plan

## Execution Order

1. **Week 1**: Phase 1 + Phase 2.1
2. **Week 2**: Phase 2.2 + Phase 3.1
3. **Week 3**: Phase 3.2 + Phase 4
4. **Week 4**: Phase 5
5. **Week 5**: Phase 6 + Testing
6. **Week 6**: Cutover + Monitoring

## Success Metrics

- All tests passing with TaskIQ
- No performance degradation
- Successful parallel running for 1 week
- Zero data loss during migration
- Rollback tested and documented