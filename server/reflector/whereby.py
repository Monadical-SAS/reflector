from datetime import datetime

import httpx
from reflector.settings import settings


async def create_meeting(
    room_name_prefix: str, start_date: datetime, end_date: datetime
):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {settings.WHEREBY_API_KEY}",
    }
    data = {
        "templateType": "viewerMode",
        "isLocked": False,
        "roomNamePrefix": room_name_prefix,
        "roomNamePattern": "uuid",
        "roomMode": "normal",
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "recording": {
            "type": "cloud",
            "destination": {
                "provider": "s3",
                "bucket": settings.AWS_WHEREBY_S3_BUCKET,
                "accessKeyId": settings.AWS_WHEREBY_ACCESS_KEY_ID,
                "accessKeySecret": settings.AWS_WHEREBY_ACCESS_KEY_SECRET,
                "fileFormat": "mp4",
            },
            "startTrigger": "automatic-2nd-participant",
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.WHEREBY_API_URL, headers=headers, json=data, timeout=10
        )
        response.raise_for_status()
        return response.json()
