# Third-party imports
from pydantic import BaseModel

# ============================
# ----- Request schemas ------
# ============================


class OTPVerificationRequest(BaseModel):
    """Request model for OTP verification."""

    otp_id: str
    otp: str

    model_config = {"json_schema_extra": {"example": {"otp_id": "uuid-4", "otp": "123456"}}}


# ============================
# ----- Response schemas -----
# ============================


class OTPVerificationResponse(BaseModel):
    """Response model for OTP verification."""

    is_verified: bool
    user_id: str | None = None

    model_config = {"json_schema_extra": {"example": {"is_verified": True}}}
