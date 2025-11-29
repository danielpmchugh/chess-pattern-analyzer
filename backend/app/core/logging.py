"""
Logging configuration for Chess Pattern Analyzer API.

This module sets up structured logging with JSON formatting for production
and human-readable formatting for development.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

from app.config import settings


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    Formats log records as JSON objects for easy parsing by log aggregation
    systems (e.g., CloudWatch, Datadog, ELK stack).
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        # Add extra fields from the log record
        if hasattr(record, "method"):
            log_obj["method"] = record.method
        if hasattr(record, "path"):
            log_obj["path"] = record.path
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "client_host"):
            log_obj["client_host"] = record.client_host
        if hasattr(record, "details"):
            log_obj["details"] = record.details

        # Add exception information if present
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add stack trace if available
        if hasattr(record, "traceback"):
            log_obj["traceback"] = record.traceback

        # Add environment information
        log_obj["environment"] = settings.ENVIRONMENT

        return json.dumps(log_obj)


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for development environment.

    Adds color coding to different log levels for better readability
    in terminal output.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.RESET}"
            )
            record.levelname = colored_levelname

        # Format the record
        formatted = super().format(record)

        # Reset the levelname for future use
        record.levelname = levelname

        return formatted


def setup_logging() -> None:
    """
    Configure application logging.

    Sets up:
    - Log level from settings
    - JSON formatter for production
    - Colored formatter for development
    - Console output to stdout
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper())

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    root_logger.handlers = []

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Choose formatter based on environment
    if settings.is_production():
        # JSON formatter for production (machine-readable)
        formatter = JSONFormatter()
    else:
        # Colored formatter for development (human-readable)
        formatter = ColoredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure third-party loggers to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={settings.LOG_LEVEL}, environment={settings.ENVIRONMENT}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
