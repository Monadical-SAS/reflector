import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import unquote

import av
import boto3
import structlog
from celery import shared_task
from celery.utils.log import get_task_logger
from pydantic import ValidationError
from redis.exceptions import LockError

from reflector.db.meetings import meetings_controller
from reflector.db.recordings import Recording, recordings_controller
from reflector.db.rooms import rooms_controller
from reflector.db.transcripts import SourceKind, transcripts_controller
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process
from reflector.pipelines.main_live_pipeline import asynctask
from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)
from reflector.redis_cache import get_redis_client
from reflector.settings import settings
from reflector.whereby import get_room_sessions
from reflector.worker.daily_stub_data import get_stub_transcript_data

logger = structlog.wrap_logger(get_task_logger(__name__))


def parse_datetime_with_timezone(iso_string: str) -> datetime:
    """Parse ISO datetime string and ensure timezone awareness (defaults to UTC if naive)."""
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@shared_task
def process_messages():
    queue_url = settings.AWS_PROCESS_RECORDING_QUEUE_URL
    if not queue_url:
        logger.warning("No process recording queue url")
        return
    try:
        logger.info("Receiving messages from: %s", queue_url)
        sqs = boto3.client(
            "sqs",
            region_name=settings.TRANSCRIPT_STORAGE_AWS_REGION,
            aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
        )

        response = sqs.receive_message(
            QueueUrl=queue_url,
            AttributeNames=["SentTimestamp"],
            MaxNumberOfMessages=1,
            MessageAttributeNames=["All"],
            VisibilityTimeout=0,
            WaitTimeSeconds=0,
        )

        for message in response.get("Messages", []):
            receipt_handle = message["ReceiptHandle"]
            body = json.loads(message["Body"])

            for record in body.get("Records", []):
                if record["eventName"].startswith("ObjectCreated"):
                    bucket = record["s3"]["bucket"]["name"]
                    key = unquote(record["s3"]["object"]["key"])
                    process_recording.delay(bucket, key)

            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            logger.info("Processed and deleted message: %s", message)

    except Exception as e:
        logger.error("process_messages", error=str(e))


@shared_task
@asynctask
async def process_recording(bucket_name: str, object_key: str):
    logger.info("Processing recording: %s/%s", bucket_name, object_key)

    # extract a guid and a datetime from the object key
    room_name = f"/{object_key[:36]}"
    recorded_at = parse_datetime_with_timezone(object_key[37:57])

    meeting = await meetings_controller.get_by_room_name(room_name)
    room = await rooms_controller.get_by_id(meeting.room_id)

    recording = await recordings_controller.get_by_object_key(bucket_name, object_key)
    if not recording:
        recording = await recordings_controller.create(
            Recording(
                bucket_name=bucket_name,
                object_key=object_key,
                recorded_at=recorded_at,
                meeting_id=meeting.id,
            )
        )

    transcript = await transcripts_controller.get_by_recording_id(recording.id)
    if transcript:
        await transcripts_controller.update(
            transcript,
            {
                "topics": [],
            },
        )
    else:
        transcript = await transcripts_controller.add(
            "",
            source_kind=SourceKind.ROOM,
            source_language="en",
            target_language="en",
            user_id=room.user_id,
            recording_id=recording.id,
            share_mode="public",
            meeting_id=meeting.id,
            room_id=room.id,
        )

    _, extension = os.path.splitext(object_key)
    upload_filename = transcript.data_path / f"upload{extension}"
    upload_filename.parent.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client(
        "s3",
        region_name=settings.TRANSCRIPT_STORAGE_AWS_REGION,
        aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
    )

    with open(upload_filename, "wb") as f:
        s3.download_fileobj(bucket_name, object_key, f)

    container = av.open(upload_filename.as_posix())
    try:
        if not len(container.streams.audio):
            raise Exception("File has no audio stream")
    except Exception:
        upload_filename.unlink()
        raise
    finally:
        container.close()

    await transcripts_controller.update(transcript, {"status": "uploaded"})

    task_pipeline_file_process.delay(transcript_id=transcript.id)


