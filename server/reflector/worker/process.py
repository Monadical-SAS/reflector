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
from reflector.db.transcripts import (
    SourceKind,
    TranscriptParticipant,
    transcripts_controller,
)
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process
from reflector.pipelines.main_live_pipeline import asynctask
from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)
from reflector.processors import AudioFileWriterProcessor
from reflector.processors.audio_waveform_processor import AudioWaveformProcessor
from reflector.redis_cache import get_redis_client
from reflector.settings import settings
from reflector.utils.daily import DailyRoomName, extract_base_room_name
from reflector.video_platforms.factory import create_platform_client
from reflector.whereby import get_room_sessions

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
                "participants": [],
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
    daily_room_name: DailyRoomName,
    recording_id: str,
    track_keys: list[str],
):
    logger.info(
        "Processing multitrack recording",
        bucket=bucket_name,
        room_name=daily_room_name,
        recording_id=recording_id,
        provided_keys=len(track_keys),
    )

    if not track_keys:
        logger.warning("No audio track keys provided")
        return

    tz = timezone.utc
    recorded_at = datetime.now(tz)
    try:
        if track_keys:
            folder = os.path.basename(os.path.dirname(track_keys[0]))
            ts_match = re.search(r"(\d{14})$", folder)
            if ts_match:
                ts = ts_match.group(1)
                recorded_at = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=tz)
    except Exception as e:
        logger.warning(
            f"Could not parse recorded_at from keys, using now() {recorded_at}",
            e,
            exc_info=True,
        )

    meeting = await meetings_controller.get_by_room_name(daily_room_name)

    room_name_base = extract_base_room_name(daily_room_name)

    room = await rooms_controller.get_by_name(room_name_base)
    if not room:
        raise Exception(f"Room not found: {room_name_base}")

    if not meeting:
        raise Exception(f"Meeting not found: {room_name_base}")

    logger.info(
        "Found existing Meeting for recording",
        meeting_id=meeting.id,
        room_name=daily_room_name,
        recording_id=recording_id,
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
                track_keys=track_keys,
            )
        )
    else:
        # Recording already exists; assume metadata was set at creation time
        pass

    transcript = await transcripts_controller.get_by_recording_id(recording.id)
    if transcript:
        await transcripts_controller.update(
            transcript,
            {
                "topics": [],
                "participants": [],
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

    try:
        daily_client = create_platform_client("daily")

        id_to_name = {}
        meeting_id = transcript.meeting_id
        if meeting_id:
            payload = await daily_client.get_meeting_participants(meeting_id)
            for p in payload.get("data", []):
                pid = p.get("participant_id")
                name = p.get("user_name")
                if pid and name:
                    id_to_name[str(pid)] = str(name)

        for idx, key in enumerate(track_keys):
            base = os.path.basename(key)
            m = re.search(r"\d{13,}-([0-9a-fA-F-]{36})-cam-audio-", base)
            participant_id = m.group(1) if m else None

            default_name = f"Speaker {idx}"
            name = id_to_name.get(participant_id, default_name)

            participant = TranscriptParticipant(
                id=participant_id, speaker=idx, name=name
            )
            await transcripts_controller.upsert_participant(transcript, participant)

    except Exception as e:
        logger.warning("Failed to map participant names", error=str(e), exc_info=True)

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
