import json
import os
import re
from datetime import datetime, timezone
from typing import List, Literal
from urllib.parse import unquote

import av
import boto3
import structlog
from celery import shared_task
from celery.utils.log import get_task_logger
from pydantic import ValidationError

from reflector.dailyco_api import FinishedRecordingResponse, RecordingResponse
from reflector.db.daily_participant_sessions import (
    DailyParticipantSession,
    daily_participant_sessions_controller,
)
from reflector.db.meetings import meetings_controller
from reflector.db.recordings import Recording, recordings_controller
from reflector.db.rooms import rooms_controller
from reflector.db.transcripts import (
    SourceKind,
    transcripts_controller,
)
from reflector.hatchet.client import HatchetClientManager
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process
from reflector.pipelines.main_live_pipeline import asynctask
from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)
from reflector.pipelines.topic_processing import EmptyPipeline
from reflector.presence.pending_joins import has_pending_joins
from reflector.processors import AudioFileWriterProcessor
from reflector.processors.audio_waveform_processor import AudioWaveformProcessor
from reflector.redis_cache import RedisAsyncLock, get_async_redis_client
from reflector.settings import settings
from reflector.storage import get_transcripts_storage
from reflector.utils.daily import (
    DailyRoomName,
    extract_base_room_name,
    filter_cam_audio_tracks,
    recording_lock_key,
)
from reflector.utils.string import NonEmptyString
from reflector.video_platforms.factory import create_platform_client
from reflector.video_platforms.whereby_utils import (
    parse_whereby_recording_filename,
    room_name_to_whereby_api_room_name,
)

logger = structlog.wrap_logger(get_task_logger(__name__))


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


# only whereby supported.
@shared_task
@asynctask
async def process_recording(bucket_name: str, object_key: str):
    logger.info("Processing recording: %s/%s", bucket_name, object_key)

    room_name_part, recorded_at = parse_whereby_recording_filename(object_key)

    # we store whereby api room names, NOT whereby room names
    room_name = room_name_to_whereby_api_room_name(room_name_part)

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

    storage = get_transcripts_storage()

    try:
        with open(upload_filename, "wb") as f:
            await storage.stream_to_fileobj(object_key, f, bucket=bucket_name)
    except Exception:
        # Clean up partial file on stream failure
        upload_filename.unlink(missing_ok=True)
        raise

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
    recording_start_ts: int,
):
    """
    Process raw-tracks (multitrack) recording from Daily.co.
    """
    logger.info(
        "Processing multitrack recording",
        bucket=bucket_name,
        room_name=daily_room_name,
        recording_id=recording_id,
        provided_keys=len(track_keys),
        recording_start_ts=recording_start_ts,
    )

    if not track_keys:
        logger.warning("No audio track keys provided")
        return

    lock_key = recording_lock_key(recording_id)
    async with RedisAsyncLock(
        key=lock_key,
        timeout=600,  # 10min for processing (includes API calls, DB writes)
        extend_interval=60,  # Auto-extend every 60s
        skip_if_locked=True,
        blocking=False,
    ) as lock:
        if not lock.acquired:
            logger.warning(
                "Recording processing skipped - lock already held (duplicate task or concurrent worker)",
                recording_id=recording_id,
                lock_key=lock_key,
                reason="duplicate_task_or_concurrent_worker",
            )
            return

        logger.info(
            "Recording worker acquired lock - starting processing",
            recording_id=recording_id,
            lock_key=lock_key,
        )

        await _process_multitrack_recording_inner(
            bucket_name, daily_room_name, recording_id, track_keys, recording_start_ts
        )


