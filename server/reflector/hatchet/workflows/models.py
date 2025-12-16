"""
Pydantic models for Hatchet workflow task return types.

Provides static typing for all task outputs, enabling type checking
and better IDE support.
"""

from typing import Any

from pydantic import BaseModel

# ============================================================================
# Track Processing Results (track_processing.py)
# ============================================================================


class PadTrackResult(BaseModel):
    """Result from pad_track task."""

    padded_key: str  # S3 key (not presigned URL) - presign on demand to avoid stale URLs on replay
    bucket_name: str | None  # None means use default transcript storage bucket
    size: int
    track_index: int


class TranscribeTrackResult(BaseModel):
    """Result from transcribe_track task."""

    words: list[dict[str, Any]]
    track_index: int


# ============================================================================
# Diarization Pipeline Results (diarization_pipeline.py)
# ============================================================================


class RecordingResult(BaseModel):
    """Result from get_recording task."""

    id: str | None
    mtg_session_id: str | None
    room_name: str | None
    duration: float


class ParticipantsResult(BaseModel):
    """Result from get_participants task."""

    participants: list[dict[str, Any]]
    num_tracks: int
    source_language: str
    target_language: str


class PaddedTrackInfo(BaseModel):
    """Info for a padded track - S3 key + bucket for on-demand presigning."""

    key: str
    bucket_name: str | None  # None = use default storage bucket


class ProcessTracksResult(BaseModel):
    """Result from process_tracks task."""

    all_words: list[dict[str, Any]]
    padded_tracks: list[PaddedTrackInfo]  # S3 keys, not presigned URLs
    word_count: int
    num_tracks: int
    target_language: str
    created_padded_files: list[str]


class MixdownResult(BaseModel):
    """Result from mixdown_tracks task."""

    audio_key: str
    duration: float
    tracks_mixed: int


class WaveformResult(BaseModel):
    """Result from generate_waveform task."""

    waveform_generated: bool


class TopicsResult(BaseModel):
    """Result from detect_topics task."""

    topics: list[dict[str, Any]]


class TitleResult(BaseModel):
    """Result from generate_title task."""

    title: str | None


class SummaryResult(BaseModel):
    """Result from generate_summary task."""

    summary: str | None
    short_summary: str | None


class FinalizeResult(BaseModel):
    """Result from finalize task."""

    status: str


class ConsentResult(BaseModel):
    """Result from cleanup_consent task."""

    consent_checked: bool


class ZulipResult(BaseModel):
    """Result from post_zulip task."""

    zulip_message_id: int | None = None
    skipped: bool = False


class WebhookResult(BaseModel):
    """Result from send_webhook task."""

    webhook_sent: bool
    skipped: bool = False
    response_code: int | None = None
