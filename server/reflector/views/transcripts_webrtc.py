from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

import reflector.auth as auth
from reflector.db.transcripts import transcripts_controller

from .rtc_offer import RtcOffer, rtc_offer_base

router = APIRouter()


@router.post("/transcripts/{transcript_id}/record/webrtc")
async def transcript_record_webrtc(
    transcript_id: str,
    params: RtcOffer,
    request: Request,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    if transcript.locked:
        raise HTTPException(status_code=400, detail="Transcript is locked")

    # create a pipeline runner
    from reflector.pipelines.main_live_pipeline import PipelineMainLive

    pipeline_runner = PipelineMainLive(transcript_id=transcript_id)

    # FIXME do not allow multiple recording at the same time
    return await rtc_offer_base(
        params,
        request,
        pipeline_runner=pipeline_runner,
    )
