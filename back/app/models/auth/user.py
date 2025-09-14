# Standard library imports
from datetime import datetime
from typing import TYPE_CHECKING

# Third-party imports
from sqlalchemy import Boolean, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func

# Local application imports
from app.models.base import Base
from app.models.mixins.uuid_timestamp import UUIDTimeStampMixin
from app.utils.validators.phone_validator import validate_phone_number

if TYPE_CHECKING:
    # Local application imports
    from app.models.auth.session import Session


class User(UUIDTimeStampMixin, Base):
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(
        String,
        index=True,
        unique=True,
        nullable=False,
        comment="User’s email (acts as username)",
    )

    # Commented out avatar_id as file table doesn't exist yet
    # avatar_id: Mapped[uuid.UUID | None] = mapped_column(
    #     PG_UUID(as_uuid=True),
    #     ForeignKey("file.id", ondelete="SET NULL"),
    #     index=True,
    #     nullable=True,
    # )

    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)

    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_phone_number_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Global availability for receiving calls

    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user", cascade="all, delete")

    # JanEye specific fields
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    local_body: Mapped[str | None] = mapped_column(String(100), nullable=True)
    monthly_vote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_vote_month: Mapped[str | None] = mapped_column(String(7), nullable=True)

    # Relationships for JanEye - commented out for now to avoid import issues
    # reported_issues = relationship("Issue", back_populates="reporter", cascade="all, delete", foreign_keys="[Issue.reporter_id]")
    # votes = relationship("Vote", back_populates="voter", cascade="all, delete", foreign_keys="[Vote.voter_id]")

    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Last login timestamp",
    )

    @validates("phone_number")
    def validate_phone_number(self, key: str, value: str | None) -> str | None:
        """
        Use the shared phone number validation utility to validate and normalize
        the phone number.
        """
        phone_value = validate_phone_number(value)
        if phone_value is None:
            raise ValueError("Invalid phone number")
        return str(phone_value)

    def __str__(self) -> str:
        return f"User: {self.first_name} {self.last_name} - {self.email}"
