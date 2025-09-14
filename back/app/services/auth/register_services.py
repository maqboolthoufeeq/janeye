# Standard library imports
import json
from typing import Any
import uuid

# Local application imports
from app.core.redis import redis_client
from app.schemas.auth import UserCreateRequest
from app.settings import settings
from app.utils.otp_utils import generate_otp
from app.utils.password_utils import get_password_hash


def prepare_registration_data(
    input_data: UserCreateRequest,
    logger: Any,
    invitation_token: str | None = None,
) -> tuple[dict[str, Any], str]:
    registration_data = input_data.model_dump()
    logger.debug(f"Registration data before processing: {registration_data}")
    email = registration_data.get("email", "")
    if not isinstance(email, str):
        raise ValueError("Email must be a string")

    password = registration_data.get("password", "")
    if not isinstance(password, str):
        raise ValueError("Password must be a string")
    hashed_password = get_password_hash(password)
    registration_data["password"] = hashed_password
    del registration_data["confirm_password"]

    # Generate OTP and OTP ID
    otp = "123456" if settings.UNDER_DEVELOPMENT else generate_otp()
    otp_id = str(uuid.uuid4())
    logger.debug(f"Generated OTP: {otp} and OTP ID: {otp_id}")
    registration_data["otp"] = otp
    registration_data["otp_id"] = otp_id

    registration_data["invitation_token"] = invitation_token

    return registration_data, otp


async def store_registration_data(otp_id: str, registration_data: dict[str, Any], logger: Any) -> None:
    redis_key = f"registration:{otp_id}"
    logger.debug(f"Storing registration data in Redis with key: {redis_key}")
    await redis_client.set(redis_key, json.dumps(registration_data), ex=300)  # 5 minutes
    logger.info("Registration data stored in Redis successfully")