@shared_task
@asynctask
async def process_multitrack_recording(
    bucket_name: str,
    room_name: str,
    recording_id: str,
    track_keys: list[str],
):
    logger.info(
        "Processing multitrack recording",
        bucket=bucket_name,
        room_name=room_name,
        recording_id=recording_id,
        provided_keys=len(track_keys),
    )

    if not track_keys:
        logger.warning("No audio track keys provided")
        return

    recorded_at = datetime.now(timezone.utc)
    try:
        if track_keys:
            folder = os.path.basename(os.path.dirname(track_keys[0]))
            ts_match = re.search(r"(\d{14})$", folder)
            if ts_match:
                ts = ts_match.group(1)
                recorded_at = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(
                    tzinfo=timezone.utc
                )
    except Exception:
        logger.warning("Could not parse recorded_at from keys, using now()")

    room_name = room_name.split("-", 1)[0]
    room = await rooms_controller.get_by_name(room_name)
    if not room:
        raise Exception(f"Room not found: {room_name}")

    meeting = await meetings_controller.create(
        id=recording_id,
        room_name=room_name,
        room_url=room.name,
        host_room_url=room.name,
        start_date=recorded_at,
        end_date=recorded_at,
        room=room,
        platform=room.platform,
    )

    recording = await recordings_controller.get_by_id(recording_id)
    if not recording:
        object_key_dir = os.path.dirname(track_keys[0]) if track_keys else ""
        recording = await recordings_controller.create(
            Recording(
                id=recording_id,
                bucket_name=bucket_name,
                object_key=object_key_dir,
                recorded_at=recorded_at,
                meeting_id=meeting.id,
            )
        )

    transcript = await transcripts_controller.get_by_recording_id(recording.id)
    if transcript:
        await transcripts_controller.update(
            transcript,
            {
                "topics": [],
            },
        )
    else:
        transcript = await transcripts_controller.add(
            "",
            source_kind=SourceKind.ROOM,
            source_language="en",
            target_language="en",
            user_id=room.user_id,
            recording_id=recording.id,
            share_mode="public",
            meeting_id=meeting.id,
            room_id=room.id,
        )

    task_pipeline_multitrack_process.delay(
        transcript_id=transcript.id,
        bucket_name=bucket_name,
        track_keys=track_keys,
    )


@shared_task
@asynctask
async def process_meetings():
    """
    Checks which meetings are still active and deactivates those that have ended.

    Deactivation logic:
    - Active sessions: Keep meeting active regardless of scheduled time
    - No active sessions:
      * Calendar meetings:
        - If previously used (had sessions): Deactivate immediately
        - If never used: Keep active until scheduled end time, then deactivate
      * On-the-fly meetings: Deactivate immediately (created when someone joins,
        so no sessions means everyone left)

    Uses distributed locking to prevent race conditions when multiple workers
    process the same meeting simultaneously.
    """
    logger.info("Processing meetings")
    meetings = await meetings_controller.get_all_active()
    current_time = datetime.now(timezone.utc)
    redis_client = get_redis_client()
    processed_count = 0
    skipped_count = 0

    for meeting in meetings:
        logger_ = logger.bind(meeting_id=meeting.id, room_name=meeting.room_name)
        lock_key = f"meeting_process_lock:{meeting.id}"
        lock = redis_client.lock(lock_key, timeout=120)

        try:
            if not lock.acquire(blocking=False):
                logger_.debug("Meeting is being processed by another worker, skipping")
                skipped_count += 1
                continue

            # Process the meeting
            should_deactivate = False
            end_date = meeting.end_date
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            # This API call could be slow, extend lock if needed
            response = await get_room_sessions(meeting.room_name)

            try:
                # Extend lock after slow operation to ensure we still hold it
                lock.extend(120, replace_ttl=True)
            except LockError:
                logger_.warning("Lost lock for meeting, skipping")
                continue

            room_sessions = response.get("results", [])
            has_active_sessions = room_sessions and any(
                rs["endedAt"] is None for rs in room_sessions
            )
            has_had_sessions = bool(room_sessions)

            if has_active_sessions:
                logger_.debug("Meeting still has active sessions, keep it")
            elif has_had_sessions:
                should_deactivate = True
                logger_.info("Meeting ended - all participants left")
            elif current_time > end_date:
                should_deactivate = True
                logger_.info(
                    "Meeting deactivated - scheduled time ended with no participants",
                )
            else:
                logger_.debug("Meeting not yet started, keep it")

            if should_deactivate:
                await meetings_controller.update_meeting(meeting.id, is_active=False)
                logger_.info("Meeting is deactivated")

            processed_count += 1

        except Exception:
            logger_.error("Error processing meeting", exc_info=True)
        finally:
            try:
                lock.release()
            except LockError:
                pass  # Lock already released or expired

    logger.info(
        "Processed meetings finished",
        processed_count=processed_count,
        skipped_count=skipped_count,
    )


