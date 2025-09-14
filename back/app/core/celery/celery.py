# Standard library imports
from datetime import datetime
from typing import Any

# Third-party imports
from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure, task_prerun, task_retry, task_success

# Local application imports
from app.settings import settings

celery_app = Celery(
    "janeye",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    # Additional settings for better async task handling
    task_acks_late=True,  # Acknowledge tasks only after completion
    worker_disable_rate_limits=True,  # Disable rate limits for better performance
    task_reject_on_worker_lost=True,  # Reject tasks if worker is lost
    task_track_started=True,  # Track when tasks start
    worker_max_tasks_per_child=1000,  # Restart workers after processing tasks
    worker_max_memory_per_child=200000,  # Restart workers after memory usage (KB)
    # Better retry configuration
    task_default_retry_delay=60,  # Default retry delay
    task_max_retries=3,  # Default max retries
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s",
    # RedBeat configuration
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.CELERY_BROKER_URL,  # Use the same Redis instance
    redbeat_key_prefix="redbeat",  # Optional: prefix for Redis keys
    redbeat_lock_timeout=300,  # Lock timeout for scheduler
)

# Configure periodic tasks with celery.conf.beat_schedule
celery_app.conf.beat_schedule = {
    # Daily subscription expiration check - runs at 3 AM daily
    "expire-monthly-subscriptions": {
        "task": "app.tasks.monthly_subscriptions.expire_monthly_subscriptions_task",
        "schedule": crontab(
            hour="2",  # Changed from "15" to "3" for 3 AM
            minute="0",  # Changed from "05" to "0"
        ),
    },
    # Auto-renewal processing - runs 4 times a day (every 6 hours)
    "process-auto-renewals-00": {
        "task": "app.tasks.subscription_renewal_tasks.process_auto_renewals_batch",
        "schedule": crontab(
            hour="0",  # 12:00 AM
            minute="0",
        ),
    },
    "process-auto-renewals-06": {
        "task": "app.tasks.subscription_renewal_tasks.process_auto_renewals_batch",
        "schedule": crontab(
            hour="6",  # 6:00 AM
            minute="0",
        ),
    },
    "process-auto-renewals-12": {
        "task": "app.tasks.subscription_renewal_tasks.process_auto_renewals_batch",
        "schedule": crontab(
            hour="12",  # 12:00 PM
            minute="0",
        ),
    },
    "process-auto-renewals-18": {
        "task": "app.tasks.subscription_renewal_tasks.process_auto_renewals_batch",
        "schedule": crontab(
            hour="18",  # 6:00 PM
            minute="0",
        ),
    },
    # Daily cleanup of expired renewal tasks - runs at 3 AM daily
    "cleanup-expired-renewal-tasks": {
        "task": "app.tasks.subscription_renewal_tasks.cleanup_expired_renewal_tasks",
        "schedule": crontab(
            hour="3",  # 3 AM
            minute="0",
        ),
    },
    # Health check task - runs every 5 minutes to verify beat scheduler
    "celery-beat-health-check": {
        "task": "app.tasks.health_check.celery_beat_health_check_task",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}


@task_prerun.connect  # type: ignore[misc]
def setup_task_logger(task_id: str, task: Any, *args: Any, **kwargs: Any) -> None:  # noqa: ARG001
    # Local application imports
    from app.core.logging import get_contextual_logger

    task.request.logger = get_contextual_logger(
        task.name,
        task_id=task_id,
    )


@task_retry.connect  # type: ignore[misc]
def task_retry_handler(
    sender: Any = None,
    task_id: str | None = None,
    reason: str | None = None,
    _traceback: Any = None,
    _einfo: Any = None,
    **kwargs: Any,  # noqa: ARG001
) -> None:
    # Local application imports
    from app.core.logging import get_contextual_logger

    logger = get_contextual_logger("celery.task.retry", task_id=task_id)
    logger.warning(f"Task {sender.name} (ID: {task_id}) is being retried. Reason: {reason}")


@task_failure.connect  # type: ignore[misc]
def task_failure_handler(
    sender: Any = None,
    task_id: str | None = None,
    exception: Exception | None = None,
    _traceback: Any = None,
    _einfo: Any = None,
    **kwargs: Any,  # noqa: ARG001
) -> None:
    # Local application imports
    from app.core.logging import get_contextual_logger

    logger = get_contextual_logger("celery.task.failure", task_id=task_id)
    logger.error(f"Task {sender.name} (ID: {task_id}) failed: {exception}")

    # Check if this is a final failure (after all retries exhausted)
    task = kwargs.get("task")
    if task and hasattr(task, "request"):
        retry_count = getattr(task.request, "retries", 0)
        max_retries = getattr(task, "max_retries", 3)

        if retry_count >= max_retries:
            # This is a permanent failure, add to dead letter queue
            _handle_permanent_task_failure(sender, task_id, task, exception, retry_count)

    # Send alert for critical beat tasks
    if sender and hasattr(sender, "name"):
        task_name = sender.name
        critical_tasks = [
            "app.tasks.monthly_subscriptions.expire_monthly_subscriptions_task",
            "app.tasks.subscription_renewal_tasks.process_auto_renewals_batch",
            "app.tasks.subscription_renewal_tasks.cleanup_expired_renewal_tasks",
        ]

        if task_name in critical_tasks:
            _send_critical_task_failure_alert(task_name, task_id, str(exception))


def _send_critical_task_failure_alert(task_name: str, task_id: str | None, error: str) -> None:
    """Send alert for critical task failures."""
    # Local application imports
    from app.core.logging import get_contextual_logger
    from app.settings import settings
    from app.tasks.email import send_email_task

    try:
        subject = f"🚨 CRITICAL: Celery Beat Task Failed - {task_name}"
        message = f"""
Critical Celery beat task has failed:

Task: {task_name}
Task ID: {task_id}
Error: {error}
Time: {datetime.now().isoformat()}

This requires immediate attention as it may affect subscription processing.
"""

        # Send alert email to admin (run synchronously to ensure delivery)
        send_email_task.apply_async(
            args=[settings.ADMIN_EMAIL, subject, message],
            retry=True,
            retry_policy={
                "max_retries": 2,
                "interval_start": 30,
                "interval_step": 30,
            },
        )
    except Exception as e:
        # Don't let alert failures break the failure handler
        logger = get_contextual_logger("celery.alert")
        logger.error(f"Failed to send critical task failure alert: {e}")


def _handle_permanent_task_failure(
    sender: Any,
    task_id: str | None,
    task: Any,
    exception: Exception | None,
    retry_count: int,
) -> None:
    """Handle permanently failed tasks by adding them to the dead letter queue."""
    # Local application imports
    from app.core.logging import get_contextual_logger
    from app.utils.celery_utils import run_async_in_celery
    from app.utils.dead_letter_queue import dlq

    logger = get_contextual_logger("celery.permanent.failure", task_id=task_id)

    try:
        task_name = sender.name if sender and hasattr(sender, "name") else "unknown"
        task_args = getattr(task.request, "args", []) if task and hasattr(task, "request") else []
        task_kwargs = getattr(task.request, "kwargs", {}) if task and hasattr(task, "request") else {}

        # Add to dead letter queue asynchronously
        run_async_in_celery(
            dlq.add_failed_task(
                task_name=task_name,
                task_id=task_id,
                task_args=task_args,
                task_kwargs=task_kwargs,
                exception=str(exception) if exception else "Unknown error",
                retry_count=retry_count,
            )
        )

        logger.error(f"Task {task_name} (ID: {task_id}) permanently failed after {retry_count} retries. Added to DLQ.")
    except Exception as e:
        logger.exception(f"Failed to handle permanent task failure: {e}")


@task_success.connect  # type: ignore[misc]
def task_success_handler(  # noqa
    sender: Any | None = None,
    result: Any = None,  # noqa: ARG001
    **kwargs: Any,  # noqa: ARG001
) -> None:
    # Local application imports
    from app.core.logging import get_contextual_logger

    logger = get_contextual_logger("celery.task.success")
    logger.info(f"Task {sender.name} completed successfully")  # type: ignore[union-attr]


# Add this at the end of celery.py to debug task registration
if __name__ == "__main__":
    print("Registered tasks:")
    for task_name in sorted(celery_app.tasks.keys()):
        print(f"  - {task_name}")

    print("\nBeat schedule:")
    for schedule_name, config in celery_app.conf.beat_schedule.items():
        print(f"  - {schedule_name}: {config['task']}")