async def _process_multitrack_recording_inner(
    bucket_name: str,
    daily_room_name: DailyRoomName,
    recording_id: str,
    track_keys: list[str],
    recording_start_ts: int,
):
    """
    Process multitrack recording (first time or reprocessing).

    For first processing (webhook/polling):
    - Uses recording_start_ts for time-based meeting matching (no instanceId available)

    For reprocessing:
    - Uses recording.meeting_id directly (already linked during first processing)
    - recording_start_ts is ignored
    """

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

    # Check if recording already exists (reprocessing path)
    recording = await recordings_controller.get_by_id(recording_id)

    if recording and recording.meeting_id:
        # Reprocessing: recording exists with meeting already linked
        meeting = await meetings_controller.get_by_id(recording.meeting_id)
        if not meeting:
            logger.error(
                "Reprocessing: meeting not found for recording - skipping",
                meeting_id=recording.meeting_id,
                recording_id=recording_id,
            )
            return

        logger.info(
            "Reprocessing: using existing recording.meeting_id",
            recording_id=recording_id,
            meeting_id=meeting.id,
            room_name=daily_room_name,
        )
    else:
        # First processing: recording doesn't exist, need time-based matching
        # (Daily.co doesn't return instanceId in API, must match by timestamp)
        recording_start = datetime.fromtimestamp(recording_start_ts, tz=timezone.utc)
        meeting = await meetings_controller.get_by_room_name_and_time(
            room_name=daily_room_name,
            recording_start=recording_start,
            time_window_hours=168,  # 1 week
        )
        if not meeting:
            logger.error(
                "Raw-tracks: no meeting found within 1-week window (time-based match) - skipping",
                recording_id=recording_id,
                room_name=daily_room_name,
                recording_start_ts=recording_start_ts,
                recording_start=recording_start.isoformat(),
            )
            return  # Skip processing, will retry on next poll
        logger.info(
            "First processing: found meeting via time-based matching",
            meeting_id=meeting.id,
            room_name=daily_room_name,
            recording_id=recording_id,
            time_delta_seconds=abs(
                (meeting.start_date - recording_start).total_seconds()
            ),
        )

    room_name_base = extract_base_room_name(daily_room_name)

    room = await rooms_controller.get_by_name(room_name_base)
    if not room:
        raise Exception(f"Room not found: {room_name_base}")

    if not recording:
        # Create recording (only happens during first processing)
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
    elif not recording.meeting_id:
        # Recording exists but meeting_id is null (failed first processing)
        # Update with meeting from time-based matching
        await recordings_controller.set_meeting_id(
            recording_id=recording.id,
            meeting_id=meeting.id,
        )
        recording.meeting_id = meeting.id
        logger.info(
            "Updated existing recording with meeting_id",
            recording_id=recording.id,
            meeting_id=meeting.id,
        )

    transcript = await transcripts_controller.get_by_recording_id(recording.id)
    if not transcript:
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

    use_celery = room and room.use_celery
    use_hatchet = not use_celery

    if use_celery:
        logger.info(
            "Room uses legacy Celery processing",
            room_id=room.id,
            transcript_id=transcript.id,
        )

    if use_hatchet:
        workflow_id = await HatchetClientManager.start_workflow(
            workflow_name="DiarizationPipeline",
            input_data={
                "recording_id": recording_id,
                "tracks": [{"s3_key": k} for k in filter_cam_audio_tracks(track_keys)],
                "bucket_name": bucket_name,
                "transcript_id": transcript.id,
                "room_id": room.id,
            },
            additional_metadata={
                "transcript_id": transcript.id,
                "recording_id": recording_id,
                "daily_recording_id": recording_id,
            },
        )
        logger.info(
            "Started Hatchet workflow",
            workflow_id=workflow_id,
            transcript_id=transcript.id,
        )

        await transcripts_controller.update(
            transcript, {"workflow_run_id": workflow_id}
        )
        return

    # Celery pipeline (runs when durable workflows disabled)
    task_pipeline_multitrack_process.delay(
        transcript_id=transcript.id,
        bucket_name=bucket_name,
        track_keys=filter_cam_audio_tracks(track_keys),
    )


