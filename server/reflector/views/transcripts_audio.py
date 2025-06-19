"""
Transcripts audio related endpoints
===================================

"""

from typing import Annotated, Optional

import httpx
import reflector.auth as auth
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import jwt
from reflector.db.transcripts import AudioWaveform, transcripts_controller
from reflector.settings import settings
from reflector.views.transcripts import ALGORITHM

from ._range_requests_response import range_requests_response

router = APIRouter()


@router.get(
    "/transcripts/{transcript_id}/audio/mp3",
    operation_id="transcript_get_audio_mp3",
)
@router.head(
    "/transcripts/{transcript_id}/audio/mp3",
    operation_id="transcript_head_audio_mp3",
)
async def transcript_get_audio_mp3(
    request: Request,
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
    token: str | None = None,
):
    user_id = user["sub"] if user else None
    if not user_id and token:
        unauthorized_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
        except jwt.JWTError:
            raise unauthorized_exception

    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    if transcript.audio_location == "storage":
        # proxy S3 file, to prevent issue with CORS
        url = await transcript.get_audio_url()
        headers = {}

        copy_headers = ["range", "accept-encoding"]
        for header in copy_headers:
            if header in request.headers:
                headers[header] = request.headers[header]

        async with httpx.AsyncClient() as client:
            resp = await client.request(request.method, url, headers=headers)
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp.headers,
            )

    if transcript.audio_location == "storage":
        # proxy S3 file, to prevent issue with CORS
        url = await transcript.get_audio_url()
        headers = {}

        copy_headers = ["range", "accept-encoding"]
        for header in copy_headers:
            if header in request.headers:
                headers[header] = request.headers[header]

        async with httpx.AsyncClient() as client:
            resp = await client.request(request.method, url, headers=headers)
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp.headers,
            )

    if transcript.audio_deleted:
        raise HTTPException(
            status_code=404, detail="Audio unavailable due to privacy settings"
        )

    if not hasattr(transcript, 'audio_mp3_filename') or not transcript.audio_mp3_filename or not transcript.audio_mp3_filename.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    truncated_id = str(transcript.id).split("-")[0]
    filename = f"recording_{truncated_id}.mp3"

    return range_requests_response(
        request,
        transcript.audio_mp3_filename,
        content_type="audio/mpeg",
        content_disposition=f"attachment; filename={filename}",
    )


@router.get("/transcripts/{transcript_id}/audio/waveform")
async def transcript_get_audio_waveform(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> AudioWaveform:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    if not transcript.audio_waveform_filename.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return transcript.audio_waveform
