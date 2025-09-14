# Third-party imports
from fastapi import APIRouter

# Local application imports
from app.schemas.auth import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login() -> Token:
    """
    OAuth2 compatible token login endpoint.

    Args:
        form_data: OAuth2 form containing username and password
        db: Database session

    Returns:
        Token: Access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    pass
