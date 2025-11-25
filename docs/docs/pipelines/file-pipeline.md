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
- Maximum size: 2GB (configurable)
- Minimum duration: 5 seconds
- Maximum duration: 6 hours
- Sample rate: Any (will be resampled)

### 2. Pre-processing

**Audio Normalization:**
```python
# Convert to standard format
- Sample rate: 16kHz (Whisper requirement)
- Channels: Mono
- Bit depth: 16-bit
- Format: WAV
```

**Volume Normalization:**
- Target: -23 LUFS (broadcast standard)
- Prevents clipping
- Improves transcription accuracy

**Noise Reduction (Optional):**
- Background noise removal
- Echo cancellation
- High-pass filter for rumble

### 3. Chunking Strategy

**Default Configuration:**
```yaml
chunk_size: 30  # seconds
overlap: 1      # seconds
max_parallel: 10
silence_detection: true
```

**Chunking with Silence Detection:**
- Detects silence periods
- Attempts to break at natural pauses
- Maintains context with overlap
- Preserves sentence boundaries

**Chunk Metadata:**
```json
{
  "chunk_id": "chunk_001",
  "start_time": 0.0,
  "end_time": 30.0,
  "duration": 30.0,
  "has_speech": true,
  "audio_hash": "sha256:..."
}
```

### 4. Transcription Processing

**Whisper Models:**

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny | 39M | Very Fast | 85% | Quick drafts |
| base | 74M | Fast | 89% | Good balance |
| small | 244M | Medium | 91% | Better accuracy |
| medium | 769M | Slow | 93% | High quality |
| large-v3 | 1550M | Very Slow | 96% | Best quality |

**Processing Configuration:**
```python
transcription_config = {
    "model": "whisper-base",
    "language": "auto",  # or specify: "en", "es", etc.
    "task": "transcribe",  # or "translate"
    "temperature": 0,  # deterministic
    "compression_ratio_threshold": 2.4,
    "no_speech_threshold": 0.6,
    "condition_on_previous_text": True,
    "initial_prompt": None,  # optional context
}
```

**Parallel Processing:**
- Each chunk processed independently
- GPU batching for efficiency
- Automatic load balancing
- Failure isolation

### 5. Diarization (Speaker Identification)

**Pyannote 3.1 Pipeline:**

1. **Voice Activity Detection (VAD)**
   - Identifies speech segments
   - Filters out silence and noise
   - Precision: 95%+

2. **Speaker Embedding**
   - Extracts voice characteristics
   - 256-dimensional vectors
   - Speaker-invariant features

3. **Clustering**
   - Groups similar voice embeddings
   - Agglomerative clustering
   - Automatic speaker count detection

4. **Segmentation**
   - Assigns speaker labels to time segments
   - Handles overlapping speech
   - Minimum segment duration: 0.5s

**Configuration:**
```python
diarization_config = {
    "min_speakers": 1,
    "max_speakers": 10,
    "min_duration": 0.5,
    "clustering": "AgglomerativeClustering",
    "embedding_model": "speechbrain/spkrec-ecapa-voxceleb",
}
```

### 6. Alignment & Merging

**Chunk Assembly:**
```python
# Merge overlapping segments
for chunk in chunks:
    # Remove overlap duplicates
    if chunk.start < previous.end:
        chunk.text = resolve_overlap(previous, chunk)

    # Maintain timeline
    merged_transcript.append(chunk)
```

**Speaker Alignment:**
- Map diarization timeline to transcript
- Resolve speaker changes mid-sentence
- Handle multiple speakers per segment

**Quality Checks:**
- Timeline consistency
- No gaps in transcript
- Speaker label continuity
- Confidence score validation

### 7. Post-processing Chain

**Text Formatting:**
- Sentence capitalization
- Punctuation restoration
- Number formatting
- Acronym detection

**Translation (Optional):**
```python
translation_config = {
    "model": "facebook/seamless-m4t-medium",
    "source_lang": "auto",
    "target_langs": ["es", "fr", "de"],
    "preserve_formatting": True
}
```

**Topic Detection:**
- LLM-based analysis
- Extract 3-5 key topics
- Keyword extraction
- Entity recognition

**Summarization:**
```python
summary_config = {
    "model": "openai-compatible",
    "max_length": 500,
    "style": "bullets",  # or "paragraph"
    "include_action_items": True,
    "include_decisions": True
}
```

### 8. Storage & Delivery

**Database Storage:**
```sql
-- Main transcript record
INSERT INTO transcripts (
    id, title, duration, language,
    transcript_text, transcript_json,
    speakers, topics, summary,
    created_at, processing_time
) VALUES (...);

-- Processing metadata
INSERT INTO processing_metadata (
    transcript_id, model_versions,
    chunk_count, total_chunks,
    error_count, warnings
) VALUES (...);
```

**File Storage:**
- Original audio: S3 (optional)
- Processed chunks: Temporary (24h)
- Transcript exports: JSON, SRT, VTT, TXT

**Notification:**
```json
{
  "type": "webhook",
  "url": "https://your-app.com/webhook",
  "payload": {
    "transcript_id": "...",
    "status": "completed",
    "duration": 3600,
    "processing_time": 180
  }
}
```

## Processing Times

**Estimated times for 1 hour of audio:**

| Component | Fast Mode | Balanced | High Quality |
|-----------|-----------|----------|--------------|
| Pre-processing | 10s | 10s | 10s |
| Transcription | 60s | 180s | 600s |
| Diarization | 30s | 60s | 120s |
| Post-processing | 20s | 30s | 60s |
| **Total** | **2 min** | **5 min** | **13 min** |

## Error Handling

### Retry Strategy

```python
@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True
)
def process_chunk(self, chunk_id):
    try:
        # Process chunk
        result = transcribe(chunk_id)
    except Exception as exc:
        # Exponential backoff
        raise self.retry(exc=exc)
```

### Partial Recovery

- Continue with successful chunks
- Mark failed chunks in output
- Provide partial transcript
- Report processing issues

### Fallback Options

1. **Model Fallback:**
   - If large model fails, try medium
   - If GPU fails, try CPU
   - If Modal fails, try local

2. **Quality Degradation:**
   - Reduce chunk size
   - Disable post-processing
   - Skip diarization if needed

## Optimization Tips

### For Speed

1. Use smaller models (tiny/base)
2. Increase parallel chunks
3. Disable diarization
4. Skip post-processing
5. Use GPU acceleration

### For Accuracy

1. Use larger models (medium/large)
2. Enable all pre-processing
3. Reduce chunk size
4. Enable silence detection
5. Multiple pass processing

### For Cost

1. Use Modal spot instances
2. Batch multiple files
3. Cache common phrases
4. Optimize chunk size
5. Selective post-processing

## Monitoring

### Metrics to Track

```python
metrics = {
    "processing_time": histogram,
    "chunk_success_rate": gauge,
    "model_accuracy": histogram,
    "queue_depth": gauge,
    "gpu_utilization": gauge,
    "cost_per_hour": counter
}
```

### Quality Metrics

- Word Error Rate (WER)
- Diarization Error Rate (DER)
- Confidence scores
- Processing speed
- User feedback

### Alerts

- Processing time > 30 minutes
- Error rate > 5%
- Queue depth > 100
- GPU memory > 90%
- Cost spike detected