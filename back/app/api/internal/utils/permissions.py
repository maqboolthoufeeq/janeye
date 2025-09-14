# Standard library imports
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

# Third-party imports
from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from app.core.caching.redis import redis_client
from app.core.db import get_async_session
from app.core.monitoring.logging import get_contextual_logger
from app.db_selectors.auth import get_session_by_jti, get_user_by_id
from app.models.auth.user import User
from app.services.auth import is_token_blocked
from app.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# For WebSockets, we need a custom token extractor since oauth2_scheme doesn't work
# with WebSocket connections due to different header handling


class WebSocketOAuth2:
    """
    Custom OAuth2 scheme for WebSocket connections.
    Mimics OAuth2PasswordBearer but works with WebSocket headers.
    """

    def __init__(self, tokenUrl: str):
        self.tokenUrl = tokenUrl

    async def __call__(self, websocket: WebSocket) -> str:
        """
        Extract Bearer token from WebSocket Authorization header.
        This mimics the behavior of OAuth2PasswordBearer for HTTP requests.
        """
        auth_header = websocket.headers.get("authorization")
        if not auth_header:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Invalid authentication scheme",
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
            return token
        except ValueError:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid authorization format",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )


# Create WebSocket OAuth2 scheme instance
websocket_oauth2_scheme = WebSocketOAuth2(tokenUrl="/api/v1/auth/token")

# Standard auth error responses
AUTH_ERROR_INVALID_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
)

AUTH_ERROR_TOKEN_EXPIRED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token has expired",
)

AUTH_ERROR_SESSION_EXPIRED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Session expired or invalid, please login again",
)

AUTH_ERROR_TOKEN_BLOCKED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required",
)

AUTH_ERROR_USER_NOT_FOUND = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="User not found",
)


async def get_token_ttl(request: Request, token: str) -> int:
    """
    Decodes a JWT token and calculates its TTL.

    Args:
        request (Request): The request object for using it in logger.
        token (str): The token to decode.

    Returns:
        int: The TTL of the token.
    """
    # Get request_id if middleware set it
    request_id = getattr(request.state, "request_id", None) if request else None

    # Log with both user_id and email for traceability
    logger = get_contextual_logger(
        __name__,
        request_id=request_id,
    )
    logger.debug("getting ttl of the token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is invalid or missing",
        )
    try:
        # Decode the JWT token without verifying signature
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        expiry_timestamp = payload.get("exp")
        if not expiry_timestamp:
            raise ValueError("Token does not have 'exp' field.")

        return int(expiry_timestamp)
    except jwt.ExpiredSignatureError:
        logger.exception("Failed to verify token ownership", extra={"token": token})
        raise AUTH_ERROR_TOKEN_EXPIRED
    except Exception:
        logger.exception("Failed to verify token ownership", extra={"token": token})
        raise AUTH_ERROR_INVALID_TOKEN


async def verify_token_ownership(request: Request, token: str, owner: str) -> bool:
    """
    Verifies if the provided token belongs to the specified owner.

    Args:
        request (Request): The HTTP request object, used for logging purposes.
        token (str): The JWT access token to verify.
        owner (str): The UUID of the expected owner of the token.

    Returns:
        bool: True if the token is valid and belongs to the specified owner,
        otherwise raises an HTTPException.

    Raises:
        HTTPException: If the token is invalid, belongs to another user, or is expired.
    """

    # Get request_id if middleware set it
    request_id = getattr(request.state, "request_id", None) if request else None

    # Log with both user_id and email for traceability
    logger = get_contextual_logger(
        __name__,
        request_id=request_id,
    )
    logger.debug("checking owner of the token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is invalid or missing",
        )
    try:
        # Decode the JWT token without verifying signature
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_owner = payload.get("sub")
        if not token_owner:
            raise ValueError("Token does not have 'sub' field.")
        token_owner_uuid = UUID(token_owner)
        owner_uuid = UUID(owner)

        if token_owner_uuid != owner_uuid:
            logger.error(
                "Failed to verify token ownership",
                extra={"token": token, "token_owner": token_owner, "owner": owner},
            )
            return False
    except jwt.ExpiredSignatureError:
        logger.exception("Failed to verify token ownership", extra={"token": token})
        raise AUTH_ERROR_TOKEN_EXPIRED
    except Exception:
        logger.exception("Failed to verify token ownership", extra={"token": token})
        raise AUTH_ERROR_INVALID_TOKEN
    return True


