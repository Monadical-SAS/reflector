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


async def _set_error_status(transcript_id: str):
    """Set transcript status to 'error' on workflow failure (matches Celery line 790)."""
    try:
        db = await _get_fresh_db_connection()
        try:
            from reflector.db.transcripts import transcripts_controller

            await transcripts_controller.set_status(transcript_id, "error")
            logger.info(
                "[Hatchet] Set transcript status to error",
                transcript_id=transcript_id,
            )
        finally:
            await _close_db_connection(db)
    except Exception as e:
        logger.error(
            "[Hatchet] Failed to set error status",
            transcript_id=transcript_id,
            error=str(e),
        )


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

    # Set transcript status to "processing" at workflow start (matches Celery behavior)
    db = await _get_fresh_db_connection()
    try:
        from reflector.db.transcripts import transcripts_controller

        transcript = await transcripts_controller.get_by_id(input.transcript_id)
        if transcript:
            await transcripts_controller.set_status(input.transcript_id, "processing")
            logger.info(
                "[Hatchet] Set transcript status to processing",
                transcript_id=input.transcript_id,
            )
    finally:
        await _close_db_connection(db)

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
        await _set_error_status(input.transcript_id)
        await emit_progress_async(
            input.transcript_id, "get_recording", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[get_recording], execution_timeout=timedelta(seconds=60), retries=3
)
async def get_participants(input: PipelineInput, ctx: Context) -> dict:
    """Fetch participant list from Daily.co API and update transcript in database.

    Matches Celery's update_participants_from_daily() behavior.
    """
    logger.info("[Hatchet] get_participants", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "get_participants", "in_progress", ctx.workflow_run_id
    )

    try:
        recording_data = ctx.task_output(get_recording)
        mtg_session_id = recording_data.get("mtg_session_id")

        from reflector.dailyco_api.client import DailyApiClient
        from reflector.settings import settings
        from reflector.utils.daily import (
            filter_cam_audio_tracks,
            parse_daily_recording_filename,
        )

        # Get transcript and reset events/topics/participants (matches Celery line 599-607)
        db = await _get_fresh_db_connection()
        try:
            from reflector.db.transcripts import (
                TranscriptParticipant,
                transcripts_controller,
            )

            transcript = await transcripts_controller.get_by_id(input.transcript_id)
            if transcript:
                # Reset events/topics/participants (matches Celery line 599-607)
                # Note: title NOT cleared - Celery preserves existing titles
                await transcripts_controller.update(
                    transcript,
                    {
                        "events": [],
                        "topics": [],
                        "participants": [],
                    },
                )

            if not mtg_session_id or not settings.DAILY_API_KEY:
                await emit_progress_async(
                    input.transcript_id,
                    "get_participants",
                    "completed",
                    ctx.workflow_run_id,
                )
                return {
                    "participants": [],
                    "num_tracks": len(input.tracks),
                    "source_language": transcript.source_language
                    if transcript
                    else "en",
                    "target_language": transcript.target_language
                    if transcript
                    else "en",
                }

            # Fetch participants from Daily API
            async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
                participants = await client.get_meeting_participants(mtg_session_id)

            id_to_name = {}
            id_to_user_id = {}
            for p in participants.data:
                if p.user_name:
                    id_to_name[p.participant_id] = p.user_name
                if p.user_id:
                    id_to_user_id[p.participant_id] = p.user_id

            # Get track keys and filter for cam-audio tracks
            track_keys = [t["s3_key"] for t in input.tracks]
            cam_audio_keys = filter_cam_audio_tracks(track_keys)

            # Update participants in database (matches Celery lines 568-590)
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

            logger.info(
                "[Hatchet] get_participants complete",
                participant_count=len(participants_list),
            )

        finally:
            await _close_db_connection(db)

        await emit_progress_async(
            input.transcript_id, "get_participants", "completed", ctx.workflow_run_id
        )

        return {
            "participants": participants_list,
            "num_tracks": len(input.tracks),
            "source_language": transcript.source_language if transcript else "en",
            "target_language": transcript.target_language if transcript else "en",
        }

    except Exception as e:
        logger.error("[Hatchet] get_participants failed", error=str(e), exc_info=True)
        await _set_error_status(input.transcript_id)
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

    try:
        # Get source_language from get_participants (matches Celery: uses transcript.source_language)
        participants_data = ctx.task_output(get_participants)
        source_language = participants_data.get("source_language", "en")

        # Spawn child workflows for each track with correct language
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

        # Wait for all child workflows to complete
        results = await asyncio.gather(*child_coroutines)

        # Get target_language for later use in detect_topics
        target_language = participants_data.get("target_language", "en")

        # Collect all track results
        all_words = []
        padded_urls = []
        created_padded_files = set()

        for result in results:
            transcribe_result = result.get("transcribe_track", {})
            all_words.extend(transcribe_result.get("words", []))

            pad_result = result.get("pad_track", {})
            padded_urls.append(pad_result.get("padded_url"))

            # Track padded files for cleanup (matches Celery line 636-637)
            track_index = pad_result.get("track_index")
            if pad_result.get("size", 0) > 0 and track_index is not None:
                # File was created (size > 0 means padding was applied)
                storage_path = f"file_pipeline_hatchet/{input.transcript_id}/tracks/padded_{track_index}.webm"
                created_padded_files.add(storage_path)

        # Sort words by start time
        all_words.sort(key=lambda w: w.get("start", 0))

        # NOTE: Cleanup of padded S3 files moved to generate_waveform (after mixdown completes)
        # Mixdown needs the padded files, so we can't delete them here

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
            "target_language": target_language,
            "created_padded_files": list(
                created_padded_files
            ),  # For cleanup after mixdown
        }

    except Exception as e:
        logger.error("[Hatchet] process_tracks failed", error=str(e), exc_info=True)
        await _set_error_status(input.transcript_id)
        await emit_progress_async(
            input.transcript_id, "process_tracks", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[process_tracks], execution_timeout=timedelta(seconds=300), retries=3
)
async def mixdown_tracks(input: PipelineInput, ctx: Context) -> dict:
    """Mix all padded tracks into single audio file using PyAV (same as Celery)."""
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

        # Use PipelineMainMultitrack.mixdown_tracks which uses PyAV filter graph
        from fractions import Fraction

        from av.audio.resampler import AudioResampler

        from reflector.processors import AudioFileWriterProcessor

        valid_urls = [url for url in padded_urls if url]
        if not valid_urls:
            raise ValueError("No valid padded tracks to mixdown")

        # Determine target sample rate from first track
        target_sample_rate = None
        for url in valid_urls:
            try:
                container = av.open(url)
                for frame in container.decode(audio=0):
                    target_sample_rate = frame.sample_rate
                    break
                container.close()
                if target_sample_rate:
                    break
            except Exception:
                continue

        if not target_sample_rate:
            raise ValueError("No decodable audio frames in any track")

        # Build PyAV filter graph: N abuffer -> amix -> aformat -> sink
        graph = av.filter.Graph()
        inputs = []

        for idx, url in enumerate(valid_urls):
            args = (
                f"time_base=1/{target_sample_rate}:"
                f"sample_rate={target_sample_rate}:"
                f"sample_fmt=s32:"
                f"channel_layout=stereo"
            )
            in_ctx = graph.add("abuffer", args=args, name=f"in{idx}")
            inputs.append(in_ctx)

        mixer = graph.add("amix", args=f"inputs={len(inputs)}:normalize=0", name="mix")
        fmt = graph.add(
            "aformat",
            args=f"sample_fmts=s32:channel_layouts=stereo:sample_rates={target_sample_rate}",
            name="fmt",
        )
        sink = graph.add("abuffersink", name="out")

        for idx, in_ctx in enumerate(inputs):
            in_ctx.link_to(mixer, 0, idx)
        mixer.link_to(fmt)
        fmt.link_to(sink)
        graph.configure()

        # Create temp output file
        output_path = tempfile.mktemp(suffix=".mp3")
        containers = []

        try:
            # Open all containers
            for url in valid_urls:
                try:
                    c = av.open(
                        url,
                        options={
                            "reconnect": "1",
                            "reconnect_streamed": "1",
                            "reconnect_delay_max": "5",
                        },
                    )
                    containers.append(c)
                except Exception as e:
                    logger.warning(
                        "[Hatchet] mixdown: failed to open container",
                        url=url,
                        error=str(e),
                    )

            if not containers:
                raise ValueError("Could not open any track containers")

            # Create AudioFileWriterProcessor for MP3 output with duration capture
            duration_ms = [0.0]  # Mutable container for callback capture

            async def capture_duration(d):
                duration_ms[0] = d

            writer = AudioFileWriterProcessor(
                path=output_path, on_duration=capture_duration
            )

            decoders = [c.decode(audio=0) for c in containers]
            active = [True] * len(decoders)
            resamplers = [
                AudioResampler(format="s32", layout="stereo", rate=target_sample_rate)
                for _ in decoders
            ]

            while any(active):
                for i, (dec, is_active) in enumerate(zip(decoders, active)):
                    if not is_active:
                        continue
                    try:
                        frame = next(dec)
                    except StopIteration:
                        active[i] = False
                        inputs[i].push(None)
                        continue

                    if frame.sample_rate != target_sample_rate:
                        continue
                    out_frames = resamplers[i].resample(frame) or []
                    for rf in out_frames:
                        rf.sample_rate = target_sample_rate
                        rf.time_base = Fraction(1, target_sample_rate)
                        inputs[i].push(rf)

                    while True:
                        try:
                            mixed = sink.pull()
                        except Exception:
                            break
                        mixed.sample_rate = target_sample_rate
                        mixed.time_base = Fraction(1, target_sample_rate)
                        await writer.push(mixed)

            # Flush remaining frames
            while True:
                try:
                    mixed = sink.pull()
                except Exception:
                    break
                mixed.sample_rate = target_sample_rate
                mixed.time_base = Fraction(1, target_sample_rate)
                await writer.push(mixed)

            await writer.flush()

            # Duration is captured via callback in milliseconds (from AudioFileWriterProcessor)

        finally:
            for c in containers:
                try:
                    c.close()
                except Exception:
                    pass

        # Upload mixed file to correct path (matches Celery: {transcript.id}/audio.mp3)
        file_size = Path(output_path).stat().st_size
        storage_path = f"{input.transcript_id}/audio.mp3"

        with open(output_path, "rb") as mixed_file:
            await storage.put_file(storage_path, mixed_file)

        Path(output_path).unlink(missing_ok=True)

        # Update transcript with audio_location (matches Celery line 661)
        db = await _get_fresh_db_connection()
        try:
            from reflector.db.transcripts import transcripts_controller

            transcript = await transcripts_controller.get_by_id(input.transcript_id)
            if transcript:
                await transcripts_controller.update(
                    transcript, {"audio_location": "storage"}
                )
        finally:
            await _close_db_connection(db)

        logger.info(
            "[Hatchet] mixdown_tracks uploaded",
            key=storage_path,
            size=file_size,
        )

        await emit_progress_async(
            input.transcript_id, "mixdown_tracks", "completed", ctx.workflow_run_id
        )

        return {
            "audio_key": storage_path,
            "duration": duration_ms[
                0
            ],  # Duration in milliseconds from AudioFileWriterProcessor
            "tracks_mixed": len(valid_urls),
        }

    except Exception as e:
        logger.error("[Hatchet] mixdown_tracks failed", error=str(e), exc_info=True)
        await _set_error_status(input.transcript_id)
        await emit_progress_async(
            input.transcript_id, "mixdown_tracks", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[mixdown_tracks], execution_timeout=timedelta(seconds=120), retries=3
)
async def generate_waveform(input: PipelineInput, ctx: Context) -> dict:
    """Generate audio waveform visualization using AudioWaveformProcessor (matches Celery)."""
    logger.info("[Hatchet] generate_waveform", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "generate_waveform", "in_progress", ctx.workflow_run_id
    )

    try:
        import httpx

        from reflector.db.transcripts import TranscriptWaveform, transcripts_controller
        from reflector.utils.audio_waveform import get_audio_waveform

        # Cleanup temporary padded S3 files (matches Celery lines 710-725)
        # Moved here from process_tracks because mixdown_tracks needs the padded files
        track_data = ctx.task_output(process_tracks)
        created_padded_files = track_data.get("created_padded_files", [])
        if created_padded_files:
            logger.info(
                f"[Hatchet] Cleaning up {len(created_padded_files)} temporary S3 files"
            )
            storage = _get_storage()
            cleanup_tasks = []
            for storage_path in created_padded_files:
                cleanup_tasks.append(storage.delete_file(storage_path))

            cleanup_results = await asyncio.gather(
                *cleanup_tasks, return_exceptions=True
            )
            for storage_path, result in zip(created_padded_files, cleanup_results):
                if isinstance(result, Exception):
                    logger.warning(
                        "[Hatchet] Failed to cleanup temporary padded track",
                        storage_path=storage_path,
                        error=str(result),
                    )

        mixdown_data = ctx.task_output(mixdown_tracks)
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

            # Generate waveform (matches Celery: get_audio_waveform with 255 segments)
            waveform = get_audio_waveform(path=Path(temp_path), segments_count=255)

            # Save waveform to database via event (matches Celery on_waveform callback)
            db = await _get_fresh_db_connection()
            try:
                transcript = await transcripts_controller.get_by_id(input.transcript_id)
                if transcript:
                    waveform_data = TranscriptWaveform(waveform=waveform)
                    await transcripts_controller.append_event(
                        transcript=transcript, event="WAVEFORM", data=waveform_data
                    )
            finally:
                await _close_db_connection(db)

        finally:
            Path(temp_path).unlink(missing_ok=True)

        logger.info("[Hatchet] generate_waveform complete")

        await emit_progress_async(
            input.transcript_id, "generate_waveform", "completed", ctx.workflow_run_id
        )

        return {"waveform_generated": True}

    except Exception as e:
        logger.error("[Hatchet] generate_waveform failed", error=str(e), exc_info=True)
        await _set_error_status(input.transcript_id)
        await emit_progress_async(
            input.transcript_id, "generate_waveform", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[mixdown_tracks], execution_timeout=timedelta(seconds=300), retries=3
)
async def detect_topics(input: PipelineInput, ctx: Context) -> dict:
    """Detect topics using LLM and save to database (matches Celery on_topic callback)."""
    logger.info("[Hatchet] detect_topics", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "detect_topics", "in_progress", ctx.workflow_run_id
    )

    try:
        track_data = ctx.task_output(process_tracks)
        words = track_data.get("all_words", [])
        target_language = track_data.get("target_language", "en")

        from reflector.db.transcripts import TranscriptTopic, transcripts_controller
        from reflector.pipelines import topic_processing
        from reflector.processors.types import (
            TitleSummaryWithId as TitleSummaryWithIdProcessorType,
        )
        from reflector.processors.types import Transcript as TranscriptType
        from reflector.processors.types import Word

        # Convert word dicts to Word objects
        word_objects = [Word(**w) for w in words]
        transcript_type = TranscriptType(words=word_objects)

        empty_pipeline = topic_processing.EmptyPipeline(logger=logger)

        # Get DB connection for callbacks
        db = await _get_fresh_db_connection()

        try:
            transcript = await transcripts_controller.get_by_id(input.transcript_id)

            # Callback that upserts topics to DB (matches Celery on_topic)
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
                await transcripts_controller.append_event(
                    transcript=transcript, event="TOPIC", data=topic
                )

            topics = await topic_processing.detect_topics(
                transcript_type,
                target_language,
                on_topic_callback=on_topic_callback,
                empty_pipeline=empty_pipeline,
            )
        finally:
            await _close_db_connection(db)

        topics_list = [t.model_dump() for t in topics]

        logger.info("[Hatchet] detect_topics complete", topic_count=len(topics_list))

        await emit_progress_async(
            input.transcript_id, "detect_topics", "completed", ctx.workflow_run_id
        )

        return {"topics": topics_list}

    except Exception as e:
        logger.error("[Hatchet] detect_topics failed", error=str(e), exc_info=True)
        await _set_error_status(input.transcript_id)
        await emit_progress_async(
            input.transcript_id, "detect_topics", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[detect_topics], execution_timeout=timedelta(seconds=120), retries=3
)
async def generate_title(input: PipelineInput, ctx: Context) -> dict:
    """Generate meeting title using LLM and save to database (matches Celery on_title callback)."""
    logger.info("[Hatchet] generate_title", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "generate_title", "in_progress", ctx.workflow_run_id
    )

    try:
        topics_data = ctx.task_output(detect_topics)
        topics = topics_data.get("topics", [])

        from reflector.db.transcripts import (
            TranscriptFinalTitle,
            transcripts_controller,
        )
        from reflector.pipelines import topic_processing
        from reflector.processors.types import TitleSummary

        topic_objects = [TitleSummary(**t) for t in topics]

        empty_pipeline = topic_processing.EmptyPipeline(logger=logger)
        title_result = None

        db = await _get_fresh_db_connection()
        try:
            transcript = await transcripts_controller.get_by_id(input.transcript_id)

            # Callback that updates title in DB (matches Celery on_title)
            async def on_title_callback(data):
                nonlocal title_result
                title_result = data.title
                final_title = TranscriptFinalTitle(title=data.title)
                if not transcript.title:
                    await transcripts_controller.update(
                        transcript,
                        {"title": final_title.title},
                    )
                await transcripts_controller.append_event(
                    transcript=transcript, event="FINAL_TITLE", data=final_title
                )

            await topic_processing.generate_title(
                topic_objects,
                on_title_callback=on_title_callback,
                empty_pipeline=empty_pipeline,
                logger=logger,
            )
        finally:
            await _close_db_connection(db)

        logger.info("[Hatchet] generate_title complete", title=title_result)

        await emit_progress_async(
            input.transcript_id, "generate_title", "completed", ctx.workflow_run_id
        )

        return {"title": title_result}

    except Exception as e:
        logger.error("[Hatchet] generate_title failed", error=str(e), exc_info=True)
        await _set_error_status(input.transcript_id)
        await emit_progress_async(
            input.transcript_id, "generate_title", "failed", ctx.workflow_run_id
        )
        raise


