import httpx
from reflector.processors.base import Processor
from reflector.processors.types import Transcript, TranslationLanguages
from reflector.settings import settings
from reflector.utils.retry import retry


class TranscriptTranslatorProcessor(Processor):
    """
    Translate the transcript into the target language
    """

    INPUT_TYPE = Transcript
    OUTPUT_TYPE = Transcript
    TASK = "translate"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transcript_url = settings.TRANSCRIPT_URL
        self.timeout = settings.TRANSCRIPT_TIMEOUT
        self.headers = {"Authorization": f"Bearer {settings.LLM_MODAL_API_KEY}"}

    async def _push(self, data: Transcript):
        self.transcript = data
        await self.flush()

    async def get_translation(self, text: str) -> str | None:
        # FIXME this should be a processor after, as each user may want
        # different languages

        source_language = self.get_pref("audio:source_language", "en")
        target_language = self.get_pref("audio:target_language", "en")
        if source_language == target_language:
            return

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
                settings.TRANSCRIPT_URL + "/translate",
                headers=self.headers,
                params=json_payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()["text"]

            # Sanity check for translation status in the result
            if target_language in result:
                translation = result[target_language]
            self.logger.debug(f"Translation response: {text=}, {translation=}")
        return translation

    async def _flush(self):
        if not self.transcript:
            return
        self.transcript.translation = await self.get_translation(
            text=self.transcript.text
        )
        await self.emit(self.transcript)
