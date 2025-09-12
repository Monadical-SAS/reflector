from fastapi import APIRouter, Depends

from ..auth import apikey_auth
from ..config import UPLOADS_PATH
from ..services.diarizer import PyannoteDiarizationService
from ..utils import download_audio_file

router = APIRouter(tags=["diarization"])

diarizer = PyannoteDiarizationService()


@router.post("/diarize", dependencies=[Depends(apikey_auth)])
def diarize(audio_file_url: str, timestamp: float = 0.0):
    with download_audio_file(audio_file_url) as (unique_filename, _ext):
        file_path = str(UPLOADS_PATH / unique_filename)
        return diarizer.diarize_file(file_path, timestamp=timestamp)
