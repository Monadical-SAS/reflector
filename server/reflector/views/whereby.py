import hmac
import json
import re
import time
from datetime import datetime
from hashlib import sha256

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from reflector.db.meetings import meetings_controller
from reflector.settings import settings

router = APIRouter()


class WherebyWebhookEvent(BaseModel):
    apiVersion: str
    id: str
    createdAt: datetime
    type: str
    data: dict


MAX_ELAPSED_TIME = 60 * 1000  # 1 minute in milliseconds


def is_webhook_event_valid(body: dict, signature: str) -> bool:
    """Validate Whereby webhook signature and timestamp."""
    if not signature:
        return False

    matches = re.match(r"t=(.*),v1=(.*)", signature)
    if not matches:
        return False

    timestamp, signature = matches.groups()

    current_time = int(time.time() * 1000)
    diff_time = current_time - int(timestamp) * 1000
    if diff_time >= MAX_ELAPSED_TIME:
        return False

    signed_payload = f"{timestamp}.{json.dumps(body, separators=(',', ':'))}"
    hmac_obj = hmac.new(
        settings.WHEREBY_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload.encode("utf-8"),
        sha256,
    )
    expected_signature = hmac_obj.hexdigest()
    try:
        return hmac.compare_digest(
            expected_signature.encode("utf-8"), signature.encode("utf-8")
        )
    except Exception:
        return False


@router.post("/whereby")
async def whereby_webhook(event: WherebyWebhookEvent, request: Request):
    if not is_webhook_event_valid(
        await request.json(), request.headers["whereby-signature"]
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    meeting = await meetings_controller.get_by_id(event.data["meetingId"])
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if event.type in ["room.client.joined", "room.client.left"]:
        await meetings_controller.update_meeting(
            meeting.id, num_clients=event.data["numClients"]
        )

    return {"status": "ok"}
