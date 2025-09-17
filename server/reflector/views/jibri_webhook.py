from pathlib import Path
from typing import Annotated, Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import reflector.auth as auth
from reflector.db.transcripts import SourceKind, transcripts_controller
from reflector.jibri_events import JitsiEventParser
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process
from reflector.settings import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/jibri", tags=["jibri"])


class RecordingReadyRequest(BaseModel):
    session_id: str
    path: str  # Relative path from recordings directory
    meeting_url: str


@router.post("/recording-ready")
async def handle_recording_ready(
    request: RecordingReadyRequest,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> Dict[str, Any]:
    user_id = user["sub"] if user else None

    recordings_base = Path(settings.JIBRI_RECORDINGS_PATH or "/recordings")
    recording_path = recordings_base / request.path

    if not recording_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Recording path not found: {request.path}"
        )

    recording_file = recording_path / "recording.mp4"
    events_file = recording_path / "events.jsonl"

    if not recording_file.exists():
        raise HTTPException(status_code=404, detail="Recording file not found")

    # Parse events if available
    metadata = {}
    participant_count = 0

    if events_file.exists():
        parser = JitsiEventParser()
        metadata = parser.parse_events_file(str(recording_path))
        participant_count = len(metadata.get("participants", []))
        logger.info(
            "Parsed Jibri events",
            session_id=request.session_id,
            event_count=metadata.get("event_count", 0),
            participant_count=participant_count,
        )
    else:
        logger.warning("No events file found", session_id=request.session_id)
        metadata = {
            "room": {"meeting_url": request.meeting_url, "name": request.session_id},
            "participants": [],
            "speaker_stats": {},
            "event_count": 0,
        }

    # Create transcript using controller
    title = f"Meeting: {metadata.get('room', {}).get('name', request.session_id)}"
    transcript = await transcripts_controller.add(
        name=title,
        source_kind=SourceKind.FILE,
        source_language="en",
        target_language="en",
        user_id=user_id,
    )

    # Store Jitsi data in appropriate fields
    update_data = {}

    # Store participants if available
    if metadata.get("participants"):
        update_data["participants"] = metadata["participants"]

    # Store events data (room info, speaker stats, etc.)
    update_data["events"] = {
        "jitsi_metadata": metadata,
        "session_id": request.session_id,
        "recording_path": str(recording_path),
        "meeting_url": request.meeting_url,
    }

    if update_data:
        await transcripts_controller.update(transcript, update_data)

    # Copy recording file to transcript data path
    # The pipeline expects the file to be in the transcript's data path
    upload_file = transcript.data_path / "upload.mp4"
    upload_file.parent.mkdir(parents=True, exist_ok=True)

    # Create symlink or copy the file
    import shutil

    shutil.copy2(recording_file, upload_file)

    # Update status to uploaded
    await transcripts_controller.update(transcript, {"status": "uploaded"})

    # Trigger processing pipeline
    task_pipeline_file_process.delay(transcript_id=transcript.id)

    logger.info(
        "Jibri recording ready for processing",
        transcript_id=transcript.id,
        session_id=request.session_id,
        participant_count=participant_count,
    )

    return {
        "status": "accepted",
        "transcript_id": transcript.id,
        "session_id": request.session_id,
        "events_found": events_file.exists(),
        "participant_count": participant_count,
    }
