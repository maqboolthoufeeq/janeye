"""
Celery application configuration.
"""

# Third-party imports
from celery import Celery

# Local application imports
from app.settings import settings

# Create Celery app
celery_app = Celery(
    "fastapi_boilerplate",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Update task settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks from all apps
celery_app.autodiscover_tasks(["app.tasks"])


# Example task
@celery_app.task
def test_celery(msg: str) -> str:
    """Test celery task."""
    return f"Celery is working! Message: {msg}"
