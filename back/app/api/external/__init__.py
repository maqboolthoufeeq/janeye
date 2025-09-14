# Third-party imports
from fastapi import APIRouter

from .v1 import router as v1_router

router = APIRouter(prefix="/external")

# Include versioned routers
router.include_router(v1_router)
