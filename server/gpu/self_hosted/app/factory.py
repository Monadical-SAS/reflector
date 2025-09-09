from fastapi import FastAPI

from .routers.diarization import router as diarization_router
from .routers.transcription import router as transcription_router
from .routers.translation import router as translation_router


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(transcription_router)
    # match modal endpoints: /v1/audio/* and top-level /translate, /diarize
    app.include_router(translation_router)
    app.include_router(diarization_router)
    return app
