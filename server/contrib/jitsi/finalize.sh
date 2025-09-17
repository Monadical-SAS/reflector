#!/bin/bash
# Jibri finalize script to notify Reflector when recording is complete
# This script is called by Jibri with the recording directory as argument

RECORDING_PATH="$1"
SESSION_ID=$(basename "$RECORDING_PATH")
METADATA_FILE="$RECORDING_PATH/metadata.json"

# Extract meeting URL from Jibri's metadata
MEETING_URL=""
if [ -f "$METADATA_FILE" ]; then
    MEETING_URL=$(jq -r '.meeting_url' "$METADATA_FILE" 2>/dev/null || echo "")
fi

echo "[$(date)] Recording finalized: $RECORDING_PATH"
echo "[$(date)] Session ID: $SESSION_ID"
echo "[$(date)] Meeting URL: $MEETING_URL"

# Check if events.jsonl was created by our Prosody module
if [ -f "$RECORDING_PATH/events.jsonl" ]; then
    EVENT_COUNT=$(wc -l < "$RECORDING_PATH/events.jsonl")
    echo "[$(date)] Found events.jsonl with $EVENT_COUNT events"
else
    echo "[$(date)] Warning: No events.jsonl found"
fi

# Notify Reflector if webhook URL is configured
if [ -n "$REFLECTOR_WEBHOOK_URL" ]; then
    echo "[$(date)] Notifying Reflector at: $REFLECTOR_WEBHOOK_URL"

    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$REFLECTOR_WEBHOOK_URL/api/v1/jibri/recording-ready" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\":\"$SESSION_ID\",\"path\":\"$SESSION_ID\",\"meeting_url\":\"$MEETING_URL\"}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        echo "[$(date)] Reflector notified successfully"
        echo "[$(date)] Response: $BODY"
    else
        echo "[$(date)] Failed to notify Reflector. HTTP code: $HTTP_CODE"
        echo "[$(date)] Response: $BODY"
    fi
else
    echo "[$(date)] No REFLECTOR_WEBHOOK_URL configured, skipping notification"
fi

echo "[$(date)] Finalize script completed"