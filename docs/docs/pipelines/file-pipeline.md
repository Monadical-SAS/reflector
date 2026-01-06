---
sidebar_position: 2
title: File Processing Pipeline
---

# File Processing Pipeline

The file processing pipeline handles uploaded audio files, optimizing for accuracy and throughput.

## Pipeline Stages

### 1. Input Stage

**Accepted Formats:**
- MP3 (most common)
- WAV (uncompressed)
- M4A (Apple format)
- WebM (browser recordings)
- MP4 (video with audio track)

**File Validation:**
- Sample rate: Any (will be resampled to 16kHz)

### 2. Pre-processing

**Audio Normalization:**
```yaml
# Convert to standard format
- Sample rate: 16kHz (Whisper requirement)
- Channels: Mono
- Bit depth: 16-bit
- Format: WAV
```

**Noise Reduction (Optional):**
- Background noise removal
- Echo cancellation
- High-pass filter for rumble

### 3. Chunking Strategy

Audio is split into segments for processing:
- Configurable chunk sizes
- Optional silence detection for natural breaks
- Parallel processing of chunks

### 4. Transcription Processing

Transcription uses OpenAI Whisper models via Modal.com or self-hosted GPU:
- Automatic language detection
- Word-level timestamps

### 5. Diarization (Speaker Identification)

Speaker diarization uses Pyannote 3.1:

1. **Voice Activity Detection (VAD)** - Identifies speech segments
2. **Speaker Embedding** - Extracts voice characteristics
3. **Clustering** - Groups similar voices
4. **Segmentation** - Assigns speaker labels to time segments

### 6. Alignment & Merging

- Combines transcription with speaker diarization
- Maps speaker labels to transcript segments
- Resolves timing overlaps
- Validates timeline consistency

### 7. Post-processing Chain

- **Text Formatting**: Punctuation, capitalization
- **Topic Detection**: LLM-based topic extraction
- **Summarization**: AI-generated summaries and action items

### 8. Storage & Delivery

**File Storage:**
- Original audio: S3 (optional)
- Transcript exports: JSON, VTT, TXT

**Notifications:**
- WebSocket updates during processing
- Webhook notifications on completion (optional)