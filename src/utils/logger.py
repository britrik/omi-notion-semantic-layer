"""
Logging configuration for the OMI-to-Notion Semantic Intelligence Layer.

Provides structured logging with:
- Console and file handlers
- Separate log files per component
- Optional JSON formatting
- Contextual logging with extra fields
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Component-specific logger names
LOGGER_NAMES = {
    "main": "omi_notion",
    "processor": "omi_notion.processor",
    "omi": "omi_notion.omi",
    "notion": "omi_notion.notion",
    "semantic": "omi_notion.semantic",
    "pipeline": "omi_notion.pipeline",
}

# Log file names per component
LOG_FILES = {
    "main": "processor.log",
    "omi": "omi.log",
    "notion": "notion.log",
    "errors": "errors.log",
}


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "taskName",
                "message",
            }:
                log_data[key] = value

        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format with colors for terminal output."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    json_format: bool = False,
    console_output: bool = True,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files. If None, file logging is disabled.
        json_format: Use JSON formatting for logs
        console_output: Enable console output
    """
    # Get numeric log level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create root logger for the application
    root_logger = logging.getLogger("omi_notion")
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Standard format
    standard_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        if json_format:
            console_handler.setFormatter(JSONFormatter())
        else:
            # Use colored formatter for TTY, standard otherwise
            if sys.stdout.isatty():
                console_handler.setFormatter(
                    ColoredFormatter(standard_format, datefmt=date_format)
                )
            else:
                console_handler.setFormatter(
                    logging.Formatter(standard_format, datefmt=date_format)
                )

        root_logger.addHandler(console_handler)

    # File handlers
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        file_formatter = (
            JSONFormatter()
            if json_format
            else logging.Formatter(standard_format, datefmt=date_format)
        )

        # Main log file
        main_handler = logging.FileHandler(log_dir / LOG_FILES["main"])
        main_handler.setLevel(numeric_level)
        main_handler.setFormatter(file_formatter)
        root_logger.addHandler(main_handler)

        # Error log file (ERROR and above)
        error_handler = logging.FileHandler(log_dir / LOG_FILES["errors"])
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

        # Component-specific log files
        for component, filename in LOG_FILES.items():
            if component in ("main", "errors"):
                continue

            component_logger = logging.getLogger(f"omi_notion.{component}")
            component_handler = logging.FileHandler(log_dir / filename)
            component_handler.setLevel(numeric_level)
            component_handler.setFormatter(file_formatter)
            component_logger.addHandler(component_handler)

    # Prevent propagation to root logger
    root_logger.propagate = False


def get_logger(name: str = "main") -> logging.Logger:
    """
    Get a logger instance for the specified component.

    Args:
        name: Component name (main, processor, omi, notion, semantic, pipeline)
              or a custom name that will be prefixed with 'omi_notion.'

    Returns:
        Logger instance for the component.
    """
    # Use predefined logger name or create custom one
    logger_name = LOGGER_NAMES.get(name, f"omi_notion.{name}")
    return logging.getLogger(logger_name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds contextual information to log records.

    Useful for adding request IDs, transcript IDs, or other context.
    """

    def process(
        self, msg: str, kwargs: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Add extra context to the log message."""
        # Add context from adapter's extra dict
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra

        # Optionally prefix message with context
        if self.extra:
            context_str = " ".join(f"[{k}={v}]" for k, v in self.extra.items())
            msg = f"{context_str} {msg}"

        return msg, kwargs


def get_contextual_logger(
    name: str = "main", **context: Any
) -> LoggerAdapter:
    """
    Get a logger with contextual information attached.

    Args:
        name: Component name
        **context: Key-value pairs to include in all log messages

    Returns:
        LoggerAdapter with context attached.

    Example:
        logger = get_contextual_logger("processor", transcript_id="abc123")
        logger.info("Processing started")  # Includes transcript_id in output
    """
    base_logger = get_logger(name)
    return LoggerAdapter(base_logger, context)


# Convenience function for quick setup from settings
def setup_logging_from_settings() -> None:
    """Configure logging from application settings."""
    # NOTE: Import is intentionally inside this function to avoid circular imports.
    # config.py imports logger.py for type hints, and logger.py needs config for settings.
    # This lazy import pattern is the standard solution for circular dependency issues.
    from src.utils.config import get_settings

    settings = get_settings()
    setup_logging(
        level=settings.logging.level.value,
        log_dir=settings.logging.dir,
        json_format=settings.logging.json_format,
        console_output=True,
    )
