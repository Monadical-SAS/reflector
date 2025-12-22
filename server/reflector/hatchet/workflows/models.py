"""
Pydantic models for Hatchet workflow task return types.

Provides static typing for all task outputs, enabling type checking
and better IDE support.
"""

from pydantic import BaseModel

from reflector.processors.types import TitleSummary, Word
from reflector.utils.string import NonEmptyString


class ParticipantInfo(BaseModel):
    """Participant info with speaker index for workflow result."""

    participant_id: NonEmptyString
    user_name: NonEmptyString
    speaker: int


class PadTrackResult(BaseModel):
    """Result from pad_track task."""

    padded_key: NonEmptyString  # S3 key (not presigned URL) - presign on demand to avoid stale URLs on replay
    bucket_name: (
        NonEmptyString | None
    )  # None means use default transcript storage bucket
    size: int
    track_index: int


class TranscribeTrackResult(BaseModel):
    """Result from transcribe_track task."""

    words: list[Word]
    track_index: int


class RecordingResult(BaseModel):
    """Result from get_recording task."""

    id: NonEmptyString | None
    mtg_session_id: NonEmptyString | None
    duration: float


class ParticipantsResult(BaseModel):
    """Result from get_participants task."""

    participants: list[ParticipantInfo]
    num_tracks: int
    source_language: NonEmptyString
    target_language: NonEmptyString


class PaddedTrackInfo(BaseModel):
    """Info for a padded track - S3 key + bucket for on-demand presigning."""

    key: NonEmptyString
    bucket_name: NonEmptyString | None  # None = use default storage bucket


class ProcessTracksResult(BaseModel):
    """Result from process_tracks task."""

    all_words: list[Word]
    padded_tracks: list[PaddedTrackInfo]  # S3 keys, not presigned URLs
    word_count: int
    num_tracks: int
    target_language: NonEmptyString
    created_padded_files: list[NonEmptyString]


class MixdownResult(BaseModel):
    """Result from mixdown_tracks task."""

    audio_key: NonEmptyString
    duration: float
    tracks_mixed: int


class WaveformResult(BaseModel):
    """Result from generate_waveform task."""

    waveform_generated: bool


class TopicChunkResult(BaseModel):
    """Result from topic chunk child workflow."""

    chunk_index: int
    title: str
    summary: str
    timestamp: float
    duration: float
    words: list[Word]


class TopicsResult(BaseModel):
    """Result from detect_topics task."""

    topics: list[TitleSummary]


class TitleResult(BaseModel):
    """Result from generate_title task."""

    title: str | None


class SubjectsResult(BaseModel):
    """Result from extract_subjects task."""

    subjects: list[str]
    transcript_text: str  # Formatted transcript for LLM consumption
    participant_names: list[str]
    participant_name_to_id: dict[str, str]


class SubjectSummaryResult(BaseModel):
    """Result from subject summary child workflow."""

    subject: str
    subject_index: int
    detailed_summary: str
    paragraph_summary: str


class ProcessSubjectsResult(BaseModel):
    """Result from process_subjects fan-out task."""

    subject_summaries: list[SubjectSummaryResult]


class RecapResult(BaseModel):
    """Result from generate_recap task."""

    short_summary: str  # Recap paragraph
    long_summary: str  # Full markdown summary


class ActionItemsResult(BaseModel):
    """Result from identify_action_items task."""

    action_items: dict  # ActionItemsResponse as dict (may have empty lists)


class FinalizeResult(BaseModel):
    """Result from finalize task."""

    status: NonEmptyString


class ConsentResult(BaseModel):
    """Result from cleanup_consent task."""


class ZulipResult(BaseModel):
    """Result from post_zulip task."""

    zulip_message_id: int | None = None
    skipped: bool = False


class WebhookResult(BaseModel):
    """Result from send_webhook task."""

    webhook_sent: bool
    skipped: bool = False
    response_code: int | None = None
