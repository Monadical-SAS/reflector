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
1. **`reflector/tools/process.py`** (main changes):
   - Add `--multitrack` argument
   - Add S3 URL parsing function
   - Add multitrack processing function
   - Route to appropriate pipeline

2. **`reflector/worker/process.py`** (possible minor changes):
   - May need to make Room/Meeting optional (see Open Issues)

#### Key Functions to Add
```python
# In tools/process.py

def parse_s3_url(url: str) -> tuple[str, str]:
    """Parse S3 URL to (bucket, key)"""
    # Handle s3:// and https:// formats

def validate_s3_objects(bucket_keys: list[tuple[str, str]]) -> None:
    """Check all S3 objects exist and are accessible"""
    # Use boto3 head_object()

async def process_multitrack(
    s3_urls: list[str],
    source_language: str,
    target_language: str,
    output_path: str,
):
    """Process multitrack recording"""
    # Parse URLs
    # Validate S3 objects
    # Create Transcript (no Room/Meeting)
    # Call task_pipeline_multitrack_process
```

### 4.3 S3 URL Parsing Logic

```python
from urllib.parse import urlparse

def parse_s3_url(url: str) -> tuple[str, str]:
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

## 8. Open Issues

### Database Entity Dependencies

**Issue**: `process_multitrack_recording()` requires Room and Meeting entities (lines 244-253 in `worker/process.py`).

**Options** (detailed in `docs/cli_multitrack_database_entities.md`):
1. **Skip entities** - Make Room/Meeting optional in code
2. **Dummy entities** - Create placeholder Room/Meeting for CLI
3. **Refactor** - Make pipeline accept optional Room/Meeting

**Recommendation**: Investigate database schema constraints first. If `meeting_id` and `room_id` are nullable in `transcripts` table, implement Option 1. Otherwise, Option 2.

**Decision Required**: Before implementation, check:
```sql
-- Check if these are nullable
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_name = 'transcripts'
AND column_name IN ('meeting_id', 'room_id');
```

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

## 11. Implementation Steps

1. **Phase 1**: Research & Decision
   - Check database schema for nullable constraints
   - Decide on Room/Meeting handling approach
   - Create feature branch

2. **Phase 2**: Core Implementation
   - Add argument parsing in `tools/process.py`
   - Implement S3 URL parsing
   - Add validation logic
   - Implement multitrack processing function

3. **Phase 3**: Integration
   - Handle database entity creation/skipping
   - Connect to multitrack pipeline
   - Ensure output format compatibility

4. **Phase 4**: Testing
   - Unit tests for new functions
   - Integration tests with real S3 files
   - Manual testing with Evaluator tool

5. **Phase 5**: Documentation
   - Update CLI help text
   - Add usage examples to README
   - Document in developer docs

## 12. Risk Mitigation

| Risk | Impact | Mitigation |
|------|---------|------------|
| Database constraints block nullable Room/Meeting | High | Implement dummy entity fallback (Option 2) |
| S3 permission issues across buckets | Medium | Add clear error messages, document IAM requirements |
| Pipeline expects Meeting metadata | Medium | Skip participant name fetching, use generic names |
| Breaking changes to existing CLI users | High | Keep single-track behavior 100% unchanged |

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
**Date**: 2024-11-20
**Author**: Based on research and requirements gathering session
**Status**: Ready for implementation