# Reflector Webhook Documentation

## Overview

Reflector supports webhook notifications to notify external systems when transcript processing is completed. Webhooks can be configured per room and are triggered automatically after a transcript is successfully processed.

## Configuration

Webhooks are configured at the room level with two fields:
- `webhook_url`: The HTTPS endpoint to receive webhook notifications
- `webhook_secret`: Optional secret key for HMAC signature verification (auto-generated if not provided)

## Events

### `transcript.completed`

Triggered when a transcript has been fully processed, including transcription, diarization, summarization, and topic detection.

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
  }
}
```

### `test` Event

```json
{
  "event": "test",
  "timestamp": "2025-08-27T12:34:56.789012Z",
  "message": "This is a test webhook from Reflector",
  "room": {
    "id": "room-789",
    "name": "Product Team Room"
  }
}
```

## Retry Policy

Webhooks are delivered with automatic retry logic to handle transient failures:

- **Initial retry delay**: 60 seconds
- **Backoff factor**: 2x (exponential backoff)
- **Maximum retry interval**: 1 hour
- **Maximum retry attempts**: 100 (covers ~24 hours)
- **Total retry duration**: ~24 hours

### Retry Behavior by HTTP Status Code

| Status Code | Behavior |
|-------------|----------|
| 2xx (Success) | No retry, webhook marked as delivered |
| 4xx (Client Error) | No retry, request is invalid |
| 5xx (Server Error) | Automatic retry with exponential backoff |
| Network/Timeout Error | Automatic retry with exponential backoff |

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

## Security Considerations

- Always use HTTPS endpoints for webhook URLs
- Configure a webhook secret for signature verification
- Verify signatures before processing webhook payloads
- Implement idempotency to handle potential duplicate deliveries
- Set appropriate timeouts on your webhook endpoint (< 30 seconds)

## Best Practices

1. **Respond quickly**: Return a 2xx status code as soon as possible
2. **Process asynchronously**: Queue the webhook for processing rather than processing inline
3. **Handle duplicates**: Use the transcript ID to ensure idempotent processing
4. **Verify signatures**: Always verify the HMAC signature when a secret is configured
5. **Monitor failures**: Track webhook failures and implement alerting
6. **Use HTTPS**: Always use secure HTTPS endpoints for production webhooks

## Example Webhook Receiver (Python/FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException, Header
import hmac
import hashlib
import json

app = FastAPI()

WEBHOOK_SECRET = "your-secret-key-here"

def verify_signature(payload: bytes, signature_header: str) -> bool:
    parts = dict(part.split("=") for part in signature_header.split(","))
    timestamp = parts["t"]
    received_signature = parts["v1"]

    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, received_signature)

@app.post("/webhook/reflector")
async def handle_reflector_webhook(
    request: Request,
    x_webhook_event: str = Header(None),
    x_webhook_signature: str = Header(None)
):
    # Get raw payload
    payload = await request.body()

    # Verify signature if present
    if x_webhook_signature and WEBHOOK_SECRET:
        if not verify_signature(payload, x_webhook_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON
    data = json.loads(payload)

    # Handle different event types
    if x_webhook_event == "transcript.completed":
        # Process completed transcript
        transcript_id = data["transcript"]["id"]
        title = data["transcript"]["title"]
        print(f"Transcript completed: {title} (ID: {transcript_id})")

        # Queue for async processing
        # process_transcript.delay(data)

    elif x_webhook_event == "test":
        print("Received test webhook")

    # Return success immediately
    return {"status": "ok"}
```

