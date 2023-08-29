import importlib

from reflector.processors.audio_transcript import AudioTranscriptProcessor
from reflector.processors.base import Pipeline, Processor
from reflector.processors.types import AudioFile
from reflector.settings import settings


class AudioTranscriptAutoProcessor(AudioTranscriptProcessor):
    _registry = {}

    @classmethod
    def register(cls, name, kclass):
        cls._registry[name] = kclass

    @classmethod
    def get_instance(cls, name):
        if name not in cls._registry:
            module_name = f"reflector.processors.audio_transcript_{name}"
            importlib.import_module(module_name)

        # gather specific configuration for the processor
        # search `TRANSCRIPT_BACKEND_XXX_YYY`, push to constructor as `backend_xxx_yyy`
        config = {}
        name_upper = name.upper()
        settings_prefix = "TRANSCRIPT_"
        config_prefix = f"{settings_prefix}{name_upper}_"
        for key, value in settings:
            if key.startswith(config_prefix):
                config_name = key[len(settings_prefix) :].lower()
                config[config_name] = value

        return cls._registry[name](**config)

    def __init__(self, **kwargs):
        self.processor = self.get_instance(settings.TRANSCRIPT_BACKEND)
        super().__init__(**kwargs)

    def set_pipeline(self, pipeline: Pipeline):
        super().set_pipeline(pipeline)
        self.processor.set_pipeline(pipeline)

    def connect(self, processor: Processor):
        self.processor.connect(processor)

    def disconnect(self, processor: Processor):
        self.processor.disconnect(processor)

    def on(self, callback):
        self.processor.on(callback)

    def off(self, callback):
        self.processor.off(callback)

    async def _warmup(self):
        return await self.processor._warmup()

    async def _push(self, data: AudioFile):
        return await self.processor._push(data)

    async def _flush(self):
        return await self.processor._flush()
