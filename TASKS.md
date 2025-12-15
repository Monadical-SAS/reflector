# Conductor Migration Tasks

This document defines atomic, isolated work items for migrating the Daily.co multitrack diarization pipeline from Celery to Conductor. Each task is self-contained with clear dependencies, acceptance criteria, and references to the codebase.

---

## Task Index

| ID | Title | Phase | Dependencies | Complexity |
|----|-------|-------|--------------|------------|
| INFRA-001 | Add Conductor container to docker-compose | 1 | None | Low |
| INFRA-002 | Create Conductor Python client wrapper | 1 | INFRA-001 | Medium |
| INFRA-003 | Add Conductor environment configuration | 1 | INFRA-001 | Low |
| INFRA-004 | Create health check endpoint for Conductor | 1 | INFRA-002 | Low |
| TASK-001 | Create task definitions registry module | 2 | INFRA-002 | Medium |
| TASK-002 | Implement get_recording worker | 2 | TASK-001 | Low |
| TASK-003 | Implement get_participants worker | 2 | TASK-001 | Low |
| TASK-004a | Implement pad_track: extract stream metadata | 2 | TASK-001 | Medium |
| TASK-004b | Implement pad_track: PyAV padding filter | 2 | TASK-004a | Medium |
| TASK-004c | Implement pad_track: S3 upload padded file | 2 | TASK-004b | Low |
| TASK-005a | Implement mixdown_tracks: build filter graph | 2 | TASK-001 | Medium |
| TASK-005b | Implement mixdown_tracks: S3 streaming + upload | 2 | TASK-005a | Medium |
| TASK-006 | Implement generate_waveform worker | 2 | TASK-001 | Medium |
| TASK-007 | Implement transcribe_track worker | 2 | TASK-001 | Medium |
| TASK-008 | Implement merge_transcripts worker | 2 | TASK-001 | Medium |
| TASK-009 | Implement detect_topics worker | 2 | TASK-001 | Medium |
| TASK-010 | Implement generate_title worker | 2 | TASK-001 | Low |
| TASK-011 | Implement generate_summary worker | 2 | TASK-001 | Medium |
| TASK-012 | Implement finalize worker | 2 | TASK-001 | Medium |
| TASK-013 | Implement cleanup_consent worker | 2 | TASK-001 | Low |
| TASK-014 | Implement post_zulip worker | 2 | TASK-001 | Low |
| TASK-015 | Implement send_webhook worker | 2 | TASK-001 | Low |
| TASK-016 | Implement generate_dynamic_fork_tasks helper | 2 | TASK-001 | Low |
| STATE-001 | Add workflow_id to Recording model | 2 | INFRA-002 | Low |
| WFLOW-001 | Create workflow definition JSON with FORK_JOIN_DYNAMIC | 3 | TASK-002..015 | High |
| WFLOW-002 | Implement workflow registration script | 3 | WFLOW-001 | Medium |
| EVENT-001 | Add PIPELINE_PROGRESS WebSocket event (requires frontend ticket) | 2 | None | Medium |
| EVENT-002 | Emit progress events from workers (requires frontend ticket) | 2 | EVENT-001, TASK-002..015 | Medium |
| INTEG-001 | Modify pipeline trigger to start Conductor workflow | 4 | WFLOW-002, STATE-001 | Medium |
| SHADOW-001 | Implement shadow mode toggle | 4 | INTEG-001 | Medium |
| SHADOW-002 | Add result comparison: content fields | 4 | SHADOW-001 | Medium |
| CUTOVER-001 | Create feature flag for Conductor-only mode | 5 | SHADOW-001 | Low |
| CUTOVER-002 | Add fallback to Celery on Conductor failure | 5 | CUTOVER-001 | Medium |
| CLEANUP-001 | Remove deprecated Celery task code | 6 | CUTOVER-001 | Medium |
| CLEANUP-002 | Update documentation | 6 | CLEANUP-001 | Low |
| TEST-001a | Integration tests: API workers (defer to human if complex) | 2 | TASK-002, TASK-003 | Low |
| TEST-001b | Integration tests: audio workers (defer to human if complex) | 2 | TASK-004c, TASK-005b, TASK-006 | Medium |
| TEST-001c | Integration tests: transcription workers (defer to human if complex) | 2 | TASK-007, TASK-008 | Medium |
| TEST-001d | Integration tests: LLM workers (defer to human if complex) | 2 | TASK-009..011 | Medium |
| TEST-001e | Integration tests: finalization workers (defer to human if complex) | 2 | TASK-012..015 | Low |
| TEST-002 | E2E test for complete workflow (defer to human if complex) | 3 | WFLOW-002 | High |
| TEST-003 | Shadow mode comparison tests (defer to human tester if too complex) | 4 | SHADOW-002 | Medium |

---

## Phase 1: Infrastructure Setup

### INFRA-001: Add Conductor Container to docker-compose

**Description:**
Add the Conductor OSS standalone container to the docker-compose configuration.

**Files to Modify:**
- `docker-compose.yml`

**Implementation Details:**
```yaml
conductor:
  image: conductoross/conductor-standalone:3.15.0
  ports:
    - 8127:8080
    - 5001:5000
  environment:
    - conductor.db.type=memory  # Use postgres in production
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    interval: 30s
    timeout: 10s
    retries: 5
```

**Acceptance Criteria:**
- [ ] Conductor UI accessible at http://localhost:8127
- [ ] Swagger docs available at http://localhost:8127/swagger-ui/index.html
- [ ] Health endpoint returns 200

**Dependencies:** None

**Reference Files:**
- `docs/conductor-pipeline-mock/docker-compose.yml`

---

### INFRA-002: Create Conductor Python Client Wrapper

**Description:**
Create a reusable client wrapper module for interacting with the Conductor server using the `conductor-python` SDK.

**Files to Create:**
- `server/reflector/conductor/__init__.py`
- `server/reflector/conductor/client.py`

**Implementation Details:**
```python
# server/reflector/conductor/client.py
from conductor.client.configuration.configuration import Configuration
from conductor.client.orkes_clients import OrkesClients
from conductor.client.workflow_client import WorkflowClient
from reflector.settings import settings

class ConductorClientManager:
    _instance = None

    @classmethod
    def get_client(cls) -> WorkflowClient:
        if cls._instance is None:
            config = Configuration(
                server_api_url=settings.CONDUCTOR_SERVER_URL,
                debug=settings.CONDUCTOR_DEBUG,
            )
            cls._instance = OrkesClients(config)
        return cls._instance.get_workflow_client()

    @classmethod
    def start_workflow(cls, name: str, version: int, input_data: dict) -> str:
        """Start a workflow and return the workflow ID."""
        client = cls.get_client()
        return client.start_workflow_by_name(name, input_data, version=version)

    @classmethod
    def get_workflow_status(cls, workflow_id: str) -> dict:
        """Get the current status of a workflow."""
        client = cls.get_client()
        return client.get_workflow(workflow_id, include_tasks=True)
```

**Acceptance Criteria:**
- [ ] Can connect to Conductor server
- [ ] Can start a workflow
- [ ] Can retrieve workflow status
- [ ] Proper error handling for connection failures

**Dependencies:** INFRA-001

**Reference Files:**
- `docs/conductor-pipeline-mock/src/main.py`
- `docs/conductor-pipeline-mock/src/register_workflow.py`

---

### INFRA-003: Add Conductor Environment Configuration

