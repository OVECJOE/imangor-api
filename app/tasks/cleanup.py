import logging
from celery import Task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.crud.job import cleanup_expired_jobs

logger = logging.getLogger(__name__)


class CleanupTask(Task):
    """Base task class for cleanup operations."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Cleanup task {task_id} failed: {exc}", exc_info=einfo)


@celery_app.task(base=CleanupTask, bind=True)
def cleanup_expired_jobs_task(self, days: int = 30) -> int:
    """
    Clean up expired jobs from the database.
    
    Args:
        days: Number of days after which to delete completed/failed jobs
    
    Returns:
        Number of jobs deleted
    """
    try:
        db = SessionLocal()
        try:
            deleted_count = cleanup_expired_jobs(db, days=days)
            logger.info(f"Cleaned up {deleted_count} expired jobs")
            return deleted_count
        finally:
            db.close()
    except Exception as e:
        logger.exception("Failed to clean up expired jobs")
        raise 