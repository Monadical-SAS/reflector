import logging
from datetime import datetime

import httpx

from reflector.db.rooms import Room
from reflector.settings import settings
from reflector.utils.string import parse_non_empty_string

logger = logging.getLogger(__name__)


def _get_headers():
    api_key = parse_non_empty_string(
        settings.WHEREBY_API_KEY, "WHEREBY_API_KEY value is required."
    )
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {api_key}",
    }


TIMEOUT = 10  # seconds


def _get_whereby_s3_auth():
    errors = []
    try:
        bucket_name = parse_non_empty_string(
            settings.RECORDING_STORAGE_AWS_BUCKET_NAME,
            "RECORDING_STORAGE_AWS_BUCKET_NAME value is required.",
        )
    except Exception as e:
        errors.append(e)
    try:
        key_id = parse_non_empty_string(
            settings.AWS_WHEREBY_ACCESS_KEY_ID,
            "AWS_WHEREBY_ACCESS_KEY_ID value is required.",
        )
    except Exception as e:
        errors.append(e)
    try:
        key_secret = parse_non_empty_string(
            settings.AWS_WHEREBY_ACCESS_KEY_SECRET,
            "AWS_WHEREBY_ACCESS_KEY_SECRET value is required.",
        )
    except Exception as e:
        errors.append(e)
    if len(errors) > 0:
        raise Exception(
            f"Failed to get Whereby auth settings: {', '.join(str(e) for e in errors)}"
        )
    return bucket_name, key_id, key_secret


async def create_meeting(room_name_prefix: str, end_date: datetime, room: Room):
    s3_bucket_name, s3_key_id, s3_key_secret = _get_whereby_s3_auth()
    data = {
        "isLocked": room.is_locked,
        "roomNamePrefix": room_name_prefix,
        "roomNamePattern": "uuid",
        "roomMode": room.room_mode,
        "endDate": end_date.isoformat(),
        "recording": {
            "type": room.recording_type,
            "destination": {
                "provider": "s3",
                "bucket": s3_bucket_name,
                "accessKeyId": s3_key_id,
                "accessKeySecret": s3_key_secret,
                "fileFormat": "mp4",
            },
            "startTrigger": room.recording_trigger,
        },
        "fields": ["hostRoomUrl"],
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.WHEREBY_API_URL}/meetings",
            headers=_get_headers(),
            json=data,
            timeout=TIMEOUT,
        )
        if response.status_code == 403:
            logger.warning(
                f"Failed to create meeting: access denied on Whereby: {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def get_room_sessions(room_name: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.WHEREBY_API_URL}/insights/room-sessions?roomName={room_name}",
            headers=_get_headers(),
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


async def upload_logo(room_name: str, logo_path: str):
    async with httpx.AsyncClient() as client:
        with open(logo_path, "rb") as f:
            response = await client.put(
                f"{settings.WHEREBY_API_URL}/rooms{room_name}/theme/logo",
                headers={
                    "Authorization": f"Bearer {settings.WHEREBY_API_KEY}",
                },
                timeout=TIMEOUT,
                files={"image": f},
            )
            response.raise_for_status()
