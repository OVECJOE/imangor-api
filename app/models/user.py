from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, Index, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base

class UserStatus(enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    google_id = Column(String(255), unique=True, index=True)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(500))
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    
    # Credit system
    credits_balance = Column(Float, default=0.0)
    total_credits_purchased = Column(Float, default=0.0)
    total_credits_used = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # API access
    api_key = Column(String(64), unique=True, index=True)
    api_key_created_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_user_email_status', 'email', 'status'),
        Index('idx_user_created_at', 'created_at'),
    )

class DeviceFingerprint(Base):
    __tablename__ = "device_fingerprints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint_hash = Column(String(64), unique=True, index=True, nullable=False)
    
    # Device info
    user_agent = Column(Text)
    screen_resolution = Column(String(50))
    timezone = Column(String(50))
    language = Column(String(10))
    platform = Column(String(50))
    
    # Usage tracking
    images_processed = Column(Integer, default=0)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_fingerprint_hash', 'fingerprint_hash'),
        Index('idx_fingerprint_last_seen', 'last_seen'),
    )
