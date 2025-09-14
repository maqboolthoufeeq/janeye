# Standard library imports
from datetime import UTC, datetime
import json
from typing import TypedDict

# Third-party imports
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from app.core.caching.redis import redis_client
from app.core.monitoring.logging import get_contextual_logger
from app.db_selectors.auth import get_user_by_email
from app.models.auth.user import User

logger = get_contextual_logger(__name__)


class OTPVerificationResult(TypedDict, total=False):
    """Type for representing the result of OTP verification."""

    success: bool
    error: str
    user_id: str
    is_new_user: bool


async def verify_otp(
    db: AsyncSession,
    otp_id: str,
    otp_code: str,
) -> OTPVerificationResult:
    """
    Verify OTP and create a user if valid.

    Args:
        db: Database session
        otp_id: The unique ID for the OTP
        otp_code: The OTP code to verify

    Returns:
        A dictionary with verification results
    """
    logger.info(f"Verifying OTP with ID: {otp_id}")

    # Retrieve registration data from Redis
    redis_key = f"registration:{otp_id}"
    registration_data_str = await redis_client.get(redis_key)

    if not registration_data_str:
        logger.warning("OTP verification failed: Registration data not found or expired")
        return {
            "success": False,
            "error": "OTP expired or invalid. Please request a new OTP.",
        }

    # Parse the registration data
    registration_data = json.loads(registration_data_str)
    stored_otp = registration_data.get("otp")

    # Check if OTP matches
    if otp_code != stored_otp:
        logger.warning("OTP verification failed: Invalid OTP provided")
        return {"success": False, "error": "Invalid OTP code."}

    # OTP is valid, check if user exists
    email = registration_data.get("email")
    existing_user = await get_user_by_email(db, email)
    is_new_user = existing_user is None

    user_id = None

    if existing_user:
        # User exists
        logger.info(f"User with email {email} already exists")
        user_id = str(existing_user.id)

    else:
        # Create a new user
        logger.info(f"Creating new user with email {email}")
        new_user = User(
            email=email,
            hashed_password=registration_data.get("password"),
            first_name=registration_data.get("first_name"),
            last_name=registration_data.get("last_name"),
            phone_number=registration_data.get("phone_number"),
            is_email_verified=True,  # Email verified through OTP
            is_phone_number_verified=False,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        user_id = str(new_user.id)
        logger.info(f"New user created with id {user_id}")

        # Store verification data
        verified_data = {
            "user_id": user_id,
            "email": email,
            "verified_at": datetime.now(UTC).isoformat(),
        }

        # Store for 24 hours
        await redis_client.set(
            f"verified_user:{user_id}",
            json.dumps(verified_data),
            ex=86400,  # 24 hours
        )
        logger.info("User verification data stored in Redis for 24 hours")

    # Delete the OTP data as it's been used
    await redis_client.delete(redis_key)
    logger.info("OTP data removed from Redis after successful verification")

    return {
        "success": True,
        "user_id": user_id,
        "is_new_user": is_new_user,
    }
