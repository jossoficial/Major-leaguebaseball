import json
import logging
import os
import sys
from datetime import datetime, timezone

from src.core.config import env_bool


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """Create an idempotent stdout logger suitable for local and container logs."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    configured = os.getenv("MLB_LOG_LEVEL", "INFO").upper()
    logger.setLevel(level or getattr(logging, configured, logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    if env_bool("MLB_LOG_JSON"):
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
