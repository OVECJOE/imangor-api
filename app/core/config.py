from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "imangor-api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 90  # 3 months
    API_KEY_LENGTH: int = 32

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Google Cloud
    GOOGLE_CLOUD_PROJECT_ID: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    GOOGLE_CLOUD_STORAGE_BUCKET: str
    GOOGLE_STORAGE_BASE_URL: str = "https://storage.googleapis.com"

    # OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # Flutterwave
    FLUTTERWAVE_PUBLIC_KEY: str
    FLUTTERWAVE_SECRET_KEY: str
    FLUTTERWAVE_WEBHOOK_SECRET: str

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    ANONYMOUS_RATE_LIMIT: int = 10  # requests per minute
    AUTHENTICATED_RATE_LIMIT: int = 100  # requests per minute

    # File upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = ["png", "jpg", "jpeg", "svg", "webp", "bmp", "tiff"]

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://yourdomain.com"]
    ALLOWED_HOSTS: List[str] = ["localhost", "yourdomain.com"]

    # Webhooks
    WEBHOOK_TIMEOUT: int = 30
    WEBHOOK_MAX_RETRIES: int = 3

    # Credits and pricing
    ANONYMOUS_IMAGE_LIMIT: int = 3
    FREE_CREDITS_NEW_USER: int = 5
    CREDIT_EXPIRY_MONTHS: int = 6

    # Credit costs by file size (in MB)
    CREDIT_COST_SMALL: float = 1.0  # < 10MB
    CREDIT_COST_LARGE: float = 2.0  # >= 10MB
    NO_TEXT_PENALTY: float = 0.2

    # Celery settings
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    CELERY_TASK_TIME_LIMIT: int = 3600  # 1 hour
    CELERY_TASK_SOFT_TIME_LIMIT: int = 3300  # 55 minutes
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 1000
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_TASK_REJECT_ON_WORKER_LOST: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
