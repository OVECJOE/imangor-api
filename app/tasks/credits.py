import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from celery import Task
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.user import DeviceFingerprint, User
from app.models.transaction import CreditTransaction, TransactionType
from app.services.credit_management import CreditService
from app.services.device_tracking import DeviceTrackingService

logger = logging.getLogger(__name__)


class CreditTask(Task):
    """Base task class for credit management operations."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Credit task {task_id} failed: {exc}", exc_info=einfo)


@celery_app.task(base=CreditTask, bind=True)
def expire_old_credits(self) -> Dict[str, int]:
    """
    Expire old credits that have passed their expiration date.
    
    Returns:
        Dict containing number of expired credits and affected users
    """
    try:
        db = SessionLocal()
        try:
            credit_service = CreditService(db)
            now = datetime.now(timezone.utc)
            
            # Find credits that have expired
            expired_credits = db.query(CreditTransaction).filter(
                and_(
                    CreditTransaction.transaction_type == TransactionType.PURCHASE,
                    CreditTransaction.status == "completed",
                    CreditTransaction.expires_at <= now,
                    CreditTransaction.credits_amount > 0
                )
            ).all()
            
            # Expire credits and update user balances
            affected_users = set()
            total_expired = 0
            
            for credit in expired_credits:
                user = credit.user
                if user:
                    affected_users.add(user.id)
                    total_expired += credit.credits_amount
                    credit_service.expire_credits(user.id, credit.credits_amount)
            
            result = {
                "expired_credits": total_expired,
                "affected_users": len(affected_users),
                "timestamp": now.isoformat()
            }
            
            logger.info("Expired old credits", extra=result)
            return result
            
        finally:
            db.close()
    except Exception as e:
        logger.exception("Failed to expire old credits")
        raise


@celery_app.task(base=CreditTask, bind=True)
def cleanup_old_fingerprints(self, days: int = 90) -> Dict[str, int]:
    """
    Clean up old device fingerprints that haven't been seen in a while.
    
    Args:
        days: Number of days of inactivity before cleanup (default: 90)
        
    Returns:
        Dict containing number of cleaned up fingerprints
    """
    try:
        db = SessionLocal()
        try:
            device_service = DeviceTrackingService(db)
            now = datetime.now(timezone.utc)
            cutoff_date = now - timedelta(days=days)
            
            # Find old fingerprints
            old_fingerprints = db.query(DeviceFingerprint).filter(
                DeviceFingerprint.last_seen < cutoff_date
            ).all()
            
            # Delete old fingerprints
            deleted_count = 0
            for fingerprint in old_fingerprints:
                db.delete(fingerprint)
                deleted_count += 1
            
            db.commit()
            
            result = {
                "deleted_fingerprints": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "timestamp": now.isoformat()
            }
            
            logger.info("Cleaned up old fingerprints", extra=result)
            return result
            
        finally:
            db.close()
    except Exception as e:
        logger.exception("Failed to cleanup old fingerprints")
        raise


@celery_app.task
def process_credit_expiry():
    """Periodic task to expire old credits."""
    db = SessionLocal()
    try:
        credit_service = CreditService(db)
        expired_count = credit_service.expire_old_credits()
        logger.info(f"Expired {expired_count} credit transactions")
    finally:
        db.close() 