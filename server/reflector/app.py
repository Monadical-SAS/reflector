from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from reflector.views.rtc_offer import router as rtc_offer_router

# build app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# register views
app.include_router(rtc_offer_router)
