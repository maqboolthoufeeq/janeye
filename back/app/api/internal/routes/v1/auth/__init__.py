# Third-party imports
from fastapi import APIRouter

# Local application imports
from app.api.internal.routes.v1.auth.login_routes import router as login_router

router = APIRouter(prefix="/auth", tags=["Authentication"])

router.include_router(login_router)
