from enum import Enum
from typing import Any, Dict, Optional
from fastapi import HTTPException, status

from app.core.config import settings


class ErrorCode(str, Enum):
    """Standardized error codes for the API."""
    # Authentication errors (1xxx)
    INVALID_CREDENTIALS = "AUTH_1001"
    TOKEN_EXPIRED = "AUTH_1002"
    INSUFFICIENT_PERMISSIONS = "AUTH_1003"
    
    # Validation errors (2xxx)
    INVALID_INPUT = "VAL_2001"
    INVALID_IMAGE_FORMAT = "VAL_2002"
    FILE_TOO_LARGE = "VAL_2003"
    INVALID_VIDEO_FORMAT = "VAL_2004"
    
    # Resource errors (3xxx)
    RESOURCE_NOT_FOUND = "RES_3001"
    RESOURCE_ALREADY_EXISTS = "RES_3002"
    RATE_LIMIT_EXCEEDED = "RES_3003"
    
    # Processing errors (4xxx)
    PROCESSING_FAILED = "PROC_4001"
    OCR_FAILED = "PROC_4002"
    TRANSLATION_FAILED = "PROC_4003"
    VIDEO_PROCESSING_FAILED = "PROC_4004"
    
    # External service errors (5xxx)
    GOOGLE_CLOUD_ERROR = "EXT_5001"
    STORAGE_ERROR = "EXT_5002"
    PAYMENT_ERROR = "EXT_5003"
    
    # System errors (9xxx)
    INTERNAL_ERROR = "SYS_9001"
    SERVICE_UNAVAILABLE = "SYS_9002"


class APIException(HTTPException):
    """Base exception class for API errors with standardized error codes."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.details = details
        super().__init__(status_code=status_code, detail=message)


class ValidationException(APIException):
    """Exception for validation errors."""
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class AuthenticationException(APIException):
    """Exception for authentication errors."""
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class ResourceException(APIException):
    """Exception for resource-related errors."""
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class ProcessingException(APIException):
    """Exception for processing errors."""
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class ExternalServiceException(APIException):
    """Exception for external service errors."""
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )


class SystemException(APIException):
    """Exception for system errors."""
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class CustomException(Exception):
    """Base custom exception class for the application.

    Attributes:
        message: The error message
        status_code: HTTP status code for the error
        details: Additional error details as a dictionary
    """

    message: str
    status_code: int
    details: Dict[str, Any]

    def __init__(self, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        """Initialize the custom exception.

        Args:
            message: The error message
            status_code: HTTP status code for the error (default: 400)
            details: Additional error details as a dictionary (default: None)
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class InsufficientCreditsException(CustomException):
    """Exception raised when a user has insufficient credits for an operation.

    Attributes:
        required: Number of credits required for the operation
        available: Number of credits available to the user
    """

    required: float
    available: float

    def __init__(self, required: float, available: float):
        """Initialize the insufficient credits exception.

        Args:
            required: Number of credits required for the operation
            available: Number of credits available to the user
        """
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient credits. Required: {required}, Available: {available}",
            status_code=402,
            details={"required_credits": required, "available_credits": available},
        )


class AnonymousLimitExceededException(CustomException):
    """Exception raised when an anonymous user exceeds their image processing limit."""

    def __init__(self):
        """Initialize the anonymous limit exceeded exception."""
        super().__init__(
            f"Anonymous users can only process {settings.ANONYMOUS_IMAGE_LIMIT} images. Please sign up for more.",
            status_code=429,
            details={"limit": settings.ANONYMOUS_IMAGE_LIMIT},
        )


class InvalidFileFormatException(CustomException):
    """Exception raised when an unsupported file format is provided.

    Attributes:
        format_received: The unsupported file format that was received
    """

    format_received: str

    def __init__(self, format_received: str):
        """Initialize the invalid file format exception.

        Args:
            format_received: The unsupported file format that was received
        """
        self.format_received = format_received
        super().__init__(
            f"Unsupported file format: {format_received}. Supported formats: {', '.join(settings.ALLOWED_EXTENSIONS)}",
            status_code=400,
            details={
                "received_format": format_received,
                "supported_formats": settings.ALLOWED_EXTENSIONS,
            },
        )
