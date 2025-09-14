# Local application imports
from app.settings.common import CommonSettings


class ProductionSettings(CommonSettings):
    DEBUG_MODE: bool = True
    SENTRY_DSN: str | None = None
