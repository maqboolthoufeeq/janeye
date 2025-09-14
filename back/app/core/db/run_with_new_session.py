# Standard library imports
from collections.abc import Awaitable, Callable
from typing import Any

# Third-party imports
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from app.core.db.get_async_session import get_async_session


async def run_with_new_session(
    func: Callable[[AsyncSession, Any], Awaitable[Any]],
    # Function receiving AsyncSession and returning an Awaitable
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Run any function with a fresh new DB session.

    Args:
        func: The function to run, which must accept an
        AsyncSession as its first argument.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        Any: The result of the function execution.
    """
    async for session in get_async_session():
        return await func(session, *args, **kwargs)
