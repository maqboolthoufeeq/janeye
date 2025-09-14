# Standard library imports
import asyncio
from collections.abc import Awaitable, Callable
import functools
from typing import Any, TypeVar

# Local application imports
from app.core.monitoring.logging import get_contextual_logger

logger = get_contextual_logger(__name__)

T = TypeVar("T")


def run_async_in_celery(coro: Awaitable[T]) -> T:
    """
    Utility function to properly run async code in Celery tasks.

    This creates a new event loop only if one doesn't exist, and properly handles cleanup.
    It's designed to be thread-safe and work correctly in Celery's execution environment.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine

    Raises:
        Any exception raised by the coroutine
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        else:
            # Loop exists but not running, we can use it
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)


def celery_async_task(func: Callable[..., Awaitable[T]]) -> Callable[..., T]:
    """
    Decorator to convert async functions to sync functions for Celery tasks.

    This decorator wraps async functions to make them compatible with Celery,
    which expects synchronous functions.

    Usage:
        @celery_app.task(bind=True)
        @celery_async_task
        async def my_async_task(self, param1, param2):
            # async code here
            result = await some_async_function()
            return result
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return run_async_in_celery(func(*args, **kwargs))

    return wrapper


class CeleryAsyncTaskMixin:
    """
    Mixin class to provide async support for Celery tasks.

    This can be used when you have a class-based approach to Celery tasks.
    """

    def run_async(self, coro: Awaitable[T]) -> T:
        """Run an async coroutine in the Celery task context."""
        return run_async_in_celery(coro)

    def safe_async_call(self, coro: Awaitable[T], default: T | None = None) -> T | None:
        """
        Safely run an async coroutine, returning default on error.

        Args:
            coro: The coroutine to run
            default: Default value to return on error

        Returns:
            The result of the coroutine or the default value
        """
        try:
            return self.run_async(coro)
        except Exception as e:
            logger.exception(f"Error in safe_async_call: {e}")
            return default


def with_retry_on_failure(
    max_retries: int = 3,
    countdown: int = 60,
    exponential_backoff: bool = True,
) -> Callable[..., Callable[..., Any]]:
    """
    Decorator to add retry logic to Celery tasks.

    Args:
        max_retries: Maximum number of retries
        countdown: Initial countdown in seconds
        exponential_backoff: Whether to use exponential backoff

    Usage:
        @celery_app.task(bind=True)
        @with_retry_on_failure(max_retries=3, countdown=30)
        def my_task(self, param1):
            # task logic here
            pass
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                retry_countdown = countdown
                if exponential_backoff:
                    # Exponential backoff: 2^retry_count * countdown
                    retry_count = getattr(self.request, "retries", 0)
                    retry_countdown = countdown * (2**retry_count)

                logger.exception(f"Task {func.__name__} failed, retrying...")
                raise self.retry(exc=exc, countdown=retry_countdown, max_retries=max_retries)

        return wrapper

    return decorator
