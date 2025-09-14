# Standard library imports
from typing import Any

# Third-party imports
from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

# Local application imports
from app.utils.validators.phone_validator import validate_phone_number as validate_phone_number_util


class UserSchema(BaseModel):
    """
    A reusable schema to represent user metadata.
    """

    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    email: EmailStr
    is_email_verified: bool
    is_phone_number_verified: bool
    is_available_for_calls: bool | None = None

    model_config = ConfigDict(
        from_attributes=True,  # This allows ORM-like attribute handling
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+14155552671",
                "email": "mail@example.com",
                "is_email_verified": True,
                "is_phone_number_verified": False,
                "is_available_for_calls": True,
            }
        },
    )


# ============================
# ----- Request schemas ------
# ============================


class UserCreateRequest(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    email: EmailStr
    password: str
    confirm_password: str

    @model_validator(mode="before")
    def check_passwords(cls, values: dict[str, Any]) -> dict[str, Any]:
        pwd = values.get("password")
        confirm = values.get("confirm_password")
        if pwd != confirm:
            raise ValueError("Passwords do not match")
        phone_number = values.get("phone_number")
        phone_value = validate_phone_number_util(phone_number)
        if phone_value is None:
            raise ValueError("Invalid phone number")

        return values

    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+14155552671",
                "email": "mail@example.com",
                "password": "secret123",
                "confirm_password": "secret123",
            }
        }
    }


class UserCreateRequestInvite(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    password: str
    confirm_password: str

    @model_validator(mode="before")
    def check_passwords(cls, values: dict[str, Any]) -> dict[str, Any]:
        pwd = values.get("password")
        confirm = values.get("confirm_password")
        if pwd != confirm:
            raise ValueError("Passwords do not match")
        return values

    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+14155552671",
                "password": "secret123",
                "confirm_password": "secret123",
            }
        }
    }


# ============================
# ----- Response schemas -----
# ============================


class UserCreateResponse(BaseModel):
    otp_id: str

    model_config = {"json_schema_extra": {"example": {"otp_id": "uuid-4"}}}
