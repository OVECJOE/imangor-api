from typing import Optional
from app.core.config import settings


class CustomException(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class InsufficientCreditsException(CustomException):
    def __init__(self, required: float, available: float):
        super().__init__(
            f"Insufficient credits. Required: {required}, Available: {available}",
            status_code=402,
            details={"required_credits": required, "available_credits": available}
        )

class AnonymousLimitExceededException(CustomException):
    def __init__(self):
        super().__init__(
            f"Anonymous users can only process {settings.ANONYMOUS_IMAGE_LIMIT} images. Please sign up for more.",
            status_code=429,
            details={"limit": settings.ANONYMOUS_IMAGE_LIMIT}
        )

class InvalidFileFormatException(CustomException):
    def __init__(self, format_received: str):
        super().__init__(
            f"Unsupported file format: {format_received}. Supported formats: {', '.join(settings.ALLOWED_EXTENSIONS)}",
            status_code=400,
            details={"received_format": format_received, "supported_formats": settings.ALLOWED_EXTENSIONS}
        )
