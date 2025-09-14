# Standard library imports
import os

# Local application imports
from app.settings.dev import DevSettings
from app.settings.production import ProductionSettings


def get_settings() -> DevSettings | ProductionSettings:
    """
    Return an instance of the appropriate settings class
    based on the ENV environment variable.
    """
    env = os.environ.get("ENVIRONMENT", "dev").lower()
    if env == "production":
        return ProductionSettings()  # type: ignore[call-arg]
    return DevSettings()  # type: ignore[call-arg]


settings = get_settings()
