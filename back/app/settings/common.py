# Standard library imports
from pathlib import Path
import secrets
from typing import Annotated, Any, Literal

# Third-party imports
from pydantic import AnyUrl, BeforeValidator, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR: Path = Path(__file__).resolve().parent.parent


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # General settings
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ENVIRONMENT: Literal["dev", "staging", "production"] = "dev"
    UNDER_DEVELOPMENT: bool = False  # Set to True for skipping otp/emails/..
    DEBUG_MODE: bool = False
    PROJECT_NAME: str = "Project Name"
    FRONTEND_BASE_URL: str = "https://app.projectname.com"
    BACKEND_BASE_URL: str = "https://projectname.com"

    # Database settings
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    @computed_field  # type: ignore[prop-decorator, misc]
    @property
    def API_BASE_URL(self) -> str:
        """Get the external API base URL computed from BACKEND_BASE_URL"""
        backend_url = str(self.BACKEND_BASE_URL)
        if "localhost" in backend_url:
            return backend_url.replace("localhost", "api.localhost")
        else:
            return backend_url.replace("://", "://api.")

    @computed_field  # type: ignore[prop-decorator, misc]
    @property
    def DEVELOPERS_BASE_URL(self) -> str:
        """Get the developers documentation base URL computed from BACKEND_BASE_URL"""
        backend_url = str(self.BACKEND_BASE_URL)
        if "localhost" in backend_url:
            return backend_url.replace("localhost", "developers.localhost")
        else:
            return backend_url.replace("://", "://developers.")

    @computed_field  # type: ignore[prop-decorator, misc]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> MultiHostUrl:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @property
    def SQLALCHEMY_ASYNC_DATABASE_URI(self) -> MultiHostUrl:
        return MultiHostUrl.build(
            scheme="postgresql+asyncpg",  # async driver for async queries
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # CORS settings
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = [
        AnyUrl("http://localhost/"),
        AnyUrl("http://localhost:3000/"),
        AnyUrl("http://localhost:8000/"),
        AnyUrl("http://developers.localhost:8000/"),
        AnyUrl("http://api.localhost:8000/"),
        AnyUrl("https://projectname.com/"),
        AnyUrl("https://www.projectname.com/"),
        AnyUrl("https://developers.projectname.com/"),
        AnyUrl("https://developers.localhost:8000/"),
        AnyUrl("https://api.projectname.com/"),
        AnyUrl("https://api.localhost:8000/"),
    ]

    @computed_field  # type: ignore[prop-decorator, misc]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]  # + FE_URLS

    # Optional settings
    SENTRY_DSN: str | None = None

    # JWT settings
    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 1  # 1 day for production must be 30 min
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # Redis settings
    REDIS_URL: str

    # Mailgun settings
    MAILGUN_API_KEY: str
    MAILGUN_DOMAIN: str

    # Admin settings
    ADMIN_EMAIL: str = "admin@projectname.com"
    ADMIN_PASSWORD: str = "password@1234"
    ADMIN_PHONE_NUMBER: str = "+14155552671"
    ADMIN_FIRST_NAME: str = "Admin"
    ADMIN_LAST_NAME: str = "User"

    # S3 settings
    S3_URL: str
    S3_ACCESS_KEY_ID: str
    S3_SECRET_ACCESS_KEY: str
    S3_DEFAULT_REGION: str
    S3_PRIVATE_BUCKET_NAME: str
    S3_PUBLIC_BUCKET_NAME: str
    S3_PRESIGNED_URL_EXPIRY_TIME: int = 3600
    S3_CLIENT_ADDRESS: str

    # File allowed format
    ALLOWED_FILE_TYPES: list[str] = [
        "image/png",
        "image/jpeg",
        "audio/mpeg",
        "text/csv",
    ]
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100 MB

    # RabbitMQ settings
    RABBITMQ_USER: str = "devuser"
    RABBITMQ_PASSWORD: str = "devpass"

    # Celery settings
    CELERY_BROKER_URL: str = "redis://redis:6379/2"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/3"
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_TIME_LIMIT: int = 300  # 5 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = 240  # 4 minutes
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_SEND_SENT_EVENT: bool = True

    # AI settings
    ACCEPTED_LANGUAGES_DICT: dict[str, str] = {
        "en": "English",
        "it": "Italian",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "ar": "Arabic",
    }

    # Pagination configurations
    PAGINATION_CONFIGS: dict[str, dict[str, int]] = {
        "small": {
            # Lightweight operations like feature categories, individual features
            "default_limit": 25,
            "max_limit": 100,
            "min_limit": 1,
            "default_offset": 0,
        },
        "medium": {
            # Standard operations like resources listing, resource types
            "default_limit": 50,
            "max_limit": 500,
            "min_limit": 1,
            "default_offset": 0,
        },
        "large": {
            # Heavy operations like search, bulk operations, detailed listings
            "default_limit": 100,
            "max_limit": 1000,
            "min_limit": 1,
            "default_offset": 0,
        },
    }
