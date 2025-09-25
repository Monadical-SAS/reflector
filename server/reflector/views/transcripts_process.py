from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import reflector.auth as auth
from reflector.db import get_session
from reflector.db.transcripts import transcripts_controller
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process

router = APIRouter()


class ProcessStatus(BaseModel):
    status: str


@router.post("/transcripts/{transcript_id}/process")
async def transcript_process(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
    session: AsyncSession = Depends(get_session),
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        session, transcript_id, user_id=user_id
    )

    if transcript.locked:
        raise HTTPException(status_code=400, detail="Transcript is locked")

    if transcript.status == "idle":
        raise HTTPException(
            status_code=400, detail="Recording is not ready for processing"
        )

    await task_pipeline_file_process.kiq(transcript_id=transcript_id)

    return ProcessStatus(status="ok")
