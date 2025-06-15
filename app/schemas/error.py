from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from uuid import UUID


class ErrorResponse(BaseModel):
    """Standardized error response schema."""
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    trace_id: UUID = Field(..., description="Unique request trace ID for debugging")
    timestamp: float = Field(..., description="Unix timestamp of the error")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "INVALID_IMAGE_FORMAT",
                "message": "The uploaded image format is not supported",
                "details": {"supported_formats": ["PNG", "JPEG", "WEBP"]},
                "trace_id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": 1678901234.567
            }
        } 