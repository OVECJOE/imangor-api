import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from celery import Task
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.image import ImageJob, ProcessingStatus
from app.models.user import DeviceFingerprint, User
from app.models.transaction import CreditTransaction, TransactionType
from app.services.device_tracking import DeviceTrackingService

logger = logging.getLogger(__name__)


class MetricsTask(Task):
    """Base task class for metrics operations."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Metrics task {task_id} failed: {exc}", exc_info=einfo)


@celery_app.task(base=MetricsTask, bind=True)
def update_usage_metrics(self) -> Dict:
    """
    Update usage metrics and statistics.
    
    Returns:
        Dict containing updated metrics
    """
    try:
        db = SessionLocal()
        try:
            # Get current time and time ranges
            now = datetime.now(timezone.utc)
            today = now.date()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            # Image processing metrics
            total_images = db.query(func.count(ImageJob.id)).scalar()
            successful_images = db.query(func.count(ImageJob.id)).filter(
                ImageJob.processing_status == ProcessingStatus.COMPLETED
            ).scalar()
            failed_images = db.query(func.count(ImageJob.id)).filter(
                ImageJob.processing_status == ProcessingStatus.FAILED
            ).scalar()

            # Recent activity
            images_today = db.query(func.count(ImageJob.id)).filter(
                func.date(ImageJob.created_at) == today
            ).scalar()
            images_this_week = db.query(func.count(ImageJob.id)).filter(
                ImageJob.created_at >= week_ago
            ).scalar()
            images_this_month = db.query(func.count(ImageJob.id)).filter(
                ImageJob.created_at >= month_ago
            ).scalar()

            # User metrics
            total_users = db.query(func.count(User.id)).scalar()
            active_users = db.query(func.count(User.id)).filter(
                User.last_login >= week_ago
            ).scalar()
            total_credits = db.query(func.sum(CreditTransaction.credits_amount)).filter(
                CreditTransaction.transaction_type == TransactionType.PURCHASE,
                CreditTransaction.status == "completed"
            ).scalar() or 0.0

            # Device fingerprint metrics
            total_devices = db.query(func.count(DeviceFingerprint.id)).scalar()
            active_devices = db.query(func.count(DeviceFingerprint.id)).filter(
                DeviceFingerprint.last_seen >= week_ago
            ).scalar()

            # Compile metrics
            metrics = {
                "total_images": total_images,
                "successful_images": successful_images,
                "failed_images": failed_images,
                "success_rate": (successful_images / total_images * 100) if total_images > 0 else 0,
                "images_today": images_today,
                "images_this_week": images_this_week,
                "images_this_month": images_this_month,
                "total_users": total_users,
                "active_users": active_users,
                "total_credits": total_credits,
                "total_devices": total_devices,
                "active_devices": active_devices,
                "timestamp": now.isoformat()
            }

            logger.info("Updated usage metrics", extra=metrics)
            return metrics

        finally:
            db.close()
    except Exception as e:
        logger.exception("Failed to update usage metrics")
        raise 