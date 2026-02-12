"""Typed WebSocket event models.

Defines Pydantic models with Literal discriminators for all WS events.
Exposed via stub GET endpoints so ``pnpm openapi`` generates TS discriminated unions.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Discriminator

from reflector.db.transcripts import (
    TranscriptActionItems,
    TranscriptDuration,
    TranscriptFinalLongSummary,
    TranscriptFinalShortSummary,
    TranscriptFinalTitle,
    TranscriptStatus,
    TranscriptText,
    TranscriptTopic,
    TranscriptWaveform,
)

# ---------------------------------------------------------------------------
# Transcript-level event name literal
# ---------------------------------------------------------------------------

TranscriptEventName = Literal[
    "TRANSCRIPT",
    "TOPIC",
    "STATUS",
    "FINAL_TITLE",
    "FINAL_LONG_SUMMARY",
    "FINAL_SHORT_SUMMARY",
    "ACTION_ITEMS",
    "DURATION",
    "WAVEFORM",
]

# ---------------------------------------------------------------------------
# Transcript-level WS event wrappers
# ---------------------------------------------------------------------------


class TranscriptWsTranscript(BaseModel):
    event: Literal["TRANSCRIPT"] = "TRANSCRIPT"
    data: TranscriptText


class TranscriptWsTopic(BaseModel):
    event: Literal["TOPIC"] = "TOPIC"
    data: TranscriptTopic


class TranscriptWsStatusData(BaseModel):
    value: TranscriptStatus


class TranscriptWsStatus(BaseModel):
    event: Literal["STATUS"] = "STATUS"
    data: TranscriptWsStatusData


class TranscriptWsFinalTitle(BaseModel):
    event: Literal["FINAL_TITLE"] = "FINAL_TITLE"
    data: TranscriptFinalTitle


class TranscriptWsFinalLongSummary(BaseModel):
    event: Literal["FINAL_LONG_SUMMARY"] = "FINAL_LONG_SUMMARY"
    data: TranscriptFinalLongSummary


class TranscriptWsFinalShortSummary(BaseModel):
    event: Literal["FINAL_SHORT_SUMMARY"] = "FINAL_SHORT_SUMMARY"
    data: TranscriptFinalShortSummary


class TranscriptWsActionItems(BaseModel):
    event: Literal["ACTION_ITEMS"] = "ACTION_ITEMS"
    data: TranscriptActionItems


class TranscriptWsDuration(BaseModel):
    event: Literal["DURATION"] = "DURATION"
    data: TranscriptDuration


class TranscriptWsWaveform(BaseModel):
    event: Literal["WAVEFORM"] = "WAVEFORM"
    data: TranscriptWaveform


TranscriptWsEvent = Annotated[
    Union[
        TranscriptWsTranscript,
        TranscriptWsTopic,
        TranscriptWsStatus,
        TranscriptWsFinalTitle,
        TranscriptWsFinalLongSummary,
        TranscriptWsFinalShortSummary,
        TranscriptWsActionItems,
        TranscriptWsDuration,
        TranscriptWsWaveform,
    ],
    Discriminator("event"),
]

# ---------------------------------------------------------------------------
# User-level event name literal
# ---------------------------------------------------------------------------

UserEventName = Literal[
    "TRANSCRIPT_CREATED",
    "TRANSCRIPT_DELETED",
    "TRANSCRIPT_STATUS",
    "TRANSCRIPT_FINAL_TITLE",
    "TRANSCRIPT_DURATION",
]

# ---------------------------------------------------------------------------
# User-level WS event data models
# ---------------------------------------------------------------------------


class UserTranscriptCreatedData(BaseModel):
    id: str


class UserTranscriptDeletedData(BaseModel):
    id: str


class UserTranscriptStatusData(BaseModel):
    id: str
    value: str


class UserTranscriptFinalTitleData(BaseModel):
    id: str
    title: str


class UserTranscriptDurationData(BaseModel):
    id: str
    duration: float


# ---------------------------------------------------------------------------
# User-level WS event wrappers
# ---------------------------------------------------------------------------


class UserWsTranscriptCreated(BaseModel):
    event: Literal["TRANSCRIPT_CREATED"] = "TRANSCRIPT_CREATED"
    data: UserTranscriptCreatedData


class UserWsTranscriptDeleted(BaseModel):
    event: Literal["TRANSCRIPT_DELETED"] = "TRANSCRIPT_DELETED"
    data: UserTranscriptDeletedData


class UserWsTranscriptStatus(BaseModel):
    event: Literal["TRANSCRIPT_STATUS"] = "TRANSCRIPT_STATUS"
    data: UserTranscriptStatusData


class UserWsTranscriptFinalTitle(BaseModel):
    event: Literal["TRANSCRIPT_FINAL_TITLE"] = "TRANSCRIPT_FINAL_TITLE"
    data: UserTranscriptFinalTitleData


class UserWsTranscriptDuration(BaseModel):
    event: Literal["TRANSCRIPT_DURATION"] = "TRANSCRIPT_DURATION"
    data: UserTranscriptDurationData


UserWsEvent = Annotated[
    Union[
        UserWsTranscriptCreated,
        UserWsTranscriptDeleted,
        UserWsTranscriptStatus,
        UserWsTranscriptFinalTitle,
        UserWsTranscriptDuration,
    ],
    Discriminator("event"),
]
