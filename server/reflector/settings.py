from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    OPENMP_KMP_DUPLICATE_LIB_OK: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./reflector.sqlite3"

    # local data directory (audio for no)
    DATA_DIR: str = "./data"

    # Whisper
    WHISPER_MODEL_SIZE: str = "tiny"
    WHISPER_REAL_TIME_MODEL_SIZE: str = "tiny"

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

    # Audio Transcription
    # backends: whisper, banana, modal
    TRANSCRIPT_BACKEND: str = "whisper"
    TRANSCRIPT_URL: str | None = None
    TRANSCRIPT_TIMEOUT: int = 90

    # Audio transcription banana.dev configuration
    TRANSCRIPT_BANANA_API_KEY: str | None = None
    TRANSCRIPT_BANANA_MODEL_KEY: str | None = None

    # Audio transcription modal.com configuration
    TRANSCRIPT_MODAL_API_KEY: str | None = None

    # Audio transcription storage
    TRANSCRIPT_STORAGE_BACKEND: str = "aws"

    # Storage configuration for AWS
    TRANSCRIPT_STORAGE_AWS_BUCKET_NAME: str = "reflector-bucket/chunks"
    TRANSCRIPT_STORAGE_AWS_REGION: str = "us-east-1"
    TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID: str | None = None
    TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY: str | None = None

    # LLM
    # available backend: openai, banana, modal, oobabooga
    LLM_BACKEND: str = "oobabooga"

    # LLM common configuration
    LLM_URL: str | None = None
    LLM_HOST: str = "localhost"
    LLM_PORT: int = 7860
    LLM_OPENAI_KEY: str | None = None
    LLM_OPENAI_MODEL: str = "gpt-3.5-turbo"
    LLM_OPENAI_TEMPERATURE: float = 0.7
    LLM_TIMEOUT: int = 60 * 5  # take cold start into account
    LLM_MAX_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.7

    # LLM Banana configuration
    LLM_BANANA_API_KEY: str | None = None
    LLM_BANANA_MODEL_KEY: str | None = None

    # LLM Modal configuration
    LLM_MODAL_API_KEY: str | None = None

    # Sentry
    SENTRY_DSN: str | None = None

    # User authentication (none, fief)
    AUTH_BACKEND: str = "none"

    # User authentication using fief
    AUTH_FIEF_URL: str | None = None
    AUTH_FIEF_CLIENT_ID: str | None = None
    AUTH_FIEF_CLIENT_SECRET: str | None = None

    # API public mode
    # if set, all anonymous record will be public
    PUBLIC_MODE: bool = False


settings = Settings()
