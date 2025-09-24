from typing import Annotated, Optional

import av
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import reflector.auth as auth
from reflector.db import get_session
from reflector.db.transcripts import transcripts_controller
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process

router = APIRouter()


class UploadStatus(BaseModel):
    status: str


@router.post("/transcripts/{transcript_id}/record/upload")
async def transcript_record_upload(
    transcript_id: str,
    chunk_number: int,
    total_chunks: int,
    chunk: UploadFile,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
    session: AsyncSession = Depends(get_session),
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        session, transcript_id, user_id=user_id
    )

    if transcript.locked:
        raise HTTPException(status_code=400, detail="Transcript is locked")

    # ensure there is no other upload in the directory (searching data_path/upload.*)
    if any(transcript.data_path.glob("upload.*")):
        raise HTTPException(
            status_code=400, detail="There is already an upload in progress"
        )

    # save the chunk to the transcript folder
    extension = chunk.filename.split(".")[-1]
    chunk_filename = transcript.data_path / f"upload_{chunk_number}.{extension}"
    chunk_filename.parent.mkdir(parents=True, exist_ok=True)

    # ensure the chunk is back to the beginning
    await chunk.seek(0)

    # save the chunk to the transcript folder
    try:
        with open(chunk_filename, "wb") as f:
            f.write(await chunk.read())
    except Exception:
        chunk_filename.unlink()
        raise

    # return if it's not the last chunk
    if chunk_number < total_chunks - 1:
        return UploadStatus(status="ok")

    # merge chunks to a single file
    upload_filename = transcript.data_path / f"upload.{extension}"
    try:
        with open(upload_filename, "ab") as f:
            for chunk_number in range(0, total_chunks):
                chunk_filename = (
                    transcript.data_path / f"upload_{chunk_number}.{extension}"
                )
                with open(chunk_filename, "rb") as chunk:
                    f.write(chunk.read())
                chunk_filename.unlink()
    except Exception:
        upload_filename.unlink()
        raise

    # ensure the file have audio part, using av
    # XXX Trying to do this check on the initial UploadFile object is not
    # possible, dunno why. UploadFile.file has no name.
    # Trying to pass UploadFile.file with format=extension does not work
    # it never detect audio stream...
    container = av.open(upload_filename.as_posix())
    try:
        if not len(container.streams.audio):
            raise HTTPException(status_code=400, detail="File has no audio stream")
    except Exception:
        # delete the uploaded file
        upload_filename.unlink()
        raise
    finally:
        container.close()

    # set the status to "uploaded"
    await transcripts_controller.update(session, transcript, {"status": "uploaded"})

    # launch a background task to process the file
    task_pipeline_file_process.delay(transcript_id=transcript_id)

    return UploadStatus(status="ok")
