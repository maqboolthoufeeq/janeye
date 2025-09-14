# Standard library imports
import logging

# Third-party imports
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Local application imports
from app.settings import settings


# Configure Sentry logging integration once
def _setup_sentry_logging() -> None:
    """
    Sets up Sentry logging integration if Sentry is configured.
    This ensures logs above a certain level are sent to Sentry.
    """
    if settings.ENVIRONMENT == "production" and settings.SENTRY_DSN:
        # Configure Sentry logging integration
        # Send logs of level WARNING and above to Sentry
        sentry_logging = LoggingIntegration(
            level=logging.WARNING,  # Capture warnings and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )

        # Add the logging integration to Sentry (if not already initialized)
        if not sentry_sdk.Hub.current.client:
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                integrations=[sentry_logging],
                environment=settings.ENVIRONMENT,
                traces_sample_rate=1.0,
            )


# Call setup once at module import time
_setup_sentry_logging()
