# Standard library imports
from datetime import datetime
import re

# Third-party imports
from pydantic import BaseModel, Field, validator


class PhoneSignupRequest(BaseModel):
    phone_number: str = Field(..., description="Indian phone number (10 digits)")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str | None = Field(None, max_length=50)
    state: str = Field(..., description="Indian state")
    district: str = Field(..., description="District")
    local_body: str | None = Field(None, description="Panchayath/Corporation")

    @validator("phone_number")
    def validate_indian_phone(cls, v):
        # Remove any spaces, dashes, or country code
        cleaned = re.sub(r"[\s\-\+]", "", v)
        if cleaned.startswith("91"):
            cleaned = cleaned[2:]

        # Check if it's a valid 10-digit Indian mobile number
        if not re.match(r"^[6-9]\d{9}$", cleaned):
            raise ValueError("Invalid Indian mobile number. Must be 10 digits starting with 6-9")

        return cleaned


class OTPRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to send OTP")
    purpose: str = Field("signup", description="Purpose of OTP: signup, login, password_reset")


class OTPVerifyRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    purpose: str = Field("signup", description="Purpose of OTP")


class PhoneLoginRequest(BaseModel):
    phone_number: str = Field(..., description="Indian phone number")

    @validator("phone_number")
    def validate_indian_phone(cls, v):
        cleaned = re.sub(r"[\s\-\+]", "", v)
        if cleaned.startswith("91"):
            cleaned = cleaned[2:]

        if not re.match(r"^[6-9]\d{9}$", cleaned):
            raise ValueError("Invalid Indian mobile number")

        return cleaned


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    first_name: str | None
    last_name: str | None
    phone_number: str
    is_phone_verified: bool
    state: str | None
    district: str | None


class UserResponse(BaseModel):
    id: str
    phone_number: str
    first_name: str | None
    last_name: str | None
    email: str | None
    state: str | None
    district: str | None
    local_body: str | None
    is_phone_number_verified: bool
    monthly_vote_count: int
    current_vote_month: str | None
    created_at: datetime

    @validator("id", pre=True)
    def convert_uuid_to_str(cls, v):
        if hasattr(v, "__str__"):
            return str(v)
        return v

    class Config:
        from_attributes = True
