import httpx

from reflector.processors.audio_diarization import AudioDiarizationProcessor
from reflector.processors.audio_diarization_auto import AudioDiarizationAutoProcessor
from reflector.processors.types import AudioDiarizationInput, TitleSummary
from reflector.settings import settings


class AudioDiarizationModalProcessor(AudioDiarizationProcessor):
    INPUT_TYPE = AudioDiarizationInput
    OUTPUT_TYPE = TitleSummary

    def __init__(self, modal_api_key: str | None = None, **kwargs):
        super().__init__(**kwargs)
        if not settings.DIARIZATION_URL:
            raise Exception(
                "DIARIZATION_URL required to use AudioDiarizationModalProcessor"
            )
        self.diarization_url = settings.DIARIZATION_URL + "/diarize"
        self.modal_api_key = modal_api_key
        self.headers = {}
        if self.modal_api_key:
            self.headers["Authorization"] = f"Bearer {self.modal_api_key}"

    async def _diarize(self, data: AudioDiarizationInput):
        # Gather diarization data
        params = {
            "audio_file_url": data.audio_url,
            "timestamp": 0,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.diarization_url,
                headers=self.headers,
                params=params,
                timeout=None,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.json()["diarization"]


AudioDiarizationAutoProcessor.register("modal", AudioDiarizationModalProcessor)
