# Reflector Webhook Documentation

## Overview

Reflector supports webhook notifications to notify external systems when transcript processing is completed. Webhooks can be configured per room and are triggered automatically after a transcript is successfully processed.

## Configuration

Webhooks are configured at the room level with two fields:
- `webhook_url`: The HTTPS endpoint to receive webhook notifications
- `webhook_secret`: Optional secret key for HMAC signature verification (auto-generated if not provided)

## Events

### `transcript.completed`

Triggered when a transcript has been fully processed, including transcription, diarization, summarization, topic detection and calendar event integration.

### `test`

A test event that can be triggered manually to verify webhook configuration.

## Webhook Request Format

### Headers

All webhook requests include the following headers:

| Header | Description | Example |
|--------|-------------|---------|
| `Content-Type` | Always `application/json` | `application/json` |
| `User-Agent` | Identifies Reflector as the source | `Reflector-Webhook/1.0` |
| `X-Webhook-Event` | The event type | `transcript.completed` or `test` |
| `X-Webhook-Retry` | Current retry attempt number | `0`, `1`, `2`... |
| `X-Webhook-Signature` | HMAC signature (if secret configured) | `t=1735306800,v1=abc123...` |

### Signature Verification

If a webhook secret is configured, Reflector includes an HMAC-SHA256 signature in the `X-Webhook-Signature` header to verify the webhook authenticity.

The signature format is: `t={timestamp},v1={signature}`

To verify the signature:
1. Extract the timestamp and signature from the header
2. Create the signed payload: `{timestamp}.{request_body}`
3. Compute HMAC-SHA256 of the signed payload using your webhook secret
4. Compare the computed signature with the received signature

Example verification (Python):
```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    # Parse header: "t=1735306800,v1=abc123..."
    parts = dict(part.split("=") for part in signature_header.split(","))
    timestamp = parts["t"]
    received_signature = parts["v1"]

    # Create signed payload
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"

    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # Compare signatures
    return hmac.compare_digest(expected_signature, received_signature)
```

## Event Payloads

### `transcript.completed` Event

This event includes a convenient URL for accessing the transcript:
- `frontend_url`: Direct link to view the transcript in the web interface

```json
{
  "event": "transcript.completed",
  "event_id": "transcript.completed-abc-123-def-456",
  "timestamp": "2025-08-27T12:34:56.789012Z",
  "transcript": {
    "id": "abc-123-def-456",
    "room_id": "room-789",
    "created_at": "2025-08-27T12:00:00Z",
    "duration": 1800.5,
    "title": "Q3 Product Planning Meeting",
    "short_summary": "Team discussed Q3 product roadmap, prioritizing mobile app features and API improvements.",
    "long_summary": "The product team met to finalize the Q3 roadmap. Key decisions included...",
    "webvtt": "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n<v Speaker 1>Welcome everyone to today's meeting...",
    "topics": [
      {
        "title": "Introduction and Agenda",
        "summary": "Meeting kickoff with agenda review",
        "timestamp": 0.0,
        "duration": 120.0,
        "webvtt": "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n<v Speaker 1>Welcome everyone..."
      },
      {
        "title": "Mobile App Features Discussion",
        "summary": "Team reviewed proposed mobile app features for Q3",
        "timestamp": 120.0,
        "duration": 600.0,
        "webvtt": "WEBVTT\n\n00:02:00.000 --> 00:02:10.000\n<v Speaker 2>Let's talk about the mobile app..."
      }
    ],
    "participants": [
      {
        "id": "participant-1",
        "name": "John Doe",
        "speaker": "Speaker 1"
      },
      {
        "id": "participant-2",
        "name": "Jane Smith",
        "speaker": "Speaker 2"
      }
    ],
    "source_language": "en",
    "target_language": "en",
    "status": "completed",
    "frontend_url": "https://app.reflector.com/transcripts/abc-123-def-456"
  },
  "room": {
    "id": "room-789",
    "name": "Product Team Room"
  },
  "calendar_event": {
    "id": "calendar-event-123",
    "ics_uid": "event-123",
    "title": "Q3 Product Planning Meeting",
    "start_time": "2025-08-27T12:00:00Z",
    "end_time": "2025-08-27T12:30:00Z",
    "description": "Team discussed Q3 product roadmap, prioritizing mobile app features and API improvements.",
    "location": "Conference Room 1",
    "attendees": [
      {
        "id": "participant-1",
        "name": "John Doe",
        "speaker": "Speaker 1"
      },
      {
        "id": "participant-2",
        "name": "Jane Smith",
        "speaker": "Speaker 2"
      }
    ]
  }
}
```

### `test` Event

```json
{
  "event": "test",
  "event_id": "test.2025-08-27T12:34:56.789012Z",
  "timestamp": "2025-08-27T12:34:56.789012Z",
  "message": "This is a test webhook from Reflector",
  "room": {
    "id": "room-789",
    "name": "Product Team Room"
  }
}
```

## Retry Policy

Webhooks are delivered with automatic retry logic to handle transient failures. When a webhook delivery fails due to server errors or network issues, Reflector will automatically retry the delivery multiple times over an extended period.

### Retry Mechanism

Reflector implements an exponential backoff strategy for webhook retries:

- **Initial retry delay**: 60 seconds after the first failure
- **Exponential backoff**: Each subsequent retry waits approximately twice as long as the previous one
- **Maximum retry interval**: 1 hour (backoff is capped at this duration)
- **Maximum retry attempts**: 30 attempts total
- **Total retry duration**: Retries continue for approximately 24 hours

### How Retries Work

When a webhook fails, Reflector will:
1. Wait 60 seconds, then retry (attempt #1)
2. If it fails again, wait ~2 minutes, then retry (attempt #2)
3. Continue doubling the wait time up to a maximum of 1 hour between attempts
4. Keep retrying at 1-hour intervals until successful or 30 attempts are exhausted

The `X-Webhook-Retry` header indicates the current retry attempt number (0 for the initial attempt, 1 for first retry, etc.), allowing your endpoint to track retry attempts.

### Retry Behavior by HTTP Status Code

| Status Code | Behavior |
|-------------|----------|
| 2xx (Success) | No retry, webhook marked as delivered |
| 4xx (Client Error) | No retry, request is considered permanently failed |
| 5xx (Server Error) | Automatic retry with exponential backoff |
| Network/Timeout Error | Automatic retry with exponential backoff |

**Important Notes:**
- Webhooks timeout after 30 seconds. If your endpoint takes longer to respond, it will be considered a timeout error and retried.
- During the retry period (~24 hours), you may receive the same webhook multiple times if your endpoint experiences intermittent failures.
- There is no mechanism to manually retry failed webhooks after the retry period expires.

## Testing Webhooks

You can test your webhook configuration before processing transcripts:

```http
POST /v1/rooms/{room_id}/webhook/test
```

Response:
```json
{
  "success": true,
  "status_code": 200,
  "message": "Webhook test successful",
  "response_preview": "OK"
}
```

Or in case of failure:
```json
{
  "success": false,
  "error": "Webhook request timed out (10 seconds)"
}
```
