# LLM Text Processing Chunking Analysis

## Executive Summary

Many LLM-based processors in Reflector send entire transcript texts without chunking, which can cause failures for long recordings. A typical 1-hour meeting generates 50,000-75,000 characters (~10,000-15,000 tokens), easily exceeding API limits and context windows.

## Current LLM Token Limits and Context Windows

- **Default LLM max tokens**: 1,024 (output limit)
- **Summary LLM context window**: 16,000 tokens
- **Minimum transcript length for processing**: 750 characters
- **Maximum chunk length for summarizer**: 1,024 tokens

## Processors Sending Full Transcripts to LLMs

### 1. TranscriptTopicDetectorProcessor
**Current behavior**: 
- Accumulates transcript until MIN_TRANSCRIPT_LENGTH (750 chars)
- Sends entire accumulated text to LLM
- No upper limit or chunking

**Text volume for 1-hour meeting**: 
- ~10,000-15,000 words
- ~50,000-75,000 characters
- ~10,000-15,000 tokens

**Risk**: High - Will fail on recordings longer than ~1.5 hours with typical LLM context limits

### 2. TranscriptTranslatorProcessor
**Current behavior**:
- Sends `transcript.text` in single API call
- No chunking implementation
- No handling for API token limits

**Text volume**: Same as above (entire transcript)

**Risk**: Critical - Translation APIs have strict token limits (typically 5,000-10,000 tokens)

### 3. SummaryBuilder Operations

#### a. identify_participants()
- **Sends**: Full transcript + prompt
- **Text volume**: Entire transcript
- **Risk**: Medium - Simple extraction task but still sends full text

#### b. identify_transcription_type()
- **Sends**: Full transcript + prompt
- **Text volume**: Entire transcript
- **Risk**: Medium - Classification task that doesn't need full context

#### c. generate_items() (action items, decisions, questions)
- **Sends**: Full transcript + subjects + summaries + prompt
- **Text volume**: Entire transcript PLUS additional context
- **Risk**: High - Even larger than raw transcript

#### d. deduplicate_items()
- **Sends**: Full transcript + all items + prompt
- **Text volume**: Entire transcript PLUS items list
- **Risk**: High - Compounds the problem with additional data

### 4. TranscriptFinalTitleProcessor
**Current behavior**: 
- Has chunking via `split_corpus()`
- Only processes titles (small text)
- **Risk**: Low - Already handles chunking well

### 5. TranscriptFinalSummaryProcessor
**Current behavior**:
- Uses sophisticated template-aware chunking
- 16,000 token context window
- Handles overlap and natural boundaries
- **Risk**: Low - Best implementation in the codebase

## Processors That Would Benefit Most from Chunking

### Critical Priority
1. **TranscriptTranslatorProcessor**
   - Currently sends unlimited text
   - Translation APIs have strict limits
   - Would fail on any recording >30 minutes

2. **TranscriptTopicDetectorProcessor**
   - No upper limit on text size
   - Generates topics for entire accumulated text
   - Should use sliding window approach

### High Priority
3. **SummaryBuilder.generate_items()**
   - Sends full transcript multiple times (once per item type)
   - Could use targeted extraction on relevant chunks

4. **SummaryBuilder.deduplicate_items()**
   - Processes full transcript for context
   - Could work with item descriptions alone

### Medium Priority
5. **SummaryBuilder.identify_participants()**
   - Could scan chunks for speaker names
   - Doesn't need full transcript context

6. **SummaryBuilder.identify_transcription_type()**
   - Could classify based on first few minutes
   - Wasteful to send entire transcript

## Recommended Chunking Strategies

### 1. Translation (Critical)
```python
# Chunk by tokens with overlap
chunk_size = 4096 tokens
overlap = 512 tokens (12.5%)
preserve sentence boundaries
```

### 2. Topic Detection
```python
# Sliding window approach
window_size = 5000 tokens
slide_by = 2500 tokens
aggregate topics across windows
```

### 3. Item Extraction
```python
# Process by topic chunks
for each topic_summary:
    extract items from topic.transcript
    limit context to relevant sections
```

### 4. Participant Identification
```python
# Scan first 10 minutes + sampling
process first 10 minutes fully
sample 1 minute every 10 minutes after
```

## Implementation Priority

1. **Phase 1 - Critical**: TranscriptTranslatorProcessor
   - Implement token-aware chunking
   - Preserve sentence boundaries
   - Handle chunk coordination

2. **Phase 2 - High Impact**: TranscriptTopicDetectorProcessor
   - Implement sliding window
   - Aggregate topics across windows
   - Prevent duplicate topics

3. **Phase 3 - Optimization**: SummaryBuilder operations
   - Refactor to process chunks
   - Reduce redundant full-text sends
   - Improve efficiency for long recordings

## Expected Benefits

- **Reliability**: Handle recordings of any length without API failures
- **Cost**: Reduce LLM API costs by 50-70% through targeted processing
- **Performance**: Faster processing through parallelization
- **Scalability**: Support multi-hour recordings and large meetings