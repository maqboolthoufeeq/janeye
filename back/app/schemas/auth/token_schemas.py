# Third-party imports
from pydantic import BaseModel, EmailStr

# ============================
# ----- Token schemas ------
# ============================


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


# ============================
# ----- Request schemas ------
# ============================


class AccessTokenRequest(BaseModel):
    """Request model for access token generation."""

    email: EmailStr
    password: str

    model_config = {"json_schema_extra": {"example": {"email": "admin@projectname.com", "password": "admin"}}}


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing access token."""

    refresh_token: str

    model_config = {"json_schema_extra": {"example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}}}


class LogoutRequest(BaseModel):
    """Request model for logout."""

    refresh_token: str

    model_config = {"json_schema_extra": {"example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}}}


# ============================
# ----- Response schemas -----
# ============================


class AccessTokenResponse(BaseModel):
    """Response model for access token generation."""

    access_token: str
    refresh_token: str
    token_type: str
    user_id: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "abc123",
                "refresh_token": "def456",
                "token_type": "bearer",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }
    }
