from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus


def create_job(
    db: Session,
    *,
    user_id: UUID,
    job_type: str,
    target_language: str,
    source_language: Optional[str],
    input_url: str,
) -> Job:
    """Create a new translation job."""
    job = Job(
        user_id=user_id,
        job_type=job_type,
        target_language=target_language,
        source_language=source_language,
        input_url=input_url,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: UUID) -> Optional[Job]:
    """Get a job by ID."""
    return db.query(Job).filter(Job.id == job_id).first()


def get_user_jobs(
    db: Session,
    user_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
    status: Optional[JobStatus] = None,
) -> List[Job]:
    """Get all jobs for a user with optional filtering."""
    query = db.query(Job).filter(Job.user_id == user_id)
    if status:
        query = query.filter(Job.status == status)
    return query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()


def update_job_status(
    db: Session,
    job_id: UUID,
    status: JobStatus,
    error_message: Optional[str] = None,
    output_url: Optional[str] = None,
) -> Optional[Job]:
    """Update job status and related fields."""
    job = get_job(db, job_id)
    if not job:
        return None
        
    job.status = status
    if error_message:
        job.error_message = error_message
    if output_url:
        job.output_url = output_url
    if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        job.completed_at = datetime.utcnow()
        
    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job_id: UUID) -> bool:
    """Delete a job."""
    job = get_job(db, job_id)
    if not job:
        return False
        
    db.delete(job)
    db.commit()
    return True


def cleanup_expired_jobs(db: Session, days: int = 30) -> int:
    """Delete jobs older than specified days."""
    cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
    result = db.query(Job).filter(
        Job.created_at < cutoff_date,
        Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED])
    ).delete()
    db.commit()
    return result 