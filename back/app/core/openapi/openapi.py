# Standard library imports
from typing import Any

# Third-party imports
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer

# Local application imports
from app.settings import settings

# Use the same oauth2_scheme that's defined in your permissions.py
# to maintain consistency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

# List of API paths that don't require authentication
PUBLIC_PATHS = {
    f"{settings.API_V1_STR}/auth/token",  # Login endpoint
    f"{settings.API_V1_STR}/auth/token/refresh",  # Refresh token endpoint
    f"{settings.API_V1_STR}/auth/register",  # Registration endpoint
    f"{settings.API_V1_STR}/auth/register/verify-otp",  # Verify OTP endpoint
    f"{settings.API_V1_STR}/utils/health-check",  # Health check endpoint
}


def is_path_public(path: str) -> bool:
    """
    Check if a path should be public (no authentication required)
    """
    # Check for exact matches
    if path in PUBLIC_PATHS:
        return True

    # Check for wildcard matches (paths that end with *)
    for public_path in PUBLIC_PATHS:
        if public_path.endswith("*") and path.startswith(public_path[:-1]):
            return True

    return False


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """
    Customize the OpenAPI schema to include JWT security on all routes
    except those explicitly marked as public
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description=f"{settings.PROJECT_NAME} API Documentation",
        routes=app.routes,
    )

    # Add security scheme to the OpenAPI schema
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    paths_to_fix = {}
    for path in list(openapi_schema["paths"].keys()):
        if path.endswith("$"):
            clean_path = path[:-1]
            paths_to_fix[path] = clean_path

    # Remove paths with '$' at the end
    for old_path, new_path in paths_to_fix.items():
        openapi_schema["paths"][new_path] = openapi_schema["paths"][old_path]
        del openapi_schema["paths"][old_path]

    # Apply security to specific paths instead of globally
    if "paths" in openapi_schema:
        for path, path_item in openapi_schema["paths"].items():
            for method in path_item:
                # Skip non-operation keys like 'parameters'
                if method in ["get", "post", "put", "delete", "patch"]:
                    operation = path_item[method]

                    # Apply security only to protected routes
                    if not is_path_public(path):
                        operation["security"] = [{"bearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi(app: FastAPI) -> None:
    """
    Function to apply OpenAPI customization to the FastAPI app
    """
    app.openapi = lambda: custom_openapi(app)  # type: ignore
