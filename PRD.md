# Product Requirements Document: Diarization CLI Tool

## Executive Summary

This PRD defines requirements for enhancing the existing diarization CLI functionality in Reflector. While a basic implementation exists (`process_with_diarization.py`), it requires improvements to be production-ready. The goal is to provide a robust command-line tool that adds speaker identification to audio transcriptions, supporting both local and cloud-based processing.

## Current State

### Existing Implementation
- **File**: `server/reflector/tools/process_with_diarization.py`
- **Status**: Basic functionality implemented but needs refinements
- **Features**: Transcription + diarization in a single pipeline
- **Backends**: Local (pyannote) and Modal (cloud GPU)

### Test Assets
- **Location**: `/Users/firfi/work/clients/monadical/transcription-eval/files/`
- **Test File**: `40e7fc3c-6144-47a7-ba51-00591590046d-2025-07-22T14_56_47Z_cut.mp4`
- **Duration**: 4.5 minutes (270 seconds)
- **Content**: Multi-speaker conversation (Max, Jordan, Nikita)

## User Stories

1. **As a developer**, I want to transcribe audio files with speaker identification via CLI so I can process recordings without using the web interface.

2. **As a data analyst**, I want to process existing transcripts to add speaker information so I can analyze who said what in recorded meetings.

3. **As a researcher**, I want to batch process multiple audio files with diarization so I can efficiently analyze interview data.

4. **As a CI/CD engineer**, I want predictable CLI output formats so I can integrate diarization into automated pipelines.

## Functional Requirements

### Core Features

#### 1. Two-Mode Operation
- **Integrated Mode**: Single command for transcription + diarization
- **Separate Mode**: Diarization-only for existing transcripts

#### 2. Input Support
- Audio formats: MP3, WAV, MP4, M4A, FLAC, OGG
- Video formats: MP4, MOV, AVI (audio track extraction)
- Transcript formats: JSONL from Reflector transcription

#### 3. Backend Selection
- **Local Backend**: PyAnnote-based, runs on CPU/GPU
- **Modal Backend**: Cloud GPU processing
- **Auto Selection**: Choose best available backend

#### 4. Output Formats
- **JSONL**: Default format with speaker-annotated words
- **Plain Text**: Human-readable transcript with speaker labels
- **SRT/VTT**: Subtitle formats with speaker identification
- **JSON**: Structured output for programmatic access

### Command-Line Interface

#### Integrated Mode (Enhanced Current Tool)
```bash
# Basic usage with diarization
uv run python -m reflector.tools.process audio.mp4 --enable-diarization

# With output file
uv run python -m reflector.tools.process audio.mp4 -d -o output.jsonl

# Select backend
uv run python -m reflector.tools.process audio.mp4 -d --diarization-backend modal

# Configure diarization parameters
uv run python -m reflector.tools.process audio.mp4 -d --min-speakers 2 --max-speakers 5
```

#### Separate Diarization Tool (New)
```bash
# Diarize existing transcript
uv run python -m reflector.tools.diarize transcript.jsonl audio.mp4 -o diarized.jsonl

# With audio URL
uv run python -m reflector.tools.diarize transcript.jsonl --audio-url https://example.com/audio.mp4

# Export to different format
uv run python -m reflector.tools.diarize transcript.jsonl audio.mp4 --format srt -o output.srt
```

### Configuration

#### Environment Variables
```bash
# Backend selection
DIARIZATION_BACKEND=local|modal

# Local backend
HF_TOKEN=your_huggingface_token
DIARIZATION_DEVICE=cuda|cpu

# Modal backend
LLM_MODAL_API_KEY=your_modal_key
DIARIZATION_URL=https://your-modal-endpoint

# Processing options
DIARIZATION_MIN_SPEAKERS=1
DIARIZATION_MAX_SPEAKERS=10
```

## Technical Requirements

### Dependencies

#### Local Backend
```toml
[dependencies]
pyannote-audio = "^3.1.0"
torch = "^2.0.0"
torchaudio = "^2.0.0"
```

#### Common Dependencies
```toml
av = "^10.0.0"  # Audio processing
httpx = "^0.24.0"  # File downloads
pydantic = "^2.0.0"  # Data validation
```

### Architecture

#### Processing Pipeline
```
Audio File → Chunking → Transcription → Topic Detection → Diarization → Output
                                              ↓
                                    [Temporary Audio File]
```

#### Component Structure
```
reflector/tools/
├── process_with_diarization.py  # Enhanced integrated tool
├── diarize.py                   # New standalone tool
└── common/
    ├── audio_utils.py          # Shared audio processing
    ├── jsonl_parser.py         # JSONL parsing utilities
    └── output_formatters.py    # Format converters
```

### Error Handling

1. **Missing Dependencies**: Clear error messages with installation instructions
2. **Authentication Failures**: Guide users to set up HF_TOKEN or Modal keys
3. **Audio Format Issues**: Attempt conversion or provide format requirements
4. **Partial Failures**: Save intermediate results, allow resumption
5. **Resource Limits**: Handle memory/timeout issues gracefully

### Performance Requirements

