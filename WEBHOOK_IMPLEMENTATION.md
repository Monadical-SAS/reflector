# Webhook Implementation for Reflector

## Overview
This implementation adds webhook functionality to Reflector rooms, allowing external services to be notified when transcripts are completed.

## Features Implemented

### 1. Database Changes
- Added `webhook_url` and `webhook_secret` fields to the `room` table
- Auto-generates webhook secret if URL is provided but secret is not
- Migration: `0194f65cd6d3_add_webhook_fields_to_rooms.py`

### 2. Backend Components

#### Webhook Task (`server/reflector/worker/webhook.py`)
- **`send_transcript_webhook`**: Main Celery task that sends webhook notifications
  - Retries with exponential backoff for up to 24 hours
  - Max 100 retries, starting at 1 minute intervals
  - Generates HMAC signature for request verification
  - Includes full transcript data, diarized text, topics, and summaries
  
- **`test_webhook`**: Test endpoint for validating webhook configuration
  - Sends a sample payload to verify connectivity
  - Returns immediate success/failure status

#### Webhook Payload Structure
```json
{
  "event": "transcript.completed",
  "timestamp": "2025-08-27T12:00:00Z",
  "transcript": {
    "id": "transcript-id",
    "room_id": "room-id",
    "created_at": "2025-08-27T11:00:00Z",
    "duration": 300.5,
    "title": "Meeting Title",
    "short_summary": "Brief summary",
    "long_summary": "Detailed summary",
    "diarized_text": "WebVTT formatted transcript",
    "topics": [
      {
        "title": "Topic 1",
        "summary": "Topic summary",
        "timestamp": 0.0,
        "duration": 60.0,
        "diarized_content": "WebVTT for this topic"
      }
    ],
    "participants": [
      {"id": "p1", "name": "Speaker 1", "speaker": 0}
    ],
    "source_language": "en",
    "target_language": "en",
    "status": "completed"
  },
  "room": {
    "id": "room-id",
    "name": "room-name"
  }
}
```

#### Security Headers
- `X-Webhook-Signature`: HMAC-SHA256 signature in format `t={timestamp},v1={signature}`
- `X-Webhook-Event`: Event type (e.g., "transcript.completed")
- `X-Webhook-Retry`: Current retry count

### 3. Integration Points

#### Pipeline Integration (`server/reflector/pipelines/main_file_pipeline.py`)
- Webhook triggered after successful transcript processing
- Only triggers for room recordings (`source_kind == SourceKind.ROOM`)
- Checks if room has webhook URL configured before dispatching

#### API Endpoints (`server/reflector/views/rooms.py`)
- Updated room CRUD operations to include webhook fields
- Added `/rooms/{room_id}/webhook/test` endpoint for testing webhook configuration

### 4. Frontend Updates

#### Room Management UI (`www/app/(app)/rooms/page.tsx`)
- Added webhook URL input field in room creation/edit dialog
- Display webhook secret (read-only, auto-generated)
- Test webhook button (only visible when editing existing room)
- Real-time test results display

## Usage

### Setting up a Webhook

1. **Create or Edit a Room**:
   - Navigate to Rooms page
   - Click "Add Room" or edit existing room
   - Enter webhook URL (e.g., `https://your-service.com/webhook`)
   - Webhook secret will be auto-generated on save

2. **Test the Webhook**:
   - When editing a room with webhook configured
   - Click "Test Webhook" button
   - View immediate success/failure feedback

3. **Verify Webhook Signature** (in your webhook handler):
   ```python
   import hmac
   import hashlib
   
   def verify_webhook_signature(payload: bytes, signature_header: str, secret: str) -> bool:
       # Parse header: "t=1234567890,v1=abc123..."
       parts = dict(part.split('=') for part in signature_header.split(','))
       timestamp = parts['t']
       signature = parts['v1']
       
       # Recreate signature
       signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
       expected_sig = hmac.new(
           secret.encode('utf-8'),
           signed_payload.encode('utf-8'),
           hashlib.sha256
       ).hexdigest()
       
       return hmac.compare_digest(expected_sig, signature)
   ```

## Testing

### Manual Testing
1. Use the test script: `uv run python test_webhook.py`
2. Use webhook.site for testing: https://webhook.site
3. Monitor Celery logs for webhook task execution

### Webhook Retry Behavior
- Initial retry: 1 minute after failure
- Exponential backoff: 2x previous delay
- Maximum delay: 1 hour between retries
- Total retry duration: ~24 hours
- Stops retrying on 4xx client errors

## Monitoring

### Celery Task Monitoring
```bash
# Watch webhook tasks
celery -A reflector.worker.app inspect active | grep webhook

# Check task results
celery -A reflector.worker.app result <task-id>
```

### Logging
- Webhook attempts logged with transcript_id, room_id, and retry count
- HTTP errors logged with status code and response preview
- Success logged with status code and response size

## Future Enhancements

1. **Webhook Events**:
   - Add more event types (transcript.updated, transcript.deleted)
   - Allow rooms to subscribe to specific events

2. **Webhook Management**:
   - Webhook history/logs viewer in UI
   - Retry failed webhooks manually
   - Webhook delivery statistics

3. **Advanced Features**:
   - Webhook request timeout configuration
   - Custom headers support
   - Batch webhook delivery for multiple transcripts

4. **Security**:
   - IP allowlist for webhook endpoints
   - Webhook secret rotation
   - Rate limiting for webhook deliveries