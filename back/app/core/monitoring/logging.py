# Standard library imports
from collections.abc import MutableMapping
from functools import lru_cache
import logging
import sys
from typing import Any

# Local application imports
from app.settings import settings


class CustomFormatter(logging.Formatter):
    """
    Custom formatter with color support for console output.
    """

    # ANSI color codes
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    # Format string
    CONSOLE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: GREY + CONSOLE_FORMAT + RESET,
        logging.INFO: GREY + CONSOLE_FORMAT + RESET,
        logging.WARNING: YELLOW + CONSOLE_FORMAT + RESET,
        logging.ERROR: RED + CONSOLE_FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + CONSOLE_FORMAT + RESET,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


@lru_cache
def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """
    Get a logger with the given name and configured handlers.
    Uses LRU cache to avoid creating duplicate loggers for the same name.

    In local/development: Logs to console only
    In production: Logs to console and Sentry

    Args:
        name: The name of the logger
        level: Optional logging level override

    Returns:
        A configured logger instance
    """
    # Get or create logger
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times to the same logger
    if logger.handlers:
        return logger

    # Default level from settings if not specified
    if level is None:
        level = logging.DEBUG if settings.DEBUG_MODE else logging.INFO

    logger.setLevel(level)

    # Create console handler for all environments
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    # In production, we want to ensure logs go to Sentry when appropriate
    # This is already configured via the LoggingIntegration above

    return logger


class LoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """
    Logger adapter that allows adding context to log messages.
    """

    def __init__(self, logger: logging.Logger, extra: dict[str, Any] | None = None):
        super().__init__(logger, extra or {})

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        if self.extra:
            context_str = " ".join(f"{k}={v}" for k, v in self.extra.items())
            msg = f"{msg} [{context_str}]"
        return msg, kwargs


def get_contextual_logger(name: str, **context: Any) -> LoggerAdapter:
    """
    Get a logger with additional context variables that will be included
    in all log messages.

    Args:
        name: The name of the logger
        **context: Additional context parameters to include in logs

    Returns:
        A configured logger adapter
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context)
