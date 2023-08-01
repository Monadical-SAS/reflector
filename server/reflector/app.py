from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from reflector.views.rtc_offer import router as rtc_offer_router
from reflector.events import subscribers_startup, subscribers_shutdown
from contextlib import asynccontextmanager


# lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    for func in subscribers_startup:
        await func()
    yield
    for func in subscribers_shutdown:
        await func()


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