**Description:**
Add environment variables for Conductor configuration to the settings module.

**Files to Modify:**
- `server/reflector/settings.py`
- `server/.env_template`

**Implementation Details:**
```python
# Add to settings.py
CONDUCTOR_SERVER_URL: str = "http://conductor:8080/api"
CONDUCTOR_DEBUG: bool = False
CONDUCTOR_ENABLED: bool = False  # Feature flag
CONDUCTOR_SHADOW_MODE: bool = False  # Run both Celery and Conductor
```

**Acceptance Criteria:**
- [ ] Settings load from environment variables
- [ ] Default values work for local development
- [ ] Docker container uses internal hostname

**Dependencies:** INFRA-001

**Reference Files:**
- `server/reflector/settings.py`

---

### INFRA-004: Create Health Check Endpoint for Conductor

**Description:**
Add an endpoint to check Conductor server connectivity and status.

**Files to Create:**
- `server/reflector/views/conductor.py`

**Files to Modify:**
- `server/reflector/app.py` (register router)

**Implementation Details:**
```python
from fastapi import APIRouter
from reflector.conductor.client import ConductorClientManager

router = APIRouter(prefix="/conductor", tags=["conductor"])

@router.get("/health")
async def conductor_health():
    try:
        client = ConductorClientManager.get_client()
        # Conductor SDK health check
        return {"status": "healthy", "connected": True}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

**Acceptance Criteria:**
- [ ] Endpoint returns healthy when Conductor is up
- [ ] Endpoint returns unhealthy with error when Conductor is down
- [ ] Does not block on slow responses

**Dependencies:** INFRA-002

---

## Phase 2: Task Decomposition - Worker Definitions

### TASK-001: Create Task Definitions Registry Module

**Description:**
Create a module that registers all task definitions with the Conductor server on startup.

**Files to Create:**
- `server/reflector/conductor/tasks/__init__.py`
- `server/reflector/conductor/tasks/definitions.py`
- `server/reflector/conductor/tasks/register.py`

**Implementation Details:**

Task definition schema:
```python
TASK_DEFINITIONS = [
    {
        "name": "get_recording",
        "retryCount": 3,
        "timeoutSeconds": 60,
        "responseTimeoutSeconds": 30,
        "inputKeys": ["recording_id"],
        "outputKeys": ["id", "mtg_session_id", "room_name", "duration"],
        "ownerEmail": "reflector@example.com",
    },
    # ... all other tasks
]
```

**Acceptance Criteria:**
- [ ] All 16 task types defined with correct timeouts
- [ ] Registration script runs successfully
- [ ] Tasks visible in Conductor UI

**Dependencies:** INFRA-002

**Reference Files:**
- `docs/conductor-pipeline-mock/src/register_workflow.py` (lines 10-112)
- `CONDUCTOR_MIGRATION_REQUIREMENTS.md` (Module 5 section)

---

### TASK-002: Implement get_recording Worker

**Description:**
Create a Conductor worker that fetches recording metadata from the Daily.co API.

**Files to Create:**
- `server/reflector/conductor/workers/__init__.py`
- `server/reflector/conductor/workers/get_recording.py`

**Implementation Details:**
```python
from conductor.client.worker.worker_task import worker_task
from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from reflector.video_platforms.factory import create_platform_client

@worker_task(task_definition_name="get_recording")
async def get_recording(task: Task) -> TaskResult:
    recording_id = task.input_data.get("recording_id")

    async with create_platform_client("daily") as client:
        recording = await client.get_recording(recording_id)

    result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )
    result.status = TaskResultStatus.COMPLETED
    result.output_data = {
        "id": recording.id,
        "mtg_session_id": recording.mtgSessionId,
        "room_name": recording.roomName,
        "duration": recording.duration,
    }
    return result
```

**Input Contract:**
```json
{"recording_id": "string"}
```

**Output Contract:**
```json
{"id": "string", "mtg_session_id": "string", "room_name": "string", "duration": "number"}
```

**Acceptance Criteria:**
- [ ] Worker polls for tasks correctly
- [ ] Handles Daily.co API errors gracefully
- [ ] Returns correct output schema
- [ ] Timeout: 60s, Response timeout: 30s, Retries: 3

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/worker/process.py` (lines 218-294)
- `docs/conductor-pipeline-mock/src/workers.py` (lines 13-26)

---

### TASK-003: Implement get_participants Worker

**Description:**
Create a Conductor worker that fetches meeting participants from the Daily.co API.

**Files to Create:**
- `server/reflector/conductor/workers/get_participants.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="get_participants")
async def get_participants(task: Task) -> TaskResult:
    mtg_session_id = task.input_data.get("mtg_session_id")

    async with create_platform_client("daily") as client:
        payload = await client.get_meeting_participants(mtg_session_id)

    participants = [
        {"participant_id": p.participant_id, "user_name": p.user_name, "user_id": p.user_id}
        for p in payload.data
    ]

    result = TaskResult(...)
    result.output_data = {"participants": participants}
    return result
```

**Input Contract:**
```json
{"mtg_session_id": "string"}
```

**Output Contract:**
```json
{"participants": [{"participant_id": "string", "user_name": "string", "user_id": "string|null"}]}
```

**Acceptance Criteria:**
- [ ] Fetches participants from Daily.co API
- [ ] Maps participant IDs to names correctly
- [ ] Handles missing mtg_session_id

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 513-596)
- `docs/conductor-pipeline-mock/src/workers.py` (lines 29-42)

---

### TASK-004a: Implement pad_track - Extract Stream Metadata

**Description:**
Extract stream.start_time from WebM container metadata for timestamp alignment.

**Files to Create:**
- `server/reflector/conductor/workers/pad_track.py` (partial - metadata extraction)

**Implementation Details:**
```python
def _extract_stream_start_time_from_container(source_url: str) -> float:
    """Extract start_time from WebM stream metadata using PyAV."""
    container = av.open(source_url, options={
        "reconnect": "1",
        "reconnect_streamed": "1",
        "reconnect_delay_max": "30",
    })
    audio_stream = container.streams.audio[0]
    start_time = float(audio_stream.start_time * audio_stream.time_base)
    container.close()
    return start_time
```

**Acceptance Criteria:**
- [ ] Opens WebM container from S3 presigned URL
- [ ] Extracts start_time from audio stream metadata
- [ ] Handles missing/invalid start_time (returns 0)
- [ ] Closes container properly

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 56-85)
  - `_extract_stream_start_time_from_container()` method

---

### TASK-004b: Implement pad_track - PyAV Padding Filter

**Description:**
Apply adelay filter using PyAV filter graph to pad audio with silence.

**Files to Modify:**
- `server/reflector/conductor/workers/pad_track.py` (add filter logic)

**Implementation Details:**
```python
def _apply_audio_padding_to_file(in_container, output_path: str, start_time_seconds: float):
    """Apply adelay filter to pad audio with silence."""
    delay_ms = math.floor(start_time_seconds * 1000)

    graph = av.filter.Graph()
    src = graph.add("abuffer", args=abuf_args, name="src")
    aresample_f = graph.add("aresample", args="async=1", name="ares")
    delays_arg = f"{delay_ms}|{delay_ms}"
    adelay_f = graph.add("adelay", args=f"delays={delays_arg}:all=1", name="delay")
    sink = graph.add("abuffersink", name="sink")

    src.link_to(aresample_f)
    aresample_f.link_to(adelay_f)
    adelay_f.link_to(sink)
    graph.configure()

    # Process frames through filter graph
    # Write to output file
```

