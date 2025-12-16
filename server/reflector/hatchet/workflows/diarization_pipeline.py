"""
Hatchet main workflow: DiarizationPipeline

Multitrack diarization pipeline for Daily.co recordings.
Orchestrates the full processing flow from recording metadata to final transcript.
"""

import asyncio
import tempfile
from datetime import timedelta
from pathlib import Path

import av
from hatchet_sdk import Context
from pydantic import BaseModel

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.progress import emit_progress_async
from reflector.hatchet.workflows.track_processing import TrackInput, track_workflow
from reflector.logger import logger

# Audio constants
OPUS_STANDARD_SAMPLE_RATE = 48000
OPUS_DEFAULT_BIT_RATE = 64000
PRESIGNED_URL_EXPIRATION_SECONDS = 7200


class PipelineInput(BaseModel):
    """Input to trigger the diarization pipeline."""

    recording_id: str | None
    room_name: str | None
    tracks: list[dict]  # List of {"s3_key": str}
    bucket_name: str
    transcript_id: str
    room_id: str | None = None


# Get hatchet client and define workflow
hatchet = HatchetClientManager.get_client()

diarization_pipeline = hatchet.workflow(
    name="DiarizationPipeline", input_validator=PipelineInput
)


# ============================================================================
# Helper Functions
# ============================================================================


async def _get_fresh_db_connection():
    """Create fresh database connection for subprocess."""
    import databases

    from reflector.db import _database_context
    from reflector.settings import settings

    _database_context.set(None)
    db = databases.Database(settings.DATABASE_URL)
    _database_context.set(db)
    await db.connect()
    return db


async def _close_db_connection(db):
    """Close database connection."""
    from reflector.db import _database_context

    await db.disconnect()
    _database_context.set(None)


def _get_storage():
    """Create fresh storage instance."""
    from reflector.settings import settings
    from reflector.storage.storage_aws import AwsStorage

    return AwsStorage(
        aws_bucket_name=settings.TRANSCRIPT_STORAGE_AWS_BUCKET_NAME,
        aws_region=settings.TRANSCRIPT_STORAGE_AWS_REGION,
        aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
    )


# ============================================================================
# Pipeline Tasks
# ============================================================================


