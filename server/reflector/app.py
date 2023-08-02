from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from reflector.views.rtc_offer import router as rtc_offer_router
from reflector.events import subscribers_startup, subscribers_shutdown
from reflector.logger import logger
from reflector.settings import settings
from contextlib import asynccontextmanager

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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("reflector.app:app", host="0.0.0.0", port=1250, reload=True)