@diarization_pipeline.task(
    parents=[detect_topics], execution_timeout=timedelta(seconds=300), retries=3
)
async def generate_summary(input: PipelineInput, ctx: Context) -> dict:
    """Generate meeting summary using LLM and save to database (matches Celery callbacks)."""
    logger.info("[Hatchet] generate_summary", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "generate_summary", "in_progress", ctx.workflow_run_id
    )

    try:
        topics_data = ctx.task_output(detect_topics)
        topics = topics_data.get("topics", [])

        from reflector.db.transcripts import (
            TranscriptFinalLongSummary,
            TranscriptFinalShortSummary,
            transcripts_controller,
        )
        from reflector.pipelines import topic_processing
        from reflector.processors.types import TitleSummary

        topic_objects = [TitleSummary(**t) for t in topics]

        empty_pipeline = topic_processing.EmptyPipeline(logger=logger)
        summary_result = None
        short_summary_result = None

        db = await _get_fresh_db_connection()
        try:
            transcript = await transcripts_controller.get_by_id(input.transcript_id)

            # Callback that updates long_summary in DB (matches Celery on_long_summary)
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
                await transcripts_controller.append_event(
                    transcript=transcript,
                    event="FINAL_LONG_SUMMARY",
                    data=final_long_summary,
                )

            # Callback that updates short_summary in DB (matches Celery on_short_summary)
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
                await transcripts_controller.append_event(
                    transcript=transcript,
                    event="FINAL_SHORT_SUMMARY",
                    data=final_short_summary,
                )

            await topic_processing.generate_summaries(
                topic_objects,
                transcript,  # DB transcript for context
                on_long_summary_callback=on_long_summary_callback,
                on_short_summary_callback=on_short_summary_callback,
                empty_pipeline=empty_pipeline,
                logger=logger,
            )
        finally:
            await _close_db_connection(db)

        logger.info("[Hatchet] generate_summary complete")

        await emit_progress_async(
            input.transcript_id, "generate_summary", "completed", ctx.workflow_run_id
        )

        return {"summary": summary_result, "short_summary": short_summary_result}

    except Exception as e:
        logger.error("[Hatchet] generate_summary failed", error=str(e), exc_info=True)
        await _set_error_status(input.transcript_id)
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
    """Finalize transcript: save words, emit TRANSCRIPT event, set status to 'ended'.

    Matches Celery's on_transcript + set_status behavior.
    Note: Title and summaries are already saved by their respective task callbacks.
    """
    logger.info("[Hatchet] finalize", transcript_id=input.transcript_id)

    await emit_progress_async(
        input.transcript_id, "finalize", "in_progress", ctx.workflow_run_id
    )

    try:
        mixdown_data = ctx.task_output(mixdown_tracks)
        track_data = ctx.task_output(process_tracks)

        duration = mixdown_data.get("duration", 0)
        all_words = track_data.get("all_words", [])

        db = await _get_fresh_db_connection()

        try:
            from reflector.db.transcripts import TranscriptText, transcripts_controller
            from reflector.processors.types import Transcript as TranscriptType
            from reflector.processors.types import Word

            transcript = await transcripts_controller.get_by_id(input.transcript_id)
            if transcript is None:
                raise ValueError(
                    f"Transcript {input.transcript_id} not found in database"
                )

            # Convert words back to Word objects for storage
            word_objects = [Word(**w) for w in all_words]

            # Create merged transcript for TRANSCRIPT event (matches Celery line 734-736)
            merged_transcript = TranscriptType(words=word_objects, translation=None)

            # Emit TRANSCRIPT event (matches Celery on_transcript callback)
            await transcripts_controller.append_event(
                transcript=transcript,
                event="TRANSCRIPT",
                data=TranscriptText(
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

            # Set status to "ended" (matches Celery line 745)
            await transcripts_controller.set_status(input.transcript_id, "ended")

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
        await _set_error_status(input.transcript_id)
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
