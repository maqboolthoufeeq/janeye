from .issue_routes import router as issue_router
from .location_routes import router as location_router
from .vote_routes import router as vote_router

__all__ = ["issue_router", "vote_router", "location_router"]
