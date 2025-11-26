"""Schema definitions for transcript format types and segments."""

from typing import Literal

from pydantic import BaseModel

TranscriptFormat = Literal["text", "text-timestamped", "webvtt-named", "json"]


class TranscriptSegment(BaseModel):
    """A single transcript segment with speaker and timing information."""

    speaker: int
    speaker_name: str
    text: str
    start: float
    end: float
