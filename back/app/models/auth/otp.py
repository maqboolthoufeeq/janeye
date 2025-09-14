# Standard library imports
from datetime import UTC, datetime, timedelta
import secrets

# Third-party imports
from sqlalchemy import Boolean, Column, DateTime, Integer, String

# Local application imports
from app.models.base import Base
from app.models.mixins.uuid_timestamp import UUIDTimeStampMixin


class OTP(Base, UUIDTimeStampMixin):
    __tablename__ = "otp"

    phone_number = Column(String, nullable=False, index=True)
    otp_code = Column(String(6), nullable=False)
    purpose = Column(String(50), nullable=False)  # signup, login, password_reset
    is_verified = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    @classmethod
    def generate_otp(cls):
        """Generate a 6-digit OTP using secure random"""
        return "".join(str(secrets.randbelow(10)) for _ in range(6))

    @classmethod
    def create_otp(cls, phone_number: str, purpose: str = "signup"):
        """Create a new OTP with 10 minutes expiry"""
        return cls(
            phone_number=phone_number,
            otp_code=cls.generate_otp(),
            purpose=purpose,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

    def is_expired(self) -> bool:
        """Check if OTP has expired"""
        return datetime.now(UTC) > self.expires_at

    def verify(self, otp_code: str) -> bool:
        """Verify OTP code"""
        if self.is_expired():
            return False
        if self.is_verified:
            return False
        if self.attempts >= 3:
            return False

        self.attempts += 1

        if self.otp_code == otp_code:
            self.is_verified = True
            self.verified_at = datetime.now(UTC)
            return True

        return False