@diarization_pipeline.task(execution_timeout=timedelta(seconds=60), retries=3)
async def get_recording(input: PipelineInput, ctx: Context) -> dict:
    """Fetch recording metadata from Daily.co API."""
    logger.info("[Hatchet] get_recording", recording_id=input.recording_id)

    await emit_progress_async(
        input.transcript_id, "get_recording", "in_progress", ctx.workflow_run_id
    )

    try:
        from reflector.dailyco_api.client import DailyApiClient
        from reflector.settings import settings

        if not input.recording_id:
            # No recording_id in reprocess path - return minimal data
            await emit_progress_async(
                input.transcript_id, "get_recording", "completed", ctx.workflow_run_id
            )
            return {
                "id": None,
                "mtg_session_id": None,
                "room_name": input.room_name,
                "duration": 0,
            }

        if not settings.DAILY_API_KEY:
            raise ValueError("DAILY_API_KEY not configured")

        async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
            recording = await client.get_recording(input.recording_id)

        logger.info(
            "[Hatchet] get_recording complete",
            recording_id=input.recording_id,
            room_name=recording.room_name,
            duration=recording.duration,
        )

        await emit_progress_async(
            input.transcript_id, "get_recording", "completed", ctx.workflow_run_id
        )

        return {
            "id": recording.id,
            "mtg_session_id": recording.mtgSessionId,
            "room_name": recording.room_name,
            "duration": recording.duration,
        }

    except Exception as e:
        logger.error("[Hatchet] get_recording failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "get_recording", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[get_recording], execution_timeout=timedelta(seconds=60), retries=3
)
async def get_participants(input: PipelineInput, ctx: Context) -> dict:
    """Fetch participant list from Daily.co API."""
    logger.info("[Hatchet] get_participants", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "get_participants", "in_progress", ctx.workflow_run_id
    )

    try:
        recording_data = ctx.task_output(get_recording)
        mtg_session_id = recording_data.get("mtg_session_id")

        from reflector.dailyco_api.client import DailyApiClient
        from reflector.settings import settings

        if not mtg_session_id or not settings.DAILY_API_KEY:
            # Return empty participants if no session ID
            await emit_progress_async(
                input.transcript_id,
                "get_participants",
                "completed",
                ctx.workflow_run_id,
            )
            return {"participants": [], "num_tracks": len(input.tracks)}

        async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
            participants = await client.get_meeting_participants(mtg_session_id)

        participants_list = [
            {"participant_id": p.participant_id, "user_name": p.user_name}
            for p in participants.data
        ]

        logger.info(
            "[Hatchet] get_participants complete",
            participant_count=len(participants_list),
        )

        await emit_progress_async(
            input.transcript_id, "get_participants", "completed", ctx.workflow_run_id
        )

        return {"participants": participants_list, "num_tracks": len(input.tracks)}

    except Exception as e:
        logger.error("[Hatchet] get_participants failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "get_participants", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[get_participants], execution_timeout=timedelta(seconds=600), retries=3
)
async def process_tracks(input: PipelineInput, ctx: Context) -> dict:
    """Spawn child workflows for each track (dynamic fan-out).

    Processes pad_track and transcribe_track for each audio track in parallel.
    """
    logger.info(
        "[Hatchet] process_tracks",
        num_tracks=len(input.tracks),
        transcript_id=input.transcript_id,
    )

    # Spawn child workflows for each track
    child_coroutines = [
        track_workflow.aio_run(
            TrackInput(
                track_index=i,
                s3_key=track["s3_key"],
                bucket_name=input.bucket_name,
                transcript_id=input.transcript_id,
            )
        )
        for i, track in enumerate(input.tracks)
    ]

    # Wait for all child workflows to complete
    results = await asyncio.gather(*child_coroutines)

    # Collect all track results
    all_words = []
    padded_urls = []

    for result in results:
        transcribe_result = result.get("transcribe_track", {})
        all_words.extend(transcribe_result.get("words", []))

        pad_result = result.get("pad_track", {})
        padded_urls.append(pad_result.get("padded_url"))

    # Sort words by start time
    all_words.sort(key=lambda w: w.get("start", 0))

    logger.info(
        "[Hatchet] process_tracks complete",
        num_tracks=len(input.tracks),
        total_words=len(all_words),
    )

    return {
        "all_words": all_words,
        "padded_urls": padded_urls,
        "word_count": len(all_words),
        "num_tracks": len(input.tracks),
    }


