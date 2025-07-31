# @vibe-generated
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Annotated

from fastapi import APIRouter, HTTPException, Query, Response, Depends, Header
from fastapi.responses import JSONResponse
from reflector.db import database
from reflector.db.jobs import jobs, JobStatus, JobType
from reflector.logger import logger
from reflector.worker.result_consolidator import consolidate_results
from reflector.settings import settings
from reflector.views.audio_api_models import (
    DiarizationRequest,
    ErrorDetail,
    ErrorResponse,
    HealthCheckResponse,
    JobCreatedResponse,
    JobProgress,
    JobResultsMetadata,
    JobResultsResponse,
    JobStatusResponse,
    ReflectorOutput,
    ResultFormat,
    ServiceStatus,
)
from reflector.worker.audio_tasks import (
    process_audio_with_diarization_task,
)

class AudioAPIException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(status_code=status_code)


async def audio_api_exception_handler(request, exc: AudioAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details
            )
        ).model_dump()
    )


router = APIRouter()


def verify_ci_evaluation_token(authorization: Optional[str] = Header(None)) -> bool:
    """Verify CI evaluation token from Authorization header."""
    if not authorization:
        return False
    
    if not authorization.startswith("Bearer "):
        return False
        
    token = authorization[7:]  # Remove "Bearer " prefix
    return token == settings.CI_EVALUATION_TOKEN


