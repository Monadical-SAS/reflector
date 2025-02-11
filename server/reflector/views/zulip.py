from typing import Annotated, Optional

import reflector.auth as auth
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from reflector.zulip import get_zulip_streams, get_zulip_topics

router = APIRouter()


class Stream(BaseModel):
    stream_id: int
    name: str


class Topic(BaseModel):
    name: str


@router.get("/zulip/streams")
async def zulip_get_streams(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> list[Stream]:
    """
    Get all Zulip streams.
    """
    if not user:
        raise HTTPException(status_code=403, detail="Authentication required")

    streams = await get_zulip_streams()
    return streams


@router.get("/zulip/streams/{stream_id}/topics")
async def zulip_get_topics(
    stream_id: int,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> list[Topic]:
    """
    Get all topics for a specific Zulip stream.
    """
    if not user:
        raise HTTPException(status_code=403, detail="Authentication required")

    topics = await get_zulip_topics(stream_id)
    return topics
