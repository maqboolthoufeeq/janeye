"""
Pre-start script to check database connectivity and other services.
"""

# Standard library imports
import asyncio
import logging
import sys

# Third-party imports
import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Local application imports
from app.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_database() -> bool:
    """Check if database is accessible and ready."""
    try:
        # Build connection string for asyncpg
        db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

        # Try to connect using asyncpg directly first
        conn = await asyncpg.connect(db_url)
        await conn.close()
        logger.info("Database connection successful using asyncpg")

        # Also test with SQLAlchemy
        engine = create_async_engine(str(settings.SQLALCHEMY_ASYNC_DATABASE_URI), echo=False)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()

        logger.info("✅ Database is ready!")
        return True

    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def wait_for_database(max_retries: int = 30, retry_interval: int = 2) -> bool:
    """
    Wait for database to be ready.

    Args:
        max_retries: Maximum number of connection attempts
        retry_interval: Seconds between retries

    Returns:
        True if database is ready, False otherwise
    """
    logger.info("Waiting for database to be ready...")

    for attempt in range(1, max_retries + 1):
        logger.info(f"Database connection attempt {attempt}/{max_retries}")

        if await check_database():
            return True

        if attempt < max_retries:
            logger.info(f"Retrying in {retry_interval} seconds...")
            await asyncio.sleep(retry_interval)

    logger.error(f"Failed to connect to database after {max_retries} attempts")
    return False


async def main() -> None:
    """Main pre-start routine."""
    logger.info("Starting pre-start checks...")

    # Check database
    if not await wait_for_database():
        logger.error("Pre-start checks failed: Database is not available")
        sys.exit(1)

    # Add other service checks here if needed (Redis, RabbitMQ, etc.)

    logger.info("✅ All pre-start checks passed!")


if __name__ == "__main__":
    asyncio.run(main())