**Acceptance Criteria:**
- [ ] Constructs correct filter graph chain
- [ ] Calculates delay_ms correctly (start_time * 1000)
- [ ] Handles stereo audio (delay per channel)
- [ ] Edge case: skip if start_time <= 0

**Dependencies:** TASK-004a

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 87-188)
  - `_apply_audio_padding_to_file()` method

**Technical Notes:**
- Filter chain: `abuffer` -> `aresample` -> `adelay` -> `abuffersink`
- adelay format: `delays={ms}|{ms}:all=1`

---

### TASK-004c: Implement pad_track - S3 Upload

**Description:**
Complete the pad_track worker by uploading padded file to S3 and returning presigned URL.

**Files to Modify:**
- `server/reflector/conductor/workers/pad_track.py` (complete worker)

**Implementation Details:**
```python
@worker_task(task_definition_name="pad_track")
async def pad_track(task: Task) -> TaskResult:
    track_index = task.input_data.get("track_index")
    s3_key = task.input_data.get("s3_key")
    bucket_name = task.input_data.get("bucket_name")
    transcript_id = task.input_data.get("transcript_id")

    storage = get_transcripts_storage()
    source_url = await storage.get_file_url(s3_key, expires_in=7200, bucket=bucket_name)

    # Use helpers from 004a and 004b
    start_time = _extract_stream_start_time_from_container(source_url)
    padded_path = _apply_audio_padding_to_file(source_url, start_time)

    # Upload to S3
    storage_key = f"{transcript_id}/padded_track_{track_index}.webm"
    await storage.put_file(storage_key, padded_path)
    padded_url = await storage.get_file_url(storage_key, expires_in=7200)

    result.output_data = {"padded_url": padded_url, "size": file_size, "track_index": track_index}
    return result
```

**Input Contract:**
```json
{"track_index": "number", "s3_key": "string", "bucket_name": "string", "transcript_id": "string"}
```

**Output Contract:**
```json
{"padded_url": "string", "size": "number", "track_index": "number"}
```

**Acceptance Criteria:**
- [ ] Uploads padded file to S3
- [ ] Returns presigned URL (7200s expiry)
- [ ] Timeout: 300s, Response timeout: 120s, Retries: 3

**Dependencies:** TASK-004b

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 190-210)

---

### TASK-005a: Implement mixdown_tracks - Build Filter Graph

**Description:**
Build PyAV filter graph for mixing N audio tracks with amix filter.

**Files to Create:**
- `server/reflector/conductor/workers/mixdown_tracks.py` (partial - filter graph)

**Implementation Details:**
```python
def _build_mixdown_filter_graph(containers: list, out_stream) -> av.filter.Graph:
    """Build filter graph: N abuffer -> amix -> aformat -> sink."""
    graph = av.filter.Graph()

    # Create abuffer for each input
    abuffers = []
    for i, container in enumerate(containers):
        audio_stream = container.streams.audio[0]
        abuf_args = f"time_base={...}:sample_rate=48000:sample_fmt=fltp:channel_layout=stereo"
        abuffers.append(graph.add("abuffer", args=abuf_args, name=f"src{i}"))

    # amix with normalize=0 to prevent volume reduction
    amix = graph.add("amix", args=f"inputs={len(containers)}:normalize=0", name="amix")
    aformat = graph.add("aformat", args="sample_fmts=s16:channel_layouts=stereo", name="aformat")
    sink = graph.add("abuffersink", name="sink")

    # Link all sources to amix
    for abuf in abuffers:
        abuf.link_to(amix)
    amix.link_to(aformat)
    aformat.link_to(sink)
    graph.configure()
    return graph
```

**Acceptance Criteria:**
- [ ] Creates abuffer per input track
- [ ] Uses amix with normalize=0
- [ ] Outputs stereo s16 format
- [ ] Handles variable number of inputs (1-N tracks)

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 324-420)

**Technical Notes:**
- amix normalize=0 prevents volume reduction when mixing
- Output format: stereo, s16 for MP3 encoding

---

### TASK-005b: Implement mixdown_tracks - S3 Streaming and Upload

**Description:**
Complete mixdown worker with S3 streaming input and upload output.

**Files to Modify:**
- `server/reflector/conductor/workers/mixdown_tracks.py` (complete worker)

**Implementation Details:**
```python
@worker_task(task_definition_name="mixdown_tracks")
async def mixdown_tracks(task: Task) -> TaskResult:
    padded_urls = task.input_data.get("padded_urls", [])
    transcript_id = task.input_data.get("transcript_id")

    # Open containers with reconnect options for S3 streaming
    containers = []
    for url in padded_urls:
        containers.append(av.open(url, options={
            "reconnect": "1", "reconnect_streamed": "1", "reconnect_delay_max": "30"
        }))

    # Build filter graph and process
    graph = _build_mixdown_filter_graph(containers, ...)
    # Encode to MP3 and upload

    storage = get_transcripts_storage()
    storage_path = f"{transcript_id}/audio.mp3"
    await storage.put_file(storage_path, mp3_file)

    result.output_data = {"audio_key": storage_path, "duration": duration, "size": file_size}
    return result
```

**Input Contract:**
```json
{"padded_urls": ["string"], "transcript_id": "string"}
```

**Output Contract:**
```json
{"audio_key": "string", "duration": "number", "size": "number"}
```

**Acceptance Criteria:**
- [ ] Opens all padded tracks via presigned URLs
- [ ] Handles S3 streaming with reconnect options
- [ ] Encodes to MP3 format
- [ ] Uploads to `{transcript_id}/audio.mp3`
- [ ] Returns duration for broadcast
- [ ] Timeout: 600s, Response timeout: 300s, Retries: 3

**Dependencies:** TASK-005a

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 420-498)

---

### TASK-006: Implement generate_waveform Worker

**Description:**
Create a Conductor worker that generates waveform visualization data from the mixed audio.

**Files to Create:**
- `server/reflector/conductor/workers/generate_waveform.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="generate_waveform")
async def generate_waveform(task: Task) -> TaskResult:
    audio_key = task.input_data.get("audio_key")
    transcript_id = task.input_data.get("transcript_id")

    # Use AudioWaveformProcessor to generate peaks
    # This processor uses librosa/scipy internally

    result.output_data = {"waveform": waveform_peaks}
    return result
```

**Input Contract:**
```json
{"audio_key": "string", "transcript_id": "string"}
```

**Output Contract:**
```json
{"waveform": ["number"]}
```

**Acceptance Criteria:**
- [ ] Generates waveform peaks array
- [ ] Broadcasts WAVEFORM event to WebSocket
- [ ] Stores waveform JSON locally
- [ ] Timeout: 120s, Response timeout: 60s, Retries: 3

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 670-678)
- `server/reflector/processors/audio_waveform_processor.py`
- `docs/conductor-pipeline-mock/src/workers.py` (lines 79-92)

---

### TASK-007: Implement transcribe_track Worker

**Description:**
Create a Conductor worker that transcribes a single audio track using GPU (Modal.com) or local Whisper.

**Files to Create:**
- `server/reflector/conductor/workers/transcribe_track.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="transcribe_track")
async def transcribe_track(task: Task) -> TaskResult:
    track_index = task.input_data.get("track_index")
    audio_url = task.input_data.get("audio_url")
    language = task.input_data.get("language", "en")

    transcript = await transcribe_file_with_processor(audio_url, language)

    # Tag all words with speaker index
    for word in transcript.words:
        word.speaker = track_index

    result.output_data = {
        "words": [w.model_dump() for w in transcript.words],
        "track_index": track_index,
    }
    return result
```

