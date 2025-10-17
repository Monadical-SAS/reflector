from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi_pagination import add_pagination
from prometheus_fastapi_instrumentator import Instrumentator

import reflector.auth  # noqa
import reflector.db  # noqa
from reflector.events import subscribers_shutdown, subscribers_startup
from reflector.logger import logger
from reflector.metrics import metrics_init
from reflector.settings import settings
from reflector.views.meetings import router as meetings_router
from reflector.views.rooms import router as rooms_router
from reflector.views.rtc_offer import router as rtc_offer_router
from reflector.views.transcripts import router as transcripts_router
from reflector.views.transcripts_audio import router as transcripts_audio_router
from reflector.views.transcripts_participants import (
    router as transcripts_participants_router,
)
from reflector.views.transcripts_process import router as transcripts_process_router
from reflector.views.transcripts_speaker import router as transcripts_speaker_router
from reflector.views.transcripts_upload import router as transcripts_upload_router
from reflector.views.transcripts_webrtc import router as transcripts_webrtc_router
from reflector.views.transcripts_websocket import router as transcripts_websocket_router
from reflector.views.user import router as user_router
from reflector.views.user_tokens import router as user_tokens_router
from reflector.views.user_websocket import router as user_ws_router
from reflector.views.whereby import router as whereby_router
from reflector.views.zulip import router as zulip_router

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None


# lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    for func in subscribers_startup:
        await func(app)
    yield
    for func in subscribers_shutdown:
        await func(app)


# use sentry if available
if settings.SENTRY_DSN:
    if not sentry_sdk:
        logger.error("Sentry is not installed, avoided")
    else:
        logger.info("Sentry enabled")
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.01)
else:
    logger.info("Sentry disabled")

# build app
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS or False,
    allow_origins=settings.CORS_ORIGIN.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy"}


# metrics
instrumentator = Instrumentator(
    excluded_handlers=["/docs", "/metrics"],
).instrument(app)
metrics_init(app, instrumentator)

# register views
app.include_router(rtc_offer_router)
app.include_router(meetings_router, prefix="/v1")
app.include_router(rooms_router, prefix="/v1")
app.include_router(transcripts_router, prefix="/v1")
app.include_router(transcripts_audio_router, prefix="/v1")
app.include_router(transcripts_participants_router, prefix="/v1")
app.include_router(transcripts_speaker_router, prefix="/v1")
app.include_router(transcripts_upload_router, prefix="/v1")
app.include_router(transcripts_websocket_router, prefix="/v1")
app.include_router(transcripts_webrtc_router, prefix="/v1")
app.include_router(transcripts_process_router, prefix="/v1")
app.include_router(user_router, prefix="/v1")
app.include_router(user_tokens_router, prefix="/v1")
app.include_router(user_ws_router, prefix="/v1")
app.include_router(zulip_router, prefix="/v1")
app.include_router(whereby_router, prefix="/v1")
add_pagination(app)

# prepare celery
from reflector.worker import app as celery_app  # noqa


# simpler openapi id
def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.
    """
    ensure_uniq_operation_ids = set()
    for route in app.routes:
        if isinstance(route, APIRoute):
            # opid

            # extract version out of path if exists
            # /v1/transcripts -> v1
            # /transcripts -> None
            version = None
            if route.path.startswith("/v"):
                version = route.path.split("/")[1]
                if route.operation_id is not None:
                    opid = f"{version}_{route.operation_id}"
                else:
                    opid = f"{version}_{route.name}"
            else:
                opid = route.name

            if opid in ensure_uniq_operation_ids:
                raise ValueError(
                    f"Operation ID '{route.name}' is not unique. "
                    "Please rename the route or the view function."
                )
            route.operation_id = opid
            ensure_uniq_operation_ids.add(opid)


use_route_names_as_operation_ids(app)

if settings.PROFILING:
    from fastapi import Request
    from fastapi.responses import HTMLResponse
    from pyinstrument import Profiler

    @app.middleware("http")
    async def profile_request(request: Request, call_next):
        profiling = request.query_params.get("profile", False)
        if profiling:
            profiler = Profiler(async_mode="enabled")
            profiler.start()
            await call_next(request)
            profiler.stop()
            return HTMLResponse(profiler.output_html())
        else:
            return await call_next(request)


if __name__ == "__main__":
    import sys

    import uvicorn

    should_reload = "--reload" in sys.argv

    uvicorn.run("reflector.app:app", host="0.0.0.0", port=1250, reload=should_reload)