@shared_task
@asynctask
async def poll_daily_recordings():
    """Poll Daily.co API for recordings and process missing ones.

    Fetches latest recordings from Daily.co API (default limit 100), compares with DB,
    and stores/queues missing recordings:
    - Cloud recordings: Store S3 key in meeting table
    - Raw-tracks recordings: Queue multitrack processing

    Acts as fallback when webhooks active, primary discovery when webhooks unavailable.

    Worker-level locking provides idempotency (see process_multitrack_recording).
    """
    bucket_name = settings.DAILYCO_STORAGE_AWS_BUCKET_NAME
    if not bucket_name:
        logger.debug(
            "DAILYCO_STORAGE_AWS_BUCKET_NAME not configured; skipping recording poll"
        )
        return

    async with create_platform_client("daily") as daily_client:
        # latest 100. TODO cursor-based state
        api_recordings: List[RecordingResponse] = await daily_client.list_recordings()

    if not api_recordings:
        logger.debug(
            "No recordings found from Daily.co API",
        )
        return

    finished_recordings: List[FinishedRecordingResponse] = []
    for rec in api_recordings:
        finished = rec.to_finished()
        if finished is None:
            logger.debug(
                "Skipping unfinished recording",
                recording_id=rec.id,
                room_name=rec.room_name,
                status=rec.status,
            )
            continue
        finished_recordings.append(finished)

    if not finished_recordings:
        logger.debug(
            "No finished recordings found from Daily.co API",
            total_api_count=len(api_recordings),
        )
        return

    # Separate cloud and raw-tracks recordings
    cloud_recordings = []
    raw_tracks_recordings = []
    for rec in finished_recordings:
        if rec.type:
            # Daily.co API returns null type - make sure this assumption stays
            # If this logs, Daily.co API changed - we can remove inference logic.
            recording_type = rec.type
            logger.warning(
                "Recording has explicit type field from Daily.co API (unexpected, API may have changed)",
                recording_id=rec.id,
                room_name=rec.room_name,
                recording_type=recording_type,
                has_s3key=bool(rec.s3key),
                tracks_count=len(rec.tracks),
            )
        else:
            # DAILY.CO API LIMITATION:
            # GET /recordings response does NOT include type field.
            # Daily.co docs mention type field exists, but API never returns it.
            # Verified: 84 recordings from Nov 2025 - Jan 2026 ALL have type=None.
            #
            # This is not a recent API change - Daily.co has never returned type.
            # Must infer from structural properties.
            #
            # Inference heuristic (reliable for finished recordings):
            # - Has tracks array → raw-tracks
            # - Has s3key but no tracks → cloud
            # - Neither → failed/incomplete recording
            if len(rec.tracks) > 0:
                recording_type = "raw-tracks"
            elif rec.s3key and len(rec.tracks) == 0:
                recording_type = "cloud"
            else:
                logger.warning(
                    "Recording has no type, no s3key, and no tracks - likely failed recording",
                    recording_id=rec.id,
                    room_name=rec.room_name,
                    status=rec.status,
                    duration=rec.duration,
                    mtg_session_id=rec.mtgSessionId,
                )
                continue

        if recording_type == "cloud":
            cloud_recordings.append(rec)
        else:
            raw_tracks_recordings.append(rec)

    logger.debug(
        "Poll results",
        total=len(finished_recordings),
        cloud=len(cloud_recordings),
        raw_tracks=len(raw_tracks_recordings),
    )

    # Process cloud recordings
    await _poll_cloud_recordings(cloud_recordings)

    # Process raw-tracks recordings
    await _poll_raw_tracks_recordings(raw_tracks_recordings, bucket_name)


