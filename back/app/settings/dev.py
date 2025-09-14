# Local application imports
from app.settings.common import CommonSettings


class DevSettings(CommonSettings):
    # Testing database settings
    POSTGRES_TEST_SERVER: str
    POSTGRES_TEST_SERVER_PORT: str
    POSTGRES_TEST_SERVER_USER: str
    POSTGRES_TEST_SERVER_PASSWORD: str
    POSTGRES_TEST_SERVER_DB: str

    DEBUG_MODE: bool = True
