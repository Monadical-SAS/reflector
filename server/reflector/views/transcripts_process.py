from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import reflector.auth as auth
from reflector.db.transcripts import transcripts_controller
from reflector.services.transcript_process import (
    ProcessError,
    ValidationAlreadyScheduled,
    ValidationError,
    ValidationLocked,
    ValidationOk,
    dispatch_transcript_processing,
    prepare_transcript_processing,
    validate_transcript_for_processing,
)
from reflector.utils.match import absurd

router = APIRouter()


class ProcessStatus(BaseModel):
    status: str


@router.post("/transcripts/{transcript_id}/process")
async def transcript_process(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> ProcessStatus:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    validation = await validate_transcript_for_processing(transcript)
    if isinstance(validation, ValidationLocked):
        raise HTTPException(status_code=400, detail=validation.detail)
    elif isinstance(validation, ValidationError):
        raise HTTPException(status_code=400, detail=validation.detail)
    elif isinstance(validation, ValidationAlreadyScheduled):
        return ProcessStatus(status=validation.detail)
    elif isinstance(validation, ValidationOk):
        pass
    else:
        absurd(validation)

    config = await prepare_transcript_processing(validation)

    if isinstance(config, ProcessError):
        raise HTTPException(status_code=500, detail=config.detail)
    else:
        dispatch_transcript_processing(config)
        return ProcessStatus(status="ok")
