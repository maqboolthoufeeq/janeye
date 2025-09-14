# Standard library imports
from datetime import UTC, datetime, timedelta
import re
from typing import Any
from uuid import UUID

# Third-party imports
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from app.core.logging import get_contextual_logger
from app.db_selectors.auth import (
    create_session_in_db,
    get_existing_session_for_user,
    get_session_by_jti,
    invalidate_session_in_db,
    update_session_organization_in_db,
)
from app.models.auth.session import Session
from app.services.geo import geo_ip_service
from app.services.service_enums import ServiceError
from app.services.service_response import ServiceResult
from app.settings import get_settings

settings = get_settings()


async def create_session(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID | None,
    access_token_jti: str,
    refresh_token_jti: str,
    request: Request | None = None,
    expires_at: datetime | None = None,
) -> ServiceResult[Session]:
    """
    Create a new session for a user with comprehensive device and location info.

    Args:
        db: Database session
        user_id: User ID
        organization_id: Organization ID
        access_token_jti: JWT ID for the access token
        refresh_token_jti: JWT ID for the refresh token
        request: Optional request object to extract client info
        expires_at: Session expiration time

    Returns:
        ServiceResult with created Session object or error
    """
    logger = get_contextual_logger(__name__)
    try:
        if not expires_at:
            # Calculate exactly when the refresh token expires
            expires_at = datetime.now(UTC) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

        # Initialize default values
        user_agent = None
        ip_address = None
        device_type = None
        device_name = None
        device_id = None
        browser = None
        os_name = None
        country = None
        city = None
        latitude = None
        longitude = None

        if request:
            user_agent = request.headers.get("user-agent")
            ip_address = get_client_ip(request)

            # We get device ID from app (none in browser)
            device_id = request.headers.get("device-id")

            # Extract comprehensive device info from user-agent
            if user_agent:
                device_data = parse_user_agent(user_agent)
                device_type = device_data.get("device_type")
                device_name = device_data.get("device_name")
                browser = device_data.get("browser")
                os_name = device_data.get("os")

            # Try to get location from IP
            if ip_address and ip_address not in ["unknown", "127.0.0.1", "localhost"]:
                loc_result = await get_location_from_ip(ip_address)
                if loc_result and loc_result.ok and loc_result.data:
                    location_data = loc_result.data
                    country = location_data.get("country")
                    city = location_data.get("city")
                    latitude = location_data.get("latitude")
                    longitude = location_data.get("longitude")

            if ip_address and device_name:
                # Check if user already has an active session from the same device and IP
                existing_session = await get_existing_session_for_user(db, user_id, device_name, ip_address)

                if existing_session:
                    # Invalidate old session from same device
                    await invalidate_session_in_db(db, existing_session, "replaced_by_new_session")

        # Create new session
        session = Session(
            user_id=user_id,
            organization_id=organization_id,
            access_token_jti=access_token_jti,
            refresh_token_jti=refresh_token_jti,
            # Device information
            device_type=device_type,
            device_name=device_name,
            device_id=device_id,
            browser=browser,
            os_name=os_name,
            # Network information
            user_agent=user_agent,
            ip_address=ip_address,
            # Location information
            country=country,
            city=city,
            latitude=latitude,
            longitude=longitude,
            # Session timing
            expires_at=expires_at,
            last_login=datetime.now(UTC),
        )

        session = await create_session_in_db(db, session)
        return ServiceResult.success(session)

    except Exception as e:
        logger.info("Error in creating session service: ", e)
        await db.rollback()
        return ServiceResult.failure(ServiceError.Common.INTERNAL_SERVER_ERROR)


async def update_session_organization(
    db: AsyncSession,
    access_token_jti: str,
    organization_id: UUID,
) -> ServiceResult[Session]:
    """
    Update the organization associated with a session.

    Args:
        db: Database session
        access_token_jti: JWT ID for the access token
        organization_id: New organization ID

    Returns:
        ServiceResult with updated Session object or error
    """
    try:
        session = await get_session_by_jti(db, access_token_jti)

        if not session:
            return ServiceResult.failure(ServiceError.Session.SESSION_NOT_FOUND)

        if not session.is_valid:
            return ServiceResult.failure(ServiceError.Session.SESSION_EXPIRED)

        session = await update_session_organization_in_db(db, session, organization_id)
        return ServiceResult.success(session)
    except Exception:
        logger = get_contextual_logger(__name__)
        logger.error("Error in updating session organization: ", exc_info=True)
        await db.rollback()
        return ServiceResult.failure(ServiceError.Common.INTERNAL_SERVER_ERROR)


async def invalidate_session(
    db: AsyncSession,
    access_token_jti: str,
    reason: str = "user_logout",
) -> ServiceResult[Session]:
    """
    Invalidate a session.

    Args:
        db: Database session
        access_token_jti: JWT ID for the access token
        reason: Reason for invalidation

    Returns:
        ServiceResult with invalidated Session object or error
    """
    try:
        session = await get_session_by_jti(db, access_token_jti)

        if not session:
            return ServiceResult.failure(ServiceError.Session.SESSION_NOT_FOUND)

        if not session.is_active or session.invalidated_at:
            return ServiceResult.failure(ServiceError.Session.SESSION_ALREADY_INVALIDATED)

        session = await invalidate_session_in_db(db, session, reason)
        return ServiceResult.success(session)
    except Exception:
        await db.rollback()
        return ServiceResult.failure(ServiceError.Common.INTERNAL_SERVER_ERROR)


