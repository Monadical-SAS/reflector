# Implementation Tasks: CLI Multitrack Support

## Overview
Implement multitrack audio processing support in the CLI tool for Daily.co recordings evaluation.

**Primary File**: `reflector/tools/process.py`
**Feature Branch**: `feat/cli-multitrack-support`
**Dependencies**: PRD_cli_multitrack_support.md

---

## Task 1: S3 URL Parser Module

### 1.1 Implement `parse_s3_url()` Function

**Location**: `reflector/tools/process.py` (new function)

**Interface**:
```python
def parse_s3_url(url: str) -> tuple[str, str]:
    """Parse S3 URL into bucket and key components

    Args:
        url: S3 URL in any supported format

    Returns:
        Tuple of (bucket_name, object_key)

    Raises:
        ValueError: Invalid S3 URL format
    """
```

**Existing Code**:
- No existing S3 URL parser found in codebase
- `urllib.parse` is already used in `reflector/utils/url.py` for general URL parsing

**Acceptance Criteria**:
- Parse `s3://bucket/key` format
- Parse `https://bucket.s3.amazonaws.com/key` format
- Parse `https://bucket.s3.region.amazonaws.com/key` format
- Parse `https://s3.amazonaws.com/bucket/key` format
- Parse `https://s3.region.amazonaws.com/bucket/key` format
- Raise descriptive ValueError for invalid formats
- Handle URL-encoded keys correctly

**Test Coverage**:
```python
# tests/test_s3_url_parser.py
test_parse_s3_protocol()
test_parse_https_subdomain()
test_parse_https_path_style()
test_parse_regional_endpoints()
test_invalid_url_formats()
test_url_encoded_keys()
```

---

## Task 2: S3 Object Validator Module

### 2.1 Implement `validate_s3_objects()` Function

**Location**: `reflector/tools/process.py` (new function)

**Interface**:
```python
async def validate_s3_objects(
    storage: Storage,
    bucket_keys: list[tuple[str, str]]
) -> None:
    """Validate S3 objects exist and are accessible

    Args:
        storage: S3 storage client from get_transcripts_storage()
        bucket_keys: List of (bucket, key) tuples

    Raises:
        ValueError: With specific error for missing/inaccessible objects
    """
```

**Existing Infrastructure**:
- `reflector/storage/storage_aws.py` provides `AwsStorage` class with aioboto3 session
- `AwsStorage.session` can be used to create S3 client for `head_object()` calls
- Error handling decorator `@handle_s3_client_errors` exists but not for validation
- Storage supports bucket override via `bucket=` parameter in all operations

**Implementation Note**:
```python
# Use storage's existing session
async with storage.session.client("s3") as client:
    await client.head_object(Bucket=bucket, Key=key)
```

**Acceptance Criteria**:
- Use `head_object()` to verify existence
- Distinguish 404 (not found) from 403 (access denied) errors
- Provide clear error messages with S3 URL in error
- Handle network errors gracefully
- Support multiple buckets in single validation call

**Test Coverage**:
```python
# tests/test_s3_validator.py
test_validate_existing_objects()
test_validate_missing_object_error()
test_validate_access_denied_error()
test_validate_mixed_buckets()
test_validate_network_error_handling()
```

**Dependencies**: Task 1.1 (for error message formatting)

---

## Task 3: CLI Argument Parser Extension

### 3.1 Add `--multitrack` Flag to ArgumentParser

**Location**: `reflector/tools/process.py:main()` function

**Implementation**:
```python
parser.add_argument(
    "--multitrack",
    action="store_true",
    help="Process multiple audio tracks from comma-separated S3 URLs"
)
```

**Acceptance Criteria**:
- Flag is optional (defaults to False)
- When True, `--pipeline` argument becomes optional
- Help text clearly describes multitrack mode
- Mutually exclusive validation with `--pipeline` when multitrack is True

**Test Coverage**:
```python
# tests/test_cli_arguments.py
test_multitrack_flag_default_false()
test_multitrack_flag_true()
test_multitrack_pipeline_mutual_exclusion()
test_help_text_includes_multitrack()
```

---

## Task 4: Multitrack Processing Function

### 4.1 Implement `process_multitrack_cli()` Function

**Location**: `reflector/tools/process.py` (new function)

**Interface**:
```python
async def process_multitrack_cli(
    s3_urls: list[str],
    source_language: str,
    target_language: str,
    output_path: str = None,
) -> None:
    """Process multitrack recording from S3 URLs

    Args:
        s3_urls: List of S3 URLs for audio tracks
        source_language: Source language code
        target_language: Target language code
        output_path: Optional output file path for JSONL

    Raises:
        ValueError: Invalid URLs or validation failures
    """
```

