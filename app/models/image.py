import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageJob(Base):
    __tablename__ = "image_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True)  # Nullable for anonymous users
    device_fingerprint_id = Column(UUID(as_uuid=True), index=True)  # For anonymous tracking

    # File details
    original_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)

    # Storage paths
    input_image_path = Column(String(500), nullable=False)
    output_image_path = Column(String(500))

    # Processing details
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)

    # OCR and translation results
    text_blocks_detected = Column(Integer, default=0)
    text_blocks_translated = Column(Integer, default=0)
    ocr_confidence = Column(Float)

    # Credit usage
    credits_used = Column(Float, nullable=False)

    # Processing metadata
    processing_started_at = Column(DateTime(timezone=True))
    processing_completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    webhook_url = Column(String(500))
    webhook_sent = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_image_job_user", "user_id"),
        Index("idx_image_job_fingerprint", "device_fingerprint_id"),
        Index("idx_image_job_status", "processing_status"),
        Index("idx_image_job_created", "created_at"),
    )
