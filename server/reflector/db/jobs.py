# @vibe-generated
import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import sqlalchemy
from pydantic import BaseModel, ConfigDict, Field

from reflector.db import metadata


class JobStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(enum.StrEnum):
    TRANSCRIPTION_WITH_DIARIZATION = "transcription_with_diarization"


jobs = sqlalchemy.Table(
    "jobs",
    metadata,
    sqlalchemy.Column(
        "id",
        sqlalchemy.String(36),  # Use String for SQLite compatibility
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    ),
    sqlalchemy.Column("type", sqlalchemy.String(50), nullable=False),
    sqlalchemy.Column(
        "status",
        sqlalchemy.String(20),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    ),
    sqlalchemy.Column("current_step", sqlalchemy.String(100), nullable=True),
    sqlalchemy.Column("progress_percentage", sqlalchemy.Integer(), nullable=True),
    # Request data
    sqlalchemy.Column("request_data", sqlalchemy.JSON(), nullable=False, default=dict),
    # Result data - stores the JSONL output as JSON array
    sqlalchemy.Column("result_data", sqlalchemy.JSON(), nullable=True),
    # Error information
    sqlalchemy.Column("error_code", sqlalchemy.String(50), nullable=True),
    sqlalchemy.Column("error_message", sqlalchemy.Text(), nullable=True),
    sqlalchemy.Column("error_details", sqlalchemy.JSON(), nullable=True),
    # Timestamps
    sqlalchemy.Column(
        "created_at",
        sqlalchemy.DateTime(timezone=True),
        server_default=sqlalchemy.text("CURRENT_TIMESTAMP"),
    ),
    sqlalchemy.Column(
        "updated_at",
        sqlalchemy.DateTime(timezone=True),
        server_default=sqlalchemy.text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    ),
    sqlalchemy.Column(
        "completed_at", sqlalchemy.DateTime(timezone=True), nullable=True
    ),
    # Metadata
    sqlalchemy.Column("metadata", sqlalchemy.JSON(), nullable=False, default=dict),
)


# Pydantic models for API
class JobBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: JobType
    status: JobStatus = JobStatus.PENDING
    current_step: Optional[str] = None
    progress_percentage: Optional[int] = None
    request_data: Dict[str, Any] = Field(default_factory=dict)
    result_data: Optional[List[Dict[str, Any]]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobCreate(BaseModel):
    type: JobType
    request_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class JobInDB(JobBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    current_step: Optional[str] = None
    progress_percentage: Optional[int] = None
    result_data: Optional[List[Dict[str, Any]]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
