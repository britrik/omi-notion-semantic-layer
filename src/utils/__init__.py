"""
Utility modules for the OMI-to-Notion Semantic Intelligence Layer.

This package contains:
- config: Configuration management with Pydantic
- logger: Structured logging setup
- exceptions: Custom exception classes
- deduplication: Duplicate detection utilities
"""

from src.utils.config import get_settings, Settings
from src.utils.logger import get_logger, setup_logging
from src.utils.exceptions import (
    OMINotionError,
    OMIAPIError,
    NotionAPIError,
    ProcessingError,
    ValidationError,
    ConfigurationError,
)
from src.utils.deduplication import (
    DuplicateDetector,
    get_content_fingerprint,
    calculate_fingerprint_similarity,
)

__all__ = [
    "get_settings",
    "Settings",
    "get_logger",
    "setup_logging",
    "OMINotionError",
    "OMIAPIError",
    "NotionAPIError",
    "ProcessingError",
    "ValidationError",
    "ConfigurationError",
    "DuplicateDetector",
    "get_content_fingerprint",
    "calculate_fingerprint_similarity",
]
