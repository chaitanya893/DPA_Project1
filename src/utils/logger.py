import logging
import sys
import uuid
from typing import Any, Dict, Optional


class CorrelationFilter(logging.Filter):
    """Filter that injects correlation_id into log records."""

    def __init__(self, default_correlation_id: str = "GLOBAL") -> None:
        super().__init__()
        self.default_correlation_id = default_correlation_id
        self.active_correlation_id: Optional[str] = None

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = self.active_correlation_id or self.default_correlation_id
        return True


_correlation_filter = CorrelationFilter()


def setup_logger(name: str = "earnings_pipeline", level: int = logging.INFO) -> logging.Logger:
    """Configures structured logger with timestamp, loglevel, correlation ID and message."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [corr_id=%(correlation_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(_correlation_filter)
        logger.addHandler(handler)
        logger.addFilter(_correlation_filter)
    return logger


def set_correlation_id(corr_id: Optional[str] = None) -> str:
    """Sets a new correlation ID for tracking a specific workflow or request."""
    new_id = corr_id or str(uuid.uuid4())[:8]
    _correlation_filter.active_correlation_id = new_id
    return new_id


def get_correlation_id() -> str:
    """Returns the current active correlation ID or 'GLOBAL'."""
    return _correlation_filter.active_correlation_id or _correlation_filter.default_correlation_id


def clear_correlation_id() -> None:
    """Clears the active correlation ID."""
    _correlation_filter.active_correlation_id = None