**Input Contract:**
```json
{
  "track_index": "number",
  "audio_url": "string",
  "language": "string"
}
```

**Output Contract:**
```json
{
  "words": [{"word": "string", "start": "number", "end": "number", "speaker": "number"}],
  "track_index": "number"
}
```

**Acceptance Criteria:**
- [ ] Calls Modal.com GPU transcription service
- [ ] Tags words with correct speaker index
- [ ] Handles empty transcription results
- [ ] Timeout: 1800s, Response timeout: 900s, Retries: 3

**Dependencies:** TASK-001, CACHE-001

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 747-748)
- `server/reflector/pipelines/transcription_helpers.py`
- `server/reflector/processors/file_transcript_auto.py`
- `docs/conductor-pipeline-mock/src/workers.py` (lines 95-109)

**Technical Notes:**
- This is the most expensive operation (GPU time)
- Should implement caching to avoid re-transcription on retries (see CACHE-002)
- Environment variable: `TRANSCRIPT_MODAL_API_KEY`

---

### TASK-008: Implement merge_transcripts Worker

**Description:**
Create a Conductor worker that merges multiple track transcriptions into a single timeline sorted by timestamp.

**Files to Create:**
- `server/reflector/conductor/workers/merge_transcripts.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="merge_transcripts")
async def merge_transcripts(task: Task) -> TaskResult:
    transcripts = task.input_data.get("transcripts", [])
    transcript_id = task.input_data.get("transcript_id")

    all_words = []
    for t in transcripts:
        if isinstance(t, dict) and "words" in t:
            all_words.extend(t["words"])

    # Sort by start timestamp
    all_words.sort(key=lambda w: w.get("start", 0))

    # Broadcast TRANSCRIPT event
    await broadcast_transcript_event(transcript_id, all_words)

    result.output_data = {
        "all_words": all_words,
        "word_count": len(all_words),
    }
    return result
```

**Input Contract:**
```json
{
  "transcripts": [{"words": [...]}],
  "transcript_id": "string"
}
```

**Output Contract:**
```json
{"all_words": [...], "word_count": "number"}
```

**Acceptance Criteria:**
- [ ] Merges words from all tracks
- [ ] Sorts by start timestamp
- [ ] Preserves speaker attribution
- [ ] Broadcasts TRANSCRIPT event
- [ ] Updates transcript.events in DB

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 727-736)
- `docs/conductor-pipeline-mock/src/workers.py` (lines 112-131)

---

### TASK-009: Implement detect_topics Worker

**Description:**
Create a Conductor worker that detects topics using LLM calls.

**Files to Create:**
- `server/reflector/conductor/workers/detect_topics.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="detect_topics")
async def detect_topics(task: Task) -> TaskResult:
    words = task.input_data.get("words", [])
    transcript_id = task.input_data.get("transcript_id")
    target_language = task.input_data.get("target_language", "en")

    # Uses TranscriptTopicDetectorProcessor
    # Chunks words into groups of 300, calls LLM per chunk
    topics = await topic_processing.detect_topics(
        TranscriptType(words=words),
        target_language,
        on_topic_callback=lambda t: broadcast_topic_event(transcript_id, t),
        empty_pipeline=EmptyPipeline(logger),
    )

    result.output_data = {
        "topics": [t.model_dump() for t in topics]
    }
    return result
```

**Input Contract:**
```json
{
  "words": [...],
  "transcript_id": "string",
  "target_language": "string"
}
```

**Output Contract:**
```json
{"topics": [{"id": "string", "title": "string", "summary": "string", "timestamp": "number", "duration": "number"}]}
```

**Acceptance Criteria:**
- [ ] Chunks words in groups of 300
- [ ] Calls LLM for each chunk
- [ ] Broadcasts TOPIC event for each detected topic
- [ ] Returns complete topics list
- [ ] Timeout: 300s, Response timeout: 120s, Retries: 3

**Dependencies:** TASK-001, CACHE-001

**Reference Files:**
- `server/reflector/pipelines/topic_processing.py` (lines 34-63)
- `server/reflector/processors/transcript_topic_detector.py`
- `docs/conductor-pipeline-mock/src/workers.py` (lines 134-147)

**Technical Notes:**
- Number of LLM calls: `ceil(word_count / 300)`
- Uses `TranscriptTopicDetectorProcessor`

---

### TASK-010: Implement generate_title Worker

**Description:**
Create a Conductor worker that generates a meeting title from detected topics using LLM.

**Files to Create:**
- `server/reflector/conductor/workers/generate_title.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="generate_title")
async def generate_title(task: Task) -> TaskResult:
    topics = task.input_data.get("topics", [])
    transcript_id = task.input_data.get("transcript_id")

    if not topics:
        result.output_data = {"title": "Untitled Meeting"}
        return result

    # Uses TranscriptFinalTitleProcessor
    title = await topic_processing.generate_title(
        topics,
        on_title_callback=lambda t: broadcast_title_event(transcript_id, t),
        empty_pipeline=EmptyPipeline(logger),
        logger=logger,
    )

    result.output_data = {"title": title}
    return result
```

**Input Contract:**
```json
{"topics": [...], "transcript_id": "string"}
```

**Output Contract:**
```json
{"title": "string"}
```

**Acceptance Criteria:**
- [ ] Generates title from topic summaries
- [ ] Broadcasts FINAL_TITLE event
- [ ] Updates transcript.title in DB
- [ ] Handles empty topics list
- [ ] Timeout: 60s, Response timeout: 30s, Retries: 3

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/pipelines/topic_processing.py` (lines 66-84)
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 760-766)
- `docs/conductor-pipeline-mock/src/workers.py` (lines 150-163)

---

### TASK-011: Implement generate_summary Worker

**Description:**
Create a Conductor worker that generates long and short summaries from topics and words using LLM.

**Files to Create:**
- `server/reflector/conductor/workers/generate_summary.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="generate_summary")
async def generate_summary(task: Task) -> TaskResult:
    words = task.input_data.get("words", [])
    topics = task.input_data.get("topics", [])
    transcript_id = task.input_data.get("transcript_id")

    transcript = await transcripts_controller.get_by_id(transcript_id)

    # Uses TranscriptFinalSummaryProcessor
    await topic_processing.generate_summaries(
        topics, transcript,
        on_long_summary_callback=lambda s: broadcast_long_summary_event(transcript_id, s),
        on_short_summary_callback=lambda s: broadcast_short_summary_event(transcript_id, s),
        empty_pipeline=EmptyPipeline(logger),
        logger=logger,
    )

    result.output_data = {
        "summary": long_summary,
        "short_summary": short_summary,
    }
    return result
