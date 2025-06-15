import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class TransactionType(enum.Enum):
    PURCHASE = "purchase"
    USAGE = "usage"
    REFUND = "refund"
    BONUS = "bonus"
    PENALTY = "penalty"


class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)

    # Credit details
    credits_amount = Column(Float, nullable=False)
    cost_naira = Column(Float)  # For purchases
    cost_usd = Column(Float)  # For purchases

    # Payment details
    payment_reference = Column(String(255), unique=True, index=True)
    flutterwave_tx_ref = Column(String(255), index=True)

    # Metadata
    description = Column(String(500))
    transaction_metadata = Column(Text)  # JSON string
    expires_at = Column(DateTime(timezone=True))  # For purchased credits

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_transaction_user_type", "user_id", "transaction_type"),
        Index("idx_transaction_status", "status"),
        Index("idx_transaction_expires", "expires_at"),
    )
