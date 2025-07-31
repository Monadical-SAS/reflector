"""
@vibe-generated
"""

from typing import Callable, Optional, Set, Dict, Any, List
from dataclasses import dataclass, field
from reflector.processors.base import PipelineEvent
from reflector.logger import logger


INTERNAL_PROCESSORS = {
    "AudioChunkerProcessor",
    "AudioMergeProcessor",
    "AudioFileWriterProcessor",
    "BroadcastProcessor",
}

DIARIZATION_FILTERED_PROCESSORS = {
    "TopicCollectorProcessor",
}

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

    ignored_processors: Set[str] = field(
        default_factory=lambda: INTERNAL_PROCESSORS.copy()
    )
    enable_diarization: bool = False
    skip_topics_for_diarization: bool = True
    track_progress: bool = False
    progress_callback: Optional[Callable[[str, str, Optional[int]], None]] = None
    collect_events: bool = True
    collected_events: List[Dict[str, Any]] = field(default_factory=list)


def serialize_data(obj: Any) -> Any:
    """Recursively serialize objects to JSON-compatible format"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "__dict__"):
        return {k: serialize_data(v) for k, v in vars(obj).items()}
    elif isinstance(obj, dict):
        return {k: serialize_data(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_data(item) for item in obj]
    else:
        return obj


def create_event_handler(
    config: EventHandlerConfig,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
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

        processors_to_ignore = config.ignored_processors.copy()
        if config.enable_diarization:
            processors_to_ignore.update(DIARIZATION_FILTERED_PROCESSORS)

        if processor in processors_to_ignore:
            return

        if (
            config.enable_diarization
            and config.skip_topics_for_diarization
            and processor == "TranscriptTopicDetectorProcessor"
        ):
            return

        if config.track_progress and config.progress_callback:
            if processor in PROCESSOR_PROGRESS_MAP:
                step_name, progress_pct = PROCESSOR_PROGRESS_MAP[processor]
                await config.progress_callback(processor, step_name, progress_pct)

        data = event.data if hasattr(event, "data") else getattr(event, "output", None)
        serialized_data = serialize_data(data)

        event_dict = {
            "processor": processor,
            "uid": event.uid,
            "data": serialized_data,
        }

        logger.info(f"Event from {processor}: {event.uid}")

        if config.collect_events:
            config.collected_events.append(event_dict)

        if on_event:
            await on_event(event_dict)

    return event_handler


def create_diarization_wrapper(
    processor_name: str,
    processor_uid: str,
    wrapped_callback: Callable[[PipelineEvent], None],
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
        event = PipelineEvent(processor=processor_name, uid=processor_uid, data=data)
        await wrapped_callback(event)

    return wrapper


def create_progress_reporter(
    job_id: str, update_job_status_func: Callable, processing_status: Any = None
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
        processor: str, step_name: str, progress_pct: Optional[int]
    ) -> None:
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
            progress_percentage=progress_pct,
        )

    return report_progress
