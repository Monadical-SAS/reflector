from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi_pagination import add_pagination

import reflector.auth  # noqa
import reflector.db  # noqa
from reflector.events import subscribers_shutdown, subscribers_startup
from reflector.logger import logger
from reflector.settings import settings
from reflector.views.rtc_offer import router as rtc_offer_router
from reflector.views.transcripts import router as transcripts_router
from reflector.views.user import router as user_router

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None


# lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    for func in subscribers_startup:
        await func()
    yield
    for func in subscribers_shutdown:
        await func()


# use sentry if available
if settings.SENTRY_DSN:
    if not sentry_sdk:
        logger.error("Sentry is not installed, avoided")
    else:
        logger.info("Sentry enabled")
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)
else:
    logger.info("Sentry disabled")


# build app
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# register views
app.include_router(rtc_offer_router)
app.include_router(transcripts_router, prefix="/v1")
app.include_router(user_router, prefix="/v1")
add_pagination(app)


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
                opid = f"{version}_{route.name}"
            else:
                opid = route.name

            if opid in ensure_uniq_operation_ids:
                raise ValueError(
                    f"Operation ID '{route.name}' is not unique. "
                    "Please rename the route or the view function."
                )
            route.operation_id = opid
            ensure_uniq_operation_ids.add(route.name)


use_route_names_as_operation_ids(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("reflector.app:app", host="0.0.0.0", port=1250, reload=True)
