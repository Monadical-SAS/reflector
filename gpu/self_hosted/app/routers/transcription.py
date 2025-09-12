import uuid
from typing import Optional, Union

from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from pathlib import Path
from ..auth import apikey_auth
from ..config import SUPPORTED_FILE_EXTENSIONS, UPLOADS_PATH
from ..services.transcriber import MODEL_NAME
from ..utils import cleanup_uploaded_files, download_audio_file

router = APIRouter(prefix="/v1/audio", tags=["transcription"])


class WordTiming(BaseModel):
    word: str
    start: float
    end: float


class TranscriptResult(BaseModel):
    text: str
    words: list[WordTiming]
    filename: Optional[str] = None


class TranscriptBatchResponse(BaseModel):
    results: list[TranscriptResult]


@router.post(
    "/transcriptions",
    dependencies=[Depends(apikey_auth)],
    response_model=Union[TranscriptResult, TranscriptBatchResponse],
)
def transcribe(
    request: Request,
    file: UploadFile = None,
    files: list[UploadFile] | None = None,
    model: str = Form(MODEL_NAME),
    language: str = Form("en"),
    batch: bool = Form(False),
):
    service = request.app.state.whisper
    if not file and not files:
        raise HTTPException(
            status_code=400, detail="Either 'file' or 'files' parameter is required"
        )
    if batch and not files:
        raise HTTPException(
            status_code=400, detail="Batch transcription requires 'files'"
        )

    upload_files = [file] if file else files

    uploaded_paths: list[Path] = []
    with cleanup_uploaded_files(uploaded_paths):
        for upload_file in upload_files:
            audio_suffix = upload_file.filename.split(".")[-1].lower()
            if audio_suffix not in SUPPORTED_FILE_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unsupported audio format. Supported extensions: {', '.join(SUPPORTED_FILE_EXTENSIONS)}"
                    ),
                )
            unique_filename = f"{uuid.uuid4()}.{audio_suffix}"
            file_path = UPLOADS_PATH / unique_filename
            with open(file_path, "wb") as f:
                content = upload_file.file.read()
                f.write(content)
            uploaded_paths.append(file_path)

        if batch and len(upload_files) > 1:
            results = []
            for path in uploaded_paths:
                result = service.transcribe_file(str(path), language=language)
                result["filename"] = path.name
                results.append(result)
            return {"results": results}

        results = []
        for path in uploaded_paths:
            result = service.transcribe_file(str(path), language=language)
            result["filename"] = path.name
            results.append(result)

        return {"results": results} if len(results) > 1 else results[0]


@router.post(
    "/transcriptions-from-url",
    dependencies=[Depends(apikey_auth)],
    response_model=TranscriptResult,
)
def transcribe_from_url(
    request: Request,
    audio_file_url: str = Body(..., description="URL of the audio file to transcribe"),
    model: str = Body(MODEL_NAME),
    language: str = Body("en"),
    timestamp_offset: float = Body(0.0),
):
    service = request.app.state.whisper
    with download_audio_file(audio_file_url) as (file_path, _ext):
        file_path = str(file_path)
        result = service.transcribe_vad_url_segment(
            file_path=file_path, timestamp_offset=timestamp_offset, language=language
        )
        return result
