"""SQLite engine for development."""

# Third-party imports
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Local application imports
from app.settings import settings

# Create SQLite engine for development
if settings.ENVIRONMENT == "development":
    DATABASE_URL = "sqlite+aiosqlite:///./janeye.db"
else:
    DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=True if settings.ENVIRONMENT == "development" else False,
    future=True,
)

async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
