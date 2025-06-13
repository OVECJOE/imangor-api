from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.user import User
from app.models.transaction import CreditTransaction, TransactionType, TransactionStatus
from app.core.config import settings
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

class CreditService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_credits(self, user_id: str) -> float:
        """Get user's current available credits (excluding expired)"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0.0
        
        # Get unexpired credits
        current_time = datetime.now(timezone.utc)
        
        # Sum all credit additions (purchases, bonuses) that haven't expired
        credit_additions = self.db.query(CreditTransaction).filter(
            and_(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type.in_([
                    TransactionType.PURCHASE, 
                    TransactionType.BONUS, 
                    TransactionType.REFUND
                ]),
                CreditTransaction.status == TransactionStatus.COMPLETED,
                CreditTransaction.expires_at > current_time
            )
        ).all()
        
        total_available = sum(t.credits_amount for t in credit_additions)
        
        # Subtract all usage that happened after the credit additions
        total_used = self.db.query(CreditTransaction).filter(
            and_(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == TransactionType.USAGE,
                CreditTransaction.status == TransactionStatus.COMPLETED
            )
        ).with_entities(
            CreditTransaction.credits_amount
        ).scalar() or 0.0
        
        available_credits = max(0, total_available - abs(total_used))
        
        # Update user's cached balance
        user.credits_balance = available_credits
        self.db.commit()
        
        return available_credits

    def add_credits(self, user_id: str, amount: float, description: str) -> CreditTransaction:
        """Add credits to user account"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Set expiry date
        expires_at = datetime.now(timezone.utc) + timedelta(days=30 * settings.CREDIT_EXPIRY_MONTHS)
        
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type=TransactionType.BONUS,
            status=TransactionStatus.COMPLETED,
            credits_amount=amount,
            description=description,
            expires_at=expires_at
        )
        
        self.db.add(transaction)
        
        # Update user totals
        user.total_credits_purchased += amount
        user.credits_balance += amount
        
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"Added {amount} credits to user {user_id}: {description}")
        return transaction

    def deduct_credits(self, user_id: str, amount: float, description: str, transaction_type: TransactionType = TransactionType.USAGE) -> CreditTransaction:
        """Deduct credits from user account"""
        
        # Check if user has enough credits
        available = self.get_user_credits(user_id)
        if available < amount:
            raise ValueError(f"Insufficient credits. Required: {amount}, Available: {available}")
        
        user = self.db.query(User).filter(User.id == user_id).first()
        
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            status=TransactionStatus.COMPLETED,
            credits_amount=-amount,  # Negative for deduction
            description=description
        )
        
        self.db.add(transaction)
        
        # Update user totals
        user.total_credits_used += amount
        user.credits_balance -= amount
        
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"Deducted {amount} credits from user {user_id}: {description}")
        return transaction

    def calculate_image_cost(self, file_size_bytes: int) -> float:
        """Calculate credit cost for image processing based on file size"""
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        if file_size_mb < 10:
            return settings.CREDIT_COST_SMALL
        else:
            return settings.CREDIR_COST_LARGE  # Note: There's a typo in settings, should be CREDIT_COST_LARGE

    def refund_credits(self, user_id: str, amount: float, reason: str) -> CreditTransaction:
        """Refund credits to user account"""
        return self.add_credits(user_id, amount, f"Refund: {reason}")

    def get_transaction_history(self, user_id: str, limit: int = 50, offset: int = 0):
        """Get user's transaction history"""
        return self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        ).order_by(CreditTransaction.created_at.desc()).offset(offset).limit(limit).all()

    def expire_old_credits(self):
        """Expire old credits (should be run as a periodic task)"""
        current_time = datetime.now(timezone.utc)
        
        expired_transactions = self.db.query(CreditTransaction).filter(
            and_(
                CreditTransaction.expires_at <= current_time,
                CreditTransaction.transaction_type.in_([
                    TransactionType.PURCHASE, 
                    TransactionType.BONUS, 
                    TransactionType.REFUND
                ]),
                CreditTransaction.status == TransactionStatus.COMPLETED
            )
        ).all()
        
        for transaction in expired_transactions:
            # Create expiry record
            expiry_transaction = CreditTransaction(
                user_id=transaction.user_id,
                transaction_type=TransactionType.PENALTY,
                status=TransactionStatus.COMPLETED,
                credits_amount=-transaction.credits_amount,
                description=f"Expired credits from transaction {transaction.id}"
            )
            self.db.add(expiry_transaction)
        
        if expired_transactions:
            self.db.commit()
            logger.info(f"Expired {len(expired_transactions)} credit transactions")
        
        return len(expired_transactions)
