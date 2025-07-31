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
