"""
Hatchet workflow constants.
"""

from enum import StrEnum


class TaskName(StrEnum):
    GET_RECORDING = "get_recording"
    GET_PARTICIPANTS = "get_participants"
    PROCESS_TRACKS = "process_tracks"
    MIXDOWN_TRACKS = "mixdown_tracks"
    GENERATE_WAVEFORM = "generate_waveform"
    DETECT_TOPICS = "detect_topics"
    GENERATE_TITLE = "generate_title"
    EXTRACT_SUBJECTS = "extract_subjects"
    PROCESS_SUBJECTS = "process_subjects"
    GENERATE_RECAP = "generate_recap"
    IDENTIFY_ACTION_ITEMS = "identify_action_items"
    FINALIZE = "finalize"
    CLEANUP_CONSENT = "cleanup_consent"
    POST_ZULIP = "post_zulip"
    SEND_WEBHOOK = "send_webhook"
    PAD_TRACK = "pad_track"
    TRANSCRIBE_TRACK = "transcribe_track"
    DETECT_CHUNK_TOPIC = "detect_chunk_topic"
    GENERATE_DETAILED_SUMMARY = "generate_detailed_summary"


# Rate limit key for LLM API calls (shared across all LLM-calling tasks)
LLM_RATE_LIMIT_KEY = "llm"

# Max LLM calls per second across all tasks
LLM_RATE_LIMIT_PER_SECOND = 10

# Task execution timeouts (seconds)
TIMEOUT_SHORT = 60  # Quick operations: API calls, DB updates
TIMEOUT_MEDIUM = 120  # Single LLM calls, waveform generation
TIMEOUT_LONG = 180  # Action items (larger context LLM)
TIMEOUT_AUDIO = (
    300  # Audio processing: padding, mixdown (5 minutes - enough for testing)
)
TIMEOUT_HEAVY = 600  # Transcription, fan-out LLM tasks
