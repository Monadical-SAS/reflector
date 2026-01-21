"""Hatchet workflow definitions."""

from reflector.hatchet.workflows.daily_multitrack_pipeline import (
    PipelineInput,
    daily_multitrack_pipeline,
)
from reflector.hatchet.workflows.padding_workflow import (
    PaddingInput,
    padding_workflow,
)
from reflector.hatchet.workflows.subject_processing import (
    SubjectInput,
    subject_workflow,
)
from reflector.hatchet.workflows.topic_chunk_processing import (
    TopicChunkInput,
    topic_chunk_workflow,
)
from reflector.hatchet.workflows.transcription_workflow import (
    TranscriptionInput,
    transcription_workflow,
)

__all__ = [
    "daily_multitrack_pipeline",
    "subject_workflow",
    "topic_chunk_workflow",
    "padding_workflow",
    "transcription_workflow",
    "PipelineInput",
    "SubjectInput",
    "TopicChunkInput",
    "PaddingInput",
    "TranscriptionInput",
]
