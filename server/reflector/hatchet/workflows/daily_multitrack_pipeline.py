"""
Hatchet main workflow: DailyMultitrackPipeline

Multitrack processing pipeline for Daily.co recordings.
Orchestrates the full processing flow from recording metadata to final transcript.

Daily.co recordings don't require ML diarization - speaker identification comes from
track index (each participant's audio is a separate track).

Note: This file uses deferred imports (inside functions/tasks) intentionally.
Hatchet workers run in forked processes; fresh imports per task ensure DB connections
are not shared across forks, avoiding connection pooling issues.
"""

import asyncio
import functools
import json
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Coroutine, Protocol, TypeVar

import httpx
from hatchet_sdk import (
    ConcurrencyExpression,
    ConcurrencyLimitStrategy,
    Context,
)
from hatchet_sdk.labels import DesiredWorkerLabel
from pydantic import BaseModel

from reflector.dailyco_api.client import DailyApiClient
from reflector.hatchet.broadcast import (
    append_event_and_broadcast,
    set_status_and_broadcast,
)
from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.constants import (
    TIMEOUT_AUDIO,
    TIMEOUT_HEAVY,
    TIMEOUT_LONG,
    TIMEOUT_MEDIUM,
    TIMEOUT_SHORT,
    TaskName,
)
from reflector.hatchet.workflows.models import (
    ActionItemsResult,
    ConsentResult,
    FinalizeResult,
    MixdownResult,
    PaddedTrackInfo,
    PadTrackResult,
    ParticipantInfo,
    ParticipantsResult,
    ProcessPaddingsResult,
    ProcessSubjectsResult,
    ProcessTranscriptionsResult,
    RecapResult,
    RecordingResult,
    SubjectsResult,
    SubjectSummaryResult,
    TitleResult,
    TopicChunkResult,
    TopicsResult,
    TranscribeTrackResult,
    WaveformResult,
    WebhookResult,
    ZulipResult,
)
from reflector.hatchet.workflows.padding_workflow import PaddingInput, padding_workflow
from reflector.hatchet.workflows.subject_processing import (
    SubjectInput,
    subject_workflow,
)
from reflector.hatchet.workflows.topic_chunk_processing import (
    TopicChunkInput,
    topic_chunk_workflow,
)
from reflector.hatchet.workflows.transcription_workflow import (
    TranscriptionInput,
    transcription_workflow,
)
from reflector.logger import logger
from reflector.pipelines import topic_processing
from reflector.processors import AudioFileWriterProcessor
from reflector.processors.summary.models import ActionItemsResponse
from reflector.processors.summary.prompts import (
    RECAP_PROMPT,
    build_participant_instructions,
    build_summary_markdown,
)
from reflector.processors.summary.summary_builder import SummaryBuilder
from reflector.processors.types import TitleSummary, Word
from reflector.processors.types import Transcript as TranscriptType
from reflector.settings import settings
from reflector.storage.storage_aws import AwsStorage
from reflector.utils.audio_constants import (
    PRESIGNED_URL_EXPIRATION_SECONDS,
    WAVEFORM_SEGMENTS,
)
from reflector.utils.audio_mixdown import (
    detect_sample_rate_from_tracks,
    mixdown_tracks_pyav,
)
from reflector.utils.audio_waveform import get_audio_waveform
from reflector.utils.daily import (
    filter_cam_audio_tracks,
    parse_daily_recording_filename,
)
from reflector.utils.string import NonEmptyString, assert_non_none_and_non_empty
from reflector.utils.transcript_constants import TOPIC_CHUNK_WORD_COUNT
from reflector.zulip import post_transcript_notification


class PipelineInput(BaseModel):
    """Input to trigger the Daily.co multitrack pipeline."""

    recording_id: NonEmptyString
    tracks: list[dict]  # List of {"s3_key": str}
    bucket_name: NonEmptyString
    transcript_id: NonEmptyString
    room_id: NonEmptyString | None = None


hatchet = HatchetClientManager.get_client()

daily_multitrack_pipeline = hatchet.workflow(
    name="DiarizationPipeline", input_validator=PipelineInput
)


@asynccontextmanager
async def fresh_db_connection():
    """Context manager for database connections in Hatchet workers.
    TECH DEBT: Made to make connection fork-aware without changing db code too much.
    The real fix would be making the db module fork-aware instead of bypassing it.
    Current pattern is acceptable given Hatchet's process model.
    """
    import databases  # noqa: PLC0415

    from reflector.db import _database_context  # noqa: PLC0415

    _database_context.set(None)
    db = databases.Database(settings.DATABASE_URL)
    _database_context.set(db)
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()
        _database_context.set(None)


async def set_workflow_error_status(transcript_id: NonEmptyString) -> bool:
    """Set transcript status to 'error' on workflow failure.

    Returns:
        True if status was set successfully, False if failed.
        Failure is logged as CRITICAL since it means transcript may be stuck.
    """
    try:
        async with fresh_db_connection():
            await set_status_and_broadcast(transcript_id, "error", logger=logger)
            return True
    except Exception as e:
        logger.critical(
            "[Hatchet] CRITICAL: Failed to set error status - transcript may be stuck in 'processing'",
            transcript_id=transcript_id,
            error=str(e),
            exc_info=True,
        )
        return False


def _spawn_storage():
    """Create fresh storage instance."""
    return AwsStorage(
        aws_bucket_name=settings.TRANSCRIPT_STORAGE_AWS_BUCKET_NAME,
        aws_region=settings.TRANSCRIPT_STORAGE_AWS_REGION,
        aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
    )


class Loggable(Protocol):
    def log(self, message: str) -> None: ...