@diarization_pipeline.task(
    parents=[process_tracks], execution_timeout=timedelta(seconds=300), retries=3
)
async def mixdown_tracks(input: PipelineInput, ctx: Context) -> dict:
    """Mix all padded tracks into single audio file."""
    logger.info("[Hatchet] mixdown_tracks", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "mixdown_tracks", "in_progress", ctx.workflow_run_id
    )

    try:
        track_data = ctx.task_output(process_tracks)
        padded_urls = track_data.get("padded_urls", [])

        if not padded_urls:
            raise ValueError("No padded tracks to mixdown")

        storage = _get_storage()

        # Download all tracks and mix
        temp_inputs = []
        try:
            for i, url in enumerate(padded_urls):
                if not url:
                    continue
                temp_input = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
                temp_inputs.append(temp_input.name)

                # Download track
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    with open(temp_input.name, "wb") as f:
                        f.write(response.content)

            # Mix using PyAV amix filter
            if len(temp_inputs) == 0:
                raise ValueError("No valid tracks to mixdown")

            output_path = tempfile.mktemp(suffix=".mp3")

            try:
                # Use ffmpeg-style mixing via PyAV
                containers = [av.open(path) for path in temp_inputs]

                # Get the longest duration
                max_duration = 0.0
                for container in containers:
                    if container.duration:
                        duration = float(container.duration * av.time_base)
                        max_duration = max(max_duration, duration)

                # Close containers for now
                for container in containers:
                    container.close()

                # Use subprocess for mixing (simpler than complex PyAV graph)
                import subprocess

                # Build ffmpeg command
                cmd = ["ffmpeg", "-y"]
                for path in temp_inputs:
                    cmd.extend(["-i", path])

                # Build filter for N inputs
                n = len(temp_inputs)
                filter_str = f"amix=inputs={n}:duration=longest:normalize=0"
                cmd.extend(["-filter_complex", filter_str])
                cmd.extend(["-ac", "2", "-ar", "48000", "-b:a", "128k", output_path])

                subprocess.run(cmd, check=True, capture_output=True)

                # Upload mixed file
                file_size = Path(output_path).stat().st_size
                storage_path = f"file_pipeline_hatchet/{input.transcript_id}/mixed.mp3"

                with open(output_path, "rb") as mixed_file:
                    await storage.put_file(storage_path, mixed_file)

                logger.info(
                    "[Hatchet] mixdown_tracks uploaded",
                    key=storage_path,
                    size=file_size,
                )

            finally:
                Path(output_path).unlink(missing_ok=True)

        finally:
            for path in temp_inputs:
                Path(path).unlink(missing_ok=True)

        await emit_progress_async(
            input.transcript_id, "mixdown_tracks", "completed", ctx.workflow_run_id
        )

        return {
            "audio_key": storage_path,
            "duration": max_duration,
            "tracks_mixed": len(temp_inputs),
        }

    except Exception as e:
        logger.error("[Hatchet] mixdown_tracks failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "mixdown_tracks", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[mixdown_tracks], execution_timeout=timedelta(seconds=120), retries=3
)
async def generate_waveform(input: PipelineInput, ctx: Context) -> dict:
    """Generate audio waveform visualization."""
    logger.info("[Hatchet] generate_waveform", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "generate_waveform", "in_progress", ctx.workflow_run_id
    )

    try:
        mixdown_data = ctx.task_output(mixdown_tracks)
        audio_key = mixdown_data.get("audio_key")

        storage = _get_storage()
        audio_url = await storage.get_file_url(
            audio_key,
            operation="get_object",
            expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
        )

        from reflector.pipelines.waveform_helpers import generate_waveform_data

        waveform = await generate_waveform_data(audio_url)

        # Store waveform
        waveform_key = f"file_pipeline_hatchet/{input.transcript_id}/waveform.json"
        import json

        waveform_bytes = json.dumps(waveform).encode()
        import io

        await storage.put_file(waveform_key, io.BytesIO(waveform_bytes))

        logger.info("[Hatchet] generate_waveform complete")

        await emit_progress_async(
            input.transcript_id, "generate_waveform", "completed", ctx.workflow_run_id
        )

        return {"waveform_key": waveform_key}

    except Exception as e:
        logger.error("[Hatchet] generate_waveform failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "generate_waveform", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[mixdown_tracks], execution_timeout=timedelta(seconds=300), retries=3
)
async def detect_topics(input: PipelineInput, ctx: Context) -> dict:
    """Detect topics using LLM."""
    logger.info("[Hatchet] detect_topics", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "detect_topics", "in_progress", ctx.workflow_run_id
    )

    try:
        track_data = ctx.task_output(process_tracks)
        words = track_data.get("all_words", [])

        from reflector.pipelines import topic_processing
        from reflector.processors.types import Transcript as TranscriptType
        from reflector.processors.types import Word

        # Convert word dicts to Word objects
        word_objects = [Word(**w) for w in words]
        transcript = TranscriptType(words=word_objects)

        empty_pipeline = topic_processing.EmptyPipeline(logger=logger)

        async def noop_callback(t):
            pass

        topics = await topic_processing.detect_topics(
            transcript,
            "en",  # target_language
            on_topic_callback=noop_callback,
            empty_pipeline=empty_pipeline,
        )

        topics_list = [t.model_dump() for t in topics]

        logger.info("[Hatchet] detect_topics complete", topic_count=len(topics_list))

        await emit_progress_async(
            input.transcript_id, "detect_topics", "completed", ctx.workflow_run_id
        )

        return {"topics": topics_list}

    except Exception as e:
        logger.error("[Hatchet] detect_topics failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "detect_topics", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[detect_topics], execution_timeout=timedelta(seconds=120), retries=3
)
async def generate_title(input: PipelineInput, ctx: Context) -> dict:
    """Generate meeting title using LLM."""
    logger.info("[Hatchet] generate_title", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "generate_title", "in_progress", ctx.workflow_run_id
    )

    try:
        topics_data = ctx.task_output(detect_topics)
        topics = topics_data.get("topics", [])

        from reflector.pipelines import topic_processing
        from reflector.processors.types import Topic

        topic_objects = [Topic(**t) for t in topics]

        title = await topic_processing.generate_title(topic_objects)

        logger.info("[Hatchet] generate_title complete", title=title)

        await emit_progress_async(
            input.transcript_id, "generate_title", "completed", ctx.workflow_run_id
        )

        return {"title": title}

    except Exception as e:
        logger.error("[Hatchet] generate_title failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "generate_title", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[detect_topics], execution_timeout=timedelta(seconds=300), retries=3
)
async def generate_summary(input: PipelineInput, ctx: Context) -> dict:
    """Generate meeting summary using LLM."""
    logger.info("[Hatchet] generate_summary", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "generate_summary", "in_progress", ctx.workflow_run_id
    )

    try:
        track_data = ctx.task_output(process_tracks)
        topics_data = ctx.task_output(detect_topics)

        words = track_data.get("all_words", [])
        topics = topics_data.get("topics", [])

        from reflector.pipelines import topic_processing
        from reflector.processors.types import Topic, Word
        from reflector.processors.types import Transcript as TranscriptType

        word_objects = [Word(**w) for w in words]
        transcript = TranscriptType(words=word_objects)
        topic_objects = [Topic(**t) for t in topics]

        summary, short_summary = await topic_processing.generate_summary(
            transcript, topic_objects
        )

        logger.info("[Hatchet] generate_summary complete")

        await emit_progress_async(
            input.transcript_id, "generate_summary", "completed", ctx.workflow_run_id
        )

        return {"summary": summary, "short_summary": short_summary}

    except Exception as e:
        logger.error("[Hatchet] generate_summary failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "generate_summary", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[generate_waveform, generate_title, generate_summary],
    execution_timeout=timedelta(seconds=60),
    retries=3,
)
async def finalize(input: PipelineInput, ctx: Context) -> dict:
    """Finalize transcript status and update database."""
    logger.info("[Hatchet] finalize", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "finalize", "in_progress", ctx.workflow_run_id
    )

    try:
        title_data = ctx.task_output(generate_title)
        summary_data = ctx.task_output(generate_summary)
        mixdown_data = ctx.task_output(mixdown_tracks)
        track_data = ctx.task_output(process_tracks)

        title = title_data.get("title", "")
        summary = summary_data.get("summary", "")
        short_summary = summary_data.get("short_summary", "")
        duration = mixdown_data.get("duration", 0)
        all_words = track_data.get("all_words", [])

        db = await _get_fresh_db_connection()

        try:
            from reflector.db.transcripts import transcripts_controller
            from reflector.processors.types import Word

            transcript = await transcripts_controller.get_by_id(input.transcript_id)
            if transcript is None:
                raise ValueError(
                    f"Transcript {input.transcript_id} not found in database"
                )

            # Convert words back to Word objects for storage
            word_objects = [Word(**w) for w in all_words]

            await transcripts_controller.update(
                transcript,
                {
                    "status": "ended",
                    "title": title,
                    "long_summary": summary,
                    "short_summary": short_summary,
                    "duration": duration,
                    "words": word_objects,
                },
            )

            logger.info(
                "[Hatchet] finalize complete", transcript_id=input.transcript_id
            )

        finally:
            await _close_db_connection(db)

        await emit_progress_async(
            input.transcript_id, "finalize", "completed", ctx.workflow_run_id
        )

        return {"status": "COMPLETED"}

    except Exception as e:
        logger.error("[Hatchet] finalize failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "finalize", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[finalize], execution_timeout=timedelta(seconds=60), retries=3
)
async def cleanup_consent(input: PipelineInput, ctx: Context) -> dict:
    """Check and handle consent requirements."""
    logger.info("[Hatchet] cleanup_consent", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "cleanup_consent", "in_progress", ctx.workflow_run_id
    )

    try:
        db = await _get_fresh_db_connection()

        try:
            from reflector.db.meetings import meetings_controller
            from reflector.db.transcripts import transcripts_controller

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

        finally:
            await _close_db_connection(db)

        await emit_progress_async(
            input.transcript_id, "cleanup_consent", "completed", ctx.workflow_run_id
        )

        return {"consent_checked": True}

    except Exception as e:
        logger.error("[Hatchet] cleanup_consent failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "cleanup_consent", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[cleanup_consent], execution_timeout=timedelta(seconds=60), retries=5
)
async def post_zulip(input: PipelineInput, ctx: Context) -> dict:
    """Post notification to Zulip."""
    logger.info("[Hatchet] post_zulip", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "post_zulip", "in_progress", ctx.workflow_run_id
    )

    try:
        from reflector.settings import settings

        if not settings.ZULIP_REALM:
            logger.info("[Hatchet] post_zulip skipped (Zulip not configured)")
            await emit_progress_async(
                input.transcript_id, "post_zulip", "completed", ctx.workflow_run_id
            )
            return {"zulip_message_id": None, "skipped": True}

        from reflector.zulip import post_transcript_notification

        db = await _get_fresh_db_connection()

        try:
            from reflector.db.transcripts import transcripts_controller

            transcript = await transcripts_controller.get_by_id(input.transcript_id)
            if transcript:
                message_id = await post_transcript_notification(transcript)
                logger.info(
                    "[Hatchet] post_zulip complete", zulip_message_id=message_id
                )
            else:
                message_id = None

        finally:
            await _close_db_connection(db)

        await emit_progress_async(
            input.transcript_id, "post_zulip", "completed", ctx.workflow_run_id
        )

        return {"zulip_message_id": message_id}

    except Exception as e:
        logger.error("[Hatchet] post_zulip failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "post_zulip", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[post_zulip], execution_timeout=timedelta(seconds=120), retries=30
)
async def send_webhook(input: PipelineInput, ctx: Context) -> dict:
    """Send completion webhook to external service."""
    logger.info("[Hatchet] send_webhook", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "send_webhook", "in_progress", ctx.workflow_run_id
    )

    try:
        if not input.room_id:
            logger.info("[Hatchet] send_webhook skipped (no room_id)")
            await emit_progress_async(
                input.transcript_id, "send_webhook", "completed", ctx.workflow_run_id
            )
            return {"webhook_sent": False, "skipped": True}

        db = await _get_fresh_db_connection()

        try:
            from reflector.db.rooms import rooms_controller
            from reflector.db.transcripts import transcripts_controller

            room = await rooms_controller.get_by_id(input.room_id)
            transcript = await transcripts_controller.get_by_id(input.transcript_id)

            if room and room.webhook_url and transcript:
                import httpx

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

                await emit_progress_async(
                    input.transcript_id,
                    "send_webhook",
                    "completed",
                    ctx.workflow_run_id,
                )

                return {"webhook_sent": True, "response_code": response.status_code}

        finally:
            await _close_db_connection(db)

        await emit_progress_async(
            input.transcript_id, "send_webhook", "completed", ctx.workflow_run_id
        )

        return {"webhook_sent": False, "skipped": True}

    except Exception as e:
        logger.error("[Hatchet] send_webhook failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "send_webhook", "failed", ctx.workflow_run_id
        )
        raise
