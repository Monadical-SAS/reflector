from fastapi import APIRouter, Body, Depends

from ..auth import apikey_auth
from ..services.translator import TextTranslatorService

router = APIRouter(tags=["translation"])

translator = TextTranslatorService()


@router.post("/translate", dependencies=[Depends(apikey_auth)])
def translate(
    text: str,
    source_language: str = Body("en"),
    target_language: str = Body("fr"),
):
    return translator.translate(text, source_language, target_language)