- Process 1 hour of audio in < 5 minutes (local, CPU)
- Process 1 hour of audio in < 2 minutes (Modal, GPU)
- Memory usage < 4GB for typical recordings
- Support concurrent processing of multiple files
- Progress reporting at 10-second intervals

## User Experience

### Progress Reporting
```
Processing: audio.mp4
[1/5] Extracting audio... done (2.3s)
[2/5] Transcribing... ████████░░ 80% (45.2s)
[3/5] Detecting topics... done (3.1s)
[4/5] Identifying speakers... ████░░░░░░ 40% (12.5s)
[5/5] Generating output... done (0.5s)

✓ Completed in 1m 23s
  Speakers detected: 3
  Output saved to: output.jsonl
```

### Error Messages
```
✗ Error: Diarization backend not available
  
  The local diarization backend requires additional dependencies.
  
  To fix this issue:
  1. Install dependencies: uv pip install pyannote.audio torch torchaudio
  2. Set HuggingFace token: export HF_TOKEN=your_token
  3. Accept model license at: https://huggingface.co/pyannote/speaker-diarization-3.1
  
  Alternatively, use --diarization-backend modal with proper credentials.
```

## Testing Strategy

### Test Cases

1. **Basic Functionality**
   - Process test MP4 file with default settings
   - Verify speaker assignments match expected output
   - Compare with existing diarized.txt reference

2. **Format Support**
   - Test each supported audio/video format
   - Verify JSONL parsing and reconstruction
   - Test output format conversions

3. **Error Scenarios**
   - Missing dependencies
   - Invalid audio files
   - Network failures (Modal backend)
   - Insufficient permissions

4. **Performance**
   - Benchmark processing times
   - Monitor memory usage
   - Test concurrent processing

### Test Commands
```bash
# Basic test
uv run python -m reflector.tools.process_with_diarization \
  /Users/firfi/work/clients/monadical/transcription-eval/files/40e7fc3c-6144-47a7-ba51-00591590046d-2025-07-22T14_56_47Z_cut.mp4 \
  -d -o test_output.jsonl

# Verify output
grep '"speaker": 1' test_output.jsonl | wc -l  # Count speaker 1 words
grep '"speaker": 2' test_output.jsonl | wc -l  # Count speaker 2 words

# Compare with reference
diff test_output.jsonl expected_output.jsonl
```

## Implementation Plan

### Phase 1: Enhance Existing Tool (Week 1)
1. Add error handling and recovery
2. Implement progress reporting
3. Add configuration options (min/max speakers)
4. Fix temporary file cleanup
5. Add comprehensive logging

### Phase 2: Create Standalone Tool (Week 2)
1. Implement `diarize.py` for existing transcripts
2. Add JSONL parsing utilities
3. Implement output formatters (SRT, VTT, plain text)
4. Add batch processing support
5. Create shared utilities module

### Phase 3: Testing & Documentation (Week 3)
1. Write unit tests for all components
2. Create integration tests with test files
3. Write user documentation
4. Add example scripts
5. Performance optimization

### Phase 4: Production Readiness (Week 4)
1. Handle edge cases
2. Add telemetry/monitoring hooks
3. Create Docker image with dependencies
4. CI/CD integration
5. Release preparation

## Success Metrics

1. **Functionality**: Successfully process test file with correct speaker identification
2. **Performance**: Meet processing time targets for various file sizes
3. **Reliability**: < 1% failure rate on supported formats
4. **Usability**: Clear documentation, helpful error messages
5. **Adoption**: Integration into existing workflows

## Future Enhancements

1. **Streaming Support**: Process audio streams in real-time
2. **Speaker Profiles**: Save and recognize known speakers
3. **Language Models**: Improve diarization with transcript context
4. **Web UI Integration**: Expose CLI functionality via web interface
5. **Cloud Storage**: Direct processing from S3/GCS URLs
6. **Speaker Embedding Export**: Save voice prints for analysis

## Appendix

### A. Existing Code Structure

```python
# Current pipeline in process_with_diarization.py
pipeline = Pipeline(
    AudioChunkerProcessor(),
    AudioMergeProcessor(),
    AudioFileWriterProcessor(audio_path),  # Saves for diarization
    AudioTranscriptAutoProcessor(),
    TranscriptLinerProcessor(),
    TranscriptTranslatorProcessor(),
    TopicCollectorProcessor(),  # Collects for diarization
    TranscriptTopicDetectorProcessor(),
    TranscriptFinalTitleProcessor(),
    TranscriptFinalSummaryProcessor(),
)
```

### B. Diarization Data Flow

```python
# Input structure
AudioDiarizationInput(
    audio_url="path/to/audio.wav",
    topics=[
        TitleSummaryWithId(
            id="topic_1",
            title="Introduction",
            summary="...",
            timestamp=0.0,
            duration=30.0,
            transcript=Transcript(
                words=[
                    Word(text=" Hello", start=0.5, end=1.0, speaker=0),
                    # ... more words
                ]
            )
        )
    ]
)

# Output: Same structure with updated speaker IDs
```

### C. Dependencies Installation

```bash
# For local development
uv pip install pyannote.audio torch torchaudio

# For production Docker image
RUN pip install pyannote.audio torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```