def get_client_ip(request: Request) -> str:
    """
    Get the real client IP address, handling various proxy headers.
    """
    if not request or not hasattr(request, "headers"):
        return "unknown"

    # Check common proxy headers in order of preference
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Cloudflare
    cf_connecting_ip = request.headers.get("cf-connecting-ip")
    if cf_connecting_ip:
        return cf_connecting_ip

    # AWS ALB
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


def parse_user_agent(user_agent: str) -> dict[str, str]:
    """
    Parse user agent string to extract detailed device information.
    """
    if not user_agent:
        return {
            "device_type": "unknown",
            "device_name": "Unknown Device",
            "browser": "Unknown",
            "os": "Unknown",
            "platform": "Unknown",
        }

    user_agent_lower = user_agent.lower()

    # Detect device type
    if any(mobile in user_agent_lower for mobile in ["mobile", "android", "iphone", "ipad", "ios"]):
        device_type = "mobile"
    elif "electron" in user_agent_lower:
        device_type = "desktop"
    else:
        device_type = "web"

    # Detect browser
    browser = "Unknown"
    if "chrome" in user_agent_lower and "edg" not in user_agent_lower and "opr" not in user_agent_lower:
        browser = "Chrome"
    elif "firefox" in user_agent_lower:
        browser = "Firefox"
    elif "safari" in user_agent_lower and "chrome" not in user_agent_lower:
        browser = "Safari"
    elif "edg" in user_agent_lower:
        browser = "Edge"
    elif "opr" in user_agent_lower or "opera" in user_agent_lower:
        browser = "Opera"

    # Detect OS
    os_name = "Unknown"
    if "windows nt" in user_agent_lower:
        if "windows nt 10.0" in user_agent_lower:
            os_name = "Windows 10/11"
        elif "windows nt 6.1" in user_agent_lower:
            os_name = "Windows 7"
        else:
            os_name = "Windows"
    elif "mac os x" in user_agent_lower or "macos" in user_agent_lower:
        os_name = "macOS"
    elif "linux" in user_agent_lower and "android" not in user_agent_lower:
        os_name = "Linux"
    elif "android" in user_agent_lower:
        # Extract Android version if possible
        android_match = re.search(r"android (\d+(?:\.\d+)?)", user_agent_lower)
        if android_match:
            os_name = f"Android {android_match.group(1)}"
        else:
            os_name = "Android"
    elif "iphone os" in user_agent_lower or "os " in user_agent_lower or "ios" in user_agent_lower:
        # Extract iOS version if possible
        ios_match = re.search(r"os (\d+(?:[_\.]\d+)*)", user_agent_lower)
        if ios_match:
            version = ios_match.group(1).replace("_", ".")
            os_name = f"iOS {version}"
        else:
            os_name = "iOS"

    # Create device name
    if device_type == "mobile":
        if "iphone" in user_agent_lower:
            device_name = f"iPhone ({os_name})"
        elif "ipad" in user_agent_lower:
            device_name = f"iPad ({os_name})"
        elif "android" in user_agent_lower:
            device_name = f"Android Device ({os_name})"
        else:
            device_name = f"Mobile Device ({os_name})"
    elif device_type == "desktop":
        device_name = f"Desktop App ({os_name})"
    else:
        device_name = f"{browser} on {os_name}"

    return {
        "device_type": device_type,
        "device_name": device_name,
        "browser": browser,
        "os": os_name,
        "platform": os_name,
        "raw_user_agent": user_agent[:200],  # Truncate for storage
    }


async def get_location_from_ip(ip_address: str) -> ServiceResult[dict[str, Any]]:
    """
    Get location information from IP address using MaxMind's GeoLite2 database via the GeoIPService.

    Args:
        ip_address: IP address

    Returns:
        ServiceResult with location data dictionary or error
    """
    # Use the singleton service to get location data
    location_data = geo_ip_service.get_location(ip_address)
    return ServiceResult.success(location_data)


async def update_device_token(
    db: AsyncSession,
    access_token_jti: str,
    device_token: str,
) -> ServiceResult[Session]:
    """
    Update the device token for a session.

    Args:
        db: Database session
        access_token_jti: JWT ID for the access token
        device_token: Device token for push notifications

    Returns:
        ServiceResult with updated Session object or error
    """
    try:
        session = await get_session_by_jti(db, access_token_jti)

        if not session:
            return ServiceResult.failure(ServiceError.Session.SESSION_NOT_FOUND)

        if not session.is_valid:
            return ServiceResult.failure(ServiceError.Session.SESSION_EXPIRED)

        session.device_token = device_token
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return ServiceResult.success(session)
    except Exception:
        logger = get_contextual_logger(__name__)
        logger.error("Error in updating device token: ", exc_info=True)
        await db.rollback()
        return ServiceResult.failure(ServiceError.Common.INTERNAL_SERVER_ERROR)


async def update_voip_token(
    db: AsyncSession,
    access_token_jti: str,
    voip_token: str,
) -> ServiceResult[Session]:
    """
    Update the VoIP token for a session.

    Args:
        db: Database session
        access_token_jti: JWT ID for the access token
        voip_token: VoIP token for iOS push notifications

    Returns:
        ServiceResult with updated Session object or error
    """
    try:
        session = await get_session_by_jti(db, access_token_jti)

        if not session:
            return ServiceResult.failure(ServiceError.Session.SESSION_NOT_FOUND)

        if not session.is_valid:
            return ServiceResult.failure(ServiceError.Session.SESSION_EXPIRED)

        session.voip_token = voip_token
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return ServiceResult.success(session)
    except Exception:
        logger = get_contextual_logger(__name__)
        logger.error("Error in updating VoIP token: ", exc_info=True)
        await db.rollback()
        return ServiceResult.failure(ServiceError.Common.INTERNAL_SERVER_ERROR)
