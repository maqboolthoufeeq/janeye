# Third-party imports
from pydantic import BaseModel, ConfigDict, EmailStr

# ============================
# ----- Request schemas ------
# ============================


# Request schema for forget password
class ForgetPasswordRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "example@example.com",
            }
        },
    )


class ResetPasswordRequest(BaseModel):
    new_password: str
    confirm_password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_password": "secret123",
                "confirm_password": "secret123",
            }
        }
    )
