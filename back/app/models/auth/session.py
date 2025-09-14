# Standard library imports
from datetime import UTC, datetime
from typing import TYPE_CHECKING
import uuid

# Third-party imports
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# Local application imports
from app.models.base import Base
from app.models.mixins.uuid_timestamp import UUIDTimeStampMixin

if TYPE_CHECKING:  # pragma: no cover
    # Local application imports
    from app.models.auth.user import User


class Session(UUIDTimeStampMixin, Base):
    __tablename__ = "session"

    # -------------------------------------------------
    # Targeted, non-redundant indexes
    # -------------------------------------------------
    __table_args__ = (
        Index(
            "idx_session_device_token",
            "device_token",
            postgresql_where=text("device_token IS NOT NULL"),
        ),
        Index(
            "idx_session_valid_by_user",
            "user_id",
            postgresql_where=text("is_active = true AND invalidated_at IS NULL"),
        ),
    )

    # -------------------------------------------------
    # Columns
    # -------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )  # 🔸 no separate index: covered by idx_user_active_sessions

    access_token_jti: Mapped[str] = mapped_column(
        String,
        unique=True,  # unique ⇒ PgSQL builds its own unique index
        nullable=False,
        comment="JWT ID for the access token",
    )

    refresh_token_jti: Mapped[str] = mapped_column(
        String,
        unique=True,  # same reasoning as above
        nullable=False,
        comment="JWT ID for the refresh token",
    )

    # --- Device & environment info -----------------------------------------
    device_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    device_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )  # 🔸 dropped duplicate explicit index; keep column for uniqueness checks if ever needed
    device_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(100), nullable=True)
    os_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # --- Location & network -------------------------------------------------
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Session status -----------------------------------------------------
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidation_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    # --- Relationships ------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    # -----------------------------------------------------------------------
    # Helper properties & methods (unchanged)
    # -----------------------------------------------------------------------
    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.is_active and not self.is_expired and self.invalidated_at is None

    @property
    def location_display(self) -> str:
        parts = [p for p in (self.city, self.country) if p]
        return ", ".join(parts) if parts else "Unknown Location"

    @property
    def device_display_name(self) -> str:
        return self.device_name or "Unknown Device"

    @property
    def location_coordinates(self) -> tuple[float, float] | None:
        return (self.latitude, self.longitude) if self.latitude is not None and self.longitude is not None else None

    @property
    def is_mobile_device(self) -> bool:
        return self.device_type == "mobile"

    @property
    def is_suspicious_location(self) -> bool:  # placeholder
        return False

    def invalidate(self, reason: str = "manual_logout") -> None:
        self.is_active = False
        self.invalidated_at = datetime.now(UTC)
        self.invalidation_reason = reason

    def __str__(self) -> str:
        return f"Session: {self.id} · User: {self.user_id} · Device: {self.device_display_name}"