```

**Input Contract:**
```json
{
  "words": [...],
  "topics": [...],
  "transcript_id": "string"
}
```

**Output Contract:**
```json
{"summary": "string", "short_summary": "string"}
```

**Acceptance Criteria:**
- [ ] Generates long summary
- [ ] Generates short summary
- [ ] Broadcasts FINAL_LONG_SUMMARY event
- [ ] Broadcasts FINAL_SHORT_SUMMARY event
- [ ] Updates transcript.long_summary and transcript.short_summary in DB
- [ ] Timeout: 300s, Response timeout: 120s, Retries: 3

**Dependencies:** TASK-001, CACHE-001

**Reference Files:**
- `server/reflector/pipelines/topic_processing.py` (lines 86-109)
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 768-777)
- `docs/conductor-pipeline-mock/src/workers.py` (lines 166-180)

**Technical Notes:**
- LLM calls: 2 + 2*M where M = number of subjects (max 6)

---

### TASK-012: Implement finalize Worker

**Description:**
Create a Conductor worker that finalizes the transcript status and updates the database.

**Files to Create:**
- `server/reflector/conductor/workers/finalize.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="finalize")
async def finalize(task: Task) -> TaskResult:
    transcript_id = task.input_data.get("transcript_id")
    title = task.input_data.get("title")
    summary = task.input_data.get("summary")
    short_summary = task.input_data.get("short_summary")
    duration = task.input_data.get("duration")

    transcript = await transcripts_controller.get_by_id(transcript_id)
    await transcripts_controller.update(transcript, {
        "status": "ended",
        "title": title,
        "long_summary": summary,
        "short_summary": short_summary,
        "duration": duration,
    })

    # Broadcast STATUS event
    await broadcast_status_event(transcript_id, "ended")

    result.output_data = {"status": "COMPLETED"}
    return result
```

**Input Contract:**
```json
{
  "transcript_id": "string",
  "title": "string",
  "summary": "string",
  "short_summary": "string",
  "duration": "number"
}
```

**Output Contract:**
```json
{"status": "string"}
```

**Acceptance Criteria:**
- [ ] Updates transcript status to "ended"
- [ ] Persists title, summaries, duration
- [ ] Broadcasts STATUS event with "ended"
- [ ] Idempotent (can be retried safely)

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` (lines 745, 787-791)
- `docs/conductor-pipeline-mock/src/workers.py` (lines 183-196)

---

### TASK-013: Implement cleanup_consent Worker

**Description:**
Create a Conductor worker that checks participant consent and deletes audio if denied.

**Files to Create:**
- `server/reflector/conductor/workers/cleanup_consent.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="cleanup_consent")
async def cleanup_consent(task: Task) -> TaskResult:
    transcript_id = task.input_data.get("transcript_id")

    # Check if any participant denied consent
    # Delete audio from S3 if so
    # Implementation mirrors task_cleanup_consent from main_live_pipeline

    result.output_data = {
        "audio_deleted": deleted,
        "reason": reason,
    }
    return result
```

**Input Contract:**
```json
{"transcript_id": "string"}
```

**Output Contract:**
```json
{"audio_deleted": "boolean", "reason": "string|null"}
```

**Acceptance Criteria:**
- [ ] Checks all participant consent statuses
- [ ] Deletes audio from S3 if any denied
- [ ] Updates transcript.audio_deleted flag
- [ ] Idempotent deletes

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/pipelines/main_live_pipeline.py` - `task_cleanup_consent`
- `server/reflector/pipelines/main_multitrack_pipeline.py` (line 794)

---

### TASK-014: Implement post_zulip Worker

**Description:**
Create a Conductor worker that posts or updates a Zulip message with the transcript summary.

**Files to Create:**
- `server/reflector/conductor/workers/post_zulip.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="post_zulip")
async def post_zulip(task: Task) -> TaskResult:
    transcript_id = task.input_data.get("transcript_id")

    # Uses existing Zulip integration
    # Post new message or update existing using message_id

    result.output_data = {"message_id": message_id}
    return result
```

**Input Contract:**
```json
{"transcript_id": "string"}
```

**Output Contract:**
```json
{"message_id": "string|null"}
```

**Acceptance Criteria:**
- [ ] Posts to configured Zulip channel
- [ ] Updates existing message if message_id exists
- [ ] Handles Zulip API errors gracefully
- [ ] Timeout: 60s, Response timeout: 30s, Retries: 5

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/pipelines/main_live_pipeline.py` - `task_pipeline_post_to_zulip`
- `server/reflector/pipelines/main_multitrack_pipeline.py` (line 795)
- `server/reflector/zulip.py`

---

### TASK-015: Implement send_webhook Worker

**Description:**
Create a Conductor worker that sends the transcript completion webhook to the configured URL.

**Files to Create:**
- `server/reflector/conductor/workers/send_webhook.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="send_webhook")
async def send_webhook(task: Task) -> TaskResult:
    transcript_id = task.input_data.get("transcript_id")
    room_id = task.input_data.get("room_id")

    # Uses existing webhook logic from webhook.py
    # Includes HMAC signature if secret configured

    result.output_data = {
        "sent": success,
        "status_code": status_code,
    }
    return result
```

**Input Contract:**
```json
{"transcript_id": "string", "room_id": "string"}
```

**Output Contract:**
```json
{"sent": "boolean", "status_code": "number|null"}
```

**Acceptance Criteria:**
- [ ] Sends webhook with correct payload schema
- [ ] Includes HMAC signature
- [ ] Retries on 5xx, not on 4xx
- [ ] Timeout: 60s, Response timeout: 30s, Retries: 30

**Dependencies:** TASK-001

**Reference Files:**
- `server/reflector/worker/webhook.py`
- `server/reflector/pipelines/main_file_pipeline.py` - `task_send_webhook_if_needed`
- `server/reflector/pipelines/main_multitrack_pipeline.py` (line 796)

---

### TASK-016: Implement generate_dynamic_fork_tasks Helper

**Description:**
Create a helper worker that generates dynamic task definitions for FORK_JOIN_DYNAMIC. This is required because Conductor's FORK_JOIN_DYNAMIC needs pre-computed task lists and input maps.

**Files to Create:**
- `server/reflector/conductor/workers/generate_dynamic_fork_tasks.py`

**Implementation Details:**
```python
@worker_task(task_definition_name="generate_dynamic_fork_tasks")
def generate_dynamic_fork_tasks(task: Task) -> TaskResult:
    tracks = task.input_data.get("tracks", [])
    task_type = task.input_data.get("task_type")  # "pad_track" or "transcribe_track"
    transcript_id = task.input_data.get("transcript_id")

    tasks = []
    inputs = {}
    for idx, track in enumerate(tracks):
        ref_name = f"{task_type}_{idx}"
        tasks.append({
            "name": task_type,
            "taskReferenceName": ref_name,
            "type": "SIMPLE"
        })
        inputs[ref_name] = {
            "track_index": idx,
            "transcript_id": transcript_id,
            # Additional task-specific inputs based on task_type
        }

    result.output_data = {"tasks": tasks, "inputs": inputs}
    return result
```

**Input Contract:**
```json
{
  "tracks": [{"s3_key": "string"}],
  "task_type": "pad_track" | "transcribe_track",
  "transcript_id": "string",
  "bucket_name": "string"
}
```

**Output Contract:**
```json
{
  "tasks": [{"name": "string", "taskReferenceName": "string", "type": "SIMPLE"}],
  "inputs": {"ref_name": {...input_data...}}
}
```

**Acceptance Criteria:**
- [ ] Generates correct task list for variable track counts (1, 2, ... N)
- [ ] Generates correct input map with task-specific parameters
- [ ] Supports both pad_track and transcribe_track task types
- [ ] Timeout: 30s, Response timeout: 15s, Retries: 3

**Dependencies:** TASK-001

**Technical Notes:**
- This helper is required because FORK_JOIN_DYNAMIC expects `dynamicTasks` and `dynamicTasksInput` parameters
- The workflow uses this helper twice: once for padding, once for transcription
- Each invocation has different task_type and additional inputs

