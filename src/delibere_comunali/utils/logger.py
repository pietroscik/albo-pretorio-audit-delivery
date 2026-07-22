# -*- coding: utf-8 -*-
"""
Logging module with structured logging support.
Provides centralized logging configuration for the entire application.

FIXED: Removed circular import with config module.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class CustomFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        # Avoid mutating levelname for downstream handlers (e.g. file logging).
        original_level = record.levelname

        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            )

        # Format the message
        formatted = super().format(record)

        # Restore original levelname
        record.levelname = original_level

        return formatted


class JSONFormatter(logging.Formatter):
    """Formatter for JSON output."""

    def format(self, record):
        import json

        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith("_"):
                try:
                    # Try to serialize the value
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    # If not serializable, convert to string
                    log_data[key] = str(value)

        return json.dumps(log_data, ensure_ascii=False)


# Global logger configuration
_loggers = {}


def get_logger(
    name: str, log_level: Optional[str] = None, log_format: Optional[str] = None
) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ('text' or 'json')

    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]

    # Create logger
    logger = logging.getLogger(name)

    # Set log level - handle None case
    if log_level is None:
        import os

        log_level = os.environ.get("LOG_LEVEL", "INFO")

    try:
        level = getattr(logging, log_level.upper(), logging.INFO)
        logger.setLevel(level)
    except AttributeError:
        logger.setLevel(logging.INFO)

    # Prevent duplicate handlers
    if logger.handlers:
        _loggers[name] = logger
        return logger

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    # Determine format from environment or parameter
    if log_format is None:
        # Try to get from environment
        import os

        log_format = os.environ.get("LOG_FORMAT", "text")

    if log_format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            CustomFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    # Add console handler
    logger.addHandler(console_handler)

    # Try to add file handler if log file is configured
    try:
        import os

        log_file = os.environ.get("LOG_FILE")
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger.addHandler(file_handler)
    except Exception:
        pass  # Ignore file handler errors

    # Cache the logger
    _loggers[name] = logger

    return logger


def configure_logging(
    log_level: str = "INFO", log_format: str = "text", log_file: Optional[str] = None
):
    """
    Configure logging for the entire application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ('text' or 'json')
        log_file: Path to log file (optional)
    """
    # Set global log level
    try:
        level = getattr(logging, log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    except AttributeError:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    # Store configuration for get_logger
    import os

    os.environ["LOG_LEVEL"] = log_level
    os.environ["LOG_FORMAT"] = log_format
    if log_file:
        os.environ["LOG_FILE"] = log_file


def reset_loggers():
    """Reset all cached loggers."""
    global _loggers
    _loggers = {}
