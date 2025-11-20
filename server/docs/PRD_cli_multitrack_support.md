# Product Requirements Document: CLI Multitrack Support

## 1. Executive Summary

Extend the existing `reflector/tools/process.py` CLI tool to support multitrack audio processing from Daily.co recordings. This enables the external Evaluator tool to assess diarization quality for both single-track (traditional) and multitrack (per-participant) recordings through a consistent CLI interface.

## 2. Background

### Current State
- **CLI Tool**: `reflector/tools/process.py` processes single audio files with speaker diarization
- **Usage**: External Evaluator tool calls this CLI to generate JSONL output with speaker-labeled transcripts
- **Pipeline**: Uses either "live" (streaming) or "file" (batch) pipeline for processing

### Multitrack Recording Context
- **Daily.co**: Provides separate audio tracks per participant (one WebM file per speaker)
- **Production Flow**: Webhook triggers `process_multitrack_recording()` which processes tracks separately then merges
- **Advantage**: No diarization needed - speaker identity inherent in track separation

### Business Need
The Evaluator tool needs to evaluate transcript quality for multitrack recordings. Rather than build a separate evaluation path, extend the existing CLI to handle multitrack inputs transparently.

## 3. Functional Requirements

### 3.1 CLI Interface

#### New Flag
- Add `--multitrack` flag to indicate multitrack mode
- When present, the `source` argument accepts comma-separated S3 URLs
- When absent, behavior remains unchanged (single file/URL)

#### Command Structure
```bash
# Single track (unchanged)
python -m reflector.tools.process <source> --pipeline [live|file]

# Multitrack (new)
python -m reflector.tools.process <comma-separated-s3-urls> --multitrack
```

#### Argument Behavior
- `source` (positional):
  - Without `--multitrack`: Single file path or S3 URL
  - With `--multitrack`: Comma-separated S3 URLs
- `--pipeline`: NOT required when `--multitrack` is present (multitrack always uses its own pipeline)
- `--source-language`, `--target-language`, `--output`: Work identically for both modes

### 3.2 Input Validation

#### S3 URL Formats
Support both formats:
- `s3://bucket-name/path/to/file.webm`
- `https://bucket-name.s3.amazonaws.com/path/to/file.webm`
- `https://bucket-name.s3.us-east-1.amazonaws.com/path/to/file.webm`
- `https://s3.amazonaws.com/bucket-name/path/to/file.webm`
- `https://s3.us-west-2.amazonaws.com/bucket-name/path/to/file.webm`