---

## Phase 2 (Continued): State Management

### STATE-001: Add workflow_id to Recording Model

**Description:**
Add a `workflow_id` field to the Recording model to track the Conductor workflow associated with each recording.

**Files to Modify:**
- `server/reflector/db/recordings.py`
- Create migration file

**Implementation Details:**
```python
# In Recording model
workflow_id: Optional[str] = Column(String, nullable=True, index=True)
```

**Acceptance Criteria:**
- [ ] Migration adds nullable workflow_id column
- [ ] Index created for workflow_id lookups
- [ ] Recording can be queried by workflow_id

**Dependencies:** INFRA-002

**Reference Files:**
- `CONDUCTOR_MIGRATION_REQUIREMENTS.md` (Module 7: State Management)

---

## Phase 3: Workflow Definition

### WFLOW-001: Create Workflow Definition JSON with FORK_JOIN_DYNAMIC

**Description:**
Define the complete workflow DAG in Conductor's workflow definition format, including dynamic forking for variable track counts.

**Files to Create:**
- `server/reflector/conductor/workflows/diarization_pipeline.json`

**Implementation Details:**

The workflow must include:
1. Sequential: get_recording -> get_participants
2. FORK_JOIN_DYNAMIC: pad_track for each track
3. Sequential: mixdown_tracks -> generate_waveform
4. FORK_JOIN_DYNAMIC: transcribe_track for each track (parallel!)
5. Sequential: merge_transcripts -> detect_topics
6. FORK_JOIN: generate_title || generate_summary
7. Sequential: finalize -> cleanup_consent -> post_zulip -> send_webhook

**FORK_JOIN_DYNAMIC Pattern:**
```json
{
  "name": "fork_track_padding",
  "taskReferenceName": "fork_track_padding",
  "type": "FORK_JOIN_DYNAMIC",
  "inputParameters": {
    "dynamicTasks": "${generate_padding_tasks.output.tasks}",
    "dynamicTasksInput": "${generate_padding_tasks.output.inputs}"
  },
  "dynamicForkTasksParam": "dynamicTasks",
  "dynamicForkTasksInputParamName": "dynamicTasksInput"
}
```

This requires a helper task that generates the dynamic fork structure based on track count.

**Acceptance Criteria:**
- [ ] Valid Conductor workflow schema
- [ ] All task references match registered task definitions
- [ ] Input/output parameter mappings correct
- [ ] FORK_JOIN_DYNAMIC works with 1, 2, ... N tracks
- [ ] JOIN correctly collects all parallel results
- [ ] DAG renders correctly in Conductor UI

**Dependencies:** TASK-002 through TASK-015

**Reference Files:**
- `docs/conductor-pipeline-mock/src/register_workflow.py` (lines 125-304)
- `CONDUCTOR_MIGRATION_REQUIREMENTS.md` (Module 3 section, Target Architecture diagram)

---

### WFLOW-002: Implement Workflow Registration Script

**Description:**
Create a script that registers the workflow definition with the Conductor server.

**Files to Create:**
- `server/reflector/conductor/workflows/register.py`

**Implementation Details:**
```python
import requests
from reflector.settings import settings

def register_workflow():
    with open("diarization_pipeline.json") as f:
        workflow = json.load(f)

    resp = requests.put(
        f"{settings.CONDUCTOR_SERVER_URL}/metadata/workflow",
        json=[workflow],
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
```

**Acceptance Criteria:**
- [ ] Workflow visible in Conductor UI
- [ ] Can start workflow via API
- [ ] DAG renders correctly in UI

**Dependencies:** WFLOW-001

**Reference Files:**
- `docs/conductor-pipeline-mock/src/register_workflow.py` (lines 317-327)

---

## Phase 2 (Continued): WebSocket Events

### EVENT-001: Add PIPELINE_PROGRESS WebSocket Event

**Description:**
Define a new WebSocket event type for granular pipeline progress tracking.

**⚠️ Note:** Requires separate frontend ticket to add UI consumer for this event.

**Files to Modify:**
- `server/reflector/db/transcripts.py` (add event type)
- `server/reflector/ws_manager.py` (ensure broadcast support)

**Implementation Details:**
```python
# New event schema
class PipelineProgressEvent(BaseModel):
    event: str = "PIPELINE_PROGRESS"
    data: PipelineProgressData

class PipelineProgressData(BaseModel):
    workflow_id: str
    current_step: str
    step_index: int
    total_steps: int
    step_status: Literal["pending", "in_progress", "completed", "failed"]
```

**Acceptance Criteria:**
- [ ] Event schema defined
- [ ] Works with existing WebSocket infrastructure
- [ ] Frontend ticket created for progress UI consumer

**Dependencies:** None

**Reference Files:**
- `CONDUCTOR_MIGRATION_REQUIREMENTS.md` (Module 6 section)
- `server/reflector/pipelines/main_live_pipeline.py` (broadcast_to_sockets decorator)

---

### EVENT-002: Emit Progress Events from Workers

**Description:**
Modify workers to emit PIPELINE_PROGRESS events at start and completion of each task.

**⚠️ Note:** Requires separate frontend ticket to add UI consumer (see EVENT-001).

**Files to Modify:**
- All worker files in `server/reflector/conductor/workers/`

**Implementation Details:**
```python
async def emit_progress(transcript_id: str, step: str, status: str, index: int, total: int):
    ws_manager = get_ws_manager()
    await ws_manager.send_json(
        room_id=f"ts:{transcript_id}",
        message={
            "event": "PIPELINE_PROGRESS",
            "data": {
                "current_step": step,
                "step_index": index,
                "total_steps": total,
                "step_status": status,
            }
        }
    )

@worker_task(task_definition_name="transcribe_track")
async def transcribe_track(task: Task) -> TaskResult:
    await emit_progress(transcript_id, "transcribe_track", "in_progress", 6, 14)
    # ... processing ...
    await emit_progress(transcript_id, "transcribe_track", "completed", 6, 14)
```

**Acceptance Criteria:**
- [ ] Progress emitted at task start
- [ ] Progress emitted at task completion

**Dependencies:** EVENT-001, TASK-002 through TASK-015

---

## Phase 4: Integration

### INTEG-001: Modify Pipeline Trigger to Start Conductor Workflow

**Description:**
Replace `task_pipeline_multitrack_process.delay()` with Conductor workflow start in `process_multitrack_recording`.
This single change captures BOTH webhook AND polling entry paths, since both converge at this function.

**Files to Modify:**
- `server/reflector/worker/process.py`

**Implementation Details:**
```python
# In _process_multitrack_recording_inner(), around line 289
# Replace:
#   task_pipeline_multitrack_process.delay(
#       transcript_id=transcript.id,
#       bucket_name=bucket_name,
#       track_keys=filter_cam_audio_tracks(track_keys),
#   )
# With:

if settings.CONDUCTOR_ENABLED:
    from reflector.conductor.client import ConductorClientManager
    from reflector.db.recordings import recordings_controller

    workflow_id = ConductorClientManager.start_workflow(
        name="diarization_pipeline",
        version=1,
        input_data={
            "recording_id": recording_id,
            "room_name": daily_room_name,
            "tracks": [{"s3_key": k} for k in filter_cam_audio_tracks(track_keys)],
            "bucket_name": bucket_name,
            "transcript_id": transcript.id,
            "room_id": room.id,
        }
    )
    logger.info("Started Conductor workflow", workflow_id=workflow_id, transcript_id=transcript.id)

    # Store workflow_id on recording for status tracking
    await recordings_controller.update(recording, {"workflow_id": workflow_id})

    if not settings.CONDUCTOR_SHADOW_MODE:
        return  # Don't trigger Celery

# Existing Celery trigger (runs in shadow mode or when Conductor disabled)
task_pipeline_multitrack_process.delay(
    transcript_id=transcript.id,
    bucket_name=bucket_name,
    track_keys=filter_cam_audio_tracks(track_keys),
)
```

