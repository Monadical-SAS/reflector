#!/bin/bash
# Jibri Recording Finalization Script
# Called automatically when recording stops
# Jibri passes the recordings directory path as first argument

set -e

# Arguments provided by Jibri
RECORDINGS_DIR="$1"
LOG_FILE="/config/logs/finalize.log"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

log_message() {
    local level=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*"
}

log_message "INFO" "Finalize script started for directory: $RECORDINGS_DIR"

# Extract session ID from directory path (last component)
SESSION_ID=$(basename "$RECORDINGS_DIR")
log_message "INFO" "Session ID: $SESSION_ID"

# Find the MP4 file
VIDEO_FILE=$(find "$RECORDINGS_DIR" -name "*.mp4" -type f | head -1)

if [ -z "$VIDEO_FILE" ]; then
    log_message "ERROR" "No MP4 file found in $RECORDINGS_DIR"

    # Send failure event
    curl -X POST "http://event-collector:3002/webhook/jibri" \
        -H "Content-Type: application/json" \
        -d "{
            \"source\": \"jibri\",
            \"type\": \"recording_failed\",
            \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\",
            \"roomName\": \"unknown\",
            \"data\": {
                \"session_id\": \"$SESSION_ID\",
                \"error\": \"No MP4 file found\",
                \"recordings_dir\": \"$RECORDINGS_DIR\"
            }
        }" \
        --max-time 10 \
        --silent \
        --show-error \
        || log_message "WARN" "Failed to send failure webhook"

    exit 1
fi

log_message "INFO" "Found video file: $VIDEO_FILE"

# Extract room name from filename (format: roomname_YYYY-MM-DD-HH-MM-SS.mp4)
VIDEO_FILENAME=$(basename "$VIDEO_FILE")
ROOM_NAME="${VIDEO_FILENAME%_*}"
TIMESTAMP="${VIDEO_FILENAME#*_}"
TIMESTAMP="${TIMESTAMP%.mp4}"

# Get file metadata
FILE_SIZE=$(stat -c%s "$VIDEO_FILE" 2>/dev/null || stat -f%z "$VIDEO_FILE" 2>/dev/null || echo "0")
FILE_MODIFIED=$(stat -c%Y "$VIDEO_FILE" 2>/dev/null || stat -f%m "$VIDEO_FILE" 2>/dev/null || date +%s)

# Try to extract duration using ffprobe if available
DURATION="0"
if command -v ffprobe &> /dev/null; then
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VIDEO_FILE" 2>/dev/null || echo "0")
    log_message "INFO" "Video duration: $DURATION seconds"
else
    log_message "WARN" "ffprobe not available, cannot determine video duration"
fi

# Extract participants from metadata.json if it exists
PARTICIPANTS="[]"
METADATA_FILE="$RECORDINGS_DIR/metadata.json"
if [ -f "$METADATA_FILE" ]; then
    log_message "INFO" "Found metadata file: $METADATA_FILE"
    # Try to extract participants array from metadata
    if command -v jq &> /dev/null; then
        PARTICIPANTS=$(jq -c '.participants // []' "$METADATA_FILE" 2>/dev/null || echo "[]")
    fi
    log_message "INFO" "Participants: $PARTICIPANTS"
fi

log_message "INFO" "Sending recording completed event to event collector"

# Send webhook to event collector
PAYLOAD=$(cat <<EOF
{
    "source": "jibri",
    "type": "recording_completed",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "roomName": "$ROOM_NAME",
    "data": {
        "session_id": "$SESSION_ID",
        "recording_path": "$VIDEO_FILE",
        "recording_filename": "$VIDEO_FILENAME",
        "recording_timestamp": "$TIMESTAMP",
        "file_size": $FILE_SIZE,
        "duration": $DURATION,
        "file_modified": $FILE_MODIFIED,
        "participants": $PARTICIPANTS
    },
    "metadata": {
        "recordingId": "${VIDEO_FILENAME%.mp4}",
        "sessionId": "$SESSION_ID"
    }
}
EOF
)

log_message "DEBUG" "Payload: $PAYLOAD"

curl -X POST "http://event-collector:3002/webhook/jibri" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    --max-time 10 \
    --silent \
    --show-error \
    && log_message "INFO" "Webhook sent successfully" \
    || log_message "ERROR" "Failed to send webhook"

# Also send a simpler recording_available event
SIMPLE_PAYLOAD=$(cat <<EOF
{
    "source": "jibri",
    "type": "recording_available",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "roomName": "$ROOM_NAME",
    "data": {
        "session_id": "$SESSION_ID",
        "recording_path": "$VIDEO_FILE",
        "recording_id": "${VIDEO_FILENAME%.mp4}"
    }
}
EOF
)

curl -X POST "http://event-collector:3002/webhook/jibri" \
    -H "Content-Type: application/json" \
    -d "$SIMPLE_PAYLOAD" \
    --max-time 10 \
    --silent \
    --show-error \
    && log_message "INFO" "Recording available notification sent" \
    || log_message "WARN" "Failed to send recording available notification"

# Upload to S3 if configured
if [ ! -z "$S3_BUCKET" ] && [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
    log_message "INFO" "Uploading to S3..."

    S3_KEY="recordings/$(date +%Y/%m/%d)/$(basename $VIDEO_FILE)"

    if [ ! -z "$S3_ENDPOINT" ]; then
        # Custom S3 endpoint (MinIO, etc.)
        aws s3 cp "$VIDEO_FILE" "s3://$S3_BUCKET/$S3_KEY" \
            --endpoint-url "$S3_ENDPOINT" \
            --no-progress \
            && log_message "INFO" "Uploaded to S3: s3://$S3_BUCKET/$S3_KEY" \
            || log_message "WARN" "S3 upload failed"
    else
        # Standard AWS S3
        aws s3 cp "$VIDEO_FILE" "s3://$S3_BUCKET/$S3_KEY" \
            --no-progress \
            && log_message "INFO" "Uploaded to S3: s3://$S3_BUCKET/$S3_KEY" \
            || log_message "WARN" "S3 upload failed"
    fi
fi

# Move recording to organized directory structure
ARCHIVE_DIR="/recordings/archive/$(date +%Y/%m/%d)"
mkdir -p "$ARCHIVE_DIR"

# Copy instead of move to preserve original for debugging
cp -r "$RECORDINGS_DIR" "$ARCHIVE_DIR/" && log_message "INFO" "Copied to archive: $ARCHIVE_DIR/$(basename $RECORDINGS_DIR)"

# Clean up old recordings (keep 7 days in archive)
log_message "INFO" "Cleaning up old recordings..."
find /recordings/archive -type f -mtime +7 -delete 2>/dev/null || true
find /recordings/archive -type d -empty -delete 2>/dev/null || true

log_message "INFO" "Finalization complete for session $SESSION_ID"

exit 0