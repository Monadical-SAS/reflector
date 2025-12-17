"""
Hatchet main workflow: DiarizationPipeline

Multitrack diarization pipeline for Daily.co recordings.
Orchestrates the full processing flow from recording metadata to final transcript.

Note: This file uses deferred imports (inside functions/tasks) intentionally.
Hatchet workers run in forked processes; fresh imports per task ensure DB connections
are not shared across forks, avoiding connection pooling issues.
"""

import asyncio
import functools
import tempfile
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Callable

import httpx
from hatchet_sdk import Context
from pydantic import BaseModel

from reflector.dailyco_api.client import DailyApiClient
from reflector.hatchet.broadcast import (
    append_event_and_broadcast,
    set_status_and_broadcast,
)
from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.utils import to_dict
from reflector.hatchet.workflows.models import (
    ConsentResult,
    FinalizeResult,
    MixdownResult,
    PaddedTrackInfo,
    ParticipantsResult,
    ProcessTracksResult,
    RecordingResult,
    SummaryResult,
    TitleResult,
    TopicsResult,
    WaveformResult,
    WebhookResult,
    ZulipResult,
)
from reflector.hatchet.workflows.track_processing import TrackInput, track_workflow
from reflector.logger import logger
from reflector.pipelines import topic_processing
from reflector.processors import AudioFileWriterProcessor
from reflector.processors.types import (
    TitleSummary,
    Word,
)
from reflector.processors.types import (
    Transcript as TranscriptType,
)
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
from reflector.utils.string import NonEmptyString
from reflector.zulip import post_transcript_notification


class PipelineInput(BaseModel):
    """Input to trigger the diarization pipeline."""

    recording_id: NonEmptyString
    tracks: list[dict]  # List of {"s3_key": str}
    bucket_name: NonEmptyString
    transcript_id: NonEmptyString
    room_id: NonEmptyString | None = None


hatchet = HatchetClientManager.get_client()

