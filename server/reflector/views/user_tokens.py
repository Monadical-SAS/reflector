from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import reflector.auth as auth
from reflector.db.user_tokens import user_tokens_controller

router = APIRouter()


class CreateTokenRequest(BaseModel):
    name: str | None = None


class TokenResponse(BaseModel):
    id: str
    user_id: str
    name: str | None
    created_at: datetime


class CreateTokenResponse(TokenResponse):
    token: str


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
    tokens = await user_tokens_controller.get_by_user_id(user["sub"])
    return [TokenResponse(**t.model_dump()) for t in tokens]


@router.delete("/user/tokens/{token_id}")
async def delete_token(
    token_id: str,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    try:
        success = await user_tokens_controller.delete_token(token_id, user["sub"])
        if not success:
            raise HTTPException(status_code=404, detail="Token not found")
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
