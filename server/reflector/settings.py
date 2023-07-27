from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    OPENMP_KMP_DUPLICATE_LIB_OK: bool = False

    # Whisper
    WHISPER_MODEL_SIZE: str = "tiny"
    whisper_real_time_model_size: str = "tiny"

    # Summarizer
    SUMMARIZER_MODEL: str = "facebook/bart-large-cnn"
    SUMMARIZER_INPUT_ENCODING_MAX_LENGTH: int = 1024
    SUMMARIZER_MAX_LENGTH: int = 2048
    SUMMARIZER_BEAM_SIZE: int = 6
    SUMMARIZER_MAX_CHUNK_LENGTH: int = 1024
    SUMMARIZER_USING_CHUNKS: bool = True

    # Audio
    AUDIO_BLACKHOLE_INPUT_AGGREGATOR_DEVICE_NAME: str = "aggregator"
    AUDIO_AV_FOUNDATION_DEVICE_ID: int = 1
    AUDIO_CHANNELS: int = 2
    AUDIO_SAMPLING_RATE: int = 48000
    AUDIO_SAMPLING_WIDTH: int = 2
    AUDIO_BUFFER_SIZE: int = 256 * 960

    # LLM
    LLM_BACKEND: str = "oobagooda"
    LLM_URL: str | None = None
    LLM_HOST: str = "localhost"
    LLM_PORT: int = 7860

    # Storage
    STORAGE_BACKEND: str = "aws"
    STORAGE_AWS_ACCESS_KEY: str = ""
    STORAGE_AWS_SECRET_KEY: str = ""
    STORAGE_AWS_BUCKET: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""


settings = Settings()
