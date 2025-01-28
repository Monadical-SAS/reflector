import json
import os
from datetime import datetime
from urllib.parse import unquote

import av
import boto3
import structlog
from celery import shared_task
from celery.utils.log import get_task_logger
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import rooms_controller
from reflector.db.transcripts import SourceKind, transcripts_controller
from reflector.pipelines.main_live_pipeline import asynctask, task_pipeline_process
from reflector.settings import settings
from reflector.whereby import get_room_sessions

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


@shared_task
@asynctask
async def process_recording(bucket_name: str, object_key: str):
    logger.info("Processing recording: %s/%s", bucket_name, object_key)

    # extract a guid from the object key
    room_name = f"/{object_key[:36]}"
    meeting = await meetings_controller.get_by_room_name(room_name)
    room = await rooms_controller.get_by_id(meeting.room_id)

    transcript = await transcripts_controller.add(
        "",
        source_kind=SourceKind.ROOM,
        source_language="en",
        target_language="en",
        user_id=room.user_id,
        meeting_id=meeting.id,
        share_mode="public",
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

    task_pipeline_process.delay(transcript_id=transcript.id)


@shared_task
@asynctask
async def process_meetings():
    logger.info("Processing meetings")
    meetings = await meetings_controller.get_all_active()
    for meeting in meetings:
        is_active = False
        if meeting.end_date > datetime.utcnow():
            response = await get_room_sessions(meeting.room_name)
            room_sessions = response.get("results", [])
            is_active = not room_sessions or any(
                rs["endedAt"] is None for rs in room_sessions
            )
        if not is_active:
            await meetings_controller.update_meeting(meeting.id, is_active=False)
            logger.info("Meeting %s is deactivated", meeting.id)

    logger.info("Processed meetings")