async def get_access(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> tuple[User]:
    """
    Verifies that the user is authenticated.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        email = payload.get("email")

        if user_id_str is None or email is None:
            raise AUTH_ERROR_INVALID_TOKEN

        token_type = payload.get("token_type")
        if token_type != "access":  # nosec B105
            raise AUTH_ERROR_INVALID_TOKEN

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise AUTH_ERROR_INVALID_TOKEN

        is_access_token_blocked = await is_token_blocked(redis_client, token, True)
        if is_access_token_blocked:
            raise AUTH_ERROR_TOKEN_BLOCKED

    except jwt.ExpiredSignatureError:
        raise AUTH_ERROR_TOKEN_EXPIRED
    except jwt.PyJWTError:
        raise AUTH_ERROR_INVALID_TOKEN

    # Get request_id if middleware set it
    request_id = getattr(request.state, "request_id", None)

    logger = get_contextual_logger(__name__, request_id=request_id, user_id=user_id_str, email=email)

    # Get user first
    user = await get_user_by_id(db, user_id)

    if user is None:
        logger.warning(f"User with ID {user_id_str} not found")
        raise AUTH_ERROR_USER_NOT_FOUND

    # Verify email matches
    if user.email != email:
        logger.warning(f"Token email mismatch: {email} vs {user.email}")
        raise AUTH_ERROR_INVALID_TOKEN

    return user


def authenticated_user_only() -> Callable[[Request, str, AsyncSession], Awaitable[User]]:
    """
    Dependency for endpoints that require a *logged‑in* user.

    Returns the `User` object.
    """

    async def _check_user(
        request: Request,
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_async_session),
    ) -> User:
        """
        Check if the user is authenticated.
        """
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id_str = payload.get("sub")
            email = payload.get("email")
            jti = payload.get("jti")

            if user_id_str is None or email is None or jti is None:
                raise AUTH_ERROR_INVALID_TOKEN

            token_type = payload.get("token_type")
            if token_type != "access":  # nosec B105
                raise AUTH_ERROR_INVALID_TOKEN

            try:
                user_id = UUID(user_id_str)
            except ValueError:
                raise AUTH_ERROR_INVALID_TOKEN

            # Check if token is blocked in Redis
            is_access_token_blocked = await is_token_blocked(redis_client, token, True)
            if is_access_token_blocked:
                raise AUTH_ERROR_TOKEN_BLOCKED

            # Check if session is valid
            session = await get_session_by_jti(db, access_token_jti=jti)
            if not session or not session.is_active or session.invalidated_at:
                raise AUTH_ERROR_SESSION_EXPIRED

        except jwt.ExpiredSignatureError:
            raise AUTH_ERROR_TOKEN_EXPIRED
        except jwt.PyJWTError:
            raise AUTH_ERROR_INVALID_TOKEN

        # Get request_id if middleware set it
        request_id = getattr(request.state, "request_id", None)

        # Log with both user_id and email for traceability
        logger = get_contextual_logger(__name__, request_id=request_id, user_id=user_id_str, email=email)

        # Get user first
        user = await get_user_by_id(db, user_id)

        if user is None:
            logger.warning(f"User with ID {user_id_str} not found")
            raise AUTH_ERROR_USER_NOT_FOUND

        if user.email != email:
            logger.warning(f"Token email mismatch: {email} vs {user.email}")
            raise AUTH_ERROR_INVALID_TOKEN

        return user

    return _check_user


def decode_jwt_and_get_fields(
    token: str,
    token_type: str,
    required_fields: list[str],
    optional_fields: list[str] | None = None,
) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("token_type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        result = {}
        for field in required_fields:
            value = payload.get(field)
            if value is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: missing required field '{field}'",
                )
            result[field] = value
        if optional_fields:
            for field in optional_fields:
                result[field] = payload.get(field)
        return result
    except jwt.ExpiredSignatureError:
        raise AUTH_ERROR_TOKEN_EXPIRED
    except jwt.PyJWTError:
        raise AUTH_ERROR_INVALID_TOKEN


async def get_websocket_user_auth(
    websocket: WebSocket,
    user_id: str,
    db: AsyncSession = Depends(get_async_session),
    token: str = Depends(websocket_oauth2_scheme),
) -> tuple[User, dict[str, Any]]:
    """
    Authenticate and authorize WebSocket connection for a specific user.

    Args:
        websocket: The WebSocket connection
        user_id: Expected user ID from URL path
        db: Database session
        token: JWT token extracted from Authorization header

    Returns:
        tuple[User, dict]: Authenticated user and token payload

    Raises:
        Closes WebSocket connection with appropriate error codes
    """
    try:
        # Validate JWT token
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_user_id = payload.get("sub")
        email = payload.get("email")
        token_type = payload.get("token_type")
        jti = payload.get("jti")

        if not token_user_id or not email or token_type != "access" or not jti:  # nosec B105
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token structure")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure",
            )

        # Validate user_id matches token
        if token_user_id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User ID mismatch")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID mismatch")

        # Check if token is blocked
        is_blocked = await is_token_blocked(redis_client, token, True)
        if is_blocked:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token invalid")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is blocked")

        # Check if session is valid
        session = await get_session_by_jti(db, access_token_jti=jti)
        if not session or not session.is_active or session.invalidated_at:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid",
            )

        # Get user from database
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid user ID format")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        user = await get_user_by_id(db, user_uuid)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # Verify email matches
        if user.email != email:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Email mismatch")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email mismatch")

        return user, payload

    except jwt.ExpiredSignatureError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
        raise AUTH_ERROR_TOKEN_EXPIRED
    except jwt.PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        raise AUTH_ERROR_INVALID_TOKEN
    except Exception:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason="Authentication error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error",
        )
