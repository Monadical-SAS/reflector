from datetime import timedelta
from urllib.parse import urlparse

import httpx

from reflector.db.rooms import rooms_controller
from reflector.db.transcripts import Transcript, transcripts_controller
from reflector.settings import settings


class InvalidMessageError(Exception):
    pass


def _zulip_client() -> httpx.AsyncClient:
    headers = {}
    if settings.ZULIP_HOST_HEADER:
        headers["Host"] = settings.ZULIP_HOST_HEADER
    return httpx.AsyncClient(verify=False, headers=headers)


async def get_zulip_topics(stream_id: int) -> list[dict]:
    try:
        async with _zulip_client() as client:
            response = await client.get(
                f"https://{settings.ZULIP_REALM}/api/v1/users/me/{stream_id}/topics",
                auth=(settings.ZULIP_BOT_EMAIL, settings.ZULIP_API_KEY),
            )

            response.raise_for_status()

            return response.json().get("topics", [])
    except httpx.RequestError as error:
        raise Exception(f"Failed to get topics: {error}")


async def get_zulip_streams() -> list[dict]:
    try:
        async with _zulip_client() as client:
            response = await client.get(
                f"https://{settings.ZULIP_REALM}/api/v1/streams",
                auth=(settings.ZULIP_BOT_EMAIL, settings.ZULIP_API_KEY),
            )

            response.raise_for_status()

            return response.json().get("streams", [])
    except httpx.RequestError as error:
        raise Exception(f"Failed to get streams: {error}")


async def send_message_to_zulip(stream: str, topic: str, content: str):
    try:
        async with _zulip_client() as client:
            response = await client.post(
                f"https://{settings.ZULIP_REALM}/api/v1/messages",
                data={
                    "type": "stream",
                    "to": stream,
                    "topic": topic,
                    "content": content,
                },
                auth=(settings.ZULIP_BOT_EMAIL, settings.ZULIP_API_KEY),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            response.raise_for_status()

            return response.json()
    except httpx.RequestError as error:
        raise Exception(f"Failed to send message to Zulip: {error}")


async def update_zulip_message(message_id: int, stream: str, topic: str, content: str):
    try:
        async with _zulip_client() as client:
            response = await client.patch(
                f"https://{settings.ZULIP_REALM}/api/v1/messages/{message_id}",
                data={
                    "topic": topic,
                    "content": content,
                },
                auth=(settings.ZULIP_BOT_EMAIL, settings.ZULIP_API_KEY),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if (
                response.status_code == 400
                and response.json()["msg"] == "Invalid message(s)"
            ):
                raise InvalidMessageError(f"There is no message with id: {message_id}")

            response.raise_for_status()

            return response.json()
    except httpx.RequestError as error:
        raise Exception(f"Failed to update Zulip message: {error}")


async def delete_zulip_message(message_id: int):
    try:
        async with _zulip_client() as client:
            response = await client.delete(
                f"https://{settings.ZULIP_REALM}/api/v1/messages/{message_id}",
                auth=(settings.ZULIP_BOT_EMAIL, settings.ZULIP_API_KEY),
            )

            if (
                response.status_code == 400
                and response.json()["msg"] == "Invalid message(s)"
            ):
                raise InvalidMessageError(f"There is no message with id: {message_id}")

            response.raise_for_status()

            return response.json()
    except httpx.RequestError as error:
        raise Exception(f"Failed to delete Zulip message: {error}")


def get_zulip_message(transcript: Transcript, include_topics: bool):
    transcript_url = f"{settings.UI_BASE_URL}/transcripts/{transcript.id}"

    header_text = f"# Reflector – {transcript.title or 'Unnamed recording'}\n\n"
    header_text += f"**Date**: <time:{transcript.created_at.isoformat()}>\n"
    header_text += f"**Link**: [{extract_domain(transcript_url)}]({transcript_url})\n"
    header_text += f"**Duration**: {format_time_ms(transcript.duration)}\n\n"

    topic_text = ""

    if include_topics and transcript.topics:
        topic_text = "```spoiler Topics\n"
        for topic in transcript.topics:
            topic_text += f"1. [{format_time(topic.timestamp)}] {topic.title}\n"
        topic_text += "```\n\n"

    summary = "```spoiler Summary\n"
    summary += transcript.long_summary or "No summary available"
    summary += "\n```\n\n"

    message = header_text + summary + topic_text + "-----\n"
    return message


async def post_transcript_notification(transcript: Transcript) -> int | None:
    """Post or update transcript notification in Zulip.

    Uses transcript.room_id directly (Hatchet flow).
    Celery's pipeline_post_to_zulip uses recording→meeting→room path instead.
    DUPLICATION NOTE: This function will stay when we use Celery no more, and Celery one will be removed.
    """
    if not transcript.room_id:
        return None

    room = await rooms_controller.get_by_id(transcript.room_id)
    if not room or not room.zulip_stream or not room.zulip_auto_post:
        return None

    message = get_zulip_message(transcript=transcript, include_topics=True)
    message_updated = False

    if transcript.zulip_message_id:
        try:
            await update_zulip_message(
                transcript.zulip_message_id,
                room.zulip_stream,
                room.zulip_topic,
                message,
            )
            message_updated = True
        except Exception:
            pass

    if not message_updated:
        response = await send_message_to_zulip(
            room.zulip_stream, room.zulip_topic, message
        )
        message_id = response.get("id")
        if message_id:
            await transcripts_controller.update(
                transcript, {"zulip_message_id": message_id}
            )
        return message_id

    return transcript.zulip_message_id


def extract_domain(url: str) -> str:
    return urlparse(url).netloc


def format_time_ms(milliseconds: float) -> str:
    return format_time(milliseconds // 1000)


def format_time(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    time = str(td - timedelta(microseconds=td.microseconds))

    return time[2:] if time.startswith("0:") else time