async def convert_audio_and_waveform(transcript) -> None:
    """Convert WebM to MP3 and generate waveform for Daily.co recordings.

    This bypasses the full file pipeline which would overwrite stub data.
    """
    try:
        logger.info(
            "Converting audio to MP3 and generating waveform",
            transcript_id=transcript.id,
        )

        # Import processors we need
        from reflector.processors import AudioFileWriterProcessor
        from reflector.processors.audio_waveform_processor import AudioWaveformProcessor

        upload_path = transcript.data_path / "upload.webm"
        mp3_path = transcript.audio_mp3_filename

        # Convert WebM to MP3
        mp3_writer = AudioFileWriterProcessor(path=mp3_path)

        container = av.open(str(upload_path))
        for frame in container.decode(audio=0):
            await mp3_writer.push(frame)
        await mp3_writer.flush()
        container.close()

        logger.info(
            "Converted WebM to MP3",
            transcript_id=transcript.id,
            mp3_size=mp3_path.stat().st_size,
        )

        # Generate waveform
        waveform_processor = AudioWaveformProcessor(
            audio_path=mp3_path,
            waveform_path=transcript.audio_waveform_filename,
        )

        # Create minimal pipeline object for processor (matching EmptyPipeline from main_file_pipeline.py)
        class MinimalPipeline:
            def __init__(self, logger_instance):
                self.logger = logger_instance

            def get_pref(self, k, d=None):
                return d

        waveform_processor.set_pipeline(MinimalPipeline(logger))
        await waveform_processor.flush()

        logger.info(
            "Generated waveform",
            transcript_id=transcript.id,
            waveform_path=transcript.audio_waveform_filename,
        )

        # Update transcript status to ended (successful)
        await transcripts_controller.update(transcript, {"status": "ended"})

    except Exception as e:
        logger.error(
            "Failed to convert audio or generate waveform",
            transcript_id=transcript.id,
            error=str(e),
        )
        # Keep status as uploaded even if conversion fails
        pass


