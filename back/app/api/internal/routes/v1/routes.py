# Third-party imports
from fastapi import APIRouter

# Local application imports
from app.api.internal.routes.v1.auth import router as auth_router

router = APIRouter()

# Include all internal v1 routers
router.include_router(auth_router)