**Acceptance Criteria:**
- [ ] Conductor workflow started from process_multitrack_recording
- [ ] Workflow ID stored on Recording model
- [ ] Both webhook and polling paths covered (single integration point)
- [ ] Celery still triggered in shadow mode

**Dependencies:** WFLOW-002, STATE-001

**Reference Files:**
- `server/reflector/worker/process.py` (lines 172-293)
- `CONDUCTOR_MIGRATION_REQUIREMENTS.md` (Module 4 section)

---

### SHADOW-001: Implement Shadow Mode Toggle

**Description:**
Add configuration and logic to run both Celery and Conductor pipelines simultaneously for comparison.

**Files to Modify:**
- `server/reflector/settings.py` (already has CONDUCTOR_SHADOW_MODE from INFRA-003)
- `server/reflector/worker/process.py` (INTEG-001 already implements shadow mode logic)

**Implementation Details:**
```python
# settings.py (already done in INFRA-003)
CONDUCTOR_SHADOW_MODE: bool = False

# worker/process.py (in _process_multitrack_recording_inner)
if settings.CONDUCTOR_ENABLED:
    workflow_id = ConductorClientManager.start_workflow(...)
    await recordings_controller.update(recording, {"workflow_id": workflow_id})

    if not settings.CONDUCTOR_SHADOW_MODE:
        return  # Conductor only - skip Celery
    # If shadow mode, fall through to Celery trigger below

# Celery trigger (runs when Conductor disabled OR in shadow mode)
task_pipeline_multitrack_process.delay(...)
```

**Acceptance Criteria:**
- [ ] Both pipelines triggered when CONDUCTOR_SHADOW_MODE=True
- [ ] Only Conductor triggered when CONDUCTOR_ENABLED=True and SHADOW_MODE=False
- [ ] Only Celery triggered when CONDUCTOR_ENABLED=False
- [ ] workflow_id stored on Recording model for comparison

**Dependencies:** INTEG-001

**Note:** INTEG-001 already implements the shadow mode toggle logic. This task verifies
the implementation and adds any missing comparison/monitoring infrastructure.

**Reference Files:**
- `CONDUCTOR_MIGRATION_REQUIREMENTS.md` (Phase 3: Shadow Mode)

---

### SHADOW-002: Add Result Comparison - Content Fields

**Description:**
Compare content fields (title, summaries, topics, word counts) between Celery and Conductor outputs.

**Files to Create:**
- `server/reflector/conductor/shadow_compare.py`

**Implementation Details:**
```python
async def compare_content_results(recording_id: str, workflow_id: str) -> dict:
    """Compare content results from Celery and Conductor pipelines."""
    celery_transcript = await transcripts_controller.get_by_recording_id(recording_id)
    workflow_status = ConductorClientManager.get_workflow_status(workflow_id)

    differences = []
    # Compare title
    if celery_transcript.title != workflow_status.output.get("title"):
        differences.append({"field": "title", ...})
    # Compare summaries, topics, word_count
    ...

    return {"match": len(differences) == 0, "differences": differences}
```

**Acceptance Criteria:**
- [ ] Compares title, long_summary, short_summary
- [ ] Compares topic count and content
- [ ] Compares word_count
- [ ] Logs differences for debugging

**Dependencies:** SHADOW-001

---

## Phase 5: Cutover

### CUTOVER-001: Create Feature Flag for Conductor-Only Mode

**Description:**
Enable Conductor-only mode by setting environment variables. No code changes required.

**Files to Modify:**
- `.env` or environment configuration

**Implementation Details:**
```bash
# .env (production)
CONDUCTOR_ENABLED=true         # Enable Conductor
CONDUCTOR_SHADOW_MODE=false    # Disable shadow mode (Conductor only)
```

The logic is already implemented in INTEG-001:
```python
# worker/process.py (_process_multitrack_recording_inner)
if settings.CONDUCTOR_ENABLED:
    workflow_id = ConductorClientManager.start_workflow(...)
    if not settings.CONDUCTOR_SHADOW_MODE:
        return  # Conductor only - Celery not triggered
# Celery only reached if Conductor disabled or shadow mode enabled
task_pipeline_multitrack_process.delay(...)
```

**Acceptance Criteria:**
- [ ] Set CONDUCTOR_ENABLED=true in production environment
- [ ] Set CONDUCTOR_SHADOW_MODE=false
- [ ] Verify Celery not triggered (check logs for "Started Conductor workflow")
- [ ] Can toggle back via environment variables without code changes

**Dependencies:** SHADOW-001

**Note:** This is primarily a configuration change. The code logic is already in place from INTEG-001.

---

### CUTOVER-002: Add Fallback to Celery on Conductor Failure

**Description:**
Implement automatic fallback to Celery pipeline if Conductor fails to start or process a workflow.

**Files to Modify:**
- `server/reflector/worker/process.py`
- `server/reflector/conductor/client.py`

**Implementation Details:**
```python
# In _process_multitrack_recording_inner()
if settings.CONDUCTOR_ENABLED:
    try:
        workflow_id = ConductorClientManager.start_workflow(
            name="diarization_pipeline",
            version=1,
            input_data={...}
        )
        logger.info("Conductor workflow started", workflow_id=workflow_id, transcript_id=transcript.id)
        await recordings_controller.update(recording, {"workflow_id": workflow_id})

        if not settings.CONDUCTOR_SHADOW_MODE:
            return  # Success - don't trigger Celery
    except Exception as e:
        logger.error(
            "Conductor workflow start failed, falling back to Celery",
            error=str(e),
            transcript_id=transcript.id,
            exc_info=True,
        )
        # Fall through to Celery trigger below

# Celery fallback (runs on Conductor failure, or when disabled, or in shadow mode)
task_pipeline_multitrack_process.delay(
    transcript_id=transcript.id,
    bucket_name=bucket_name,
    track_keys=filter_cam_audio_tracks(track_keys),
)
```

**Acceptance Criteria:**
- [ ] Celery triggered on Conductor connection failure
- [ ] Celery triggered on workflow start failure
- [ ] Errors logged with full context for debugging
- [ ] workflow_id still stored if partially successful

**Dependencies:** CUTOVER-001

---

## Phase 6: Cleanup

### CLEANUP-001: Remove Deprecated Celery Task Code

**Description:**
After successful migration, remove the old Celery-based pipeline code.

**Files to Modify:**
- `server/reflector/pipelines/main_multitrack_pipeline.py` - Remove entire file
- `server/reflector/worker/process.py` - Remove `task_pipeline_multitrack_process.delay()` call
- `server/reflector/pipelines/main_live_pipeline.py` - Remove shared utilities if unused

