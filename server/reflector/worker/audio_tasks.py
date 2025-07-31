# @vibe-generated
import asyncio
import json
import os
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import aiohttp
import aioboto3

from celery import shared_task
from reflector.db import database
from reflector.db.jobs import jobs, JobStatus, JobUpdate
from reflector.logger import logger
from reflector.processors import PipelineEvent
from reflector.tools.process import process_audio_file
from reflector.tools.process_with_diarization import process_audio_file_with_diarization
from reflector.storage import get_transcripts_storage
from reflector.utils.s3_temp_file import S3TemporaryFile
from reflector.settings import settings
from reflector.worker.url_validator import check_file_size


async def update_job_status(
    job_id: str,
    status: JobStatus,
    current_step: Optional[str] = None,
    progress_percentage: Optional[int] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None,
    result_data: Optional[List[Dict[str, Any]]] = None,
):
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow(),
    }
    
    if current_step is not None:
        update_data["current_step"] = current_step
    if progress_percentage is not None:
        update_data["progress_percentage"] = progress_percentage
    if error_code is not None:
        update_data["error_code"] = error_code
    if error_message is not None:
        update_data["error_message"] = error_message
    if error_details is not None:
        update_data["error_details"] = error_details
    if result_data is not None:
        update_data["result_data"] = result_data
    if status == JobStatus.COMPLETED:
        update_data["completed_at"] = datetime.utcnow()
    
    query = jobs.update().where(jobs.c.id == job_id).values(**update_data)
    await database.execute(query)


def parse_s3_url(url: str) -> Optional[Tuple[str, str]]:
    """
    Parse S3 URL and return (bucket, key) tuple.
    Handles both s3:// and https:// formats.
    """
    # s3://bucket/key format
    if url.startswith("s3://"):
        parts = url[5:].split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
    
    # https://bucket.s3.amazonaws.com/key format
    # https://s3.amazonaws.com/bucket/key format
    # https://s3.region.amazonaws.com/bucket/key format
    if "s3.amazonaws.com" in url or re.search(r"s3[.-][\w-]+\.amazonaws\.com", url):
        parsed = urlparse(url)
        if parsed.hostname:
            # Virtual-hosted-style
            if ".s3.amazonaws.com" in parsed.hostname or re.match(r".*\.s3[.-][\w-]+\.amazonaws\.com", parsed.hostname):
                bucket = parsed.hostname.split(".s3")[0]
                key = parsed.path.lstrip("/")
                return bucket, key
            # Path-style
            elif parsed.hostname == "s3.amazonaws.com" or re.match(r"s3[.-][\w-]+\.amazonaws\.com", parsed.hostname):
                path_parts = parsed.path.lstrip("/").split("/", 1)
                if len(path_parts) == 2:
                    return path_parts[0], path_parts[1]
    
    return None


async def _download_from_http(audio_url: str, tmp_path: str):
    """Download file from HTTP/HTTPS URL with security checks"""
    async with aiohttp.ClientSession() as session:
        # Check file size before downloading
        is_valid, error = await check_file_size(audio_url, session)
        if not is_valid:
            raise ValueError(f"File validation failed: {error}")
        
        async with session.get(audio_url) as response:
            response.raise_for_status()
            with open(tmp_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)


async def _download_from_s3(audio_url: str, tmp_path: str):
    """Download file from S3 using AWS credentials"""
    parsed = parse_s3_url(audio_url)
    if not parsed:
        # If we can't parse it as an S3 URL, try HTTP download
        # (might be a presigned URL or CloudFront URL)
        await _download_from_http(audio_url, tmp_path)
        return
    
    bucket, key = parsed
    
    # Use the same credentials as the storage configuration
    session = aioboto3.Session(
        aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
        region_name=settings.TRANSCRIPT_STORAGE_AWS_REGION,
    )
    
    async with session.client("s3") as s3:
        try:
            logger.info(f"Downloading from S3: bucket={bucket}, key={key}")
            with open(tmp_path, 'wb') as f:
                await s3.download_fileobj(bucket, key, f)
        except Exception as e:
            logger.error(f"Failed to download from S3: {e}")
            # Fall back to HTTP download if S3 fails
            # (might be a presigned URL that we couldn't parse correctly)
            logger.info("Falling back to HTTP download")
            await _download_from_http(audio_url, tmp_path)


