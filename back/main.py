# Standard library imports
from typing import cast
from uuid import UUID

# Third-party imports
from fastapi import FastAPI
from fastapi.routing import APIRoute
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sqlalchemy import select, text

# Local application imports
from app.core.db import get_async_session
from app.core.monitoring.logging import get_logger
from app.models.auth.user import User
from app.settings import settings
from app.utils.password_utils import get_password_hash

# Set up the main application logger
logger = get_logger("app")


if settings.ENVIRONMENT == "production":
    logger.info(f"Initializing Sentry in {settings.ENVIRONMENT} environment")
    # Note: Basic Sentry logging integration is already set up in core/logging.py
    # Here we just add the FastAPI integration if it's not already initialized
    if not sentry_sdk.Hub.current.client:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            environment="production",
            enable_tracing=True,
            traces_sample_rate=1.0,  # tweak for performance
        )
    else:
        # Add FastAPI integration to existing Sentry client
        # Instead of directly accessing client.integrations, reinitialize with
        # the new integration
        logger.info("Adding FastAPI integration to existing Sentry configuration")
        current_options = sentry_sdk.Hub.current.client.options
        integrations = current_options.get("integrations", [])

        # Check if FastAPI integration is already present
        has_fastapi_integration = any(isinstance(integration, FastApiIntegration) for integration in integrations)

        if not has_fastapi_integration:
            # Add the FastAPI integration and reinitialize
            integrations.append(FastApiIntegration())
            sentry_sdk.init(
                dsn=current_options.get("dsn"),
                integrations=integrations,
                environment=current_options.get("environment", "production"),
                enable_tracing=current_options.get("enable_tracing", True),
                traces_sample_rate=current_options.get("traces_sample_rate", 1.0),
            )


async def create_default_admin_user() -> UUID:
    # Use the session generator
    db_session_generator = get_async_session()

    async for db in db_session_generator:
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        existing_admin = result.scalar_one_or_none()

        if existing_admin is None:
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                first_name=settings.ADMIN_FIRST_NAME,
                last_name=settings.ADMIN_LAST_NAME,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                is_admin=True,
                is_email_verified=True,
                is_phone_number_verified=True,
                phone_number=settings.ADMIN_PHONE_NUMBER,
            )
            db.add(admin_user)
            await db.commit()
            logger.info("Admin user created.")
            return cast(UUID, admin_user.id)
        else:
            logger.info("Admin user already exists.")
            return cast(UUID, existing_admin.id)
    # If `get_async_session` yielded nothing
    logger.error("Failed to create admin user: no session yielded.")
    raise RuntimeError("Failed to obtain database session for admin-seed")


# ---- FASTAPI APP CREATION ----
def custom_generate_unique_id(route: APIRoute) -> str:
    # Handle routes without tags
    if route.tags and len(route.tags) > 0:
        return f"{route.tags[0]}-{route.name}"
    else:
        return route.name or "unnamed_route"


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    # Standard library imports
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Startup
        logger.info("Starting up FastAPI application")

        # Create default admin user
        try:
            admin_id = await create_default_admin_user()
            logger.info(f"Admin user ready with ID: {admin_id}")
        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")

        yield

        # Shutdown
        logger.info("Shutting down FastAPI application")

    # Create FastAPI app
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="FastAPI boilerplate application",
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT != "production" else None,
        docs_url=f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=f"{settings.API_V1_STR}/redoc" if settings.ENVIRONMENT != "production" else None,
        generate_unique_id_function=custom_generate_unique_id,
        lifespan=lifespan,
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0", "database": "connected"}

    # Test database connection endpoint
    @app.get("/test-db")
    async def test_database():
        try:
            # Local application imports
            from app.core.db import get_async_session

            db_session_generator = get_async_session()
            async for db in db_session_generator:
                # Simple query to test connection
                result = await db.execute(text("SELECT 1"))
                return {"status": "database_connected", "result": result.scalar()}
        except Exception as e:
            return {"status": "database_error", "error": str(e)}

    # Include test routes for all services
    # Local application imports
    from app.api.internal.routes.v1 import test_routes

    app.include_router(test_routes.router, prefix=settings.API_V1_STR)

    # Include authentication routes
    # Local application imports
    from app.api.internal.routes.v1.auth.auth_routes import router as auth_router

    app.include_router(auth_router, prefix=settings.API_V1_STR)

    # Include JanEye routes
    # Local application imports
    from app.api.internal.routes.v1.issues import issue_router, location_router, vote_router

    app.include_router(issue_router, prefix=settings.API_V1_STR)
    app.include_router(vote_router, prefix=settings.API_V1_STR)
    app.include_router(location_router, prefix=settings.API_V1_STR)

    return app


# Create the app instance
app = create_app()
