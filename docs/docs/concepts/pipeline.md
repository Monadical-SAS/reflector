---
sidebar_position: 4
title: Processing Pipeline
---

# Processing Pipeline

Reflector uses a modular pipeline architecture to process audio efficiently and accurately.

## Pipeline Overview

The processing pipeline consists of modular components that can be combined and configured based on your needs:

```mermaid
graph LR
    A[Audio Input] --> B[Pre-processing]
    B --> C[Chunking]
    C --> D[Transcription]
    D --> E[Diarization]
    E --> F[Alignment]
    F --> G[Post-processing]
    G --> H[Output]
```

## Pipeline Components

### Audio Input

Accepts various input sources:
- **File Upload**: MP3, WAV, M4A, WebM, MP4
- **WebRTC Stream**: Live browser audio
- **Recording Integration**: Whereby recordings
- **API Upload**: Direct API submission

### Pre-processing

Prepares audio for optimal processing:
- **Format Conversion**: Convert to 16kHz mono WAV
- **Normalization**: Adjust volume to -23 LUFS
- **Noise Reduction**: Optional background noise removal
- **Validation**: Check duration and quality

### Chunking

Splits audio for parallel processing:
- **Fixed Size**: 30-second chunks by default
- **Overlap**: 1-second overlap for continuity
- **Silence Detection**: Attempt to split at silence
- **Metadata**: Track chunk positions

### Transcription

Converts speech to text:
- **Model Selection**: Whisper or Parakeet
- **Language Detection**: Automatic or specified
- **Timestamp Generation**: Word-level timing
- **Confidence Scores**: Quality indicators

### Diarization

Identifies different speakers:
- **Voice Activity Detection**: Find speech segments
- **Speaker Embedding**: Extract voice characteristics
- **Clustering**: Group similar voices
- **Label Assignment**: Assign speaker IDs

### Alignment

Merges all processing results:
- **Chunk Assembly**: Combine transcription chunks
- **Speaker Mapping**: Align speakers with text
- **Overlap Resolution**: Handle chunk boundaries
- **Timeline Creation**: Build unified timeline

### Post-processing

Enhances the final output:
- **Formatting**: Apply punctuation and capitalization
- **Translation**: Convert to target languages
- **Summarization**: Generate concise summaries
- **Topic Extraction**: Identify key themes
- **Action Items**: Extract tasks and decisions

## Processing Modes

### Batch Processing

For uploaded files:
- Optimized for throughput
- Parallel chunk processing
- Higher accuracy models
- Complete file analysis

### Stream Processing

For live audio:
- Optimized for latency
- Sequential processing
- Real-time feedback
- Progressive results

### Hybrid Processing

For meetings:
- Stream during meeting
- Batch after completion
- Best of both modes
- Maximum accuracy

## Pipeline Configuration

### Model Selection

Choose models based on requirements:

```python
# High accuracy (slower)
config = {
    "transcription_model": "whisper-large-v3",
    "diarization_model": "pyannote-3.1",
    "translation_model": "seamless-m4t-large"
}

# Balanced (default)
config = {
    "transcription_model": "whisper-base",
    "diarization_model": "pyannote-3.1",
    "translation_model": "seamless-m4t-medium"
}

# Fast processing
config = {
    "transcription_model": "whisper-tiny",
    "diarization_model": "pyannote-3.1-fast",
    "translation_model": "seamless-m4t-small"
}
```

### Processing Options

Customize pipeline behavior:

```yaml
# Parallel processing
max_parallel_chunks: 10
chunk_size_seconds: 30
chunk_overlap_seconds: 1

# Quality settings
enable_noise_reduction: true
enable_normalization: true
min_speech_confidence: 0.5

# Post-processing
enable_translation: true
target_languages: ["es", "fr", "de"]
enable_summarization: true
summary_length: "medium"
```

## Performance Characteristics

### Processing Times

For 1 hour of audio:

| Pipeline Config | Processing Time | Accuracy |
|----------------|-----------------|----------|
| Fast | 2-3 minutes | 85-90% |
| Balanced | 5-8 minutes | 92-95% |
| High Accuracy | 15-20 minutes | 95-98% |

### Resource Usage

| Component | CPU Usage | Memory | GPU |
|-----------|-----------|---------|-----|
| Transcription | Medium | 2-4 GB | Required |
| Diarization | High | 4-8 GB | Required |
| Translation | Low | 2-3 GB | Optional |
| Post-processing | Low | 1-2 GB | Not needed |

## Pipeline Orchestration

### Celery Task Chain

The pipeline is orchestrated using Celery:

```python
chain = (
    chunk_audio.s(audio_id) |
    group(transcribe_chunk.s(chunk) for chunk in chunks) |
    merge_transcriptions.s() |
    diarize_audio.s() |
    align_speakers.s() |
    post_process.s()
)
```

### Error Handling

Error recovery:
- **Automatic Retry**: Failed tasks retry up to 3 times
- **Partial Recovery**: Continue with successful chunks
- **Fallback Models**: Use alternative models on failure
- **Error Reporting**: Detailed error messages

### Progress Tracking

Real-time progress updates:
- **Chunk Progress**: Track individual chunk processing
- **Overall Progress**: Percentage completion
- **ETA Calculation**: Estimated completion time
- **WebSocket Updates**: Live progress to clients

## Optimization Strategies

### GPU Utilization

Maximize GPU efficiency:
- **Batch Processing**: Process multiple chunks together
- **Model Caching**: Keep models loaded in memory
- **Dynamic Batching**: Adjust batch size based on GPU memory
- **Multi-GPU Support**: Distribute across available GPUs

### Memory Management

Efficient memory usage:
- **Streaming Processing**: Process large files in chunks
- **Garbage Collection**: Clean up after each chunk
- **Memory Limits**: Prevent out-of-memory errors
- **Disk Caching**: Use disk for large intermediate results

### Network Optimization

Minimize network overhead:
- **Compression**: Compress audio before transfer
- **CDN Integration**: Use CDN for static assets
- **Connection Pooling**: Reuse network connections
- **Parallel Uploads**: Multiple concurrent uploads

## Quality Assurance

### Accuracy Metrics

Monitor processing quality:
- **Word Error Rate (WER)**: Transcription accuracy
- **Diarization Error Rate (DER)**: Speaker identification accuracy
- **Translation BLEU Score**: Translation quality
- **Summary Coherence**: Summary quality metrics

### Validation Steps

Ensure output quality:
- **Confidence Thresholds**: Filter low-confidence segments
- **Consistency Checks**: Verify timeline consistency
- **Language Validation**: Ensure correct language detection
- **Format Validation**: Check output format compliance

## Advanced Features

### Custom Models

Use your own models:
- **Fine-tuned Whisper**: Domain-specific models
- **Custom Diarization**: Trained on your speakers
- **Specialized Post-processing**: Industry-specific formatting

### Pipeline Extensions

Add custom processing steps:
- **Sentiment Analysis**: Analyze emotional tone
- **Entity Extraction**: Identify people, places, organizations
- **Custom Metrics**: Calculate domain-specific metrics
- **Integration Hooks**: Call external services