async def download_audio_file(audio_url: str) -> str:
    """
    Download audio file from URL to temporary location with security validation.
    
    Supports:
    - HTTP/HTTPS URLs (validated against allowed domains)
    - S3 URLs (s3://bucket/key)
    - S3 HTTPS URLs (https://bucket.s3.amazonaws.com/key)
    - Reflector storage keys (audio/file.mp4 - uses configured bucket)
    """
    
    suffix = Path(audio_url).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Check if this is a local file path
        if os.path.exists(audio_url):
            # Local file, just copy it
            import shutil
            shutil.copy2(audio_url, tmp_path)
            logger.info(f"Using local file: {audio_url}")
            return tmp_path
        
        # Check if this is a simple storage key (no protocol)
        if not audio_url.startswith(("http://", "https://", "s3://")):
            # Treat as a key in the configured S3 bucket
            bucket = settings.TRANSCRIPT_STORAGE_AWS_BUCKET_NAME
            key = audio_url
            audio_url = f"s3://{bucket}/{key}"
            logger.info(f"Treating as storage key: {key} in bucket {bucket}")
        
        # Check if this is an S3 URL
        if audio_url.startswith("s3://") or "s3.amazonaws.com" in audio_url or re.search(r"s3[.-][\w-]+\.amazonaws\.com", audio_url):
            await _download_from_s3(audio_url, tmp_path)
        else:
            await _download_from_http(audio_url, tmp_path)
        
        logger.info(f"Successfully downloaded audio file to {tmp_path}")
        return tmp_path
    except Exception as e:
        # Clean up the temp file if download failed
        try:
            Path(tmp_path).unlink()
        except:
            pass
        raise


@shared_task(bind=True)
def process_audio_task(
    self,
    job_id: str,
    audio_url: str,
    source_language: str = "en",
    target_language: str = "en",
    only_transcript: bool = True,
    enable_topics: bool = False,
):
    """
    Process audio file and update job status with progress tracking.
    """
    async def _process():
        tmp_path = None
        try:
            # Update job status
            await update_job_status(
                job_id, JobStatus.PROCESSING, current_step="downloading_audio"
            )
            
            # Download audio file
            logger.info(f"Downloading audio from {audio_url}")
            tmp_path = await download_audio_file(audio_url)
            
            from reflector.processors import (
                EventHandlerConfig, 
                create_event_handler,
                create_progress_reporter
            )
            
            progress_reporter = create_progress_reporter(job_id, update_job_status, JobStatus.PROCESSING)
            
            config = EventHandlerConfig(
                enable_diarization=False,
                track_progress=True,
                progress_callback=progress_reporter,
                collect_events=True,
            )
            
            event_callback = create_event_handler(config)
            events = config.collected_events
            
            # Process audio file
            await update_job_status(
                job_id, JobStatus.PROCESSING, current_step="processing (0/6)"
            )
            
            process_only_transcript = only_transcript or not enable_topics
            
            await process_audio_file(
                tmp_path,
                event_callback,
                only_transcript=process_only_transcript,
                source_language=source_language,
                target_language=target_language,
            )
            
            # Update job with results
            await update_job_status(
                job_id,
                JobStatus.COMPLETED,
                current_step="completed",
                result_data=events,
            )
            
            logger.info(f"Job {job_id} completed successfully with {len(events)} events")
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            await update_job_status(
                job_id,
                JobStatus.FAILED,
                error_code="PROCESSING_ERROR",
                error_message=str(e),
                error_details={"exception": type(e).__name__},
            )
            raise
        finally:
            # Clean up temporary file
            if tmp_path and Path(tmp_path).exists():
                try:
                    Path(tmp_path).unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")
    
    # Run the async function
    asyncio.run(_process())


@shared_task(bind=True)
def process_audio_with_diarization_task(
    self,
    job_id: str,
    audio_url: str,
    source_language: str = "en",
    target_language: str = "en",
    only_transcript: bool = False,
    diarization_backend: str = "modal",
):
    """
    Process audio file with diarization and update job status with progress tracking.
    """
    async def _process():
        tmp_path = None
        try:
            # Update job status
            await update_job_status(
                job_id, JobStatus.PROCESSING, current_step="downloading_audio"
            )
            
            # Download audio file
            logger.info(f"Downloading audio from {audio_url}")
            tmp_path = await download_audio_file(audio_url)
            
            from reflector.processors import (
                EventHandlerConfig, 
                create_event_handler,
                create_progress_reporter
            )
            
            progress_reporter = create_progress_reporter(job_id, update_job_status, JobStatus.PROCESSING)
            
            config = EventHandlerConfig(
                enable_diarization=True,
                skip_topics_for_diarization=not only_transcript,
                track_progress=True,
                progress_callback=progress_reporter,
                collect_events=True,
            )
            
            event_callback = create_event_handler(config)
            events = config.collected_events
            
            # Process audio file with diarization
            await update_job_status(
                job_id, JobStatus.PROCESSING, current_step="processing (0/6)"
            )
            
            await process_audio_file_with_diarization(
                tmp_path,
                event_callback,
                only_transcript=only_transcript,
                source_language=source_language,
                target_language=target_language,
                enable_diarization=True,
                diarization_backend=diarization_backend,
            )
            
            # Update job with results
            await update_job_status(
                job_id,
                JobStatus.COMPLETED,
                current_step="completed",
                result_data=events,
            )
            
            logger.info(f"Job {job_id} completed successfully with {len(events)} events")
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            await update_job_status(
                job_id,
                JobStatus.FAILED,
                error_code="PROCESSING_ERROR",
                error_message=str(e),
                error_details={"exception": type(e).__name__},
            )
            raise
        finally:
            # Clean up temporary file
            if tmp_path and Path(tmp_path).exists():
                try:
                    Path(tmp_path).unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")
    
    # Run the async function
    asyncio.run(_process())