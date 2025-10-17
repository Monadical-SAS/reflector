from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import reflector.auth as auth
from reflector.db.user_tokens import user_tokens_controller
from reflector.utils.string import NonEmptyString

router = APIRouter()
logger = structlog.get_logger(__name__)


class CreateTokenRequest(BaseModel):
    name: NonEmptyString | None = None


class TokenResponse(BaseModel):
    id: NonEmptyString
    user_id: NonEmptyString
    name: NonEmptyString | None
    created_at: datetime


class CreateTokenResponse(TokenResponse):
    token: NonEmptyString


@router.post("/user/tokens", response_model=CreateTokenResponse)
async def create_token(
    req: CreateTokenRequest,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    token_model, plaintext = await user_tokens_controller.create_token(
        user_id=user["sub"],
        name=req.name,
    )
    return CreateTokenResponse(
        **token_model.model_dump(),
        token=plaintext,
    )


@router.get("/user/tokens", response_model=list[TokenResponse])
async def list_tokens(
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    tokens = await user_tokens_controller.list_by_user_id(user["sub"])
    return [TokenResponse(**t.model_dump()) for t in tokens]


@router.delete("/user/tokens/{token_id}")
async def delete_token(
    token_id: NonEmptyString,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    try:
        r = await user_tokens_controller.delete_token(token_id, user["sub"])
        if r == "not-yours" or r == "not-here":
            raise HTTPException(status_code=404)
        if r is None:
            return {"status": "ok"}
        logger.error(f"token deletion panic: delete_token result not known: {r}")
        raise HTTPException(status_code=500)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
