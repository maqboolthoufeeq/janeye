# Standard library imports
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

# Third-party imports
from fastapi import HTTPException, status
import jwt

# Local application imports
from app.schemas.auth import AccessTokenResponse
from app.settings import settings


def create_access_token(
    user_id: UUID,
    email: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """
    Create a JWT access token with a short expiration time.

    Args:
        user_id: The user's ID
        email: The user's email
        expires_delta: Optional custom expiration time

    Returns:
        Tuple of (token, jti)
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    # Generate a unique JWT ID
    jti = str(uuid4())

    to_encode = {
        "sub": str(user_id),  # Standard JWT claim for subject
        "email": email,  # Include email
        "exp": expire,  # Expiration time
        "iat": now,  # Issued at time
        "token_type": "access",  # Token type  # nosec B106
        "jti": jti,  # JWT ID for tracking
    }

    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return token, jti


def create_refresh_token(
    user_id: UUID,
    email: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """
    Create a JWT refresh token with a longer expiration time.

    Args:
        user_id: The user's ID
        email: The user's email
        expires_delta: Optional custom expiration time

    Returns:
        Tuple of (token, jti)
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))

    # Generate a unique JWT ID
    jti = str(uuid4())

    to_encode = {
        "sub": str(user_id),  # Standard JWT claim for subject
        "email": email,  # Include email
        "exp": expire,  # Expiration time
        "iat": now,  # Issued at time
        "token_type": "refresh",  # Token type  # nosec B106
        "jti": jti,  # JWT ID for tracking
    }

    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return token, jti


def generate_auth_tokens(email: str, user_id: UUID) -> tuple[AccessTokenResponse, str, str]:
    """
    Generate access and refresh tokens for a user.

    Args:
        email: User's email to use as subject in token
        user_id: User ID to include in the token payload and response

    Returns:
        Tuple of (AccessTokenResponse, access_token_jti, refresh_token_jti)
    """

    # Generate access token with configured expiration time
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, access_token_jti = create_access_token(
        user_id=user_id,
        email=email,
        expires_delta=access_token_expires,
    )
    refresh_token, refresh_token_jti = create_refresh_token(
        user_id=user_id,
        email=email,
    )

    # Return the token response and JTIs
    response = AccessTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",  # nosec B106
        user_id=str(user_id),
    )

    return response, access_token_jti, refresh_token_jti


def create_invitation_token(
    email: str,
    role: str,
    organization_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(days=2))

    payload = {
        "sub": email,
        "role": role,
        "organization_id": str(organization_id),
        "exp": expire,
        "iat": now,
        "token_type": "invitation",  # nosec B106
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_reservation_token(
    event_id: UUID,
    client_phone_number: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT token for reservation access with event ID and customer phone.

    Args:
        event_id: The event ID to access
        client_phone_number: Customer's phone number for verification
        expires_delta: Optional custom expiration time (default: 30 days)

    Returns:
        JWT token for secure reservation access
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(days=30))  # Long-lived for customer convenience

    to_encode = {
        "event_id": str(event_id),
        "client_phone": client_phone_number,
        "exp": expire,
        "iat": now,
        "token_type": "reservation_access",  # nosec B106
    }

    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return token


def verify_reservation_token(token: str) -> UUID:
    """
    Verify and decode a reservation access token.

    Args:
        token: The JWT token to verify

    Returns:
        Tuple of (event_id, client_phone_number)

    Raises:
        HTTPException: If token is invalid or expired
    """

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        token_type = payload.get("token_type")
        if token_type != "reservation_access":  # nosec B105
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        event_id = payload.get("event_id")
        client_phone = payload.get("client_phone")

        if not event_id or not client_phone:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing required fields",
            )

        return UUID(event_id)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reservation link has expired. Please contact the organization for assistance.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reservation link. Please contact the organization for assistance.",
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")
