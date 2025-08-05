# Task 1: Add WebVTT Field to Transcript Table

## Overview
Add a `webvtt` field to the `transcript` table that stores subtitle data in WebVTT format. WebVTT will be generated after diarization completes, using the existing segmentation logic from `Transcript.as_segments()`.

## Architecture Context

### Current Pipeline Flow
1. **Live Pipeline**: Whisper segments → words → topics (no speakers yet)
2. **Post Pipeline**: Diarization assigns speakers to words in topics
3. **WebVTT Generation**: After diarization completes, generate WebVTT from topics

### Key Insights
- **Words are in topics**: After diarization, `topic.words` contains `Word` objects with speaker assignments
- **Real-time streaming**: Diarization emits topics one-by-one for WebSocket broadcasting
- **Existing segmentation**: `Transcript.as_segments()` already creates caption-like segments based on speaker changes and punctuation
- **Speaker format**: Speakers are integers (0, 1, 2...) - no name mapping exists

## Implementation

### 1. Database Changes

#### Add WebVTT Column
```python
# server/reflector/db/transcripts.py

# Add to transcripts table (~line 79)
sqlalchemy.Column("webvtt", sqlalchemy.Text),

# Add to Transcript model (~line 173) 
webvtt: str | None = None
```

#### Migration
```bash
cd server
uv run alembic revision -m "add_webvtt_field"
```

### 2. WebVTT Generation Utility

#### Create `server/reflector/utils/webvtt.py`
```python
import webvtt
from reflector.processors.types import Word, Transcript

# words_to_webvtt MUST BE WRITTEN TDD (test first)
def words_to_webvtt(words: list[Word]) -> WebVTTText: # branded string
    """Convert words to WebVTT using existing segmentation logic"""
    vtt = webvtt.WebVTT()
    if not words:
        
        return str(vtt)
    
    # Use existing as_segments logic - make it static first
    segments = Transcript.words_to_segments(words)
    
    for segment in segments:
        caption = webvtt.Caption(
            start=webvtt.utils.seconds_to_timestamp(segment.start),
            end=webvtt.utils.seconds_to_timestamp(segment.end),
            text=segment.text.strip()
        )
        if segment.speaker is not None:
            caption.voice = f"Speaker{segment.speaker}"
        vtt.captions.append(caption)
    
    return str(vtt)

# MUST BE WRITTEN TDD (test first)
def topics_to_webvtt(topics: list) -> WebVTTText:
    """Extract all words from topics and generate WebVTT"""
    all_words = []
    for topic in topics:
        if hasattr(topic, 'words') and topic.words:
            all_words.extend(topic.words)
    
    # Sort by timestamp 
    all_words.sort(key=lambda w: w.start)
    return words_to_webvtt(all_words)
```

### 3. Make `as_segments` Static

#### Update `server/reflector/processors/types.py`
```python
class Transcript(BaseModel):
    # ... existing code ...
    # MUST BE WRITTEN TDD (test first)
    @staticmethod
    def words_to_segments(words: list[Word]) -> list[TranscriptSegment]:
        """Static version of segment creation"""
        segments = []
        current_segment = None
        MAX_SEGMENT_LENGTH = 120

        for word in words:
            if current_segment is None:
                current_segment = TranscriptSegment(
                    text=word.text,
                    start=word.start,
                    end=word.end,
                    speaker=word.speaker,
                )
                continue

            # If the word is attach to another speaker, push the current segment
            # and start a new one
            if word.speaker != current_segment.speaker:
                segments.append(current_segment)
                current_segment = TranscriptSegment(
                    text=word.text,
                    start=word.start,
                    end=word.end,
                    speaker=word.speaker,
                )
                continue

            # if the word is the end of a sentence, and we have enough content,
            # add the word to the current segment and push it
            current_segment.text += word.text
            current_segment.end = word.end

            have_punc = PUNC_RE.search(word.text)
            if have_punc and (len(current_segment.text) > MAX_SEGMENT_LENGTH):
                segments.append(current_segment)
                current_segment = None

        if current_segment:
            segments.append(current_segment)

        return segments
    
    def as_segments(self) -> list[TranscriptSegment]:
        """Backward compatibility wrapper"""
        return Transcript.words_to_segments(self.words)
```

### 4. Pipeline Integration

#### Add WebVTT Generation After Diarization
```python
# server/reflector/pipelines/main_live_pipeline.py
from reflector.utils.webvtt import topics_to_webvtt

class PipelineMainDiarization(PipelineMainBase):
    async def create(self) -> Pipeline:
        # ... existing setup code ...
        
        await self.push(audio_diarization_input)
        await self.flush()  # All topics now have speakers assigned
        
        # Generate WebVTT after diarization completes
        transcript = await self.get_transcript()
        if transcript.topics:
            
            webvtt_content = topics_to_webvtt(transcript.topics)
            await transcripts_controller.update(
                transcript,
                {"webvtt": webvtt_content}
            )
        
        return pipeline
```

### 5. Dependencies

#### Add to `server/pyproject.toml`
```toml
webvtt-py = "^0.5.0"
```

### 6. Migration Backfill

#### In migration file
```python
def upgrade():
    # Add column
    op.add_column('transcript', 
        sa.Column('webvtt', sa.Text(), nullable=True)
    )
    
    # Backfill existing data - simple version for now
    # Can be done as separate script if needed

def downgrade():
    op.drop_column('transcript', 'webvtt')
```

## Validation
- WebVTT uses existing segment boundaries (speaker changes + punctuation)
- Speakers are integers as expected (`Speaker0`, `Speaker1`, etc.)
- Generation happens after all speaker assignments complete
- Uses webvtt-py library utilities for proper formatting