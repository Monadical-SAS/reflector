import os

from fastapi import APIRouter, Depends

from ..auth import apikey_auth
from ..config import UPLOADS_PATH
from ..services.diarizer import PyannoteDiarizationService
from ..utils import ensure_dirs

router = APIRouter(tags=["diarization"])

diarizer = PyannoteDiarizationService()


@router.post("/diarize", dependencies=[Depends(apikey_auth)])
def diarize(audio_file_url: str, timestamp: float = 0.0):
    from ..utils import download_audio_to_uploads

    ensure_dirs()
    unique_filename, _ext = download_audio_to_uploads(audio_file_url)
    try:
        file_path = f"{UPLOADS_PATH}/{unique_filename}"
        return diarizer.diarize_file(file_path, timestamp=timestamp)
    finally:
        try:
            os.remove(f"{UPLOADS_PATH}/{unique_filename}")
        except Exception:
            pass
