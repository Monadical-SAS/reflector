import uuid

from fastapi import APIRouter, Body, Depends, Form, HTTPException, UploadFile

from ..auth import apikey_auth
from ..config import SUPPORTED_FILE_EXTENSIONS, UPLOADS_PATH
from ..services.transcriber import MODEL_NAME, WhisperService
from ..utils import cleanup_uploaded_files, download_audio_file, ensure_dirs

router = APIRouter(prefix="/v1/audio", tags=["transcription"])


service = WhisperService()


@router.on_event("startup")
def _startup():
    ensure_dirs()
    service.load()


@router.post("/transcriptions", dependencies=[Depends(apikey_auth)])
def transcribe(
    file: UploadFile = None,
    files: list[UploadFile] | None = None,
    model: str = Form(MODEL_NAME),
    language: str = Form("en"),
    batch: bool = Form(False),
):
    if not file and not files:
        raise HTTPException(
            status_code=400, detail="Either 'file' or 'files' parameter is required"
        )
    if batch and not files:
        raise HTTPException(
            status_code=400, detail="Batch transcription requires 'files'"
        )

    upload_files = [file] if file else files

    uploaded_filenames: list[str] = []
    with cleanup_uploaded_files(uploaded_filenames):
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
            uploaded_filenames.append(unique_filename)

        if batch and len(upload_files) > 1:
            results = []
            for filename in uploaded_filenames:
                file_path = str(UPLOADS_PATH / filename)
                result = service.transcribe_file(file_path, language=language)
                result["filename"] = filename
                results.append(result)
            return {"results": results}

        results = []
        for filename in uploaded_filenames:
            file_path = str(UPLOADS_PATH / filename)
            result = service.transcribe_file(file_path, language=language)
            result["filename"] = filename
            results.append(result)

        return {"results": results} if len(results) > 1 else results[0]


@router.post("/transcriptions-from-url", dependencies=[Depends(apikey_auth)])
def transcribe_from_url(
    audio_file_url: str = Body(..., description="URL of the audio file to transcribe"),
    model: str = Body(MODEL_NAME),
    language: str = Body("en"),
    timestamp_offset: float = Body(0.0),
):
    with download_audio_file(audio_file_url) as (unique_filename, _ext):
        file_path = str(UPLOADS_PATH / unique_filename)
        result = service.transcribe_vad_url_segment(
            file_path=file_path, timestamp_offset=timestamp_offset, language=language
        )
        return result
