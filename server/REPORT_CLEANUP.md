# Diarization Code Cleanup Report

## Overview
This report documents all code that should be cleaned up after the diarization debugging iterations. The analysis compares the current state with the committed code and identifies unnecessary debugging code, redundant logic, and code written under wrong assumptions.

## Files to Clean Up

### 1. `/Users/firfi/work/clients/monadical/reflector/server/reflector/tools/process_with_diarization.py`

This file contains the most debugging code that needs cleanup:

#### A. Excessive Debug Logging (Lines to remove/simplify)
- **Line 142**: `logger.info(f"[DIARIZATION CHECK] enable_diarization={enable_diarization}, only_transcript={only_transcript}, audio_temp_path={audio_temp_path}")`
- **Line 145**: `logger.info(f"[DIARIZATION CHECK] Collected {len(topics)} topics")`
- **Line 148**: `logger.info(f"[DIARIZATION] Starting diarization phase with {len(topics)} topics")`
- **Line 160**: `logger.info(f"Created diarization processor: {diarization_processor.__class__.__name__}, name={getattr(diarization_processor, 'name', 'unknown')}")`
- **Lines 169-180**: All logging inside `diarization_callback` with `[DIARIZATION CALLBACK]` prefix
- **Line 184**: `logger.info(f"[DIARIZATION CALLBACK] Creating PipelineEvent with processor: {processor_name}")`
- **Line 191**: `logger.info(f"[DIARIZATION CALLBACK] Passing wrapped event to main callback")`
- **Line 193**: `logger.info(f"[DIARIZATION CALLBACK] Event callback completed")`
- **Line 217**: `logger.info(f"[DIARIZATION] Uploading audio to S3: {audio_filename}")`
- **Line 222**: `logger.info(f"[DIARIZATION] Audio uploaded to: {audio_url}")`
- **Line 237**: `logger.info(f"[DIARIZATION] Starting diarization with backend: {diarization_backend}")`
- **Line 238**: `logger.info(f"[DIARIZATION] Processing {len(topics)} topics for diarization")`
- **Line 239**: `logger.info(f"[DIARIZATION] Audio file: {audio_temp_path}")`
- **Line 243**: `logger.info(f"[DIARIZATION] Push completed")`
- **Line 245**: `logger.info(f"[DIARIZATION] Flush completed")`
- **Line 262**: `logger.debug(f"[DIARIZATION] Topic '{topic.title[:30]}...' has speaker info")`
- **Line 264-266**: Detailed completion logging with speaker counts
- **Line 271**: `logger.info(f"[DIARIZATION] Cleaning up S3 file: {s3_audio_filename}")`
- **Line 346**: `logger.debug(f"Event: processor={processor}, data_type={type(data).__name__}")`
- **Line 352**: `logger.debug(f"Filtering internal processor: {processor}")`
- **Line 358**: `logger.debug(f"Skipping non-diarized topic event (will be emitted with speakers later)")`
- **Line 366**: `logger.debug(f"[EVENT_CALLBACK] Checking if {processor} is in diarization processors: {processor in diarization_processors}")`
- **Lines 369-375**: Special diarization event detection logging

#### B. Unnecessary Code Constructs
- **Lines 163-164**: Callback counter mechanism (used only for debugging)
  ```python
  # Count callback invocations
  callback_count = 0
  ```
- **Lines 165-194**: The entire `diarization_callback` wrapper function is overly complex for production. Can be simplified to:
  ```python
  diarization_processor.on(event_callback)
  ```
  The wrapping in PipelineEvent is unnecessary since the base Processor.emit() already does this.

- **Lines 250-266**: Speaker counting logic (only used for debug logging)

#### C. Redundant Imports
- **Line 10**: `import sys` - Only used for `sys.exit(1)`, can use `raise SystemExit(1)` instead
- **Line 12**: `import uuid` - Only needed for the unnecessary PipelineEvent wrapping in the callback

#### D. Code Written Under Wrong Assumptions
- **Lines 181-192**: Manual PipelineEvent wrapping - The comment "Diarization processor emits raw TitleSummaryWithId objects" is correct, but the wrapping is unnecessary because this is the expected behavior. All processors emit raw data, and the pipeline handles event wrapping.

### 2. Test Files to Remove (in server root directory)

These files were created during debugging and should be removed:

- **`/Users/firfi/work/clients/monadical/reflector/server/test_diarization_simple.py`** (tracked in git)
  - Contains hardcoded paths specific to developer's machine
  - Temporary debugging script
  
- **`/Users/firfi/work/clients/monadical/reflector/server/test_diarization_complete.py`** (tracked in git)
  - Another debugging script
  - Depends on output from test_diarization_simple.py

### 3. Output Files to Clean Up

These test output files should be removed and added to `.gitignore`:

- `test_audio.mp4` (copied test file)
- `test_diarization_output.jsonl`
- `test_diarization_modal_output.jsonl`
- `test_diarization_output.json`
- `test_transcription_output.json`
- `test_output.log`
- `test_full_output.jsonl`
- `test_output.jsonl`

## Summary of Essential Changes to Keep

After cleanup, the essential changes that should be kept are:

1. **Event Filtering** (lines 357-359): Filter out TranscriptTopicDetectorProcessor events when diarization is enabled
2. **S3 Upload for Modal** (lines 201-228): Upload audio files to S3 for Modal backend (but with reduced logging)
3. **S3 Cleanup** (lines 268-274, 280-285, 289-294): Clean up temporary S3 files after processing
4. **Error Handling**: Exit with code 1 on diarization failures

## Recommended Final Code Structure

The cleaned-up version should:
1. Remove all `[DIARIZATION*]` and `[EVENT_CALLBACK]` debug logging
2. Simplify the diarization callback to just use `event_callback` directly
3. Remove callback counting and detailed speaker analysis
4. Keep only essential info-level logging
5. Remove test files from the server root directory
6. Add test output files to `.gitignore`

## Action Items

1. Clean up `process_with_diarization.py` by removing debug code
2. Delete test files from server root: `test_diarization_simple.py`, `test_diarization_complete.py`
3. Remove all test output files
4. Add `test_*.json*` and `test_*.log` patterns to `.gitignore`
5. Simplify the diarization callback mechanism
6. Remove unnecessary imports