**Implementation Details:**
```python
# worker/process.py - Remove Celery fallback entirely
if settings.CONDUCTOR_ENABLED:
    workflow_id = ConductorClientManager.start_workflow(...)
    await recordings_controller.update(recording, {"workflow_id": workflow_id})
    return  # No Celery fallback

# Delete this:
# task_pipeline_multitrack_process.delay(...)
```

**Acceptance Criteria:**
- [ ] `main_multitrack_pipeline.py` deleted
- [ ] Celery trigger removed from `worker/process.py`
- [ ] Old task imports removed
- [ ] No new recordings processed via Celery
- [ ] Code removed after stability period (1-2 weeks)

**Dependencies:** CUTOVER-001

---

### CLEANUP-002: Update Documentation

**Description:**
Update all documentation to reflect the new Conductor-based architecture.

**Files to Modify:**
- `CLAUDE.md`
- `README.md`
- `docs/` (if applicable)

**Files to Archive:**
- `CONDUCTOR_MIGRATION_REQUIREMENTS.md` (move to docs/archive/)

**Acceptance Criteria:**
- [ ] Architecture diagrams updated
- [ ] API documentation reflects new endpoints
- [ ] Runbooks updated for Conductor operations

**Dependencies:** CLEANUP-001

---

## Testing Tasks

**⚠️ Note:** All test tasks should be deferred to human tester if automated testing proves too complex or time-consuming.

### TEST-001a: Integration Tests - API Workers

**Description:**
Write integration tests for get_recording and get_participants workers.

**Files to Create:**
- `server/tests/conductor/test_workers_api.py`

**Implementation Details:**
```python
@pytest.mark.asyncio
async def test_get_recording_worker():
    with patch("reflector.conductor.workers.get_recording.create_platform_client") as mock:
        mock.return_value.__aenter__.return_value.get_recording.return_value = MockRecording()

        task = Task(input_data={"recording_id": "rec_123"})
        result = await get_recording(task)

        assert result.status == TaskResultStatus.COMPLETED
        assert result.output_data["id"] == "rec_123"
```

**Acceptance Criteria:**
- [ ] get_recording worker tested with mock Daily.co API
- [ ] get_participants worker tested with mock response
- [ ] Error handling tested (API failures)

**Dependencies:** TASK-002, TASK-003

---

### TEST-001b: Integration Tests - Audio Processing Workers

**Description:**
Write integration tests for pad_track, mixdown_tracks, and generate_waveform workers.

**Files to Create:**
- `server/tests/conductor/test_workers_audio.py`

**Acceptance Criteria:**
- [ ] pad_track worker tested with mock S3 and sample WebM
- [ ] mixdown_tracks worker tested with mock audio streams
- [ ] generate_waveform worker tested
- [ ] PyAV filter graph execution verified

**Dependencies:** TASK-004c, TASK-005b, TASK-006

---

### TEST-001c: Integration Tests - Transcription Workers

**Description:**
Write integration tests for transcribe_track and merge_transcripts workers.

**Files to Create:**
- `server/tests/conductor/test_workers_transcription.py`

**Acceptance Criteria:**
- [ ] transcribe_track worker tested with mock Modal.com response
- [ ] merge_transcripts worker tested with multiple track inputs
- [ ] Word sorting by timestamp verified

**Dependencies:** TASK-007, TASK-008

---

### TEST-001d: Integration Tests - LLM Workers

**Description:**
Write integration tests for detect_topics, generate_title, and generate_summary workers.

**Files to Create:**
- `server/tests/conductor/test_workers_llm.py`

**Acceptance Criteria:**
- [ ] detect_topics worker tested with mock LLM response
- [ ] generate_title worker tested
- [ ] generate_summary worker tested
- [ ] WebSocket event broadcasting verified

**Dependencies:** TASK-009, TASK-010, TASK-011

---

### TEST-001e: Integration Tests - Finalization Workers

**Description:**
Write integration tests for finalize, cleanup_consent, post_zulip, and send_webhook workers.

**Files to Create:**
- `server/tests/conductor/test_workers_finalization.py`

**Acceptance Criteria:**
- [ ] finalize worker tested (DB update)
- [ ] cleanup_consent worker tested (S3 deletion)
- [ ] post_zulip worker tested with mock API
- [ ] send_webhook worker tested with HMAC verification

**Dependencies:** TASK-012, TASK-013, TASK-014, TASK-015

---

### TEST-002: E2E Test for Complete Workflow

**Description:**
Create an end-to-end test that runs the complete Conductor workflow with mock services.

**Files to Create:**
- `server/tests/conductor/test_workflow_e2e.py`

**Implementation Details:**
```python
@pytest.mark.asyncio
async def test_complete_diarization_workflow():
    # Start Conductor in test mode
    workflow_id = ConductorClientManager.start_workflow(
        "diarization_pipeline", 1,
        {"recording_id": "test_123", "tracks": [...]}
    )

    # Wait for completion
    status = await wait_for_workflow(workflow_id, timeout=60)

    assert status.status == "COMPLETED"
    assert status.output["title"] is not None
```

**Acceptance Criteria:**
- [ ] Complete workflow runs successfully
- [ ] All tasks execute in correct order
- [ ] FORK_JOIN_DYNAMIC parallelism works
- [ ] Output matches expected schema

**Dependencies:** WFLOW-002

---

### TEST-003: Shadow Mode Comparison Tests

**Description:**
Write tests that verify Celery and Conductor produce equivalent results.

**Files to Create:**
- `server/tests/conductor/test_shadow_compare.py`

**Acceptance Criteria:**
- [ ] Same input produces same output
- [ ] Timing differences documented
- [ ] Edge cases handled

**Dependencies:** SHADOW-002b

---

## Appendix: Task Timeout Reference

| Task | Timeout (s) | Response Timeout (s) | Retry Count |
|------|-------------|---------------------|-------------|
| get_recording | 60 | 30 | 3 |
| get_participants | 60 | 30 | 3 |
| pad_track | 300 | 120 | 3 |
| mixdown_tracks | 600 | 300 | 3 |
| generate_waveform | 120 | 60 | 3 |
| transcribe_track | 1800 | 900 | 3 |
| merge_transcripts | 60 | 30 | 3 |
| detect_topics | 300 | 120 | 3 |
| generate_title | 60 | 30 | 3 |
| generate_summary | 300 | 120 | 3 |
| finalize | 60 | 30 | 3 |
| cleanup_consent | 60 | 30 | 3 |
| post_zulip | 60 | 30 | 5 |
| send_webhook | 60 | 30 | 30 |

---

## Appendix: File Structure After Migration

```
server/reflector/
├── conductor/
│   ├── __init__.py
│   ├── client.py              # Conductor SDK wrapper
│   ├── cache.py               # Idempotency cache
│   ├── shadow_compare.py      # Shadow mode comparison
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── definitions.py     # Task definitions with timeouts
│   │   └── register.py        # Registration script
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── get_recording.py
│   │   ├── get_participants.py
│   │   ├── pad_track.py
│   │   ├── mixdown_tracks.py
│   │   ├── generate_waveform.py
│   │   ├── transcribe_track.py
│   │   ├── merge_transcripts.py
│   │   ├── detect_topics.py
│   │   ├── generate_title.py
│   │   ├── generate_summary.py
│   │   ├── finalize.py
│   │   ├── cleanup_consent.py
│   │   ├── post_zulip.py
│   │   └── send_webhook.py
│   └── workflows/
│       ├── diarization_pipeline.json
│       └── register.py
├── views/
│   └── conductor.py           # Health & status endpoints
└── ...existing files...
```