async def store_cloud_recording(
    recording_id: NonEmptyString,
    room_name: NonEmptyString,
    s3_key: NonEmptyString,
    duration: int,
    start_ts: int,
    source: Literal["webhook", "polling"],
) -> bool:
    """
    Store cloud recording reference in meeting table.

    Common function for both webhook and polling code paths.
    Uses time-based matching to handle duplicate room_name values.

    Args:
        recording_id: Daily.co recording ID
        room_name: Daily.co room name
        s3_key: S3 key where recording is stored
        duration: Recording duration in seconds
        start_ts: Unix timestamp when recording started
        source: "webhook" or "polling" (for logging)

    Returns:
        True if stored, False if skipped/failed
    """
    recording_start = datetime.fromtimestamp(start_ts, tz=timezone.utc)

    meeting = await meetings_controller.get_by_room_name_and_time(
        room_name=room_name,
        recording_start=recording_start,
        time_window_hours=168,  # 1 week
    )

    if not meeting:
        logger.warning(
            f"Cloud recording ({source}): no meeting found within 1-week window",
            recording_id=recording_id,
            room_name=room_name,
            recording_start_ts=start_ts,
            recording_start=recording_start.isoformat(),
        )
        return False

    success = await meetings_controller.set_cloud_recording_if_missing(
        meeting_id=meeting.id,
        s3_key=s3_key,
        duration=duration,
    )

    if not success:
        logger.debug(
            f"Cloud recording ({source}): already set (race lost)",
            recording_id=recording_id,
            room_name=room_name,
            meeting_id=meeting.id,
        )
        return False

    logger.info(
        f"Cloud recording stored via {source} (time-based match)",
        meeting_id=meeting.id,
        recording_id=recording_id,
        s3_key=s3_key,
        duration=duration,
        time_delta_seconds=abs((meeting.start_date - recording_start).total_seconds()),
    )
    return True


async def _poll_cloud_recordings(cloud_recordings: List[FinishedRecordingResponse]):
    """
    Store cloud recordings missing from meeting table via polling.

    Uses time-based matching via store_cloud_recording().
    """
    if not cloud_recordings:
        return

    stored_count = 0
    for recording in cloud_recordings:
        # Extract S3 key from recording (cloud recordings use s3key field)
        s3_key = recording.s3key or (recording.s3.key if recording.s3 else None)
        if not s3_key:
            logger.warning(
                "Cloud recording: missing S3 key",
                recording_id=recording.id,
                room_name=recording.room_name,
            )
            continue

        stored = await store_cloud_recording(
            recording_id=recording.id,
            room_name=recording.room_name,
            s3_key=s3_key,
            duration=recording.duration,
            start_ts=recording.start_ts,
            source="polling",
        )
        if stored:
            stored_count += 1

    logger.info(
        "Cloud recording polling complete",
        total=len(cloud_recordings),
        stored=stored_count,
    )


async def _poll_raw_tracks_recordings(
    raw_tracks_recordings: List[FinishedRecordingResponse],
    bucket_name: str,
):
    """Queue raw-tracks recordings missing from DB (existing logic)."""
    if not raw_tracks_recordings:
        return

    recording_ids = [rec.id for rec in raw_tracks_recordings]
    existing_recordings = await recordings_controller.get_by_ids(recording_ids)
    existing_ids = {rec.id for rec in existing_recordings}

    missing_recordings = [
        rec for rec in raw_tracks_recordings if rec.id not in existing_ids
    ]

    if not missing_recordings:
        logger.debug(
            "All raw-tracks recordings already in DB",
            api_count=len(raw_tracks_recordings),
            existing_count=len(existing_recordings),
        )
        return

    logger.info(
        "Found raw-tracks recordings missing from DB",
        missing_count=len(missing_recordings),
        total_api_count=len(raw_tracks_recordings),
        existing_count=len(existing_recordings),
    )

    for recording in missing_recordings:
        if not recording.tracks:
            logger.warning(
                "Finished raw-tracks recording has no tracks (no audio captured)",
                recording_id=recording.id,
                room_name=recording.room_name,
            )
            continue

        track_keys = [t.s3Key for t in recording.tracks if t.type == "audio"]

        if not track_keys:
            logger.warning(
                "No audio tracks found in raw-tracks recording",
                recording_id=recording.id,
                room_name=recording.room_name,
                total_tracks=len(recording.tracks),
            )
            continue

        logger.info(
            "Queueing missing raw-tracks recording for processing",
            recording_id=recording.id,
            room_name=recording.room_name,
            track_count=len(track_keys),
        )

        process_multitrack_recording.delay(
            bucket_name=bucket_name,
            daily_room_name=recording.room_name,
            recording_id=recording.id,
            track_keys=track_keys,
            recording_start_ts=recording.start_ts,
        )


