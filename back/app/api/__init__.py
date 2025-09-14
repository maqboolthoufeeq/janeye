# Third-party imports
from fastapi import APIRouter

# Local application imports
from app.api.internal.main import router as internal_router

router = APIRouter(prefix="/api")

# Include internal and external API routers
router.include_router(internal_router)
