from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.transaction import CreditTransaction, TransactionType, TransactionStatus
from app.core.config import settings
from app.core.exceptions import InsufficientCreditsException

class CreditService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_credits(self, user_id: str) -> float:
        """Get user's current available credits (non-expired)"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0.0
        
        # Get valid credits (non-expired)
        valid_credits = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.status == TransactionStatus.COMPLETED,
            CreditTransaction.transaction_type.in_([TransactionType.PURCHASE, TransactionType.BONUS]),
            CreditTransaction.expires_at > datetime.now(timezone.utc)
        ).all()
        
        total_valid = sum(t.credits_amount for t in valid_credits)
        
        # Subtract used credits
        used_credits = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.status == TransactionStatus.COMPLETED,
            CreditTransaction.transaction_type.in_([TransactionType.USAGE, TransactionType.PENALTY])
        ).all()
        
        total_used = sum(abs(t.credits_amount) for t in used_credits)
        
        return max(0.0, total_valid - total_used)
    
    def calculate_image_cost(self, file_size_bytes: int) -> float:
        """Calculate credit cost based on file size"""
        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb < 10:
            return settings.CREDIT_COST_SMALL
        # Scale cost for larger files
        return settings.CREDIR_COST_LARGE * (file_size_mb / 10)

    def deduct_credits(self, user_id: str, amount: float, description: str, 
                      transaction_type: TransactionType = TransactionType.USAGE) -> CreditTransaction:
        """Deduct credits from user account"""
        available_credits = self.get_user_credits(user_id)
        
        if available_credits < amount:
            raise InsufficientCreditsException(amount, available_credits)
        
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            status=TransactionStatus.COMPLETED,
            credits_amount=-amount,  # Negative for deduction
            description=description
        )
        
        self.db.add(transaction)
        
        # Update user's total used credits
        user = self.db.query(User).filter(User.id == user_id).first()
        user.total_credits_used += amount
        
        self.db.commit()
        return transaction
    
    def add_credits(self, user_id: str, amount: float, description: str,
                   expires_months: int = None, transaction_type: TransactionType = TransactionType.BONUS) -> CreditTransaction:
        """Add credits to user account"""
        expires_at = None
        if expires_months:
            expires_at = datetime.utcnow() + timedelta(days=expires_months * 30)
        
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            status=TransactionStatus.COMPLETED,
            credits_amount=amount,
            description=description,
            expires_at=expires_at
        )
        
        self.db.add(transaction)
        
        # Update user's balance if it's a purchase
        if transaction_type == TransactionType.PURCHASE:
            user = self.db.query(User).filter(User.id == user_id).first()
            user.total_credits_purchased += amount
        
        self.db.commit()
        return transaction
