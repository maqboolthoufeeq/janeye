# Standard library imports
from datetime import datetime, timedelta
import uuid

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from app.core.db import get_async_session
from app.core.monitoring.logging import get_logger
from app.dependancies.common import get_current_user as get_current_user_dep
from app.models.auth.otp import OTP
from app.models.auth.session import Session
from app.models.auth.user import User
from app.schemas.auth.auth_schemas import (
    OTPRequest,
    OTPVerifyRequest,
    PhoneLoginRequest,
    PhoneSignupRequest,
    TokenResponse,
    UserResponse,
)
from app.settings import settings
from app.utils.password_utils import get_password_hash

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt, to_encode["jti"]


def create_refresh_token(data: dict):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt, to_encode["jti"]


@router.post("/signup", response_model=UserResponse)
async def signup(request: PhoneSignupRequest, db: AsyncSession = Depends(get_async_session)):
    """
    Register a new user with phone number
    Step 1: Submit user details
    """
    # Check if phone number already exists
    result = await db.execute(select(User).where(User.phone_number == request.phone_number))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )

    # Create new user (unverified)
    new_user = User(
        phone_number=request.phone_number,
        first_name=request.first_name,
        last_name=request.last_name,
        state=request.state,
        district=request.district,
        local_body=request.local_body,
        email=f"{request.phone_number}@janeye.in",  # Placeholder email
        hashed_password=get_password_hash(str(uuid.uuid4())),  # Random password
        is_phone_number_verified=False,
        is_email_verified=False,
        monthly_vote_count=0,
        current_vote_month=datetime.now().strftime("%Y-%m"),
    )

    db.add(new_user)

    # Create OTP for verification
    otp = OTP.create_otp(request.phone_number, purpose="signup")
    db.add(otp)

    await db.commit()
    await db.refresh(new_user)

    # In production, send OTP via SMS
    # For development, log the OTP
    logger.info(f"OTP for {request.phone_number}: {otp.otp_code}")
    print(f"\n📱 OTP for {request.phone_number}: {otp.otp_code}\n")

    return UserResponse.model_validate(new_user)


@router.post("/send-otp")
async def send_otp(request: OTPRequest, db: AsyncSession = Depends(get_async_session)):
    """Send OTP to phone number"""
    # Check if user exists for login
    if request.purpose == "login":
        result = await db.execute(select(User).where(User.phone_number == request.phone_number))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phone number not registered",
            )

    # Delete any existing OTPs for this phone number
    await db.execute(
        select(OTP).where(
            and_(
                OTP.phone_number == request.phone_number,
                OTP.purpose == request.purpose,
                OTP.is_verified.is_(False),
            )
        )
    )

    # Create new OTP
    otp = OTP.create_otp(request.phone_number, purpose=request.purpose)
    db.add(otp)
    await db.commit()

    # In production, send OTP via SMS
    # For development, log the OTP
    logger.info(f"OTP for {request.phone_number}: {otp.otp_code}")
    print(f"\n📱 OTP for {request.phone_number}: {otp.otp_code}\n")

    return {"message": "OTP sent successfully", "expires_in_seconds": 600}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(request: OTPVerifyRequest, db: AsyncSession = Depends(get_async_session)):
    """Verify OTP and complete signup/login"""
    # Find the OTP
    result = await db.execute(
        select(OTP)
        .where(
            and_(
                OTP.phone_number == request.phone_number,
                OTP.purpose == request.purpose,
                OTP.is_verified.is_(False),
            )
        )
        .order_by(OTP.created_at.desc())
    )
    otp = result.scalar_one_or_none()

    if not otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    # Verify OTP
    if not otp.verify(request.otp_code):
        await db.commit()  # Save attempt count
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code")

    # Get user - need to format phone number to match storage format
    formatted_phone = request.phone_number
    if not formatted_phone.startswith("+"):
        formatted_phone = f"+91{formatted_phone}"

    result = await db.execute(select(User).where(User.phone_number == formatted_phone))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Mark phone as verified
    user.is_phone_number_verified = True
    user.last_login = datetime.utcnow()

    # Create tokens
    access_token, access_jti = create_access_token(data={"sub": str(user.id)})
    refresh_token, refresh_jti = create_refresh_token(data={"sub": str(user.id)})

    # Create session
    session = Session(
        user_id=user.id,
        access_token_jti=access_jti,
        refresh_token_jti=refresh_jti,
        expires_at=datetime.utcnow() + timedelta(days=7),
        device_type="mobile",
        is_active=True,
    )
    db.add(session)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        is_phone_verified=user.is_phone_number_verified,
        state=user.state,
        district=user.district,
    )


@router.post("/login")
async def login(request: PhoneLoginRequest, db: AsyncSession = Depends(get_async_session)):
    """
    Login with phone number
    Step 1: Request OTP
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.phone_number == request.phone_number))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not registered. Please sign up first.",
        )

    # Create OTP for login
    otp = OTP.create_otp(request.phone_number, purpose="login")
    db.add(otp)
    await db.commit()

    # In production, send OTP via SMS
    # For development, log the OTP
    logger.info(f"Login OTP for {request.phone_number}: {otp.otp_code}")
    print(f"\n📱 Login OTP for {request.phone_number}: {otp.otp_code}\n")

    return {
        "message": "OTP sent to your phone number",
        "phone_number": request.phone_number,
        "expires_in_seconds": 600,
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user_dep),
):
    """Get current user details"""
    return UserResponse.model_validate(current_user)