@router.post(
    "/audio/diarize",
    response_model=JobCreatedResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def diarize_audio(
    request: DiarizationRequest,
    is_valid_token: Annotated[bool, Depends(verify_ci_evaluation_token)],
):
    """Process an audio file with speaker diarization (includes transcription)."""
    # Check CI evaluation token
    if not is_valid_token:
        raise AudioAPIException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Valid CI evaluation token required"
        )
    
    try:
        # Create job in database
        job_id = uuid.uuid4()
        job_data = {
            "id": str(job_id),
            "type": JobType.TRANSCRIPTION_WITH_DIARIZATION,
            "status": JobStatus.PENDING,
            "request_data": {
                "audio_url": str(request.audio_url),
                "options": request.options.model_dump(),
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        query = jobs.insert().values(**job_data)
        await database.execute(query)
        
        # Submit to Celery (diarization includes transcription)
        process_audio_with_diarization_task.apply_async(
            args=[
                str(job_id),
                str(request.audio_url),
                request.options.source_language,
                request.options.target_language,
                False,  # only_transcript - always False for diarization
                request.options.diarization_backend.value,
            ],
            time_limit=request.options.timeout_ms / 1000,
        )
        
        # Estimate completion time
        estimated_completion = datetime.utcnow() + timedelta(minutes=10)
        
        return JobCreatedResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=job_data["created_at"],
            estimated_completion=estimated_completion,
        )
        
    except Exception as e:
        logger.error(f"Error creating diarization job: {e}")
        raise AudioAPIException(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Failed to create diarization job",
            details={"exception": str(e)}
        )


@router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Job not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_job_status(
    job_id: uuid.UUID,
    is_valid_token: Annotated[bool, Depends(verify_ci_evaluation_token)],
):
    """Check the status of a processing job."""
    # Check CI evaluation token
    if not is_valid_token:
        raise AudioAPIException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Valid CI evaluation token required"
        )
    
    try:
        # Validate UUID format to prevent SQL injection
        validated_id = uuid.UUID(str(job_id))
        
        query = jobs.select().where(jobs.c.id == str(validated_id))
        result = await database.fetch_one(query)
        
        if not result:
            raise AudioAPIException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {job_id} not found"
            )
        
        # Build error object if job failed
        error = None
        if result["status"] == JobStatus.FAILED:
            error_details = result["error_details"] or {}
            # Handle SQLite JSON serialization
            if isinstance(error_details, str):
                error_details = json.loads(error_details)
            
            error = {
                "code": result["error_code"] or "UNKNOWN_ERROR",
                "message": result["error_message"] or "Processing failed",
                "details": error_details,
            }
        
        return JobStatusResponse(
            job_id=uuid.UUID(result["id"]),
            status=result["status"],
            progress=JobProgress(
                current_step=result["current_step"],
                percentage=result["progress_percentage"],
            ),
            created_at=result["created_at"],
            updated_at=result["updated_at"],
            completed_at=result["completed_at"],
            error=error,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise AudioAPIException(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Failed to get job status",
            details={"exception": str(e)}
        )


@router.get(
    "/jobs/{job_id}/results",
    response_model=JobResultsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Job not found"},
        400: {"model": ErrorResponse, "description": "Job not completed"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_job_results(
    job_id: uuid.UUID,
    is_valid_token: Annotated[bool, Depends(verify_ci_evaluation_token)],
    format: ResultFormat = Query(default=ResultFormat.JSON),
    include_metadata: bool = Query(default=True),
):
    """Retrieve the results of a completed processing job."""
    # Check CI evaluation token
    if not is_valid_token:
        raise AudioAPIException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Valid CI evaluation token required"
        )
    
    try:
        # Validate UUID format to prevent SQL injection
        validated_id = uuid.UUID(str(job_id))
        
        query = jobs.select().where(jobs.c.id == str(validated_id))
        result = await database.fetch_one(query)
        
        if not result:
            raise AudioAPIException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {job_id} not found"
            )
        
        if result["status"] != JobStatus.COMPLETED:
            raise AudioAPIException(
                status_code=400,
                code="JOB_NOT_COMPLETED",
                message=f"Job is in {result['status']} state, not completed"
            )
        
        # Get result data
        result_data = result["result_data"] or []
        
        # Handle SQLite JSON serialization - if result_data is a string, parse it
        if isinstance(result_data, str):
            result_data = json.loads(result_data)
        
        # Consolidate fragmented results to match CLI behavior
        consolidated_data = consolidate_results(result_data)
        
        # Convert to ReflectorOutput objects
        outputs = []
        
        for item in consolidated_data:
            output_data = item.get("data")
            
            output = ReflectorOutput(
                processor=item.get("processor", "Unknown"),
                uid=item.get("uid"),
                data=output_data,
            )
            outputs.append(output)
        
        # Calculate metadata
        metadata = JobResultsMetadata()
        
        if include_metadata and result["metadata"]:
            job_metadata = result["metadata"]
            metadata.audio_duration = job_metadata.get("audio_duration")
            metadata.processing_time = job_metadata.get("processing_time")
        
        # Return based on format
        if format == ResultFormat.JSONL:
            # Return as newline-delimited JSON with consolidated results
            jsonl_lines = []
            for item in consolidated_data:
                # Return the raw data as stored by the worker
                jsonl_lines.append(json.dumps(item))
            
            content = "\n".join(jsonl_lines)
            return Response(
                content=content,
                media_type="application/x-ndjson",
                headers={
                    "Content-Disposition": f"attachment; filename=job_{job_id}_results.jsonl"
                },
            )
        
        # Default JSON format
        return JobResultsResponse(
            job_id=uuid.UUID(result["id"]),
            results=outputs,
            metadata=metadata,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job results: {e}", exc_info=True)
        raise AudioAPIException(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Failed to get job results",
            details={"exception": str(e)}
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
)
async def health_check():
    """Check if the API service is available and healthy."""
    try:
        # Check database connectivity
        db_status = ServiceStatus.AVAILABLE
        try:
            await database.execute("SELECT 1")
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_status = ServiceStatus.UNAVAILABLE
        
        # Check if we can import required processors
        transcription_status = ServiceStatus.AVAILABLE
        diarization_status = ServiceStatus.AVAILABLE
        translation_status = ServiceStatus.AVAILABLE
        
        try:
            pass
        except Exception as e:
            logger.error(f"Transcription import check failed: {e}")
            transcription_status = ServiceStatus.UNAVAILABLE
        
        try:
            pass
        except Exception as e:
            logger.error(f"Diarization import check failed: {e}")
            diarization_status = ServiceStatus.UNAVAILABLE
        
        try:
            pass
        except Exception as e:
            logger.error(f"Translation import check failed: {e}")
            translation_status = ServiceStatus.UNAVAILABLE
        
        # Overall health status
        all_services = [
            db_status,
            transcription_status,
            diarization_status,
            translation_status,
        ]
        
        if all(s == ServiceStatus.AVAILABLE for s in all_services):
            overall_status = "healthy"
        elif any(s == ServiceStatus.UNAVAILABLE for s in all_services):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
        
        response = HealthCheckResponse(
            status=overall_status,
            version="1.0.0",
            services={
                "database": db_status,
                "transcription": transcription_status,
                "diarization": diarization_status,
                "translation": translation_status,
            },
        )
        
        # Return 503 if unhealthy
        if overall_status == "unhealthy":
            raise HTTPException(status_code=503, detail=response.model_dump())
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during health check: {e}")
        raise AudioAPIException(
            status_code=503,
            code="HEALTH_CHECK_FAILED",
            message="Health check encountered an error",
            details={"exception": str(e)}
        )