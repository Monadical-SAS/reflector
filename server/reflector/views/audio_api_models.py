from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


# Request Models
class AudioProcessOptions(BaseModel):
    source_language: str = Field(default="en", description="Source language code")
    target_language: str = Field(default="en", description="Target language code")
    only_transcript: bool = Field(
        default=True,
        description="If true, only generate transcript without topics/summaries"
    )
    enable_topics: bool = Field(
        default=False,
        description="Enable topic detection, title, and summary generation"
    )
    timeout_ms: int = Field(
        default=600000,
        description="Processing timeout in milliseconds",
        ge=1000,
        le=3600000  # Max 1 hour
    )


class AudioProcessRequest(BaseModel):
    audio_url: HttpUrl = Field(description="URL to the audio file (S3, HTTP, etc.)")
    options: AudioProcessOptions = Field(default_factory=AudioProcessOptions)


class DiarizationBackend(str, Enum):
    MODAL = "modal"
    LOCAL = "local"


class AudioProcessWithDiarizationOptions(BaseModel):
    source_language: str = Field(default="en", description="Source language code")
    target_language: str = Field(default="en", description="Target language code")
    only_transcript: bool = Field(
        default=False,
        description="If true, only generate transcript without topics/summaries"
    )
    diarization_backend: DiarizationBackend = Field(
        default=DiarizationBackend.MODAL,
        description="Diarization backend to use"
    )
    timeout_ms: int = Field(
        default=600000,
        description="Processing timeout in milliseconds",
        ge=1000,
        le=3600000
    )


class AudioProcessWithDiarizationRequest(BaseModel):
    audio_url: HttpUrl = Field(description="URL to the audio file (S3, HTTP, etc.)")
    options: AudioProcessWithDiarizationOptions = Field(
        default_factory=AudioProcessWithDiarizationOptions
    )


# Response Models
class JobCreatedResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    created_at: datetime
    estimated_completion: Optional[datetime] = None


class JobProgress(BaseModel):
    current_step: Optional[str] = None
    percentage: Optional[int] = Field(None, ge=0, le=100)


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    progress: JobProgress
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[Dict[str, Any]] = None


# Result Models (matching the JSONL structure)
class Word(BaseModel):
    text: str
    start: float
    end: float
    speaker: Optional[int] = None


class Segment(BaseModel):
    start: float
    end: float
    text: str
    words: Optional[List[Word]] = None
    speaker: Optional[int] = None


class Topic(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    name: Optional[str] = None
    confidence: Optional[float] = None


class Translation(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    text: Optional[str] = None
    language: Optional[str] = None


class ReflectorOutputData(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    segments: Optional[List[Segment]] = None
    topics: Optional[List[Topic]] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    words: Optional[List[Word]] = None
    translation: Optional[Translation] = None
    transcript: Optional[Dict[str, Any]] = None


class ReflectorOutput(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    processor: str
    uid: Optional[str] = None
    output: Optional[ReflectorOutputData] = None  # Legacy field
    data: Optional[ReflectorOutputData] = None     # Current field
    
    def model_dump(self, **kwargs):
        # Exclude None values and legacy output field
        kwargs['exclude_none'] = True
        kwargs['exclude'] = kwargs.get('exclude', set()) | {'output'}
        return super().model_dump(**kwargs)
    
    def model_dump_json(self, **kwargs):
        # Exclude None values and legacy output field
        kwargs['exclude_none'] = True
        kwargs['exclude'] = kwargs.get('exclude', set()) | {'output'}
        return super().model_dump_json(**kwargs)


class ResultFormat(str, Enum):
    JSONL = "jsonl"
    JSON = "json"


class JobResultsMetadata(BaseModel):
    audio_duration: Optional[float] = None
    processing_time: Optional[float] = None
    processors_used: List[str] = Field(default_factory=list)


class JobResultsResponse(BaseModel):
    job_id: uuid.UUID
    results: List[ReflectorOutput]
    metadata: JobResultsMetadata


# Error Models
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# Health Check Models
class ServiceStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class HealthCheckResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    services: Dict[str, ServiceStatus]