@shared_task
@asynctask
async def process_daily_recording(
    meeting_id: str, recording_id: str, tracks: list[dict]
) -> None:
    """Stub processor for Daily.co recordings - writes fake transcription/diarization.

    Handles webhook retries by checking if recording already exists.
    Validates track structure before processing.

    Args:
        meeting_id: Meeting ID
        recording_id: Recording ID from Daily.co webhook
        tracks: List of track dicts from Daily.co webhook
                [{type: 'audio'|'video', s3Key: str, size: int}, ...]
    """
    logger.info(
        "Processing Daily.co recording (STUB)",
        meeting_id=meeting_id,
        recording_id=recording_id,
        num_tracks=len(tracks),
    )

    # Check if recording already exists (webhook retry case)
    existing_recording = await recordings_controller.get_by_id(recording_id)
    if existing_recording:
        logger.warning(
            "Recording already exists, skipping processing (likely webhook retry)",
            recording_id=recording_id,
        )
        return

    meeting = await meetings_controller.get_by_id(meeting_id)
    if not meeting:
        raise Exception(f"Meeting {meeting_id} not found")

    room = await rooms_controller.get_by_id(meeting.room_id)

    # Validate bucket configuration
    if not settings.AWS_DAILY_S3_BUCKET:
        raise ValueError("AWS_DAILY_S3_BUCKET not configured for Daily.co processing")

    # Validate and parse tracks
    # Import at runtime to avoid circular dependency (daily.py imports from process.py)
    from reflector.views.daily import DailyTrack  # noqa: PLC0415

    try:
        validated_tracks = [DailyTrack(**t) for t in tracks]
    except Exception as e:
        logger.error(
            "Invalid track structure from Daily.co webhook",
            error=str(e),
            tracks=tracks,
        )
        raise ValueError(f"Invalid track structure: {e}")

    # Find first audio track for Recording entity
    audio_track = next((t for t in validated_tracks if t.type == "audio"), None)
    if not audio_track:
        raise Exception(f"No audio tracks found in {len(tracks)} tracks")

    # Create Recording entry
    recording = await recordings_controller.create(
        Recording(
            id=recording_id,
            bucket_name=settings.AWS_DAILY_S3_BUCKET,
            object_key=audio_track.s3Key,
            recorded_at=datetime.now(timezone.utc),
            meeting_id=meeting.id,
            status="completed",
        )
    )

    logger.info(
        "Created recording",
        recording_id=recording.id,
        s3_key=audio_track.s3Key,
    )

    # Create Transcript entry
    transcript = await transcripts_controller.add(
        "",
        source_kind=SourceKind.ROOM,
        source_language="en",
        target_language="en",
        user_id=room.user_id,
        recording_id=recording.id,
        share_mode="public",
        meeting_id=meeting.id,
        room_id=room.id,
    )

    logger.info("Created transcript", transcript_id=transcript.id)

    # Download audio file from Daily.co S3 for playback
    upload_filename = transcript.data_path / "upload.webm"
    upload_filename.parent.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client(
        "s3",
        region_name=settings.TRANSCRIPT_STORAGE_AWS_REGION,
        aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
    )

    try:
        logger.info(
            "Downloading audio from Daily.co S3",
            bucket=settings.AWS_DAILY_S3_BUCKET,
            key=audio_track.s3Key,
        )
        with open(upload_filename, "wb") as f:
            s3.download_fileobj(settings.AWS_DAILY_S3_BUCKET, audio_track.s3Key, f)

        # Validate audio file
        container = av.open(upload_filename.as_posix())
        try:
            if not len(container.streams.audio):
                raise Exception("File has no audio stream")
        finally:
            container.close()

        logger.info("Audio file downloaded and validated", file=str(upload_filename))
    except Exception as e:
        logger.error(
            "Failed to download or validate audio file",
            error=str(e),
            bucket=settings.AWS_DAILY_S3_BUCKET,
            key=audio_track.s3Key,
        )
        # Continue with stub data even if audio download fails
        pass

    # Generate fake data
    stub_data = get_stub_transcript_data()

    # Update transcript with fake data
    await transcripts_controller.update(
        transcript,
        {
            "topics": stub_data["topics"],
            "participants": stub_data["participants"],
            "title": stub_data["title"],
            "short_summary": stub_data["short_summary"],
            "long_summary": stub_data["long_summary"],
            "duration": stub_data["duration"],
            "status": "uploaded" if upload_filename.exists() else "ended",
        },
    )

    logger.info(
        "Daily.co recording processed (STUB)",
        transcript_id=transcript.id,
        duration=stub_data["duration"],
        num_topics=len(stub_data["topics"]),
        has_audio=upload_filename.exists(),
    )

    # Convert WebM to MP3 and generate waveform without full pipeline
    # (full pipeline would overwrite our stub transcription data)
    if upload_filename.exists():
        await convert_audio_and_waveform(transcript)


@shared_task
@asynctask
async def reprocess_failed_recordings():
    """
    Find recordings in the S3 bucket and check if they have proper transcriptions.
    If not, requeue them for processing.
    """
    logger.info("Checking for recordings that need processing or reprocessing")

    s3 = boto3.client(
        "s3",
        region_name=settings.TRANSCRIPT_STORAGE_AWS_REGION,
        aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
    )

    reprocessed_count = 0
    try:
        paginator = s3.get_paginator("list_objects_v2")
        bucket_name = settings.RECORDING_STORAGE_AWS_BUCKET_NAME
        pages = paginator.paginate(Bucket=bucket_name)

        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                object_key = obj["Key"]

                if not (object_key.endswith(".mp4")):
                    continue

                recording = await recordings_controller.get_by_object_key(
                    bucket_name, object_key
                )
                if not recording:
                    logger.info(f"Queueing recording for processing: {object_key}")
                    process_recording.delay(bucket_name, object_key)
                    reprocessed_count += 1
                    continue

                transcript = None
                try:
                    transcript = await transcripts_controller.get_by_recording_id(
                        recording.id
                    )
                except ValidationError:
                    await transcripts_controller.remove_by_recording_id(recording.id)
                    logger.warning(
                        f"Removed invalid transcript for recording: {recording.id}"
                    )

                if transcript is None or transcript.status == "error":
                    logger.info(f"Queueing recording for processing: {object_key}")
                    process_recording.delay(bucket_name, object_key)
                    reprocessed_count += 1

    except Exception as e:
        logger.error(f"Error checking S3 bucket: {str(e)}")

    logger.info(f"Reprocessing complete. Requeued {reprocessed_count} recordings")
    return reprocessed_count
