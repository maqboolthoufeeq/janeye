# Third-party imports
from sqlalchemy import create_engine

# Local application imports
from app.settings import settings

# Synchronous Engine
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=True,  # Set to False in production
    future=True,
)
