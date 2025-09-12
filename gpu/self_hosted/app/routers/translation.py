from typing import Dict

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel

from ..auth import apikey_auth
from ..services.translator import TextTranslatorService

router = APIRouter(tags=["translation"])

translator = TextTranslatorService()


class TranslationResponse(BaseModel):
    text: Dict[str, str]


@router.post(
    "/translate",
    dependencies=[Depends(apikey_auth)],
    response_model=TranslationResponse,
)
def translate(
    text: str,
    source_language: str = Body("en"),
    target_language: str = Body("fr"),
):
    return translator.translate(text, source_language, target_language)
