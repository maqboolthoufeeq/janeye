# Third-party imports
from sqlalchemy.ext.asyncio import create_async_engine

# Local application imports
from app.settings import settings

# Asynchronous Engine
async_engine = create_async_engine(
    str(settings.SQLALCHEMY_ASYNC_DATABASE_URI),
    echo=True,  # Set to False in production
    future=True,
)
