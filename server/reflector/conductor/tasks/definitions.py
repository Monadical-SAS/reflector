"""Task definitions for Conductor workflow orchestration.

Timeout reference (from CONDUCTOR_MIGRATION_REQUIREMENTS.md):
| Task              | Timeout (s) | Response Timeout (s) | Retry Count |
|-------------------|-------------|----------------------|-------------|
| get_recording     | 60          | 30                   | 3           |
| get_participants  | 60          | 30                   | 3           |
| pad_track         | 300         | 120                  | 3           |
| mixdown_tracks    | 600         | 300                  | 3           |
| generate_waveform | 120         | 60                   | 3           |
| transcribe_track  | 1800        | 900                  | 3           |
| merge_transcripts | 60          | 30                   | 3           |
| detect_topics     | 300         | 120                  | 3           |
| generate_title    | 60          | 30                   | 3           |
| generate_summary  | 300         | 120                  | 3           |
| finalize          | 60          | 30                   | 3           |
| cleanup_consent   | 60          | 30                   | 3           |
| post_zulip        | 60          | 30                   | 5           |
| send_webhook      | 60          | 30                   | 30          |
"""

OWNER_EMAIL = "reflector@example.com"

TASK_DEFINITIONS = [
    {
        "name": "get_recording",
        "retryCount": 3,
        "timeoutSeconds": 60,
        "responseTimeoutSeconds": 30,
        "inputKeys": ["recording_id"],
        "outputKeys": ["id", "mtg_session_id", "room_name", "duration"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "get_participants",
        "retryCount": 3,
        "timeoutSeconds": 60,
        "responseTimeoutSeconds": 30,
        "inputKeys": ["mtg_session_id"],
        "outputKeys": ["participants"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "pad_track",
        "retryCount": 3,
        "timeoutSeconds": 300,
        "responseTimeoutSeconds": 120,
        "inputKeys": ["track_index", "s3_key", "bucket_name", "transcript_id"],
        "outputKeys": ["padded_url", "size", "track_index"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "mixdown_tracks",
        "retryCount": 3,
        "timeoutSeconds": 600,
        "responseTimeoutSeconds": 300,
        "inputKeys": ["padded_urls", "transcript_id"],
        "outputKeys": ["audio_key", "duration", "size"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "generate_waveform",
        "retryCount": 3,
        "timeoutSeconds": 120,
        "responseTimeoutSeconds": 60,
        "inputKeys": ["audio_key", "transcript_id"],
        "outputKeys": ["waveform"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "transcribe_track",
        "retryCount": 3,
        "timeoutSeconds": 1800,
        "responseTimeoutSeconds": 900,
        "inputKeys": ["track_index", "audio_url", "language"],
        "outputKeys": ["words", "track_index"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "merge_transcripts",
        "retryCount": 3,
        "timeoutSeconds": 60,
        "responseTimeoutSeconds": 30,
        "inputKeys": ["transcripts", "transcript_id"],
        "outputKeys": ["all_words", "word_count"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "detect_topics",
        "retryCount": 3,
        "timeoutSeconds": 300,
        "responseTimeoutSeconds": 120,
        "inputKeys": ["words", "transcript_id", "target_language"],
        "outputKeys": ["topics"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "generate_title",
        "retryCount": 3,
        "timeoutSeconds": 60,
        "responseTimeoutSeconds": 30,
        "inputKeys": ["topics", "transcript_id"],
        "outputKeys": ["title"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "generate_summary",
        "retryCount": 3,
        "timeoutSeconds": 300,
        "responseTimeoutSeconds": 120,
        "inputKeys": ["words", "topics", "transcript_id"],
        "outputKeys": ["summary", "short_summary"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "finalize",
        "retryCount": 3,
        "timeoutSeconds": 60,
        "responseTimeoutSeconds": 30,
        "inputKeys": ["transcript_id", "title", "summary", "short_summary", "duration"],
        "outputKeys": ["status"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "cleanup_consent",
        "retryCount": 3,
        "timeoutSeconds": 60,
        "responseTimeoutSeconds": 30,
        "inputKeys": ["transcript_id"],
        "outputKeys": ["audio_deleted", "reason"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "post_zulip",
        "retryCount": 5,
        "timeoutSeconds": 60,
        "responseTimeoutSeconds": 30,
        "inputKeys": ["transcript_id"],
        "outputKeys": ["message_id"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "send_webhook",
        "retryCount": 30,
        "timeoutSeconds": 60,
        "responseTimeoutSeconds": 30,
        "inputKeys": ["transcript_id", "room_id"],
        "outputKeys": ["sent", "status_code"],
        "ownerEmail": OWNER_EMAIL,
    },
    {
        "name": "generate_dynamic_fork_tasks",
        "retryCount": 3,
        "timeoutSeconds": 30,
        "responseTimeoutSeconds": 15,
        "inputKeys": ["tracks", "task_type", "transcript_id", "bucket_name"],
        "outputKeys": ["tasks", "inputs"],
        "ownerEmail": OWNER_EMAIL,
        "description": "Helper task to generate dynamic fork structure for variable track counts",
    },
]
