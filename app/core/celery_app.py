from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "imangor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.image",
        "app.tasks.video",
        "app.tasks.cleanup",
        "app.tasks.metrics",
        "app.tasks.credits"
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1
)

# Configure task queues
celery_app.conf.task_routes = {
    "app.tasks.image.*": {"queue": "image_processing"},
    "app.tasks.video.*": {"queue": "video_processing"},
    "app.tasks.cleanup.*": {"queue": "maintenance"},
    "app.tasks.metrics.*": {"queue": "maintenance"},
    "app.tasks.credits.*": {"queue": "maintenance"}
}

# Configure beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Cleanup tasks
    "cleanup-expired-jobs": {
        "task": "app.tasks.cleanup.cleanup_expired_jobs_task",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
        "args": (30,)  # Keep jobs for 30 days
    },
    
    # Metrics tasks
    "update-usage-metrics": {
        "task": "app.tasks.metrics.update_usage_metrics",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    
    # Credit management tasks
    "expire-old-credits": {
        "task": "app.tasks.credits.expire_old_credits",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    },
    "cleanup-old-fingerprints": {
        "task": "app.tasks.credits.cleanup_old_fingerprints",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
        "args": (90,)  # Clean up fingerprints older than 90 days
    }
} 