def make_audio_progress_logger(
    ctx: Loggable, task_name: TaskName, interval: float = 5.0
) -> Callable[[float | None, float], None]:
    """Create a throttled progress logger callback for audio processing.

    Args:
        ctx: Object with .log() method (e.g., Hatchet Context).
        task_name: Name to prefix in log messages.
        interval: Minimum seconds between log messages.

    Returns:
        Callback(progress_pct, audio_position) that logs at most every `interval` seconds.
    """
    start_time = time.monotonic()
    last_log_time = [start_time]

    def callback(progress_pct: float | None, audio_position: float) -> None:
        now = time.monotonic()
        if now - last_log_time[0] >= interval:
            elapsed = now - start_time
            if progress_pct is not None:
                ctx.log(
                    f"{task_name} progress: {progress_pct:.1f}% @ {audio_position:.1f}s (elapsed: {elapsed:.1f}s)"
                )
            else:
                ctx.log(
                    f"{task_name} progress: @ {audio_position:.1f}s (elapsed: {elapsed:.1f}s)"
                )
            last_log_time[0] = now

    return callback


R = TypeVar("R")


def with_error_handling(
    step_name: TaskName, set_error_status: bool = True
) -> Callable[
    [Callable[[PipelineInput, Context], Coroutine[Any, Any, R]]],
    Callable[[PipelineInput, Context], Coroutine[Any, Any, R]],
]:
    """Decorator that handles task failures uniformly.

    Args:
        step_name: Name of the step for logging and progress tracking.
        set_error_status: Whether to set transcript status to 'error' on failure.
    """

    def decorator(
        func: Callable[[PipelineInput, Context], Coroutine[Any, Any, R]],
    ) -> Callable[[PipelineInput, Context], Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(input: PipelineInput, ctx: Context) -> R:
            try:
                return await func(input, ctx)
            except Exception as e:
                logger.error(
                    f"[Hatchet] {step_name} failed",
                    transcript_id=input.transcript_id,
                    error=str(e),
                    exc_info=True,
                )
                if set_error_status:
                    await set_workflow_error_status(input.transcript_id)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


@daily_multitrack_pipeline.task(
    execution_timeout=timedelta(seconds=TIMEOUT_SHORT), retries=3
)
@with_error_handling(TaskName.GET_RECORDING)
async def get_recording(input: PipelineInput, ctx: Context) -> RecordingResult:
    """Fetch recording metadata from Daily.co API."""
    ctx.log(f"get_recording: starting for recording_id={input.recording_id}")
    ctx.log(
        f"get_recording: transcript_id={input.transcript_id}, room_id={input.room_id}"
    )
    ctx.log(
        f"get_recording: bucket_name={input.bucket_name}, tracks={len(input.tracks)}"
    )

    # Set transcript status to "processing" at workflow start (broadcasts to WebSocket)
    ctx.log("get_recording: establishing DB connection...")
    async with fresh_db_connection():
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

        ctx.log("get_recording: DB connection established, fetching transcript...")
        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        ctx.log(f"get_recording: transcript exists={transcript is not None}")
        if transcript:
            ctx.log(
                f"get_recording: current status={transcript.status}, setting to 'processing'..."
            )
            await set_status_and_broadcast(
                input.transcript_id, "processing", logger=logger
            )
            ctx.log(f"get_recording: status set to 'processing' and broadcasted")

    if not settings.DAILY_API_KEY:
        ctx.log("get_recording: ERROR - DAILY_API_KEY not configured")
        raise ValueError("DAILY_API_KEY not configured")

    ctx.log(
        f"get_recording: calling Daily.co API for recording_id={input.recording_id}..."
    )
    async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
        recording = await client.get_recording(input.recording_id)
    ctx.log(f"get_recording: Daily.co API returned successfully")

    ctx.log(
        f"get_recording complete: room={recording.room_name}, duration={recording.duration}s, mtg_session_id={recording.mtgSessionId}"
    )

    return RecordingResult(
        id=recording.id,
        mtg_session_id=recording.mtgSessionId,
        duration=recording.duration,
    )


@daily_multitrack_pipeline.task(
    parents=[get_recording],
    execution_timeout=timedelta(seconds=TIMEOUT_SHORT),
    retries=3,
)
@with_error_handling(TaskName.GET_PARTICIPANTS)
async def get_participants(input: PipelineInput, ctx: Context) -> ParticipantsResult:
    """Fetch participant list from Daily.co API and update transcript in database."""
    ctx.log(f"get_participants: transcript_id={input.transcript_id}")

    recording = ctx.task_output(get_recording)
    mtg_session_id = recording.mtg_session_id
    async with fresh_db_connection():
        from reflector.db.transcripts import (  # noqa: PLC0415
            TranscriptParticipant,
            transcripts_controller,
        )

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if not transcript:
            raise ValueError(f"Transcript {input.transcript_id} not found")
        # Note: title NOT cleared - preserves existing titles
        await transcripts_controller.update(
            transcript,
            {
                "events": [],
                "topics": [],
                "participants": [],
            },
        )

        mtg_session_id = assert_non_none_and_non_empty(
            mtg_session_id, "mtg_session_id is required"
        )
        daily_api_key = assert_non_none_and_non_empty(
            settings.DAILY_API_KEY, "DAILY_API_KEY is required"
        )

        async with DailyApiClient(api_key=daily_api_key) as client:
            participants = await client.get_meeting_participants(mtg_session_id)

        id_to_name = {}
        id_to_user_id = {}
        for p in participants.data:
            if p.user_name:
                id_to_name[p.participant_id] = p.user_name
            if p.user_id:
                id_to_user_id[p.participant_id] = p.user_id

        track_keys = [t["s3_key"] for t in input.tracks]
        cam_audio_keys = filter_cam_audio_tracks(track_keys)

        participants_list: list[ParticipantInfo] = []
        for idx, key in enumerate(cam_audio_keys):
            try:
                parsed = parse_daily_recording_filename(key)
                participant_id = parsed.participant_id
            except ValueError as e:
                logger.error(
                    "Failed to parse Daily recording filename",
                    error=str(e),
                    key=key,
                )
                continue

            default_name = f"Speaker {idx}"
            name = id_to_name.get(participant_id, default_name)
            user_id = id_to_user_id.get(participant_id)

            participant = TranscriptParticipant(
                id=participant_id, speaker=idx, name=name, user_id=user_id
            )
            await transcripts_controller.upsert_participant(transcript, participant)
            participants_list.append(
                ParticipantInfo(
                    participant_id=participant_id,
                    user_name=name,
                    speaker=idx,
                )
            )

        ctx.log(f"get_participants complete: {len(participants_list)} participants")

    return ParticipantsResult(
        participants=participants_list,
        num_tracks=len(input.tracks),
        source_language=transcript.source_language if transcript else "en",
        target_language=transcript.target_language if transcript else "en",
    )


@daily_multitrack_pipeline.task(
    parents=[get_participants],
    execution_timeout=timedelta(seconds=TIMEOUT_HEAVY),
    retries=3,
)
@with_error_handling(TaskName.PROCESS_PADDINGS)
async def process_paddings(input: PipelineInput, ctx: Context) -> ProcessPaddingsResult:
    """Spawn child workflows for each track to apply padding (dynamic fan-out)."""
    ctx.log(f"process_paddings: spawning {len(input.tracks)} padding workflows")

    bulk_runs = [
        padding_workflow.create_bulk_run_item(
            input=PaddingInput(
                track_index=i,
                s3_key=track["s3_key"],
                bucket_name=input.bucket_name,
                transcript_id=input.transcript_id,
            )
        )
        for i, track in enumerate(input.tracks)
    ]

    results = await padding_workflow.aio_run_many(bulk_runs)

    padded_tracks = []
    created_padded_files = set()

    for result in results:
        pad_result = PadTrackResult(**result[TaskName.PAD_TRACK])

        # Store S3 key info (not presigned URL) - consumer tasks presign on demand
        if pad_result.padded_key:
            padded_tracks.append(
                PaddedTrackInfo(
                    key=pad_result.padded_key, bucket_name=pad_result.bucket_name
                )
            )

        if pad_result.size > 0:
            storage_path = f"file_pipeline_hatchet/{input.transcript_id}/tracks/padded_{pad_result.track_index}.webm"
            created_padded_files.add(storage_path)

    ctx.log(f"process_paddings complete: {len(padded_tracks)} padded tracks")

    return ProcessPaddingsResult(
        padded_tracks=padded_tracks,
        num_tracks=len(input.tracks),
        created_padded_files=list(created_padded_files),
    )


@daily_multitrack_pipeline.task(
    parents=[process_paddings],
    execution_timeout=timedelta(seconds=TIMEOUT_HEAVY),
    retries=3,
)
@with_error_handling(TaskName.PROCESS_TRANSCRIPTIONS)
async def process_transcriptions(
    input: PipelineInput, ctx: Context
) -> ProcessTranscriptionsResult:
    """Spawn child workflows for each padded track to transcribe (dynamic fan-out)."""
    participants_result = ctx.task_output(get_participants)
    paddings_result = ctx.task_output(process_paddings)

    source_language = participants_result.source_language
    if not source_language:
        raise ValueError("source_language is required for transcription")

    target_language = participants_result.target_language
    padded_tracks = paddings_result.padded_tracks

    ctx.log(
        f"process_transcriptions: spawning {len(padded_tracks)} transcription workflows"
    )

    bulk_runs = [
        transcription_workflow.create_bulk_run_item(
            input=TranscriptionInput(
                track_index=i,
                padded_key=padded_track.key,
                bucket_name=padded_track.bucket_name,
                language=source_language,
            )
        )
        for i, padded_track in enumerate(padded_tracks)
    ]

    results = await transcription_workflow.aio_run_many(bulk_runs)

    track_words: list[list[Word]] = []
    for result in results:
        transcribe_result = TranscribeTrackResult(**result[TaskName.TRANSCRIBE_TRACK])
        track_words.append(transcribe_result.words)

    all_words = [word for words in track_words for word in words]
    all_words.sort(key=lambda w: w.start)

    ctx.log(
        f"process_transcriptions complete: {len(all_words)} words from {len(padded_tracks)} tracks"
    )

    return ProcessTranscriptionsResult(
        all_words=all_words,
        word_count=len(all_words),
        num_tracks=len(input.tracks),
        target_language=target_language,
    )


@daily_multitrack_pipeline.task(
    parents=[process_paddings],
    execution_timeout=timedelta(seconds=TIMEOUT_AUDIO),
    retries=3,
    desired_worker_labels={
        "pool": DesiredWorkerLabel(
            value="cpu-heavy",
            required=True,
            weight=100,
        ),
    },
    concurrency=[
        ConcurrencyExpression(
            expression="'mixdown-global'",
            max_runs=1,  # serialize mixdown to prevent resource contention
            limit_strategy=ConcurrencyLimitStrategy.GROUP_ROUND_ROBIN,  # Queue
        )
    ],
)
@with_error_handling(TaskName.MIXDOWN_TRACKS)
async def mixdown_tracks(input: PipelineInput, ctx: Context) -> MixdownResult:
    """Mix all padded tracks into single audio file using PyAV."""
    ctx.log("mixdown_tracks: mixing padded tracks into single audio file")

    paddings_result = ctx.task_output(process_paddings)
    recording_result = ctx.task_output(get_recording)
    padded_tracks = paddings_result.padded_tracks

    # Dynamic timeout: scales with track count and recording duration
    # Base 300s + 60s per track + 1s per 10s of recording
    track_count = len(padded_tracks) if padded_tracks else 0
    recording_duration = recording_result.duration or 0
    timeout_estimate = 300 + (track_count * 60) + int(recording_duration / 10)
    ctx.refresh_timeout(f"{timeout_estimate}s")
    ctx.log(
        f"mixdown_tracks: dynamic timeout set to {timeout_estimate}s "
        f"(tracks={track_count}, duration={recording_duration:.0f}s)"
    )

    # TODO think of NonEmpty type to avoid those checks, e.g. sized.NonEmpty from https://github.com/antonagestam/phantom-types/
    if not padded_tracks:
        raise ValueError("No padded tracks to mixdown")

    storage = _spawn_storage()

    # Presign URLs on demand (avoids stale URLs on workflow replay)
    padded_urls = []
    for track_info in padded_tracks:
        if track_info.key:
            url = await storage.get_file_url(
                track_info.key,
                operation="get_object",
                expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
                bucket=track_info.bucket_name,
            )
            padded_urls.append(url)

    valid_urls = [url for url in padded_urls if url]
    if not valid_urls:
        raise ValueError("No valid padded tracks to mixdown")

    target_sample_rate = detect_sample_rate_from_tracks(valid_urls, logger=logger)
    if not target_sample_rate:
        logger.error("Mixdown failed - no decodable audio frames found")
        raise ValueError("No decodable audio frames in any track")

    output_path = tempfile.mktemp(suffix=".mp3")
    duration_ms_callback_capture_container = [0.0]

    async def capture_duration(d):
        duration_ms_callback_capture_container[0] = d

    writer = AudioFileWriterProcessor(path=output_path, on_duration=capture_duration)

    await mixdown_tracks_pyav(
        valid_urls,
        writer,
        target_sample_rate,
        offsets_seconds=None,
        logger=logger,
        progress_callback=make_audio_progress_logger(ctx, TaskName.MIXDOWN_TRACKS),
        expected_duration_sec=recording_duration if recording_duration > 0 else None,
    )
    await writer.flush()

    file_size = Path(output_path).stat().st_size
    storage_path = f"{input.transcript_id}/audio.mp3"

    with open(output_path, "rb") as mixed_file:
        await storage.put_file(storage_path, mixed_file)

    Path(output_path).unlink(missing_ok=True)

    async with fresh_db_connection():
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript:
            await transcripts_controller.update(
                transcript, {"audio_location": "storage"}
            )

    ctx.log(f"mixdown_tracks complete: uploaded {file_size} bytes to {storage_path}")

    return MixdownResult(
        audio_key=storage_path,
        duration=duration_ms_callback_capture_container[0],
        tracks_mixed=len(valid_urls),
    )


@daily_multitrack_pipeline.task(
    parents=[mixdown_tracks],
    execution_timeout=timedelta(seconds=TIMEOUT_MEDIUM),
    retries=3,
)
@with_error_handling(TaskName.GENERATE_WAVEFORM)
async def generate_waveform(input: PipelineInput, ctx: Context) -> WaveformResult:
    """Generate audio waveform visualization using AudioWaveformProcessor (matches Celery)."""
    ctx.log(f"generate_waveform: transcript_id={input.transcript_id}")

    from reflector.db.transcripts import (  # noqa: PLC0415
        TranscriptWaveform,
        transcripts_controller,
    )

    mixdown_result = ctx.task_output(mixdown_tracks)
    audio_key = mixdown_result.audio_key

    storage = _spawn_storage()
    audio_url = await storage.get_file_url(
        audio_key,
        operation="get_object",
        expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
    )

    # Download MP3 to temp file (AudioWaveformProcessor needs local file)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url, timeout=120)
            response.raise_for_status()
            with open(temp_path, "wb") as f:
                f.write(response.content)

        waveform = get_audio_waveform(
            path=Path(temp_path), segments_count=WAVEFORM_SEGMENTS
        )

        async with fresh_db_connection():
            transcript = await transcripts_controller.get_by_id(input.transcript_id)
            if transcript:
                # Write waveform to file (same as Celery AudioWaveformProcessor)
                transcript.data_path.mkdir(parents=True, exist_ok=True)
                with open(transcript.audio_waveform_filename, "w") as f:
                    json.dump(waveform, f)
                ctx.log(
                    f"generate_waveform: wrote waveform to {transcript.audio_waveform_filename}"
                )

                waveform_data = TranscriptWaveform(waveform=waveform)
                await append_event_and_broadcast(
                    input.transcript_id,
                    transcript,
                    "WAVEFORM",
                    waveform_data,
                    logger=logger,
                )

    finally:
        Path(temp_path).unlink(missing_ok=True)

    ctx.log("generate_waveform complete")

    return WaveformResult(waveform_generated=True)


@daily_multitrack_pipeline.task(
    parents=[process_transcriptions],
    execution_timeout=timedelta(seconds=TIMEOUT_HEAVY),
    retries=3,
)
@with_error_handling(TaskName.DETECT_TOPICS)
async def detect_topics(input: PipelineInput, ctx: Context) -> TopicsResult:
    """Detect topics using parallel child workflows (one per chunk)."""
    ctx.log("detect_topics: analyzing transcript for topics")

    transcriptions_result = ctx.task_output(process_transcriptions)
    words = transcriptions_result.all_words

    if not words:
        ctx.log("detect_topics: no words, returning empty topics")
        return TopicsResult(topics=[])

    # Deferred imports: Hatchet workers fork processes
    from reflector.db.transcripts import (  # noqa: PLC0415
        TranscriptTopic,
        transcripts_controller,
    )

    chunk_size = TOPIC_CHUNK_WORD_COUNT
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk_words = words[i : i + chunk_size]
        if not chunk_words:
            continue

        first_word = chunk_words[0]
        last_word = chunk_words[-1]
        timestamp = first_word.start
        duration = last_word.end - timestamp
        chunk_text = " ".join(w.text for w in chunk_words)

        chunks.append(
            {
                "index": len(chunks),
                "text": chunk_text,
                "timestamp": timestamp,
                "duration": duration,
                "words": chunk_words,
            }
        )

    if not chunks:
        ctx.log("detect_topics: no chunks generated, returning empty topics")
        return TopicsResult(topics=[])

    ctx.log(f"detect_topics: spawning {len(chunks)} topic chunk workflows in parallel")

    bulk_runs = [
        topic_chunk_workflow.create_bulk_run_item(
            input=TopicChunkInput(
                chunk_index=chunk["index"],
                chunk_text=chunk["text"],
                timestamp=chunk["timestamp"],
                duration=chunk["duration"],
                words=chunk["words"],
            )
        )
        for chunk in chunks
    ]

    results = await topic_chunk_workflow.aio_run_many(bulk_runs)

    topic_chunks = [
        TopicChunkResult(**result[TaskName.DETECT_CHUNK_TOPIC]) for result in results
    ]

    async with fresh_db_connection():
        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if not transcript:
            raise ValueError(f"Transcript {input.transcript_id} not found")

        for chunk in topic_chunks:
            topic = TranscriptTopic(
                title=chunk.title,
                summary=chunk.summary,
                timestamp=chunk.timestamp,
                transcript=" ".join(w.text for w in chunk.words),
                words=chunk.words,
            )
            await transcripts_controller.upsert_topic(transcript, topic)
            await append_event_and_broadcast(
                input.transcript_id, transcript, "TOPIC", topic, logger=logger
            )

    topics_list = [
        TitleSummary(
            title=chunk.title,
            summary=chunk.summary,
            timestamp=chunk.timestamp,
            duration=chunk.duration,
            transcript=TranscriptType(words=chunk.words),
        )
        for chunk in topic_chunks
    ]

    ctx.log(f"detect_topics complete: found {len(topics_list)} topics")

    return TopicsResult(topics=topics_list)


@daily_multitrack_pipeline.task(
    parents=[detect_topics],
    execution_timeout=timedelta(seconds=TIMEOUT_HEAVY),
    retries=3,
)
@with_error_handling(TaskName.GENERATE_TITLE)
async def generate_title(input: PipelineInput, ctx: Context) -> TitleResult:
    """Generate meeting title using LLM and save to database (matches Celery on_title callback)."""
    ctx.log(f"generate_title: starting for transcript_id={input.transcript_id}")

    topics_result = ctx.task_output(detect_topics)
    topics = topics_result.topics
    ctx.log(f"generate_title: received {len(topics)} topics from detect_topics")

    from reflector.db.transcripts import (  # noqa: PLC0415
        TranscriptFinalTitle,
        transcripts_controller,
    )

    ctx.log(f"generate_title: received {len(topics)} TitleSummary objects")

    empty_pipeline = topic_processing.EmptyPipeline(logger=logger)
    title_result = None

    async with fresh_db_connection():
        ctx.log("generate_title: DB connection established")
        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if not transcript:
            raise ValueError(f"Transcript {input.transcript_id} not found")
        ctx.log(f"generate_title: fetched transcript, exists={transcript is not None}")

        async def on_title_callback(data):
            nonlocal title_result
            ctx.log(f"generate_title: on_title_callback received title='{data.title}'")
            title_result = data.title
            final_title = TranscriptFinalTitle(title=data.title)
            if not transcript.title:
                await transcripts_controller.update(
                    transcript,
                    {"title": final_title.title},
                )
                ctx.log("generate_title: saved title to DB")
            await append_event_and_broadcast(
                input.transcript_id,
                transcript,
                "FINAL_TITLE",
                final_title,
                logger=logger,
            )
            ctx.log("generate_title: broadcasted FINAL_TITLE event")

        ctx.log("generate_title: calling topic_processing.generate_title (LLM call)...")
        await topic_processing.generate_title(
            topics,
            on_title_callback=on_title_callback,
            empty_pipeline=empty_pipeline,
            logger=logger,
        )
        ctx.log("generate_title: topic_processing.generate_title returned")

    ctx.log(f"generate_title complete: '{title_result}'")

    return TitleResult(title=title_result)


@daily_multitrack_pipeline.task(
    parents=[detect_topics],
    execution_timeout=timedelta(seconds=TIMEOUT_MEDIUM),
    retries=3,
)
@with_error_handling(TaskName.EXTRACT_SUBJECTS)
async def extract_subjects(input: PipelineInput, ctx: Context) -> SubjectsResult:
    """Extract main subjects/topics from transcript for parallel processing."""
    ctx.log(f"extract_subjects: starting for transcript_id={input.transcript_id}")

    topics_result = ctx.task_output(detect_topics)
    topics = topics_result.topics

    if not topics:
        ctx.log("extract_subjects: no topics, returning empty subjects")
        return SubjectsResult(
            subjects=[],
            transcript_text="",
            participant_names=[],
            participant_name_to_id={},
        )

    # Deferred imports: Hatchet workers fork processes, fresh imports avoid
    # sharing DB connections and LLM HTTP pools across forks
    from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415
    from reflector.llm import LLM  # noqa: PLC0415

    async with fresh_db_connection():
        transcript = await transcripts_controller.get_by_id(input.transcript_id)

        # Build transcript text from topics (same logic as TranscriptFinalSummaryProcessor)
        speakermap = {}
        if transcript and transcript.participants:
            speakermap = {
                p.speaker: p.name
                for p in transcript.participants
                if p.speaker is not None and p.name
            }

        text_lines = []
        for topic in topics:
            for segment in topic.transcript.as_segments():
                name = speakermap.get(segment.speaker, f"Speaker {segment.speaker}")
                text_lines.append(f"{name}: {segment.text}")

        transcript_text = "\n".join(text_lines)

        participant_names = []
        participant_name_to_id = {}
        if transcript and transcript.participants:
            participant_names = [p.name for p in transcript.participants if p.name]
            participant_name_to_id = {
                p.name: p.id for p in transcript.participants if p.name and p.id
            }

        # TODO: refactor SummaryBuilder methods into standalone functions
        llm = LLM(settings=settings)
        builder = SummaryBuilder(llm, logger=logger)
        builder.set_transcript(transcript_text)

        if participant_names:
            builder.set_known_participants(
                participant_names, participant_name_to_id=participant_name_to_id
            )

        ctx.log("extract_subjects: calling LLM to extract subjects")
        await builder.extract_subjects()

        ctx.log(f"extract_subjects complete: {len(builder.subjects)} subjects")

    return SubjectsResult(
        subjects=builder.subjects,
        transcript_text=transcript_text,
        participant_names=participant_names,
        participant_name_to_id=participant_name_to_id,
    )


@daily_multitrack_pipeline.task(
    parents=[extract_subjects],
    execution_timeout=timedelta(seconds=TIMEOUT_HEAVY),
    retries=3,
)
@with_error_handling(TaskName.PROCESS_SUBJECTS)
async def process_subjects(input: PipelineInput, ctx: Context) -> ProcessSubjectsResult:
    """Spawn child workflows for each subject (dynamic fan-out, parallel LLM calls)."""
    subjects_result = ctx.task_output(extract_subjects)
    subjects = subjects_result.subjects

    if not subjects:
        ctx.log("process_subjects: no subjects to process")
        return ProcessSubjectsResult(subject_summaries=[])

    ctx.log(f"process_subjects: spawning {len(subjects)} subject workflows in parallel")

    bulk_runs = [
        subject_workflow.create_bulk_run_item(
            input=SubjectInput(
                subject=subject,
                subject_index=i,
                transcript_text=subjects_result.transcript_text,
                participant_names=subjects_result.participant_names,
                participant_name_to_id=subjects_result.participant_name_to_id,
            )
        )
        for i, subject in enumerate(subjects)
    ]

    results = await subject_workflow.aio_run_many(bulk_runs)

    subject_summaries = [
        SubjectSummaryResult(**result[TaskName.GENERATE_DETAILED_SUMMARY])
        for result in results
    ]

    ctx.log(f"process_subjects complete: {len(subject_summaries)} summaries")

    return ProcessSubjectsResult(subject_summaries=subject_summaries)


@daily_multitrack_pipeline.task(
    parents=[process_subjects],
    execution_timeout=timedelta(seconds=TIMEOUT_MEDIUM),
    retries=3,
)
@with_error_handling(TaskName.GENERATE_RECAP)
async def generate_recap(input: PipelineInput, ctx: Context) -> RecapResult:
    """Generate recap and long summary from subject summaries, save to database."""
    ctx.log(f"generate_recap: starting for transcript_id={input.transcript_id}")

    subjects_result = ctx.task_output(extract_subjects)
    process_result = ctx.task_output(process_subjects)

    # Deferred imports: Hatchet workers fork processes, fresh imports avoid
    # sharing DB connections and LLM HTTP pools across forks
    from reflector.db.transcripts import (  # noqa: PLC0415
        TranscriptFinalLongSummary,
        TranscriptFinalShortSummary,
        transcripts_controller,
    )
    from reflector.llm import LLM  # noqa: PLC0415

    subject_summaries = process_result.subject_summaries

    if not subject_summaries:
        ctx.log("generate_recap: no subject summaries, returning empty")
        return RecapResult(short_summary="", long_summary="")

    summaries = [
        {"subject": s.subject, "summary": s.paragraph_summary}
        for s in subject_summaries
    ]

    summaries_text = "\n\n".join([f"{s['subject']}: {s['summary']}" for s in summaries])

    llm = LLM(settings=settings)

    participant_instructions = build_participant_instructions(
        subjects_result.participant_names
    )

    recap_prompt = RECAP_PROMPT
    if participant_instructions:
        recap_prompt = f"{recap_prompt}\n\n{participant_instructions}"

    ctx.log("generate_recap: calling LLM for recap")
    recap_response = await llm.get_response(
        recap_prompt,
        [summaries_text],
        tone_name="Recap summarizer",
    )
    short_summary = str(recap_response)

    long_summary = build_summary_markdown(short_summary, summaries)

    async with fresh_db_connection():
        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript:
            await transcripts_controller.update(
                transcript,
                {
                    "short_summary": short_summary,
                    "long_summary": long_summary,
                },
            )

            final_short = TranscriptFinalShortSummary(short_summary=short_summary)
            await append_event_and_broadcast(
                input.transcript_id,
                transcript,
                "FINAL_SHORT_SUMMARY",
                final_short,
                logger=logger,
            )

            final_long = TranscriptFinalLongSummary(long_summary=long_summary)
            await append_event_and_broadcast(
                input.transcript_id,
                transcript,
                "FINAL_LONG_SUMMARY",
                final_long,
                logger=logger,
            )

    ctx.log("generate_recap complete")

    return RecapResult(short_summary=short_summary, long_summary=long_summary)


@daily_multitrack_pipeline.task(
    parents=[extract_subjects],
    execution_timeout=timedelta(seconds=TIMEOUT_LONG),
    retries=3,
)
@with_error_handling(TaskName.IDENTIFY_ACTION_ITEMS)
async def identify_action_items(
    input: PipelineInput, ctx: Context
) -> ActionItemsResult:
    """Identify action items from transcript (parallel with subject processing)."""
    ctx.log(f"identify_action_items: starting for transcript_id={input.transcript_id}")

    subjects_result = ctx.task_output(extract_subjects)

    if not subjects_result.transcript_text:
        ctx.log("identify_action_items: no transcript text, returning empty")
        return ActionItemsResult(action_items=ActionItemsResponse())

    # Deferred imports: Hatchet workers fork processes, fresh imports avoid
    # sharing DB connections and LLM HTTP pools across forks
    from reflector.db.transcripts import (  # noqa: PLC0415
        TranscriptActionItems,
        transcripts_controller,
    )
    from reflector.llm import LLM  # noqa: PLC0415

    # TODO: refactor SummaryBuilder methods into standalone functions
    llm = LLM(settings=settings)
    builder = SummaryBuilder(llm, logger=logger)
    builder.set_transcript(subjects_result.transcript_text)

    if subjects_result.participant_names:
        builder.set_known_participants(
            subjects_result.participant_names,
            participant_name_to_id=subjects_result.participant_name_to_id,
        )

    ctx.log("identify_action_items: calling LLM")
    action_items_response = await builder.identify_action_items()

    if action_items_response is None:
        raise RuntimeError("Failed to identify action items - LLM call failed")

    async with fresh_db_connection():
        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript:
            # Serialize to dict for DB storage and WebSocket broadcast
            action_items_dict = action_items_response.model_dump()
            action_items = TranscriptActionItems(action_items=action_items_dict)
            await transcripts_controller.update(
                transcript, {"action_items": action_items.action_items}
            )
            await append_event_and_broadcast(
                input.transcript_id,
                transcript,
                "ACTION_ITEMS",
                action_items,
                logger=logger,
            )

    ctx.log(
        f"identify_action_items complete: {len(action_items_response.decisions)} decisions, "
        f"{len(action_items_response.next_steps)} next steps"
    )

    return ActionItemsResult(action_items=action_items_response)


@daily_multitrack_pipeline.task(
    parents=[generate_waveform, generate_title, generate_recap, identify_action_items],
    execution_timeout=timedelta(seconds=TIMEOUT_SHORT),
    retries=3,
)
@with_error_handling(TaskName.FINALIZE)
async def finalize(input: PipelineInput, ctx: Context) -> FinalizeResult:
    """Finalize transcript: save words, emit TRANSCRIPT event, set status to 'ended'.

    Matches Celery's on_transcript + set_status behavior.
    Note: Title and summaries are already saved by their respective task callbacks.
    """
    ctx.log("finalize: saving transcript and setting status to 'ended'")

    mixdown_result = ctx.task_output(mixdown_tracks)
    transcriptions_result = ctx.task_output(process_transcriptions)
    paddings_result = ctx.task_output(process_paddings)

    duration = mixdown_result.duration
    all_words = transcriptions_result.all_words

    # Cleanup temporary padded S3 files (deferred until finalize for semantic parity with Celery)
    created_padded_files = paddings_result.created_padded_files
    if created_padded_files:
        ctx.log(f"Cleaning up {len(created_padded_files)} temporary S3 files")
        storage = _spawn_storage()
        cleanup_results = await asyncio.gather(
            *[storage.delete_file(path) for path in created_padded_files],
            return_exceptions=True,
        )
        for storage_path, result in zip(created_padded_files, cleanup_results):
            if isinstance(result, Exception):
                logger.warning(
                    "[Hatchet] Failed to cleanup temporary padded track",
                    storage_path=storage_path,
                    error=str(result),
                )

    async with fresh_db_connection():
        from reflector.db.transcripts import (  # noqa: PLC0415
            TranscriptDuration,
            TranscriptText,
            transcripts_controller,
        )

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript is None:
            raise ValueError(f"Transcript {input.transcript_id} not found in database")

        merged_transcript = TranscriptType(words=all_words, translation=None)

        await append_event_and_broadcast(
            input.transcript_id,
            transcript,
            "TRANSCRIPT",
            TranscriptText(
                text=merged_transcript.text,
                translation=merged_transcript.translation,
            ),
            logger=logger,
        )

        # Save duration and clear workflow_run_id (workflow completed successfully)
        # Note: title/long_summary/short_summary already saved by their callbacks
        await transcripts_controller.update(
            transcript,
            {
                "duration": duration,
                "workflow_run_id": None,  # Clear on success - no need to resume
            },
        )

        duration_data = TranscriptDuration(duration=duration)
        await append_event_and_broadcast(
            input.transcript_id, transcript, "DURATION", duration_data, logger=logger
        )

        await set_status_and_broadcast(input.transcript_id, "ended", logger=logger)

        ctx.log(
            f"finalize complete: transcript {input.transcript_id} status set to 'ended'"
        )

    return FinalizeResult(status="COMPLETED")


@daily_multitrack_pipeline.task(
    parents=[finalize], execution_timeout=timedelta(seconds=TIMEOUT_SHORT), retries=3
)
@with_error_handling(TaskName.CLEANUP_CONSENT, set_error_status=False)
async def cleanup_consent(input: PipelineInput, ctx: Context) -> ConsentResult:
    """Check consent and delete audio files if any participant denied."""
    ctx.log(f"cleanup_consent: transcript_id={input.transcript_id}")

    async with fresh_db_connection():
        from reflector.db.meetings import (  # noqa: PLC0415
            meeting_consent_controller,
            meetings_controller,
        )
        from reflector.db.recordings import recordings_controller  # noqa: PLC0415
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415
        from reflector.storage import get_transcripts_storage  # noqa: PLC0415

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if not transcript:
            ctx.log("cleanup_consent: transcript not found")
            return ConsentResult()

        consent_denied = False
        if transcript.meeting_id:
            meeting = await meetings_controller.get_by_id(transcript.meeting_id)
            if meeting:
                consent_denied = await meeting_consent_controller.has_any_denial(
                    meeting.id
                )

        if not consent_denied:
            ctx.log("cleanup_consent: consent approved, keeping all files")
            return ConsentResult()

        ctx.log("cleanup_consent: consent denied, deleting audio files")

        input_track_keys = set(t["s3_key"] for t in input.tracks)

        # Detect if recording.track_keys was manually modified after workflow started
        if transcript.recording_id:
            recording = await recordings_controller.get_by_id(transcript.recording_id)
            if recording and recording.track_keys:
                db_track_keys = set(filter_cam_audio_tracks(recording.track_keys))

                if input_track_keys != db_track_keys:
                    added = db_track_keys - input_track_keys
                    removed = input_track_keys - db_track_keys
                    logger.warning(
                        "[Hatchet] Track keys mismatch: DB changed since workflow start",
                        transcript_id=input.transcript_id,
                        recording_id=transcript.recording_id,
                        input_count=len(input_track_keys),
                        db_count=len(db_track_keys),
                        added_in_db=list(added) if added else None,
                        removed_from_db=list(removed) if removed else None,
                    )
                    ctx.log(
                        f"WARNING: track_keys mismatch - "
                        f"input has {len(input_track_keys)}, DB has {len(db_track_keys)}. "
                        f"Using input tracks for deletion."
                    )

        deletion_errors = []

        if input_track_keys and input.bucket_name:
            master_storage = get_transcripts_storage()
            for key in input_track_keys:
                try:
                    await master_storage.delete_file(key, bucket=input.bucket_name)
                    ctx.log(f"Deleted recording file: {input.bucket_name}/{key}")
                except Exception as e:
                    error_msg = f"Failed to delete {key}: {e}"
                    logger.error(error_msg, exc_info=True)
                    deletion_errors.append(error_msg)

        if transcript.audio_location == "storage":
            storage = get_transcripts_storage()
            try:
                await storage.delete_file(transcript.storage_audio_path)
                ctx.log(f"Deleted processed audio: {transcript.storage_audio_path}")
            except Exception as e:
                error_msg = f"Failed to delete processed audio: {e}"
                logger.error(error_msg, exc_info=True)
                deletion_errors.append(error_msg)

        if deletion_errors:
            logger.warning(
                "[Hatchet] cleanup_consent completed with errors",
                transcript_id=input.transcript_id,
                error_count=len(deletion_errors),
                errors=deletion_errors,
            )
            ctx.log(f"cleanup_consent completed with {len(deletion_errors)} errors")
        else:
            await transcripts_controller.update(transcript, {"audio_deleted": True})
            ctx.log("cleanup_consent: all audio deleted successfully")

    return ConsentResult()


@daily_multitrack_pipeline.task(
    parents=[cleanup_consent],
    execution_timeout=timedelta(seconds=TIMEOUT_SHORT),
    retries=5,
)
@with_error_handling(TaskName.POST_ZULIP, set_error_status=False)
async def post_zulip(input: PipelineInput, ctx: Context) -> ZulipResult:
    """Post notification to Zulip."""
    ctx.log(f"post_zulip: transcript_id={input.transcript_id}")

    if not settings.ZULIP_REALM:
        ctx.log("post_zulip skipped (Zulip not configured)")
        return ZulipResult(zulip_message_id=None, skipped=True)

    async with fresh_db_connection():
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript:
            message_id = await post_transcript_notification(transcript)
            ctx.log(f"post_zulip complete: zulip_message_id={message_id}")
        else:
            message_id = None

    return ZulipResult(zulip_message_id=message_id)


@daily_multitrack_pipeline.task(
    parents=[cleanup_consent],
    execution_timeout=timedelta(seconds=TIMEOUT_MEDIUM),
    retries=5,
)
@with_error_handling(TaskName.SEND_WEBHOOK, set_error_status=False)
async def send_webhook(input: PipelineInput, ctx: Context) -> WebhookResult:
    """Send completion webhook to external service with full payload and HMAC signature."""
    ctx.log(f"send_webhook: transcript_id={input.transcript_id}")

    if not input.room_id:
        ctx.log("send_webhook skipped (no room_id)")
        return WebhookResult(webhook_sent=False, skipped=True)

    async with fresh_db_connection():
        from reflector.db.rooms import rooms_controller  # noqa: PLC0415
        from reflector.utils.webhook import (  # noqa: PLC0415
            fetch_transcript_webhook_payload,
            send_webhook_request,
        )

        room = await rooms_controller.get_by_id(input.room_id)
        if not room or not room.webhook_url:
            ctx.log("send_webhook skipped (no webhook_url configured)")
            return WebhookResult(webhook_sent=False, skipped=True)

        payload = await fetch_transcript_webhook_payload(
            transcript_id=input.transcript_id,
            room_id=input.room_id,
        )

        if isinstance(payload, str):
            ctx.log(f"send_webhook skipped (could not build payload): {payload}")
            return WebhookResult(webhook_sent=False, skipped=True)

        ctx.log(
            f"send_webhook: sending to {room.webhook_url} "
            f"(topics={len(payload.transcript.topics)}, "
            f"participants={len(payload.transcript.participants)})"
        )

        response = await send_webhook_request(
            url=room.webhook_url,
            payload=payload,
            event_type="transcript.completed",
            webhook_secret=room.webhook_secret,
            timeout=30.0,
        )

        ctx.log(f"send_webhook complete: status_code={response.status_code}")

        return WebhookResult(webhook_sent=True, response_code=response.status_code)
