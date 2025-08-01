import httpx

from reflector.processors.transcript_translator import TranscriptTranslatorProcessor
from reflector.processors.transcript_translator_auto import (
    TranscriptTranslatorAutoProcessor,
)
from reflector.processors.types import TranslationLanguages
from reflector.settings import settings
from reflector.utils.retry import retry


class TranscriptTranslatorModalProcessor(TranscriptTranslatorProcessor):
    """
    Translate the transcript into the target language using Modal.com
    """

    def __init__(self, modal_api_key: str = None, **kwargs):
        super().__init__(**kwargs)
        if not settings.TRANSLATE_URL:
            raise Exception(
                "TRANSLATE_URL is required for TranscriptTranslatorModalProcessor"
            )
        self.translate_url = settings.TRANSLATE_URL
        self.timeout = settings.TRANSLATE_TIMEOUT
        self.modal_api_key = modal_api_key
        self.headers = {}
        if self.modal_api_key:
            self.headers["Authorization"] = f"Bearer {self.modal_api_key}"

    async def _translate(self, text: str) -> str | None:
        source_language = self.get_pref("audio:source_language", "en")
        target_language = self.get_pref("audio:target_language", "en")

        languages = TranslationLanguages()
        # Only way to set the target should be the UI element like dropdown.
        # Hence, this assert should never fail.
        assert languages.is_supported(target_language)
        self.logger.debug(f"Try to translate {text=}")
        json_payload = {
            "text": text,
            "source_language": source_language,
            "target_language": target_language,
        }

        async with httpx.AsyncClient() as client:
            response = await retry(client.post)(
                self.translate_url + "/translate",
                headers=self.headers,
                params=json_payload,
                timeout=self.timeout,
                follow_redirects=True,
                logger=self.logger,
            )
            response.raise_for_status()
            result = response.json()["text"]

            # Sanity check for translation status in the result
            if target_language in result:
                translation = result[target_language]
            else:
                translation = None
            self.logger.debug(f"Translation response: {text=}, {translation=}")
        return translation


TranscriptTranslatorAutoProcessor.register("modal", TranscriptTranslatorModalProcessor)
