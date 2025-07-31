"""
@vibe-generated
Common event handling utilities for transcription and diarization processing.
Provides DRY functionality for both CLI and API implementations.

Output Behavior Differences: CLI vs API
========================================

The CLI and API intentionally handle processor outputs differently:

CLI (process_with_diarization.py):
----------------------------------
- Writes raw events directly to JSONL file as they're emitted
- No consolidation or deduplication of events
- Each processor emission is a separate line in the output
- Multiple events with same/overlapping data are preserved
- Useful for debugging and analyzing the full processing pipeline
- Output format: Stream of PipelineEvent objects in JSONL

Example CLI output:
    {"processor": "AudioTranscriptModalProcessor", "uid": "abc123", "data": {"words": [...]}}
    {"processor": "AudioTranscriptModalProcessor", "uid": "abc123", "data": {"words": [...]}}  # Duplicate
    {"processor": "TranscriptLinerProcessor", "uid": "def456", "data": {"words": [...]}}

API (audio_tasks.py -> audio.py):
---------------------------------
- Collects all events in memory via EventHandlerConfig(collect_events=True)
- Applies consolidation via consolidate_results() before returning
- Deduplicates words by timestamp (start/end positions)
- Merges fragmented outputs from the same processor
- Returns cleaner, user-friendly results
- Output format: Consolidated results with deduplicated data

Example API output (after consolidation):
    {
        "AudioTranscriptModalProcessor": [{"words": [...]}],  # Deduplicated
        "TranscriptLinerProcessor": [{"words": [...]}],      # Merged fragments
        "TranscriptFinalTitleProcessor": [{"title": "..."}]
    }

Why This Design?
----------------
- CLI is used for development, debugging, and data analysis
- API is used by applications that need clean, deduplicated results
- The raw event stream (CLI) preserves the complete processing history
- The consolidated output (API) provides a better user experience

To change this behavior, modify the EventHandlerConfig in the respective files.
"""

from typing import Callable, Optional, Set, Dict, Any, List
from dataclasses import dataclass, field
from reflector.processors.base import PipelineEvent
from reflector.logger import logger


# Standard processors to ignore in event processing
INTERNAL_PROCESSORS = {
    "AudioChunkerProcessor",
    "AudioMergeProcessor", 
    "AudioFileWriterProcessor",
    "BroadcastProcessor",
}

# Processors that should be filtered when diarization is enabled
DIARIZATION_FILTERED_PROCESSORS = {
    "TopicCollectorProcessor",
}

# Progress tracking configuration
PROCESSOR_PROGRESS_MAP = {
    "AudioTranscriptAutoProcessor": ("transcription", 20),
    "TranscriptLinerProcessor": ("alignment", 30),
    "TranscriptTranslatorProcessor": ("translation", 40),
    "TranscriptTopicDetectorProcessor": ("topic_detection", 50),
    "TranscriptFinalTitleProcessor": ("title_generation", 60),
    "TranscriptFinalSummaryProcessor": ("summary_generation", 70),
    "AudioDiarizationAutoProcessor": ("diarization", 90),
}


@dataclass
class EventHandlerConfig:
    """Configuration for event handling"""
    # Processors to always ignore
    ignored_processors: Set[str] = field(default_factory=lambda: INTERNAL_PROCESSORS.copy())
    # Whether diarization is enabled
    enable_diarization: bool = False
    # Whether to skip topics when diarization is enabled
    skip_topics_for_diarization: bool = True
    # Whether to track progress
    track_progress: bool = False
    # Callback for progress updates
    progress_callback: Optional[Callable[[str, str, Optional[int]], None]] = None
    # Whether to collect events
    collect_events: bool = True
    # Collected events (if collect_events is True)
    collected_events: List[Dict[str, Any]] = field(default_factory=list)


