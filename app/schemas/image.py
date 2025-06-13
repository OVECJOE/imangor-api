from enum import Enum
from typing import Optional
import uuid
from datetime import datetime
from pydantic import BaseModel

class SupportedLanguage(str, Enum):
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    IT = "it"
    PT = "pt"
    RU = "ru"
    JA = "ja"
    KO = "ko"
    ZH = "zh"
    AR = "ar"
    HI = "hi"

class ImageUploadRequest(BaseModel):
    source_language: SupportedLanguage
    target_language: SupportedLanguage
    webhook_url: Optional[str] = None

class ImageJobResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    source_language: str
    target_language: str
    processing_status: str
    credits_used: float
    text_blocks_detected: Optional[int] = None
    text_blocks_translated: Optional[int] = None
    ocr_confidence: Optional[float] = None
    created_at: datetime
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class DeviceFingerprintRequest(BaseModel):
    user_agent: str
    screen_resolution: str
    timezone: str
    language: str
    platform: str
