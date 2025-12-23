"""Hatchet workflow definitions."""

from reflector.hatchet.workflows.diarization_pipeline import (
    PipelineInput,
    diarization_pipeline,
)
from reflector.hatchet.workflows.subject_processing import (
    SubjectInput,
    subject_workflow,
)
from reflector.hatchet.workflows.topic_chunk_processing import (
    TopicChunkInput,
    topic_chunk_workflow,
)
from reflector.hatchet.workflows.track_processing import TrackInput, track_workflow

__all__ = [
    "diarization_pipeline",
    "subject_workflow",
    "topic_chunk_workflow",
    "track_workflow",
    "PipelineInput",
    "SubjectInput",
    "TopicChunkInput",
    "TrackInput",
]
