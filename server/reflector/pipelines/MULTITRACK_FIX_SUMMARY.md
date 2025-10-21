# Multitrack Pipeline Fix Summary

## Problem
Whisper timestamps were incorrect because it ignores leading silence in audio files. Daily.co tracks can have arbitrary amounts of silence before speech starts.

## Solution
**Pad tracks BEFORE transcription using stream metadata `start_time`**

This makes Whisper timestamps automatically correct relative to recording start.

## Key Changes in `main_multitrack_pipeline_fixed.py`

### 1. Added `pad_track_for_transcription()` method (lines 55-172)

```python
async def pad_track_for_transcription(
    self,
    track_data: bytes,
    track_idx: int,
    storage,
) -> tuple[bytes, str]:
```

- Extracts stream metadata `start_time` using PyAV
- Creates PyAV filter graph with `adelay` filter to add padding
- Stores padded track to S3 and returns URL
- Uses same audio processing library (PyAV) already in the pipeline

### 2. Modified `process()` method

#### REMOVED (lines 255-302):
- Entire filename parsing for offsets - NOT NEEDED ANYMORE
- The complex regex parsing of Daily.co filenames
- Offset adjustment after transcription

#### ADDED (lines 371-382):
- Padding step BEFORE transcription:
```python
# PAD TRACKS BEFORE TRANSCRIPTION - THIS IS THE KEY FIX!
padded_track_urls: list[str] = []
for idx, data in enumerate(track_datas):
    if not data:
        padded_track_urls.append("")
        continue

    _, padded_url = await self.pad_track_for_transcription(
        data, idx, storage
    )
    padded_track_urls.append(padded_url)
```

#### MODIFIED (lines 385-435):
- Transcribe PADDED tracks instead of raw tracks
- Removed all timestamp offset adjustment code
- Just set speaker ID - timestamps already correct!

```python
# NO OFFSET ADJUSTMENT NEEDED!
# Timestamps are already correct because we transcribed padded tracks
# Just set speaker ID
for w in t.words:
    w.speaker = idx
```

## Why This Works

1. **Stream metadata is authoritative**: Daily.co sets `start_time` in the WebM container
2. **PyAV respects metadata**: `audio_stream.start_time * audio_stream.time_base` gives seconds
3. **Padding before transcription**: Whisper sees continuous audio from time 0
4. **Automatic alignment**: Word at 51s in padded track = 51s in recording

## Testing

Process the test recording (daily-20251020193458) and verify:
- Participant 0 words appear at ~2s
- Participant 1 words appear at ~51s
- No word interleaving
- Correct chronological order

## Files

- **Original**: `main_multitrack_pipeline.py`
- **Fixed**: `main_multitrack_pipeline_fixed.py`
- **Test data**: `/Users/firfi/work/clients/monadical/reflector/1760988935484-*.webm`