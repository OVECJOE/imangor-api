from typing import Optional
from pydantic import BaseModel, Field, validator
from uuid import UUID
import uuid
from datetime import datetime
from enum import Enum

from app.schemas.image import SupportedLanguage  # Reuse language enum


class VideoTranslationRequest(BaseModel):
    """Schema for video translation requests."""
    
    job_id: UUID = Field(..., description="Unique job identifier")
    target_language: SupportedLanguage
    source_language: SupportedLanguage
    max_duration: int = Field(30, description="Maximum video duration in seconds", ge=1, le=300)
    min_scene_duration: float = Field(0.5, description="Minimum duration between scenes in seconds", ge=0.1, le=5.0)
    subtitle_style: Optional[dict] = Field(
        None,
        description="Subtitle style configuration",
        example={
            "font": "Arial",
            "font_size": 24,
            "color": "#FFFFFF",
            "background_color": "#000000",
            "background_opacity": 0.7,
            "position": "bottom"
        }
    )
    webhook_url: Optional[str] = None
    subtitle_format: str = Field(default="srt", description="Format for subtitles (srt, vtt)")
    burn_subtitles: bool = Field(default=False, description="Whether to burn subtitles into video")
    output_format: str = Field(default="mp4", description="Output video format (mp4, webm)")
    
    @validator("target_language", "source_language")
    def validate_language_code(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError("Language code must be 2 characters")
        return v
    
    @validator("subtitle_style")
    def validate_subtitle_style(cls, v):
        if v is not None:
            required_fields = ["font", "font_size", "color"]
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Missing required subtitle style field: {field}")
        return v


class VideoTranslationResponse(BaseModel):
    """Schema for video translation responses."""
    
    job_id: UUID = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    translations: list = Field(..., description="List of translations with timestamps")
    output_url: str = Field(..., description="URL to the translated video")
    preview_url: Optional[str] = Field(None, description="URL to a low-resolution preview")
    estimated_completion: Optional[float] = Field(None, description="Estimated completion time in seconds")


class VideoJobResponse(BaseModel):
    """Schema for video translation job responses."""
    id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    source_language: str
    target_language: str
    processing_status: str
    credits_used: float
    duration_seconds: Optional[float] = None
    subtitle_path: Optional[str] = None
    output_video_path: Optional[str] = None
    created_at: datetime
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None

    class Config:
        from_attributes = True 