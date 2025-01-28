from datetime import datetime

import httpx
from reflector.db.rooms import Room
from reflector.settings import settings

HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": f"Bearer {settings.WHEREBY_API_KEY}",
}
TIMEOUT = 10  # seconds


async def create_meeting(room_name_prefix: str, end_date: datetime, room: Room):
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
                "bucket": settings.AWS_WHEREBY_S3_BUCKET,
                "accessKeyId": settings.AWS_WHEREBY_ACCESS_KEY_ID,
                "accessKeySecret": settings.AWS_WHEREBY_ACCESS_KEY_SECRET,
                "fileFormat": "mp4",
            },
            "startTrigger": room.recording_trigger,
        },
        "fields": ["hostRoomUrl"],
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.WHEREBY_API_URL}/meetings",
            headers=HEADERS,
            json=data,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


async def get_room_sessions(room_name: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.WHEREBY_API_URL}/insights/room-sessions?roomName={room_name}",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
