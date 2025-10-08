from pydantic.types import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

from reflector.platform_types import Platform
from reflector.utils.string import NonEmptyString


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # CORS
    UI_BASE_URL: str = "http://localhost:3000"
    CORS_ORIGIN: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = False

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://reflector:reflector@localhost:5432/reflector"
    )

    # local data directory
    DATA_DIR: str = "./data"

    # Audio Chunking
    # backends: silero, frames
    AUDIO_CHUNKER_BACKEND: str = "frames"

    # Audio Transcription
    # backends: whisper, modal
    TRANSCRIPT_BACKEND: str = "whisper"
    TRANSCRIPT_URL: str | None = None
    TRANSCRIPT_TIMEOUT: int = 90
    TRANSCRIPT_FILE_TIMEOUT: int = 600

    # Audio Transcription: modal backend
    TRANSCRIPT_MODAL_API_KEY: str | None = None

    # Audio transcription storage
    TRANSCRIPT_STORAGE_BACKEND: str | None = None

    # Storage configuration for AWS
    TRANSCRIPT_STORAGE_AWS_BUCKET_NAME: str = "reflector-bucket"
    TRANSCRIPT_STORAGE_AWS_REGION: str = "us-east-1"
    TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID: str | None = None
    TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY: str | None = None

    # Recording storage
    RECORDING_STORAGE_BACKEND: str | None = None

    # Recording storage configuration for AWS
    RECORDING_STORAGE_AWS_BUCKET_NAME: str = "recording-bucket"
    RECORDING_STORAGE_AWS_REGION: str = "us-east-1"
    RECORDING_STORAGE_AWS_ACCESS_KEY_ID: str | None = None
    RECORDING_STORAGE_AWS_SECRET_ACCESS_KEY: str | None = None

    # Translate into the target language
    TRANSLATION_BACKEND: str = "passthrough"
    TRANSLATE_URL: str | None = None
    TRANSLATE_TIMEOUT: int = 90

    # Translation: modal backend
    TRANSLATE_MODAL_API_KEY: str | None = None

    # LLM
    LLM_MODEL: str = "microsoft/phi-4"
    LLM_URL: str | None = None
    LLM_API_KEY: str | None = None
    LLM_CONTEXT_WINDOW: int = 16000

    # Diarization
    DIARIZATION_ENABLED: bool = True
    DIARIZATION_BACKEND: str = "modal"
    DIARIZATION_URL: str | None = None
    DIARIZATION_FILE_TIMEOUT: int = 600

    # Diarization: modal backend
    DIARIZATION_MODAL_API_KEY: str | None = None

    # Diarization: local pyannote.audio
    DIARIZATION_PYANNOTE_AUTH_TOKEN: str | None = None

    # Sentry
    SENTRY_DSN: str | None = None

    # User authentication (none, jwt)
    AUTH_BACKEND: str = "none"

    # User authentication using JWT
    AUTH_JWT_ALGORITHM: str = "RS256"
    AUTH_JWT_PUBLIC_KEY: str | None = "authentik.monadical.com_public.pem"
    AUTH_JWT_AUDIENCE: str | None = None

    PUBLIC_MODE: bool = False
    PUBLIC_DATA_RETENTION_DAYS: PositiveInt = 7

    # Min transcript length to generate topic + summary
    MIN_TRANSCRIPT_LENGTH: int = 750

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_CACHE_DB: int = 2

    # Secret key
    SECRET_KEY: str = "changeme-f02f86fd8b3e4fd892c6043e5a298e21"

    # Current hosting/domain
    BASE_URL: str = "http://localhost:1250"

    # Profiling
    PROFILING: bool = False

    # Healthcheck
    HEALTHCHECK_URL: str | None = None

    # Whereby integration
    WHEREBY_API_URL: str = "https://api.whereby.dev/v1"
    WHEREBY_API_KEY: NonEmptyString | None = None
    WHEREBY_WEBHOOK_SECRET: str | None = None
    AWS_WHEREBY_ACCESS_KEY_ID: str | None = None
    AWS_WHEREBY_ACCESS_KEY_SECRET: str | None = None
    AWS_PROCESS_RECORDING_QUEUE_URL: str | None = None
    SQS_POLLING_TIMEOUT_SECONDS: int = 60

    # Daily.co integration
    DAILY_API_KEY: str | None = None
    DAILY_WEBHOOK_SECRET: str | None = None
    DAILY_SUBDOMAIN: str | None = None
    AWS_DAILY_S3_BUCKET: str | None = None
    AWS_DAILY_S3_REGION: str = "us-west-2"
    AWS_DAILY_ROLE_ARN: str | None = None

    # Platform Migration Feature Flags
    DAILY_MIGRATION_ENABLED: bool = False
    DAILY_MIGRATION_ROOM_IDS: list[str] = []
    DEFAULT_VIDEO_PLATFORM: Platform = "whereby"

    # Zulip integration
    ZULIP_REALM: str | None = None
    ZULIP_API_KEY: str | None = None
    ZULIP_BOT_EMAIL: str | None = None


settings = Settings()