async def poll_daily_room_presence(meeting_id: str) -> None:
    """Poll Daily.co room presence and reconcile with DB sessions. New presence is added, old presence is marked as closed.
    Warning: Daily api returns only current state, so there could be missed presence updates, people who went and left the room quickly.
    Therefore, set(presences) != set(recordings) even if everyone said something. This is not a problem but should be noted."""

    async with RedisAsyncLock(
        key=f"meeting_presence_poll:{meeting_id}",
        timeout=120,
        extend_interval=30,
        skip_if_locked=True,
        blocking=False,
    ) as lock:
        if not lock.acquired:
            logger.debug(
                "Concurrent poll skipped (duplicate task)", meeting_id=meeting_id
            )
            return

        meeting = await meetings_controller.get_by_id(meeting_id)
        if not meeting:
            logger.warning("Meeting not found", meeting_id=meeting_id)
            return

        async with create_platform_client("daily") as daily_client:
            try:
                presence = await daily_client.get_room_presence(meeting.room_name)
            except Exception as e:
                logger.error(
                    "Daily.co API fetch failed",
                    meeting_id=meeting.id,
                    room_name=meeting.room_name,
                    error=str(e),
                    exc_info=True,
                )
                return

        api_participants = {p.id: p for p in presence.data}
        db_sessions = (
            await daily_participant_sessions_controller.get_all_sessions_for_meeting(
                meeting.id
            )
        )

        active_session_ids = {
            sid for sid, s in db_sessions.items() if s.left_at is None
        }
        missing_session_ids = set(api_participants.keys()) - active_session_ids
        stale_session_ids = active_session_ids - set(api_participants.keys())

        if missing_session_ids:
            missing_sessions = []
            for session_id in missing_session_ids:
                p = api_participants[session_id]
                session = DailyParticipantSession(
                    id=f"{meeting.id}:{session_id}",
                    meeting_id=meeting.id,
                    room_id=meeting.room_id,
                    session_id=session_id,
                    user_id=p.userId,
                    user_name=p.userName,
                    joined_at=datetime.fromisoformat(p.joinTime),
                    left_at=None,
                )
                missing_sessions.append(session)

            await daily_participant_sessions_controller.batch_upsert_sessions(
                missing_sessions
            )
            logger.info(
                "Sessions added",
                meeting_id=meeting.id,
                count=len(missing_sessions),
            )

        if stale_session_ids:
            composite_ids = [f"{meeting.id}:{sid}" for sid in stale_session_ids]
            await daily_participant_sessions_controller.batch_close_sessions(
                composite_ids,
                left_at=datetime.now(timezone.utc),
            )
            logger.info(
                "Stale sessions closed",
                meeting_id=meeting.id,
                count=len(composite_ids),
            )

        final_active_count = len(api_participants)
        if meeting.num_clients != final_active_count:
            await meetings_controller.update_meeting(
                meeting.id,
                num_clients=final_active_count,
            )
            logger.info(
                "num_clients updated",
                meeting_id=meeting.id,
                old_value=meeting.num_clients,
                new_value=final_active_count,
            )


