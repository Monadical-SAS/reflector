import httpx
from reflector.processors.audio_diarization import AudioDiarizationProcessor
from reflector.processors.audio_diarization_auto import AudioDiarizationAutoProcessor
from reflector.processors.types import AudioDiarizationInput, TitleSummary
from reflector.settings import settings


class AudioDiarizationModalProcessor(AudioDiarizationProcessor):
    INPUT_TYPE = AudioDiarizationInput
    OUTPUT_TYPE = TitleSummary

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.diarization_url = settings.DIARIZATION_URL + "/diarize"
        self.headers = {
            "Authorization": f"Bearer {settings.LLM_MODAL_API_KEY}",
        }

    async def _diarize(self, data: AudioDiarizationInput):
        # Gather diarization data
        params = {
            "audio_file_url": data.audio_url,
            "timestamp": 0,
        }
        self.logger.info("Diarization started", audio_file_url=data.audio_url)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.diarization_url,
                    headers=self.headers,
                    params=params,
                    timeout=None,
                )
                response.raise_for_status()
                self.logger.info("Diarization finished")
                return response.json()["text"]
            except Exception:
                self.logger.exception("Diarization failed after retrying")
                raise


AudioDiarizationAutoProcessor.register("modal", AudioDiarizationModalProcessor)
