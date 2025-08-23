# Data Retention and Cleanup

## Overview

For public instances of Reflector, a data retention policy is automatically enforced to delete anonymous user data after a configurable period (default: 7 days). This ensures compliance with privacy expectations and prevents unbounded storage growth.

## Configuration

### Environment Variables

- `PUBLIC_MODE` (bool): Must be set to `true` to enable automatic cleanup
- `PUBLIC_DATA_RETENTION_DAYS` (int): Number of days to retain anonymous data (default: 7)

### What Gets Deleted

When data reaches the retention period, the following items are automatically removed:

1. **Transcripts** from anonymous users (where `user_id` is NULL):
   - Database records
   - Local files (audio.wav, audio.mp3, audio.json waveform)
   - Storage files (S3/cloud storage if configured)
   - Associated WebVTT captions

2. **Meetings** from anonymous users:
   - Meeting records
   - Meeting consent records

3. **Recordings**:
   - Orphaned recordings not referenced by any transcript
   - Associated cloud storage objects

## Automatic Cleanup

### Celery Beat Schedule

When `PUBLIC_MODE=true`, a Celery beat task runs daily at 3 AM to clean up old data:

```python
# Automatically scheduled when PUBLIC_MODE=true
"cleanup_old_public_data": {
    "task": "reflector.worker.cleanup.cleanup_old_public_data",
    "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
}
```

### Running the Worker

Ensure both Celery worker and beat scheduler are running:

```bash
# Start Celery worker
uv run celery -A reflector.worker.app worker --loglevel=info

# Start Celery beat scheduler (in another terminal)
uv run celery -A reflector.worker.app beat
```

## Manual Cleanup

For testing or manual intervention, use the cleanup tool:

```bash
# Dry run - show what would be deleted
uv run python -m reflector.tools.cleanup_old_data --dry-run

# Delete data older than 7 days
uv run python -m reflector.tools.cleanup_old_data

# Delete data older than 30 days
uv run python -m reflector.tools.cleanup_old_data --days 30
```

## Important Notes

1. **User Data Protection**: Only anonymous data (where `user_id` is NULL) is deleted. Authenticated user data is preserved regardless of age.

2. **Storage Cleanup**: The system properly cleans up both local files and cloud storage (S3) when configured.

3. **Error Handling**: If individual deletions fail, the cleanup continues and logs errors. Failed deletions are reported in the task output.

4. **Public Instance Only**: The automatic cleanup task only runs when `PUBLIC_MODE=true` to prevent accidental data loss in private deployments.

## Testing

Run the cleanup tests:

```bash
uv run pytest tests/test_cleanup.py -v
```

## Monitoring

Check Celery logs for cleanup task execution:

```bash
# Look for cleanup task logs
grep "cleanup_old_public_data" celery.log
grep "Starting cleanup of old public data" celery.log
```

Task statistics are logged after each run:
- Number of transcripts deleted
- Number of meetings deleted
- Number of orphaned recordings deleted
- Any errors encountered