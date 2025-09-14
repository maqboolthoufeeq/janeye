# Standard library imports
from datetime import UTC, datetime
import uuid

# Third-party imports
from sqlalchemy import TIMESTAMP, Column, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class UUIDTimeStampMixin:
    """A reusable mixin that:
    - Provides a UUID primary key named 'id'
    - Includes created_at and updated_at timestamps automatically handled by Postgres (and SQLAlchemy)

    This mixin is abstract and is not mapped as its own table.
    """

    __abstract__ = True  # Prevents SQLAlchemy from mapping this mixin as a separate table

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=lambda: datetime.now(UTC),
    )
