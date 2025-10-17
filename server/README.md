## API Token Management

### Finding Your User ID

```bash
# Get your OAuth sub (user ID) - requires authentication
curl -H "Authorization: Bearer <your_jwt>" http://localhost:1250/v1/me
# Returns: {"sub": "your-oauth-sub-here", "email": "...", ...}
```

### Creating API Tokens

#### For yourself (via API):
```bash
curl -X POST http://localhost:1250/v1/user/tokens \
  -H "Authorization: Bearer <your_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Token"}'
```

#### For any user (via script - no auth required):
```bash
# Requires database access
cd server
uv run python scripts/create_token.py <user_id> <token_name>

# Example for OAuth user:
uv run python scripts/create_token.py "e7d4f2a8-9b3c-4d1e-8f6a" "Production Token"

# Example for service account (arbitrary ID):
uv run python scripts/create_token.py "monitoring-bot" "Monitoring Service Token"
```

### Using API Tokens

```bash
# Use X-API-Key header instead of Authorization
curl -H "X-API-Key: <your_token>" http://localhost:1250/v1/transcripts
```

## AWS S3/SQS usage clarification

Whereby.com uploads recordings directly to our S3 bucket when meetings end.

SQS Queue (AWS_PROCESS_RECORDING_QUEUE_URL)

Filled by: AWS S3 Event Notifications

The S3 bucket is configured to send notifications to our SQS queue when new objects are created. This is standard AWS infrastructure - not in our codebase.

AWS S3 → SQS Event Configuration:
- Event Type: s3:ObjectCreated:*
- Filter: *.mp4 files
- Destination: Our SQS queue

Our System's Role

Polls SQS every 60 seconds via /server/reflector/worker/process.py:24-62:

# Every 60 seconds, check for new recordings
sqs = boto3.client("sqs", ...)
response = sqs.receive_message(QueueUrl=queue_url, ...)

# Requeue

```bash
uv run /app/requeue_uploaded_file.py TRANSCRIPT_ID
```

## Pipeline Management

### Continue stuck pipeline from final summaries (identify_participants) step:

```bash
uv run python -c "from reflector.pipelines.main_live_pipeline import task_pipeline_final_summaries; result = task_pipeline_final_summaries.delay(transcript_id='TRANSCRIPT_ID'); print(f'Task queued: {result.id}')"
```

### Run full post-processing pipeline (continues to completion):

```bash
uv run python -c "from reflector.pipelines.main_live_pipeline import pipeline_post; pipeline_post(transcript_id='TRANSCRIPT_ID')"
```

.
