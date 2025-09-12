from contextlib import asynccontextmanager

from fastapi import FastAPI

from .routers.diarization import router as diarization_router
from .routers.transcription import router as transcription_router
from .routers.translation import router as translation_router
from .services.transcriber import WhisperService
from .utils import ensure_dirs


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    whisper_service = WhisperService()
    whisper_service.load()
    app.state.whisper = whisper_service
    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(transcription_router)
    app.include_router(translation_router)
    app.include_router(diarization_router)
    return app
