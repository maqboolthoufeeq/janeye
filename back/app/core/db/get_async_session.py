# Standard library imports
from collections.abc import AsyncGenerator

# Third-party imports
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Local application imports
from app.core.db.create_async_engine import async_engine

# Asynchronous Session Factory
AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


# Optional: Dependency to get an async session (e.g., for FastAPI)
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