diarization_pipeline = hatchet.workflow(
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
            await set_status_and_broadcast(transcript_id, "error")
            logger.info(
                "[Hatchet] Set transcript status to error",
                transcript_id=transcript_id,
            )
            return True
    except Exception as e:
        logger.critical(
            "[Hatchet] CRITICAL: Failed to set error status - transcript may be stuck in 'processing'",
            transcript_id=transcript_id,
            error=str(e),
            exc_info=True,
        )
        return False


def _get_storage():
    """Create fresh storage instance."""
    return AwsStorage(
        aws_bucket_name=settings.TRANSCRIPT_STORAGE_AWS_BUCKET_NAME,
        aws_region=settings.TRANSCRIPT_STORAGE_AWS_REGION,
        aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
    )


def with_error_handling(step_name: str, set_error_status: bool = True) -> Callable:
    """Decorator that handles task failures uniformly.

    Args:
        step_name: Name of the step for logging and progress tracking.
        set_error_status: Whether to set transcript status to 'error' on failure.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(input: PipelineInput, ctx: Context):
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

        return wrapper

    return decorator


@diarization_pipeline.task(execution_timeout=timedelta(seconds=60), retries=3)
@with_error_handling("get_recording")
async def get_recording(input: PipelineInput, ctx: Context) -> RecordingResult:
    """Fetch recording metadata from Daily.co API."""
    ctx.log(f"get_recording: recording_id={input.recording_id}")
    logger.info("[Hatchet] get_recording", recording_id=input.recording_id)

    # Set transcript status to "processing" at workflow start (broadcasts to WebSocket)
    async with fresh_db_connection():
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript:
            await set_status_and_broadcast(input.transcript_id, "processing")
            logger.info(
                "[Hatchet] Set transcript status to processing",
                transcript_id=input.transcript_id,
            )

    if not settings.DAILY_API_KEY:
        raise ValueError("DAILY_API_KEY not configured")

    async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
        recording = await client.get_recording(input.recording_id)

    ctx.log(
        f"get_recording complete: room={recording.room_name}, duration={recording.duration}s"
    )
    logger.info(
        "[Hatchet] get_recording complete",
        recording_id=input.recording_id,
        room_name=recording.room_name,
        duration=recording.duration,
    )

    return RecordingResult(
        id=recording.id,
        mtg_session_id=recording.mtgSessionId,
        duration=recording.duration,
    )


@diarization_pipeline.task(
    parents=[get_recording], execution_timeout=timedelta(seconds=60), retries=3
)
@with_error_handling("get_participants")
async def get_participants(input: PipelineInput, ctx: Context) -> ParticipantsResult:
    """Fetch participant list from Daily.co API and update transcript in database."""
    ctx.log(f"get_participants: transcript_id={input.transcript_id}")
    logger.info("[Hatchet] get_participants", transcript_id=input.transcript_id)

    recording_data = to_dict(ctx.task_output(get_recording))
    mtg_session_id = recording_data.get("mtg_session_id")

    async with fresh_db_connection():
        from reflector.db.transcripts import (  # noqa: PLC0415
            TranscriptParticipant,
            transcripts_controller,
        )

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript:
            # Note: title NOT cleared - preserves existing titles
            await transcripts_controller.update(
                transcript,
                {
                    "events": [],
                    "topics": [],
                    "participants": [],
                },
            )

        if not mtg_session_id or not settings.DAILY_API_KEY:
            return ParticipantsResult(
                participants=[],
                num_tracks=len(input.tracks),
                source_language=transcript.source_language if transcript else "en",
                target_language=transcript.target_language if transcript else "en",
            )

        async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
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

        participants_list = []
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
                {
                    "participant_id": participant_id,
                    "user_name": name,
                    "speaker": idx,
                }
            )

        ctx.log(f"get_participants complete: {len(participants_list)} participants")
        logger.info(
            "[Hatchet] get_participants complete",
            participant_count=len(participants_list),
        )

    return ParticipantsResult(
        participants=participants_list,
        num_tracks=len(input.tracks),
        source_language=transcript.source_language if transcript else "en",
        target_language=transcript.target_language if transcript else "en",
    )


@diarization_pipeline.task(
    parents=[get_participants], execution_timeout=timedelta(seconds=600), retries=3
)
@with_error_handling("process_tracks")
async def process_tracks(input: PipelineInput, ctx: Context) -> ProcessTracksResult:
    """Spawn child workflows for each track (dynamic fan-out)."""
    ctx.log(f"process_tracks: spawning {len(input.tracks)} track workflows")
    logger.info(
        "[Hatchet] process_tracks",
        num_tracks=len(input.tracks),
        transcript_id=input.transcript_id,
    )

    participants_data = to_dict(ctx.task_output(get_participants))
    source_language = participants_data.get("source_language", "en")

    child_coroutines = [
        track_workflow.aio_run(
            TrackInput(
                track_index=i,
                s3_key=track["s3_key"],
                bucket_name=input.bucket_name,
                transcript_id=input.transcript_id,
                language=source_language,
            )
        )
        for i, track in enumerate(input.tracks)
    ]

    results = await asyncio.gather(*child_coroutines)

    target_language = participants_data.get("target_language", "en")

    # Collect results from each track (don't mutate lists while iterating)
    track_words = []
    padded_tracks = []
    created_padded_files = set()

    for result in results:
        transcribe_result = result.get("transcribe_track", {})
        track_words.append(transcribe_result.get("words", []))

        pad_result = result.get("pad_track", {})
        padded_key = pad_result.get("padded_key")
        bucket_name = pad_result.get("bucket_name")

        # Store S3 key info (not presigned URL) - consumer tasks presign on demand
        if padded_key:
            padded_tracks.append(
                PaddedTrackInfo(key=padded_key, bucket_name=bucket_name)
            )

        track_index = pad_result.get("track_index")
        if pad_result.get("size", 0) > 0 and track_index is not None:
            storage_path = f"file_pipeline_hatchet/{input.transcript_id}/tracks/padded_{track_index}.webm"
            created_padded_files.add(storage_path)

    all_words = [word for words in track_words for word in words]
    all_words.sort(key=lambda w: w.get("start", 0))

    ctx.log(
        f"process_tracks complete: {len(all_words)} words from {len(input.tracks)} tracks"
    )
    logger.info(
        "[Hatchet] process_tracks complete",
        num_tracks=len(input.tracks),
        total_words=len(all_words),
    )

    return ProcessTracksResult(
        all_words=all_words,
        padded_tracks=padded_tracks,
        word_count=len(all_words),
        num_tracks=len(input.tracks),
        target_language=target_language,
        created_padded_files=list(created_padded_files),
    )


@diarization_pipeline.task(
    parents=[process_tracks], execution_timeout=timedelta(seconds=300), retries=3
)
@with_error_handling("mixdown_tracks")
async def mixdown_tracks(input: PipelineInput, ctx: Context) -> MixdownResult:
    """Mix all padded tracks into single audio file using PyAV (same as Celery)."""
    ctx.log("mixdown_tracks: mixing padded tracks into single audio file")
    logger.info("[Hatchet] mixdown_tracks", transcript_id=input.transcript_id)

    track_data = to_dict(ctx.task_output(process_tracks))
    padded_tracks_data = track_data.get("padded_tracks", [])

    if not padded_tracks_data:
        raise ValueError("No padded tracks to mixdown")

    storage = _get_storage()

    # Presign URLs on demand (avoids stale URLs on workflow replay)
    padded_urls = []
    for track_info in padded_tracks_data:
        # Handle both dict (from to_dict) and PaddedTrackInfo
        if isinstance(track_info, dict):
            key = track_info.get("key")
            bucket = track_info.get("bucket_name")
        else:
            key = track_info.key
            bucket = track_info.bucket_name

        if key:
            url = await storage.get_file_url(
                key,
                operation="get_object",
                expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
                bucket=bucket,
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
    duration_ms = [0.0]  # Mutable container for callback capture

    async def capture_duration(d):
        duration_ms[0] = d

    writer = AudioFileWriterProcessor(path=output_path, on_duration=capture_duration)

    await mixdown_tracks_pyav(
        valid_urls,
        writer,
        target_sample_rate,
        offsets_seconds=None,
        logger=logger,
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
    logger.info(
        "[Hatchet] mixdown_tracks uploaded",
        key=storage_path,
        size=file_size,
    )

    return MixdownResult(
        audio_key=storage_path,
        duration=duration_ms[0],
        tracks_mixed=len(valid_urls),
    )


@diarization_pipeline.task(
    parents=[mixdown_tracks], execution_timeout=timedelta(seconds=120), retries=3
)
@with_error_handling("generate_waveform")
async def generate_waveform(input: PipelineInput, ctx: Context) -> WaveformResult:
    """Generate audio waveform visualization using AudioWaveformProcessor (matches Celery)."""
    logger.info("[Hatchet] generate_waveform", transcript_id=input.transcript_id)

    from reflector.db.transcripts import (  # noqa: PLC0415
        TranscriptWaveform,
        transcripts_controller,
    )

    # Cleanup temporary padded S3 files (deferred until after mixdown)
    track_data = to_dict(ctx.task_output(process_tracks))
    created_padded_files = track_data.get("created_padded_files", [])
    if created_padded_files:
        logger.info(
            f"[Hatchet] Cleaning up {len(created_padded_files)} temporary S3 files"
        )
        storage = _get_storage()
        cleanup_tasks = []
        for storage_path in created_padded_files:
            cleanup_tasks.append(storage.delete_file(storage_path))

        cleanup_results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        for storage_path, result in zip(created_padded_files, cleanup_results):
            if isinstance(result, Exception):
                logger.warning(
                    "[Hatchet] Failed to cleanup temporary padded track",
                    storage_path=storage_path,
                    error=str(result),
                )

    mixdown_data = to_dict(ctx.task_output(mixdown_tracks))
    audio_key = mixdown_data.get("audio_key")

    storage = _get_storage()
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
                waveform_data = TranscriptWaveform(waveform=waveform)
                await append_event_and_broadcast(
                    input.transcript_id, transcript, "WAVEFORM", waveform_data
                )

    finally:
        Path(temp_path).unlink(missing_ok=True)

    logger.info("[Hatchet] generate_waveform complete")

    return WaveformResult(waveform_generated=True)


@diarization_pipeline.task(
    parents=[mixdown_tracks], execution_timeout=timedelta(seconds=300), retries=3
)
@with_error_handling("detect_topics")
async def detect_topics(input: PipelineInput, ctx: Context) -> TopicsResult:
    """Detect topics using LLM and save to database (matches Celery on_topic callback)."""
    ctx.log("detect_topics: analyzing transcript for topics")
    logger.info("[Hatchet] detect_topics", transcript_id=input.transcript_id)

    track_data = to_dict(ctx.task_output(process_tracks))
    words = track_data.get("all_words", [])
    target_language = track_data.get("target_language", "en")

    from reflector.db.transcripts import (  # noqa: PLC0415
        TranscriptTopic,
        transcripts_controller,
    )
    from reflector.processors.types import (  # noqa: PLC0415
        TitleSummaryWithId as TitleSummaryWithIdProcessorType,
    )

    word_objects = [Word(**w) for w in words]
    transcript_type = TranscriptType(words=word_objects)

    empty_pipeline = topic_processing.EmptyPipeline(logger=logger)

    async with fresh_db_connection():
        transcript = await transcripts_controller.get_by_id(input.transcript_id)

        async def on_topic_callback(data):
            topic = TranscriptTopic(
                title=data.title,
                summary=data.summary,
                timestamp=data.timestamp,
                transcript=data.transcript.text,
                words=data.transcript.words,
            )
            if isinstance(data, TitleSummaryWithIdProcessorType):
                topic.id = data.id
            await transcripts_controller.upsert_topic(transcript, topic)
            await append_event_and_broadcast(
                input.transcript_id, transcript, "TOPIC", topic
            )

        topics = await topic_processing.detect_topics(
            transcript_type,
            target_language,
            on_topic_callback=on_topic_callback,
            empty_pipeline=empty_pipeline,
        )

    topics_list = [t.model_dump() for t in topics]

    ctx.log(f"detect_topics complete: found {len(topics_list)} topics")
    logger.info("[Hatchet] detect_topics complete", topic_count=len(topics_list))

    return TopicsResult(topics=topics_list)


@diarization_pipeline.task(
    parents=[detect_topics], execution_timeout=timedelta(seconds=120), retries=3
)
@with_error_handling("generate_title")
async def generate_title(input: PipelineInput, ctx: Context) -> TitleResult:
    """Generate meeting title using LLM and save to database (matches Celery on_title callback)."""
    ctx.log("generate_title: generating title from topics")
    logger.info("[Hatchet] generate_title", transcript_id=input.transcript_id)

    topics_data = to_dict(ctx.task_output(detect_topics))
    topics = topics_data.get("topics", [])

    from reflector.db.transcripts import (  # noqa: PLC0415
        TranscriptFinalTitle,
        transcripts_controller,
    )

    topic_objects = [TitleSummary(**t) for t in topics]

    empty_pipeline = topic_processing.EmptyPipeline(logger=logger)
    title_result = None

    async with fresh_db_connection():
        transcript = await transcripts_controller.get_by_id(input.transcript_id)

        async def on_title_callback(data):
            nonlocal title_result
            title_result = data.title
            final_title = TranscriptFinalTitle(title=data.title)
            if not transcript.title:
                await transcripts_controller.update(
                    transcript,
                    {"title": final_title.title},
                )
            await append_event_and_broadcast(
                input.transcript_id, transcript, "FINAL_TITLE", final_title
            )

        await topic_processing.generate_title(
            topic_objects,
            on_title_callback=on_title_callback,
            empty_pipeline=empty_pipeline,
            logger=logger,
        )

    ctx.log(f"generate_title complete: '{title_result}'")
    logger.info("[Hatchet] generate_title complete", title=title_result)

    return TitleResult(title=title_result)


@diarization_pipeline.task(
    parents=[detect_topics], execution_timeout=timedelta(seconds=300), retries=3
)
@with_error_handling("generate_summary")
async def generate_summary(input: PipelineInput, ctx: Context) -> SummaryResult:
    """Generate meeting summary using LLM and save to database (matches Celery callbacks)."""
    ctx.log("generate_summary: generating long and short summaries")
    logger.info("[Hatchet] generate_summary", transcript_id=input.transcript_id)

    topics_data = to_dict(ctx.task_output(detect_topics))
    topics = topics_data.get("topics", [])

    from reflector.db.transcripts import (  # noqa: PLC0415
        TranscriptFinalLongSummary,
        TranscriptFinalShortSummary,
        transcripts_controller,
    )

    topic_objects = [TitleSummary(**t) for t in topics]

    empty_pipeline = topic_processing.EmptyPipeline(logger=logger)
    summary_result = None
    short_summary_result = None

    async with fresh_db_connection():
        transcript = await transcripts_controller.get_by_id(input.transcript_id)

        async def on_long_summary_callback(data):
            nonlocal summary_result
            summary_result = data.long_summary
            final_long_summary = TranscriptFinalLongSummary(
                long_summary=data.long_summary
            )
            await transcripts_controller.update(
                transcript,
                {"long_summary": final_long_summary.long_summary},
            )
            await append_event_and_broadcast(
                input.transcript_id,
                transcript,
                "FINAL_LONG_SUMMARY",
                final_long_summary,
            )

        async def on_short_summary_callback(data):
            nonlocal short_summary_result
            short_summary_result = data.short_summary
            final_short_summary = TranscriptFinalShortSummary(
                short_summary=data.short_summary
            )
            await transcripts_controller.update(
                transcript,
                {"short_summary": final_short_summary.short_summary},
            )
            await append_event_and_broadcast(
                input.transcript_id,
                transcript,
                "FINAL_SHORT_SUMMARY",
                final_short_summary,
            )

        await topic_processing.generate_summaries(
            topic_objects,
            transcript,  # DB transcript for context
            on_long_summary_callback=on_long_summary_callback,
            on_short_summary_callback=on_short_summary_callback,
            empty_pipeline=empty_pipeline,
            logger=logger,
        )

    ctx.log("generate_summary complete")
    logger.info("[Hatchet] generate_summary complete")

    return SummaryResult(summary=summary_result, short_summary=short_summary_result)


@diarization_pipeline.task(
    parents=[generate_waveform, generate_title, generate_summary],
    execution_timeout=timedelta(seconds=60),
    retries=3,
)
@with_error_handling("finalize")
async def finalize(input: PipelineInput, ctx: Context) -> FinalizeResult:
    """Finalize transcript: save words, emit TRANSCRIPT event, set status to 'ended'.

    Matches Celery's on_transcript + set_status behavior.
    Note: Title and summaries are already saved by their respective task callbacks.
    """
    ctx.log("finalize: saving transcript and setting status to 'ended'")
    logger.info("[Hatchet] finalize", transcript_id=input.transcript_id)

    mixdown_data = to_dict(ctx.task_output(mixdown_tracks))
    track_data = to_dict(ctx.task_output(process_tracks))

    duration = mixdown_data.get("duration", 0)
    all_words = track_data.get("all_words", [])

    async with fresh_db_connection():
        from reflector.db.transcripts import (  # noqa: PLC0415
            TranscriptDuration,
            TranscriptText,
            transcripts_controller,
        )
        from reflector.processors.types import (  # noqa: PLC0415
            Transcript as TranscriptType,
        )
        from reflector.processors.types import Word  # noqa: PLC0415

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript is None:
            raise ValueError(f"Transcript {input.transcript_id} not found in database")

        word_objects = [Word(**w) for w in all_words]
        merged_transcript = TranscriptType(words=word_objects, translation=None)

        await append_event_and_broadcast(
            input.transcript_id,
            transcript,
            "TRANSCRIPT",
            TranscriptText(
                text=merged_transcript.text,
                translation=merged_transcript.translation,
            ),
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
            input.transcript_id, transcript, "DURATION", duration_data
        )

        await set_status_and_broadcast(input.transcript_id, "ended")

        ctx.log(
            f"finalize complete: transcript {input.transcript_id} status set to 'ended'"
        )
        logger.info("[Hatchet] finalize complete", transcript_id=input.transcript_id)

    return FinalizeResult(status="COMPLETED")


@diarization_pipeline.task(
    parents=[finalize], execution_timeout=timedelta(seconds=60), retries=3
)
@with_error_handling("cleanup_consent", set_error_status=False)
async def cleanup_consent(input: PipelineInput, ctx: Context) -> ConsentResult:
    """Check and handle consent requirements."""
    logger.info("[Hatchet] cleanup_consent", transcript_id=input.transcript_id)

    async with fresh_db_connection():
        from reflector.db.meetings import meetings_controller  # noqa: PLC0415
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript and transcript.meeting_id:
            meeting = await meetings_controller.get_by_id(transcript.meeting_id)
            if meeting:
                # Check consent logic here
                # For now just mark as checked
                pass

        logger.info(
            "[Hatchet] cleanup_consent complete", transcript_id=input.transcript_id
        )

    return ConsentResult(consent_checked=True)


@diarization_pipeline.task(
    parents=[cleanup_consent], execution_timeout=timedelta(seconds=60), retries=5
)
@with_error_handling("post_zulip", set_error_status=False)
async def post_zulip(input: PipelineInput, ctx: Context) -> ZulipResult:
    """Post notification to Zulip."""
    logger.info("[Hatchet] post_zulip", transcript_id=input.transcript_id)

    if not settings.ZULIP_REALM:
        logger.info("[Hatchet] post_zulip skipped (Zulip not configured)")
        return ZulipResult(zulip_message_id=None, skipped=True)

    async with fresh_db_connection():
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript:
            message_id = await post_transcript_notification(transcript)
            logger.info("[Hatchet] post_zulip complete", zulip_message_id=message_id)
        else:
            message_id = None

    return ZulipResult(zulip_message_id=message_id)


@diarization_pipeline.task(
    parents=[post_zulip], execution_timeout=timedelta(seconds=120), retries=30
)
@with_error_handling("send_webhook", set_error_status=False)
async def send_webhook(input: PipelineInput, ctx: Context) -> WebhookResult:
    """Send completion webhook to external service."""
    logger.info("[Hatchet] send_webhook", transcript_id=input.transcript_id)

    if not input.room_id:
        logger.info("[Hatchet] send_webhook skipped (no room_id)")
        return WebhookResult(webhook_sent=False, skipped=True)

    async with fresh_db_connection():
        from reflector.db.rooms import rooms_controller  # noqa: PLC0415
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415

        room = await rooms_controller.get_by_id(input.room_id)
        transcript = await transcripts_controller.get_by_id(input.transcript_id)

        if room and room.webhook_url and transcript:
            webhook_payload = {
                "event": "transcript.completed",
                "transcript_id": input.transcript_id,
                "title": transcript.title,
                "duration": transcript.duration,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    room.webhook_url, json=webhook_payload, timeout=30
                )
                response.raise_for_status()

            logger.info(
                "[Hatchet] send_webhook complete", status_code=response.status_code
            )

            return WebhookResult(webhook_sent=True, response_code=response.status_code)

    return WebhookResult(webhook_sent=False, skipped=True)
