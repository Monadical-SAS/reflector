from typing import List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..auth import apikey_auth
from ..services.diarizer import PyannoteDiarizationService
from ..utils import download_audio_file

router = APIRouter(tags=["diarization"])


class DiarizationSegment(BaseModel):
    start: float
    end: float
    speaker: int


class DiarizationResponse(BaseModel):
    diarization: List[DiarizationSegment]


@router.post(
    "/diarize", dependencies=[Depends(apikey_auth)], response_model=DiarizationResponse
)
def diarize(request: Request, audio_file_url: str, timestamp: float = 0.0):
    with download_audio_file(audio_file_url) as (file_path, _ext):
        file_path = str(file_path)
        diarizer: PyannoteDiarizationService = request.app.state.diarizer
        return diarizer.diarize_file(file_path, timestamp=timestamp)
