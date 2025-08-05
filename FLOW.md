# Reflector Audio & Text Processing Flow

## Table of Contents
1. [Overview](#overview)
2. [Audio Input Sources](#audio-input-sources)
3. [Data Hierarchy & Transformations](#data-hierarchy--transformations)
4. [Processing Pipeline Architecture](#processing-pipeline-architecture)
5. [Storage & File Management](#storage--file-management)
6. [Current Architecture Details](#current-architecture-details)

## Overview

Reflector processes audio through multiple transformation stages, from raw audio input to semantic topics with speaker identification. This document describes the current implementation of the entire flow.

## Audio Input Sources

```mermaid
graph TB
    subgraph "Input Sources"
        A1[Browser Microphone]
        A2[File Upload]
        A3[Whereby Recording]
    end
    
    subgraph "Entry Points"
        B1[WebRTC Connection]
        B2[Chunked Upload]
        B3[S3 Event/SQS]
    end
    
    subgraph "Processing"
        C1[PipelineMainLive<br/>Real-time]
        C2[Pipeline Process<br/>Async/Celery]
        C3[Pipeline Process<br/>Async/Celery]
    end
    
    A1 --> B1
    A2 --> B2
    A3 --> B3
    
    B1 --> C1
    B2 --> C2
    B3 --> C3
    
    style C1 fill:#e1f5fe
    style C2 fill:#fff3e0
    style C3 fill:#fff3e0
```

### 1. WebRTC Live Streaming
- **Entry**: `/transcripts/{transcript_id}/record/webrtc`
- **Real-time**: Processes audio frames as they arrive
- **Pipeline**: `PipelineMainLive` for immediate transcription

### 2. File Upload
- **Entry**: `/transcripts/{transcript_id}/record/upload`
- **Storage**: `data/{transcript_id}/upload.{ext}`
- **Validation**: Checks for valid audio stream
- **Processing**: Async via Celery task

### 3. Cloud Recordings (Whereby)
- **Automated**: Triggered by S3 bucket events
- **Integration**: Creates recording and transcript entries
- **Processing**: Same pipeline as uploads

## Data Hierarchy & Transformations

### Data Transformation Flow

```mermaid
graph TD
    subgraph "Whisper Output"
        A[WhisperSegments<br/>5-30 seconds each]
        A --> A1[segment.text]
        A --> A2[segment.start/end]
        A --> A3[segment.words array]
    end
    
    subgraph "Current Processing"
        B[Extract Words Only]
        C[Segment Boundaries Not Preserved]
        D[Word List]
    end
    
    subgraph "Diarization"
        E[Speaker Time Ranges]
        F[Assign Speakers to Words]
    end
    
    subgraph "Boundary Creation"
        G[TranscriptLiner<br/>Punctuation-based]
        H[TopicDetector<br/>1000+ chars]
    end
    
    A --> B
    B --> C
    B --> D
    D --> E
    E --> F
    F --> G
    F --> H
    
    style C fill:#ffcccc
    style G fill:#ffe6cc
    style H fill:#ffe6cc
```

#### Data Structure Details

```
WhisperSegments (ORIGINAL):
├── segment.text: "Hello, this is a complete sentence."
├── segment.start: 0.0
├── segment.end: 3.5
└── segment.words: [
      {"word": "Hello", "start": 0.0, "end": 0.5},
      {"word": "this", "start": 0.6, "end": 0.9}
    ]

SEGMENTS NOT PRESERVED IN CURRENT FLOW

Words Only (FLATTENED):
[
  {"text": "Hello", "start": 0.0, "end": 0.5, "speaker": ?},
  {"text": "this", "start": 0.6, "end": 0.9, "speaker": ?}
]

After Diarization:
[
  {"text": "Hello", "start": 0.0, "end": 0.5, "speaker": 0},
  {"text": "this", "start": 0.6, "end": 0.9, "speaker": 0}
]
```

### Current Data Storage Structure

```sql
transcript table:
├── topics (JSON)
│   └── [{
│       "id": "uuid",
│       "title": "LLM-generated title",
│       "summary": "LLM-generated summary",
│       "timestamp": 10.5,
│       "duration": 45.2,
│       "transcript": "Full text of this topic",
│       "words": [{"text": "word", "start": 10.5, "end": 10.8, "speaker": 0}]
│   }]
├── events (JSON)
│   ├── {"event": "STATUS", "data": {"value": "recording"}}
│   ├── {"event": "TRANSCRIPT", "data": {"text": "sentence from liner"}}
│   ├── {"event": "TOPIC", "data": {topic object}}
│   └── {"event": "WAVEFORM", "data": {waveform array}}
└── Other fields (title, short_summary, long_summary, participants)
```

## Processing Pipeline Architecture

### Live Pipeline (Real-time)

```mermaid
graph TD
    A[AudioFrames from WebRTC] --> B[AudioFileWriterProcessor<br/>writes audio.wav]
    B --> C[AudioChunkerProcessor<br/>groups 256 frames]
    C --> D[AudioMergeProcessor<br/>creates AudioFile objects]
    D --> E[AudioTranscriptAutoProcessor<br/>Whisper/Modal]
    E --> E1[Segments to Words<br/>extraction]
    E1 --> F[TranscriptLinerProcessor<br/>sentence boundaries]
    F --> G[TranscriptTranslatorAutoProcessor<br/>if target != source language]
    G --> H[TranscriptTopicDetectorProcessor<br/>LLM creates topics]
    H --> I[(Database<br/>topics & events)]
    
    style E1 fill:#ffcccc
    style B fill:#e8f5e9
    style E fill:#e3f2fd
    style H fill:#fff3e0
```

### Post-Processing Pipeline (After live ends)

```mermaid
graph TB
    Start[Pipeline Post Triggered] --> Split{Parallel Chains}
    
    Split --> Audio[Audio Chain]
    Split --> Text[Text Chain]
    
    Audio --> A1[Waveform Generation<br/>255 segments]
    A1 --> A2[WAV → MP3 Conversion]
    A2 --> A3[Upload to S3]
    A3 --> A4[Delete local WAV]
    A4 --> A5[Diarization<br/>Speaker identification<br/>Updates words in topics]
    A5 --> A6[Consent Cleanup]
    
    Text --> T1[Title Generation<br/>from all topics]
    T1 --> T2[Summary Generation<br/>short & long]
    
    A6 --> Integration
    T2 --> Integration[Integration]
    Integration --> Z[Post to Zulip<br/>if configured]
    
    style A5 fill:#ffe6cc
    style T1 fill:#e8f5e9
    style T2 fill:#e8f5e9
```

## Storage & File Management

### File Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Input: File Upload/Recording
    
    state Input {
        upload_chunks: upload_{0..n}.blob
        merged: upload.mp4
        upload_chunks --> merged: Merge
    }
    
    Input --> Processing: Pipeline Start
    
    state Processing {
        wav: audio.wav
        mp3: audio.mp3
        json: audio.json
        wav --> mp3: Convert
        wav --> json: Waveform
    }
    
    Processing --> Storage: Upload
    
    state Storage {
        s3: S3 Bucket
        local_cleanup: Delete Local Files
        s3 --> local_cleanup
    }
    
    Storage --> [*]: Complete
    
    Processing --> ConsentDenied: No Consent
    Storage --> ConsentDenied: No Consent
    
    state ConsentDenied {
        delete_whereby: Delete from Whereby S3
        delete_storage: Delete from Storage S3
        delete_local: Delete Local Files
        set_flag: audio_deleted = true
    }
    
    ConsentDenied --> [*]: Cleaned
```

### Storage Locations

```mermaid
graph LR
    subgraph "Local Filesystem"
        L1["data/transcript_id/"]
        L2[upload_0..n.blob]
        L3[upload.mp4]
        L4[audio.wav]
        L5[audio.mp3]
        L6[audio.json]
        
        L1 --> L2
        L1 --> L3
        L1 --> L4
        L1 --> L5
        L1 --> L6
    end
    
    subgraph "S3 Storage"
        S1[bucket/]
        S2[transcript_id/audio.mp3]
        S1 --> S2
    end
    
    subgraph "Database"
        D1["audio_location: 'local'"]
        D2["audio_location: 'storage'"]
        D3["audio_deleted: true"]
    end
    
    L5 -.->|Upload| S2
    D1 -.->|Transition| D2
    D2 -.->|Consent Denied| D3
    
    style D3 fill:#ffcccc
```

## Current Architecture Details

### 1. Segment Information Processing
**Current Behavior**: Whisper segments are processed into individual words during transcription.

**Current State**: 
- Speakers are assigned to individual words
- Boundaries are created by different processors
- WebVTT generation will use available word data

**Data Flow**:
```python
# We have this valuable data:
segment = {
    "text": "Hello, how are you today?",
    "start": 0.0,
    "end": 3.5,
    "words": [...]
}

# But we only keep:
words = [
    {"text": "Hello,", "start": 0.0, "end": 0.5},
    {"text": "how", "start": 0.6, "end": 0.9},
    # ...
]
```

### 2. Boundary Creation Methods
**Current Implementation**: Text boundaries are created by different processors:

1. **TranscriptLiner**: Groups by punctuation (., ?, !)
2. **TopicDetector**: Groups by character count (1000+)

**Each processor serves different purposes**:
- Liner: Creates complete sentences for display
- Topics: Creates semantic chunks for LLM processing

### 3. Speaker Assignment Process
**Current Implementation**: Diarization occurs during post-processing.

```mermaid
sequenceDiagram
    participant W as Whisper
    participant L as Live Pipeline
    participant D as Database
    participant P as Post Pipeline
    participant Di as Diarization
    
    W->>L: Segments with words
    Note over L: Extract words from segments
    L->>L: Keep only words
    L->>D: Store words in topics
    Note over D: No speaker info yet!
    
    L->>P: Pipeline ends
    P->>Di: Send audio URL + topics with words
    Di->>P: Speaker time ranges
    P->>P: Assign speakers to words
    Note over P: Assigns to words
    P->>D: Update words with speakers
```

**Diarization Input Data**:
```python
AudioDiarizationInput:
├── audio_url: str  # S3 URL to the audio file
└── topics: list[TitleSummaryWithId]
    └── each topic contains:
        ├── id: str
        ├── title: str
        ├── summary: str
        ├── timestamp: float
        ├── duration: float
        └── words: list[Word]  # Text with timings, no speakers yet
```

**Current Behavior**: 
- Speaker information is at word level
- Topics may contain multiple speakers

### 4. Topic-Based Storage
**Current Design**: Topics are semantic units (typically minutes long) while captions are temporal units (seconds).

**Data Organization**:
```
Topics:    [-----Topic 1 (2 min)-----][----Topic 2 (3 min)----]
           "Discussion about project"  "Planning next steps"

WebVTT:    [Cap1][Cap2][Cap3][Cap4][Cap5][Cap6][Cap7][Cap8]...
           3-5 second captions with speaker changes
```


## Summary

The current architecture processes audio through multiple stages:
- Whisper segments are converted to individual words
- Speaker information is added at the word level during post-processing
- Topics provide semantic organization for summarization
- Different processors create boundaries for different purposes