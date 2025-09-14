"""
Dead Letter Queue utility for handling permanently failed Celery tasks.
"""

# Standard library imports
from datetime import datetime
import json
from typing import Any

# Local application imports
from app.core.caching.redis import redis_client
from app.core.monitoring.logging import get_contextual_logger

logger = get_contextual_logger(__name__)


class DeadLetterQueue:
    """
    Handles permanently failed tasks by storing them in Redis for manual inspection.
    """

    def __init__(self, redis_key_prefix: str = "dlq"):
        self.redis_key_prefix = redis_key_prefix

    async def add_failed_task(
        self,
        task_name: str,
        task_id: str | None,
        task_args: Any,
        task_kwargs: Any,
        exception: str,
        retry_count: int,
    ) -> None:
        """
        Add a permanently failed task to the dead letter queue.

        Args:
            task_name: Name of the failed task
            task_id: Celery task ID
            task_args: Task arguments
            task_kwargs: Task keyword arguments
            exception: Exception that caused the failure
            retry_count: Number of retries attempted
        """
        try:
            failed_task_data = {
                "task_name": str(task_name),
                "task_id": str(task_id) if task_id else "",
                "args": json.dumps(task_args) if task_args else "[]",
                "kwargs": json.dumps(task_kwargs) if task_kwargs else "{}",
                "exception": str(exception),
                "retry_count": str(retry_count),
                "failed_at": datetime.now().isoformat(),
                "status": "failed",
            }

            # Store in Redis with task_id as the key
            key = f"{self.redis_key_prefix}:failed_task:{task_id}"
            result = redis_client.hset(key, mapping=failed_task_data)
            if hasattr(result, "__await__"):
                await result

            # Set expiry to 30 days for cleanup
            expire_result = redis_client.expire(key, 30 * 24 * 60 * 60)
            if hasattr(expire_result, "__await__"):
                await expire_result

            # Add to a list of all failed tasks for easy enumeration
            if task_id:
                zadd_result = redis_client.zadd(
                    f"{self.redis_key_prefix}:failed_tasks_index",
                    {str(task_id): datetime.now().timestamp()},
                )
                if hasattr(zadd_result, "__await__"):
                    await zadd_result

            logger.error(f"Task {task_name} (ID: {task_id}) permanently failed and added to DLQ")

        except Exception as e:
            logger.exception(f"Failed to add task to dead letter queue: {e}")

    async def get_failed_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Retrieve failed tasks from the dead letter queue.

        Args:
            limit: Maximum number of tasks to retrieve

        Returns:
            List of failed task data
        """
        try:
            # Get most recent failed task IDs
            zrevrange_result = redis_client.zrevrange(f"{self.redis_key_prefix}:failed_tasks_index", 0, limit - 1)
            if hasattr(zrevrange_result, "__await__"):
                task_ids = await zrevrange_result
            else:
                task_ids = zrevrange_result

            failed_tasks = []
            for task_id in task_ids or []:
                key = f"{self.redis_key_prefix}:failed_task:{task_id}"
                hgetall_result = redis_client.hgetall(key)
                if hasattr(hgetall_result, "__await__"):
                    task_data = await hgetall_result
                else:
                    task_data = hgetall_result

                if task_data:
                    # Convert bytes to strings if needed
                    task_data_dict = {}
                    for k, v in task_data.items():
                        key_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                        val_str = v.decode("utf-8") if isinstance(v, bytes) else str(v)
                        task_data_dict[key_str] = val_str
                    failed_tasks.append(task_data_dict)

            return failed_tasks

        except Exception as e:
            logger.exception(f"Failed to retrieve failed tasks from DLQ: {e}")
            return []

    async def retry_failed_task(self, task_id: str) -> bool:
        """
        Retry a failed task from the dead letter queue.

        Args:
            task_id: Task ID to retry

        Returns:
            True if task was successfully requeued, False otherwise
        """
        try:
            key = f"{self.redis_key_prefix}:failed_task:{task_id}"
            hgetall_result = redis_client.hgetall(key)
            if hasattr(hgetall_result, "__await__"):
                task_data_raw = await hgetall_result
            else:
                task_data_raw = hgetall_result

            if not task_data_raw:
                logger.warning(f"Task {task_id} not found in DLQ")
                return False

            # Convert bytes to strings if needed
            task_data = {}
            for k, v in task_data_raw.items():
                key_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                val_str = v.decode("utf-8") if isinstance(v, bytes) else str(v)
                task_data[key_str] = val_str

            # Import here to avoid circular imports
            # Local application imports
            from app.core.celery import celery_app

            # Requeue the task
            task_name = task_data.get("task_name")
            if task_name:
                # Get the task by name and apply it
                task = celery_app.tasks.get(task_name)
                if task:
                    try:
                        # Safely parse JSON instead of using eval()
                        args = json.loads(task_data.get("args", "[]"))
                        kwargs = json.loads(task_data.get("kwargs", "{}"))

                        task.apply_async(args=args, kwargs=kwargs)

                        # Mark as requeued
                        hset_result = redis_client.hset(key, "status", "requeued")
                        if hasattr(hset_result, "__await__"):
                            await hset_result

                        logger.info(f"Task {task_id} requeued from DLQ")
                        return True
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse task arguments for {task_id}: {e}")
                        return False

            return False

        except Exception as e:
            logger.exception(f"Failed to retry task {task_id} from DLQ: {e}")
            return False


# Global instance
dlq = DeadLetterQueue()