#### Validation Requirements
All validation happens in CLI before processing:
1. **Format**: Each URL must be valid S3 format (s3:// or https://)
2. **Count**: At least 1 track required (empty list = error)
3. **Existence**: All S3 objects must exist (use `head_object()` to verify)
4. **Access**: Bucket must be accessible with configured credentials
5. **No file type validation**: Accept any file extension

#### Mixed Buckets
- **Allowed**: Tracks can be in different buckets
- S3 client supports per-operation bucket override via `bucket=` parameter

### 3.3 Output Format

**Unchanged**: Output remains JSONL with topics containing speaker-labeled words
```jsonl
{"words": [{"word": "hello", "start": 0.0, "end": 0.5, "speaker": 0}, ...]}
{"words": [{"word": "world", "start": 0.5, "end": 1.0, "speaker": 1}, ...]}
```

**Speaker Assignment**:
- Track order determines speaker ID
- First track → `speaker: 0`
- Second track → `speaker: 1`
- etc.

### 3.4 Error Handling

#### Pre-processing Validation Errors (CLI level)
- Invalid S3 URL format → Error message with format examples
- No tracks provided → "At least one track required"
- S3 object not found → "Track not found: {url}"
- S3 access denied → "Access denied for bucket: {bucket}. Check AWS credentials"

#### Processing Errors (Pipeline level)
- Let pipeline handle naturally, set transcript status to "error"
- Errors logged but not modified from current behavior

## 4. Technical Implementation

### 4.1 Architecture Flow

```mermaid
graph LR
    A[CLI: process.py] -->|Parse S3 URLs| B[Extract bucket + keys]
    B -->|Create Transcript| C[Database]
    B -->|Skip Room/Meeting| C
    C -->|Call task| D[task_pipeline_multitrack_process]
    D -->|Process| E[PipelineMainMultitrack]
    E -->|Output| F[JSONL]
```

### 4.2 Key Code Locations

#### Files to Modify

**Primary Changes**: `reflector/tools/process.py`
   - Add `--multitrack` argument to CLI parser
   - Add S3 URL parsing function
   - Add validation function for S3 objects
   - Add `process_multitrack_cli()` function
   - Update main routing logic

**Architecture Note**: The implementation bypasses `worker/process.py` and calls `task_pipeline_multitrack_process` directly, following the existing single-track CLI pattern.

#### Implementation Details
```python
# In tools/process.py

async def process_multitrack_cli(
    s3_urls: list[str],
    source_language: str,
    target_language: str,
    output_path: str = None,
):
    """Process multitrack recording from S3 URLs"""
    from reflector.pipelines.main_multitrack_pipeline import task_pipeline_multitrack_process
    from reflector.storage import get_transcripts_storage

    # 1. Parse and validate S3 URLs
    bucket_keys = []
    for url in s3_urls:
        bucket, key = parse_s3_url(url)
        bucket_keys.append((bucket, key))

    # Validate all tracks are in the same bucket
    buckets = set(b for b, _ in bucket_keys)
    if len(buckets) > 1:
        raise ValueError(f"Mixed buckets not supported: {buckets}")

    bucket_name = bucket_keys[0][0]
    track_keys = [key for _, key in bucket_keys]

    # 2. Validate S3 objects exist
    storage = get_transcripts_storage()
    await validate_s3_objects(storage, bucket_keys)

    # 3. Create Transcript without Meeting/Room entities
    transcript = await transcripts_controller.add(
        f"Multitrack CLI ({len(s3_urls)} tracks)",
        source_kind=SourceKind.FILE,
        source_language=source_language,
        target_language=target_language,
        user_id=None,
    )

    # 4. Call multitrack pipeline task
    result = task_pipeline_multitrack_process.delay(
        transcript_id=transcript.id,
        bucket_name=bucket_name,
        track_keys=track_keys,
    )

    # 5. Wait for completion
    while not result.ready():
        print(f"Multitrack pipeline status: {result.state}", file=sys.stderr)
        time.sleep(2)

    # 6. Extract results
    await extract_result_from_entry(transcript.id, output_path)
```

### 4.3 Helper Functions

```python
from urllib.parse import urlparse

def parse_s3_url(url: str) -> tuple[str, str]:
    """Parse S3 URL into bucket and key components"""
    parsed = urlparse(url)

    # s3:// format
    if parsed.scheme == 's3':
        return parsed.netloc, parsed.path.lstrip('/')

    # https:// format - bucket in subdomain
    elif '.s3.' in parsed.netloc or parsed.netloc.endswith('.s3.amazonaws.com'):
        bucket = parsed.netloc.split('.')[0]
        return bucket, parsed.path.lstrip('/')

    # https:// format - bucket in path
    elif parsed.netloc.startswith('s3.'):
        parts = parsed.path.lstrip('/').split('/', 1)
        return parts[0], parts[1] if len(parts) > 1 else ''

    raise ValueError(f"Invalid S3 URL format: {url}")

async def validate_s3_objects(storage, bucket_keys: list[tuple[str, str]]) -> None:
    """Check all S3 objects exist and are accessible"""
    async with storage.session.client("s3") as client:
        for bucket, key in bucket_keys:
            try:
                await client.head_object(Bucket=bucket, Key=key)
            except Exception as e:
                if hasattr(e, 'response'):
                    error_code = e.response.get('Error', {}).get('Code')
                    if error_code == '404':
                        raise ValueError(f"S3 object not found: s3://{bucket}/{key}")
                    elif error_code == '403':
                        raise ValueError(f"Access denied: s3://{bucket}/{key}")
                raise
```

### 4.4 Pipeline Integration

#### Current Multitrack Entry Points
1. **Webhook**: `views/daily.py` → `process_multitrack_recording()` → creates entities → `task_pipeline_multitrack_process()`
2. **CLI (new)**: `tools/process.py` → skip entities → `task_pipeline_multitrack_process()`

#### Task Parameters
```python
# task_pipeline_multitrack_process expects:
{
    "transcript_id": str,
    "bucket_name": str,  # Can differ per track via bucket= param
    "track_keys": list[str]
}
```

### 4.5 Participant Metadata

- **Production**: Fetches names from Daily.co API
- **CLI**: Skip API calls, use generic names "Speaker 0", "Speaker 1", etc.
- Names only affect display, not core functionality

## 5. Examples

### 5.1 Basic Usage

```bash
# Two tracks from same bucket
python -m reflector.tools.process \
  s3://reflector-dailyco-local/track1.webm,s3://reflector-dailyco-local/track2.webm \
  --multitrack \
  --output results.jsonl

# Three tracks with mixed URL formats
python -m reflector.tools.process \
  s3://bucket1/track1.webm,https://bucket2.s3.amazonaws.com/track2.webm,s3://bucket3/track3.webm \
  --multitrack \
  --source-language en \
  --target-language en \
  --output evaluation.jsonl

# Single track for comparison (existing behavior)
python -m reflector.tools.process \
  /path/to/audio.mp3 \
  --pipeline file \
  --output single.jsonl
```

### 5.2 Error Cases

```bash
# Error: No tracks
python -m reflector.tools.process "" --multitrack
> Error: At least one track required

# Error: Invalid URL
python -m reflector.tools.process \
  http://not-s3.com/file.webm,s3://bucket/track.webm \
  --multitrack
> Error: Invalid S3 URL format: http://not-s3.com/file.webm

# Error: Missing --multitrack with commas
python -m reflector.tools.process \
  s3://bucket/track1.webm,s3://bucket/track2.webm \
  --pipeline file
> Error: Multiple files detected. Use --multitrack flag for multitrack processing
```

## 6. Testing Requirements

### 6.1 Unit Tests
- S3 URL parsing (all formats)
- Argument validation logic
- Track count validation

### 6.2 Integration Tests
- CLI with valid multitrack S3 URLs
- CLI with mixed bucket URLs
- Error handling for missing S3 objects
- JSONL output format verification

### 6.3 Manual Testing
- Compare output between single-track with diarization vs multitrack
- Verify speaker IDs match track order
- Test with 1, 2, 3+ tracks

## 7. Dependencies

### External Dependencies
- `boto3` / `aioboto3` - S3 client operations
- `urllib.parse` - URL parsing

### Internal Dependencies
- `reflector.storage` - S3 storage abstraction
- `reflector.pipelines.main_multitrack_pipeline` - Core processing
- `reflector.db` - Database entities

### Configuration Required
- `TRANSCRIPT_STORAGE_AWS_*` environment variables for S3 access

## 8. Technical Notes

The implementation follows the existing single-track CLI pattern of creating Transcripts without Meeting/Room entities. Database schema validation confirms that `meeting_id` and `room_id` are nullable, and the multitrack pipeline operates independently of these entities. All changes are isolated to `tools/process.py`.

## 9. Out of Scope

1. **Local file support** for multitrack (S3 only)
2. **Presigned URL input** (always generate fresh URLs)
3. **File type validation** (accept any extension)
4. **Custom speaker names** (always use generic Speaker 0, 1, 2...)
5. **Progress monitoring** (same as current CLI behavior)
6. **Modifications to production webhook flow**

## 10. Success Criteria

1. **Functional**: Evaluator tool can process multitrack recordings via CLI
2. **Compatible**: Output format identical to single-track (JSONL with speaker labels)
3. **Transparent**: No changes required to Evaluator tool
4. **Reliable**: Proper error messages for invalid inputs
5. **Performant**: No significant overhead vs direct pipeline invocation

## 11. Implementation Plan

### Phase 1: Setup
- Create feature branch
- Verify development environment

### Phase 2: Core Implementation
- Add `--multitrack` argument to CLI parser in `tools/process.py`
- Implement `parse_s3_url()` helper function
- Implement `validate_s3_objects()` validation function
- Implement `process_multitrack_cli()` main function
- Update main routing logic to handle multitrack flag

### Phase 3: Testing
- Unit tests for S3 URL parsing
- Unit tests for validation logic
- Integration tests with mock S3 objects
- End-to-end testing with real Daily.co recordings

### Phase 4: Documentation
- Update CLI help text with multitrack examples
- Add usage examples to README
- Document supported S3 URL formats

## 12. Risk Assessment

| Risk | Impact | Mitigation Strategy |
|------|--------|-------------------|
| S3 permission issues across buckets | Medium | Implement pre-processing validation with clear error messages |
| Breaking changes to existing CLI users | High | Maintain complete backward compatibility for single-track processing |
| Invalid S3 URLs or missing objects | Low | Validate S3 objects using head_object() before processing |
| Mixed bucket processing complexity | Low | Initially restrict to single bucket, document limitation |

## 13. Appendix: Code References

### Key Files
- **CLI Entry**: `reflector/tools/process.py`
- **Multitrack Worker**: `reflector/worker/process.py:174-363`
- **Multitrack Pipeline**: `reflector/pipelines/main_multitrack_pipeline.py`
- **Webhook Handler**: `reflector/views/daily.py:172-214`
- **S3 Storage**: `reflector/storage/storage_aws.py`

### Key Functions
- **Pipeline Task**: `task_pipeline_multitrack_process()` at `main_multitrack_pipeline.py:677`
- **Worker Entry**: `process_multitrack_recording()` at `worker/process.py:174`
- **Pipeline Process**: `PipelineMainMultitrack.process()` at `main_multitrack_pipeline.py:497`

### Environment Variables
```bash
TRANSCRIPT_STORAGE_AWS_BUCKET_NAME=reflector-media
TRANSCRIPT_STORAGE_AWS_REGION=us-east-1
TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID=xxx
TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY=xxx
```

---

**Document Version**: 1.0
**Date**: 2025-11-20
**Status**: Ready for implementation