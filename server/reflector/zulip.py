from datetime import timedelta
from urllib.parse import urlparse

import requests
from reflector.db.transcripts import Transcript
from reflector.settings import settings


class InvalidMessageError(Exception):
    pass


def send_message_to_zulip(stream: str, topic: str, content: str):
    try:
        response = requests.post(
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
    except requests.RequestException as error:
        raise Exception(f"Failed to send message to Zulip: {error}")


def update_zulip_message(message_id: int, stream: str, topic: str, content: str):
    try:
        response = requests.patch(
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
    except requests.RequestException as error:
        raise Exception(f"Failed to update Zulip message: {error}")


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
    summary += transcript.long_summary
    summary += "\n```\n\n"

    message = header_text + summary + topic_text + "-----\n"
    return message


def extract_domain(url: str) -> str:
    return urlparse(url).netloc


def format_time_ms(milliseconds: float) -> str:
    return format_time(milliseconds // 1000)


def format_time(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    time = str(td - timedelta(microseconds=td.microseconds))

    return time[2:] if time.startswith("0:") else time
