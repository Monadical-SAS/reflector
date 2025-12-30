"""Pydantic models for outgoing webhook payloads.

These models define the structure of webhook payloads sent by Reflector
to external services when transcript processing completes.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from reflector.utils.string import NonEmptyString

WebhookTranscriptEventType = Literal["transcript.completed"]
WebhookTestEventType = Literal["test"]


class WebhookTopicPayload(BaseModel):
    title: NonEmptyString
    summary: NonEmptyString
    timestamp: float
    duration: float | None
    webvtt: str  # can be empty when no words


class WebhookParticipantPayload(BaseModel):
    id: NonEmptyString
    name: str | None
    speaker: int | None


class WebhookRoomPayload(BaseModel):
    id: NonEmptyString
    name: NonEmptyString


class WebhookCalendarEventPayload(BaseModel):
    id: NonEmptyString
    ics_uid: str | None = None
    title: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    description: str | None = None
    location: str | None = None
    attendees: list[str] | None = None


class WebhookTranscriptPayload(BaseModel):
    id: NonEmptyString
    room_id: NonEmptyString | None
    created_at: datetime
    duration: float | None
    title: str | None
    short_summary: str | None
    long_summary: str | None
    webvtt: str | None
    topics: list[WebhookTopicPayload]
    participants: list[WebhookParticipantPayload]
    source_language: NonEmptyString
    target_language: NonEmptyString
    status: NonEmptyString
    frontend_url: NonEmptyString
    action_items: dict | None


class WebhookPayload(BaseModel):
    event: WebhookTranscriptEventType
    event_id: NonEmptyString
    timestamp: datetime
    transcript: WebhookTranscriptPayload
    room: WebhookRoomPayload
    calendar_event: WebhookCalendarEventPayload | None = None


class WebhookTestPayload(BaseModel):
    event: WebhookTestEventType
    event_id: NonEmptyString
    timestamp: datetime
    message: NonEmptyString
    room: WebhookRoomPayload