def serialize_data(obj: Any) -> Any:
    """Recursively serialize objects to JSON-compatible format"""
    if hasattr(obj, 'model_dump'):
        # Handle Pydantic models
        return obj.model_dump()
    elif hasattr(obj, '__dict__'):
        # Handle regular objects
        return {k: serialize_data(v) for k, v in vars(obj).items()}
    elif isinstance(obj, dict):
        return {k: serialize_data(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_data(item) for item in obj]
    else:
        # Return as-is for basic types (str, int, float, bool, None)
        return obj


def create_event_handler(
    config: EventHandlerConfig,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Callable[[PipelineEvent], None]:
    """
    Creates a standardized event handler with filtering, serialization, and progress tracking.
    
    Args:
        config: Configuration for event handling
        on_event: Optional callback for each processed event
        
    Returns:
        Async event handler function
    """
    
    async def event_handler(event: PipelineEvent) -> None:
        processor = event.processor
        
        # Build set of processors to ignore
        processors_to_ignore = config.ignored_processors.copy()
        if config.enable_diarization:
            processors_to_ignore.update(DIARIZATION_FILTERED_PROCESSORS)
        
        # Filter ignored processors
        if processor in processors_to_ignore:
            return
            
        # Filter topic events when diarization is enabled
        if (config.enable_diarization and 
            config.skip_topics_for_diarization and 
            processor == "TranscriptTopicDetectorProcessor"):
            return
            
        # Track progress if enabled
        if config.track_progress and config.progress_callback:
            if processor in PROCESSOR_PROGRESS_MAP:
                step_name, progress_pct = PROCESSOR_PROGRESS_MAP[processor]
                await config.progress_callback(processor, step_name, progress_pct)
            
        # Extract and serialize event data
        data = event.data if hasattr(event, 'data') else getattr(event, 'output', None)
        serialized_data = serialize_data(data)
        
        # Create standardized event dict
        event_dict = {
            "processor": processor,
            "uid": event.uid,
            "data": serialized_data,
        }
        
        # Log the event
        logger.info(f"Event from {processor}: {event.uid}")
        
        # Collect event if enabled
        if config.collect_events:
            config.collected_events.append(event_dict)
        
        # Call the provided handler if any
        if on_event:
            await on_event(event_dict)
    
    return event_handler


def create_diarization_wrapper(
    processor_name: str,
    processor_uid: str,
    wrapped_callback: Callable[[PipelineEvent], None]
) -> Callable[[Any], None]:
    """
    Creates a wrapper that converts raw diarization data to PipelineEvent.
    
    This is needed because diarization processors emit raw data instead of
    PipelineEvent objects, which would cause the standard event handler to fail.
    
    Args:
        processor_name: Name of the diarization processor
        processor_uid: UID of the diarization processor
        wrapped_callback: The event handler to wrap
        
    Returns:
        Async wrapper function
    """
    async def wrapper(data: Any) -> None:
        # Create a PipelineEvent from raw data
        event = PipelineEvent(
            processor=processor_name,
            uid=processor_uid,
            data=data
        )
        # Pass to the wrapped callback
        await wrapped_callback(event)
    
    return wrapper


def create_progress_reporter(
    job_id: str,
    update_job_status_func: Callable,
    processing_status: Any = None
) -> Callable[[str, str, Optional[int]], None]:
    """
    Creates a progress reporter for API job tracking.
    
    Args:
        job_id: The job ID to update
        update_job_status_func: Function to update job status
        processing_status: The status value to use for processing (e.g., JobStatus.PROCESSING)
        
    Returns:
        Async progress reporter function
    """
    async def report_progress(
        processor: str, 
        step_name: str, 
        progress_pct: Optional[int]
    ) -> None:
        # Get processor index for step counting
        processor_list = list(PROCESSOR_PROGRESS_MAP.keys())
        if processor in processor_list:
            step_num = processor_list.index(processor) + 1
            total_steps = len(processor_list)
            step_with_count = f"{step_name} ({step_num}/{total_steps})"
        else:
            step_with_count = step_name
            
        await update_job_status_func(
            job_id,
            processing_status if processing_status else "PROCESSING",
            current_step=step_with_count,
            progress_percentage=progress_pct
        )
    
    return report_progress