@shared_task
@asynctask
async def poll_daily_room_presence_task(meeting_id: str) -> None:
    """Celery task wrapper for poll_daily_room_presence.

    Queued by webhooks or reconciliation timer.
    """
    await poll_daily_room_presence(meeting_id)


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

    meetings = await meetings_controller.get_all_active()
    logger.info(f"Processing {len(meetings)} meetings")
    current_time = datetime.now(timezone.utc)
    processed_count = 0
    skipped_count = 0
    for meeting in meetings:
        logger_ = logger.bind(meeting_id=meeting.id, room_name=meeting.room_name)
        logger_.info("Processing meeting")

        try:
            async with RedisAsyncLock(
                key=f"meeting_process_lock:{meeting.id}",
                timeout=120,
                extend_interval=30,
                skip_if_locked=True,
                blocking=False,
            ) as lock:
                if not lock.acquired:
                    logger_.debug(
                        "Meeting is being processed by another worker, skipping"
                    )
                    skipped_count += 1
                    continue

                # Process the meeting
                should_deactivate = False
                end_date = meeting.end_date
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)

                client = create_platform_client(meeting.platform)
                room_sessions = await client.get_room_sessions(meeting.room_name)

                has_active_sessions = bool(
                    room_sessions and any(s.ended_at is None for s in room_sessions)
                )
                has_had_sessions = bool(room_sessions)
                logger_.info(
                    f"has_active_sessions={has_active_sessions}, has_had_sessions={has_had_sessions}"
                )

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
                    # Check for pending joins before deactivating
                    # Users might be in the process of connecting via WebRTC
                    redis = await get_async_redis_client()
                    try:
                        if await has_pending_joins(redis, meeting.id):
                            logger_.info(
                                "Meeting has pending joins, skipping deactivation"
                            )
                            continue
                    finally:
                        await redis.aclose()

                    await meetings_controller.update_meeting(
                        meeting.id, is_active=False
                    )
                    logger_.info("Meeting is deactivated")

                processed_count += 1

        except Exception:
            logger_.error("Error processing meeting", exc_info=True)

    logger.debug(
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

        waveform_processor = AudioWaveformProcessor(
            audio_path=mp3_path,
            waveform_path=transcript.audio_waveform_filename,
        )
        waveform_processor.set_pipeline(EmptyPipeline(logger))
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
    Find recordings in Whereby S3 bucket and check if they have proper transcriptions.
    If not, requeue them for processing.

    Note: Daily.co multitrack recordings are handled by reprocess_failed_daily_recordings.
    """
    logger.info("Checking Whereby recordings that need processing or reprocessing")

    if not settings.WHEREBY_STORAGE_AWS_BUCKET_NAME:
        raise ValueError(
            "WHEREBY_STORAGE_AWS_BUCKET_NAME required for Whereby recording reprocessing. "
            "Set WHEREBY_STORAGE_AWS_BUCKET_NAME environment variable."
        )

    storage = get_transcripts_storage()
    bucket_name = settings.WHEREBY_STORAGE_AWS_BUCKET_NAME

    reprocessed_count = 0
    try:
        object_keys = await storage.list_objects(prefix="", bucket=bucket_name)

        for object_key in object_keys:
            if not object_key.endswith(".mp4"):
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


@shared_task
@asynctask
async def reprocess_failed_daily_recordings():
    """
    Find Daily.co multitrack recordings in the database and check if they have proper transcriptions.
    If not, requeue them for processing.
    """
    logger.info(
        "Checking Daily.co multitrack recordings that need processing or reprocessing"
    )

    if not settings.DAILYCO_STORAGE_AWS_BUCKET_NAME:
        logger.debug(
            "DAILYCO_STORAGE_AWS_BUCKET_NAME not configured; skipping Daily recording reprocessing"
        )
        return 0

    bucket_name = settings.DAILYCO_STORAGE_AWS_BUCKET_NAME
    reprocessed_count = 0

    try:
        multitrack_recordings = (
            await recordings_controller.get_multitrack_needing_reprocessing(bucket_name)
        )

        logger.info(
            "Found multitrack recordings needing reprocessing",
            count=len(multitrack_recordings),
            bucket=bucket_name,
        )

        for recording in multitrack_recordings:
            if not recording.meeting_id:
                logger.debug(
                    "Skipping recording without meeting_id",
                    recording_id=recording.id,
                )
                continue

            meeting = await meetings_controller.get_by_id(recording.meeting_id)
            if not meeting:
                logger.warning(
                    "Meeting not found for recording",
                    recording_id=recording.id,
                    meeting_id=recording.meeting_id,
                )
                continue

            room = None
            if meeting.room_id:
                room = await rooms_controller.get_by_id(meeting.room_id)

            transcript = None
            try:
                transcript = await transcripts_controller.get_by_recording_id(
                    recording.id
                )
            except ValidationError:
                await transcripts_controller.remove_by_recording_id(recording.id)
                logger.warning(
                    "Removed invalid transcript for recording",
                    recording_id=recording.id,
                )

            if not recording.track_keys:
                logger.warning(
                    "Recording has no track_keys, cannot reprocess",
                    recording_id=recording.id,
                )
                continue

            use_celery = room and room.use_celery
            use_hatchet = not use_celery

            if use_hatchet:
                if not transcript:
                    logger.warning(
                        "No transcript for Hatchet reprocessing, skipping",
                        recording_id=recording.id,
                    )
                    continue

                workflow_id = await HatchetClientManager.start_workflow(
                    workflow_name="DiarizationPipeline",
                    input_data={
                        "recording_id": recording.id,
                        "tracks": [
                            {"s3_key": k}
                            for k in filter_cam_audio_tracks(recording.track_keys)
                        ],
                        "bucket_name": bucket_name,
                        "transcript_id": transcript.id,
                        "room_id": room.id if room else None,
                    },
                    additional_metadata={
                        "transcript_id": transcript.id,
                        "recording_id": recording.id,
                        "reprocess": True,
                    },
                )
                await transcripts_controller.update(
                    transcript, {"workflow_run_id": workflow_id}
                )

                logger.info(
                    "Queued Daily recording for Hatchet reprocessing",
                    recording_id=recording.id,
                    workflow_id=workflow_id,
                    room_name=meeting.room_name,
                    track_count=len(recording.track_keys),
                )
            else:
                logger.info(
                    "Queueing Daily recording for Celery reprocessing",
                    recording_id=recording.id,
                    room_name=meeting.room_name,
                    track_count=len(recording.track_keys),
                    transcript_status=transcript.status if transcript else None,
                )

                # For reprocessing, pass actual recording time (though it's ignored - see _process_multitrack_recording_inner)
                # Reprocessing uses recording.meeting_id directly instead of time-based matching
                recording_start_ts = int(recording.recorded_at.timestamp())

                process_multitrack_recording.delay(
                    bucket_name=bucket_name,
                    daily_room_name=meeting.room_name,
                    recording_id=recording.id,
                    track_keys=recording.track_keys,
                    recording_start_ts=recording_start_ts,
                )

            reprocessed_count += 1

    except Exception as e:
        logger.error(
            "Error checking Daily multitrack recordings",
            error=str(e),
            exc_info=True,
        )

    logger.info(
        "Daily reprocessing complete",
        requeued_count=reprocessed_count,
    )
    return reprocessed_count


@shared_task
@asynctask
async def trigger_daily_reconciliation() -> None:
    """Daily.co pull"""
    try:
        active_meetings = await meetings_controller.get_all_active(platform="daily")
        queued_count = 0

        for meeting in active_meetings:
            try:
                poll_daily_room_presence_task.delay(meeting.id)
                queued_count += 1
            except Exception as e:
                logger.error(
                    "Failed to queue reconciliation poll",
                    meeting_id=meeting.id,
                    error=str(e),
                    exc_info=True,
                )
                raise

        if queued_count > 0:
            logger.debug(
                "Reconciliation polls queued",
                count=queued_count,
            )

    except Exception as e:
        logger.error("Reconciliation trigger failed", error=str(e), exc_info=True)
