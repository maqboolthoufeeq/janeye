# Standard library imports
from typing import TypeVar

# Third-party imports
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

# Local application imports
from app.api.internal.routes.v1.routes import router as v1_router

ParentT = TypeVar("ParentT", APIRouter, FastAPI)


def remove_trailing_slashes_from_routes(parent: ParentT) -> ParentT:
    "Removes trailing slashes from all routes in the given router"

    for route in parent.routes:
        if isinstance(route, APIRoute):
            route.path = route.path.rstrip("$")

    return parent


router = APIRouter()
# Include internal API routers
router.include_router(v1_router)
router = remove_trailing_slashes_from_routes(router)
