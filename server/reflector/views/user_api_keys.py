from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import reflector.auth as auth
from reflector.db.user_api_keys import user_api_keys_controller
from reflector.utils.string import NonEmptyString

router = APIRouter()
logger = structlog.get_logger(__name__)


class CreateApiKeyRequest(BaseModel):
    name: NonEmptyString | None = None


class ApiKeyResponse(BaseModel):
    id: NonEmptyString
    user_id: NonEmptyString
    name: NonEmptyString | None
    created_at: datetime


class CreateApiKeyResponse(ApiKeyResponse):
    key: NonEmptyString


@router.post("/user/api-keys", response_model=CreateApiKeyResponse)
async def create_api_key(
    req: CreateApiKeyRequest,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    api_key_model, plaintext = await user_api_keys_controller.create_key(
        user_id=user["sub"],
        name=req.name,
    )
    return CreateApiKeyResponse(
        **api_key_model.model_dump(),
        key=plaintext,
    )


@router.get("/user/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    api_keys = await user_api_keys_controller.list_by_user_id(user["sub"])
    return [ApiKeyResponse(**k.model_dump()) for k in api_keys]


@router.delete("/user/api-keys/{key_id}")
async def delete_api_key(
    key_id: NonEmptyString,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    deleted = await user_api_keys_controller.delete_key(key_id, user["sub"])
    if not deleted:
        raise HTTPException(status_code=404)
    return {"status": "ok"}
