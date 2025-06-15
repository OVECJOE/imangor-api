from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class JobStatus(str, Enum):
    """Status of a translation job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Model for tracking translation jobs."""
    
    __tablename__ = "jobs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    job_type = Column(String(50), nullable=False)  # "image" or "video"
    target_language = Column(String(2), nullable=False)
    source_language = Column(String(2), nullable=True)
    input_url = Column(String(500), nullable=False)
    output_url = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Job {self.id} ({self.status})>" 