**Existing Infrastructure**:
- `get_transcripts_storage()` from `reflector.storage` provides configured storage
- `transcripts_controller.add()` creates Transcript entities (supports NULL meeting_id/room_id)
- `task_pipeline_multitrack_process.delay()` from `reflector.pipelines.main_multitrack_pipeline`
- `extract_result_from_entry()` already exists in `tools/process.py`

**Acceptance Criteria**:
- Parse all S3 URLs using Task 1.1
- Validate all objects exist using Task 2.1
- Create Transcript entity without Meeting/Room
- Call `task_pipeline_multitrack_process.delay()`
- Poll for completion with status updates to stderr
- Extract JSONL results using existing `extract_result_from_entry()`
- Support mixed bucket URLs (document if not supported initially)

**Test Coverage**:
```python
# tests/test_multitrack_cli.py
test_process_single_track()
test_process_multiple_tracks()
test_process_mixed_buckets()
test_process_invalid_urls()
test_process_missing_objects()
test_transcript_creation_without_entities()
test_pipeline_task_invocation()
test_result_extraction()
```

**Dependencies**: Tasks 1.1, 2.1, 3.1

---

## Task 5: Main Routing Logic Update

### 5.1 Update `main()` Function Routing

**Location**: `reflector/tools/process.py:main()` function

**Implementation Points**:
- Parse source as comma-separated list when `--multitrack` is True
- Route to `process_multitrack_cli()` for multitrack mode
- Maintain existing behavior for single-track mode
- Validate comma presence in source requires `--multitrack` flag

**Acceptance Criteria**:
- Single-track mode unchanged
- Multitrack mode routes to new function
- Error if commas in source without `--multitrack`
- At least one URL required for multitrack
- All existing options work in multitrack mode except `--pipeline`

**Test Coverage**:
```python
# tests/test_main_routing.py
test_single_track_routing_unchanged()
test_multitrack_routing()
test_comma_without_flag_error()
test_empty_multitrack_list_error()
test_existing_options_compatibility()
```

**Dependencies**: Tasks 3.1, 4.1

---

## Task 6: Integration Tests

### 6.1 End-to-End Multitrack Processing

**Location**: `tests/test_e2e_multitrack.py`

**Test Scenarios**:
- Process 2-track recording from S3
- Process 3+ track recording
- Verify speaker IDs match track order
- Compare JSONL output format with single-track
- Test with real Daily.co test recording (if available)

**Acceptance Criteria**:
- Use mocked S3 client for unit tests
- Optional integration test with real S3 (skip if no credentials)
- JSONL output validates against schema
- Speaker labels are 0-indexed integers

---

## Task 7: Documentation Updates

### 7.1 Update CLI Help and README

**Locations**:
- `reflector/tools/process.py` - Docstring updates
- `README.md` - Usage examples section
- `docs/cli_usage.md` - Create if doesn't exist

**Deliverables**:
- Updated `--help` output with multitrack examples
- README section showing multitrack usage
- Document supported S3 URL formats
- Note S3-only limitation for multitrack

---

## Verification Checklist

### Pre-Implementation
- [ ] Verify `transcript` table allows NULL `meeting_id` and `room_id`
- [ ] Confirm `task_pipeline_multitrack_process` signature matches PRD
- [ ] Check AWS credentials available for S3 testing

### Post-Implementation
- [ ] Single-track mode remains unchanged (regression test)
- [ ] Multitrack produces identical JSONL schema
- [ ] Error messages are descriptive and actionable
- [ ] All test suites pass
- [ ] Documentation updated

---

## Task Dependencies Graph

```
1.1 parse_s3_url()
    ├─> 2.1 validate_s3_objects()
    └─> 4.1 process_multitrack_cli()
            └─> 5.1 main() routing
                    └─> 6.1 E2E tests

3.1 --multitrack flag
    └─> 5.1 main() routing

7.1 Documentation (can be done in parallel)
```

---

## Existing Infrastructure Summary

### Available Components
- **Storage**: `AwsStorage` class with full S3 operations (`reflector/storage/storage_aws.py`)
- **Session**: `aioboto3.Session` available via `storage.session`
- **Error Handling**: `@handle_s3_client_errors` decorator for S3 operations
- **Bucket Override**: All storage methods support `bucket=` parameter
- **Controllers**: `transcripts_controller` for entity creation
- **Pipeline**: `task_pipeline_multitrack_process` for processing
- **Utilities**: `extract_result_from_entry()` for JSONL output

### Missing Components (Need Implementation)
- S3 URL parsing function
- S3 object validation using `head_object()`
- Multitrack CLI routing logic

---

## Definition of Done

Each task is considered complete when:
1. Code implemented and passes linting
2. Unit tests written and passing
3. Integration points verified
4. Error cases handled with clear messages
5. Code reviewed and approved
6. Documentation updated where applicable

---

