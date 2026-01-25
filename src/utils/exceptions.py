"""
Custom exception classes for the OMI-to-Notion Semantic Intelligence Layer.

Provides a hierarchy of exceptions for different error categories:
- API errors (OMI, Notion)
- Processing errors
- Validation errors
- Configuration errors
"""

from typing import Any, Optional


class OMINotionError(Exception):
    """
    Base exception for all OMI-to-Notion errors.

    All custom exceptions in this project inherit from this class,
    allowing for broad exception catching when needed.
    """

    def __init__(
        self,
        message: str,
        *,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional error details as key-value pairs
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        """Return string representation with details."""
        base = self.message
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base = f"{base} ({details_str})"
        if self.cause:
            base = f"{base} [caused by: {self.cause}]"
        return base

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


class OMIAPIError(OMINotionError):
    """
    Exception for OMI API errors.

    Raised when communication with the OMI API fails or returns an error.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        endpoint: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize OMI API error.

        Args:
            message: Error message
            status_code: HTTP status code from the API
            response_body: Raw response body
            endpoint: API endpoint that was called
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        if status_code is not None:
            details["status_code"] = status_code
        if response_body is not None:
            details["response_body"] = response_body[:500]  # Truncate long responses
        if endpoint is not None:
            details["endpoint"] = endpoint

        super().__init__(message, details=details, **kwargs)
        self.status_code = status_code
        self.response_body = response_body
        self.endpoint = endpoint

    @property
    def is_auth_error(self) -> bool:
        """Check if this is an authentication error."""
        return self.status_code in (401, 403)

    @property
    def is_not_found(self) -> bool:
        """Check if the resource was not found."""
        return self.status_code == 404

    @property
    def is_rate_limited(self) -> bool:
        """Check if we hit rate limits."""
        return self.status_code == 429

    @property
    def is_server_error(self) -> bool:
        """Check if this is a server-side error."""
        return self.status_code is not None and self.status_code >= 500


class NotionAPIError(OMINotionError):
    """
    Exception for Notion API errors.

    Raised when communication with the Notion API fails or returns an error.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize Notion API error.

        Args:
            message: Error message
            status_code: HTTP status code from the API
            error_code: Notion-specific error code (e.g., 'object_not_found')
            request_id: Notion request ID for debugging
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        if status_code is not None:
            details["status_code"] = status_code
        if error_code is not None:
            details["error_code"] = error_code
        if request_id is not None:
            details["request_id"] = request_id

        super().__init__(message, details=details, **kwargs)
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id

    @property
    def is_object_not_found(self) -> bool:
        """Check if the Notion object was not found."""
        return self.error_code == "object_not_found"

    @property
    def is_validation_error(self) -> bool:
        """Check if this is a validation error from Notion."""
        return self.error_code == "validation_error"

    @property
    def is_rate_limited(self) -> bool:
        """Check if we hit Notion rate limits."""
        return self.status_code == 429 or self.error_code == "rate_limited"

    @property
    def is_unauthorized(self) -> bool:
        """Check if the integration lacks permissions."""
        return self.error_code == "unauthorized" or self.status_code == 401


class ProcessingError(OMINotionError):
    """
    Exception for transcript processing errors.

    Raised when semantic processing, classification, or enrichment fails.
    """

    def __init__(
        self,
        message: str,
        *,
        stage: Optional[str] = None,
        transcript_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize processing error.

        Args:
            message: Error message
            stage: Processing stage where error occurred
                   (e.g., 'classification', 'entity_extraction', 'enrichment')
            transcript_id: ID of the transcript being processed
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        if stage is not None:
            details["stage"] = stage
        if transcript_id is not None:
            details["transcript_id"] = transcript_id

        super().__init__(message, details=details, **kwargs)
        self.stage = stage
        self.transcript_id = transcript_id


class ValidationError(OMINotionError):
    """
    Exception for data validation errors.

    Raised when input data fails validation checks.
    """

    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraints: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Name of the field that failed validation
            value: The invalid value (will be truncated if too long)
            constraints: List of constraints that were violated
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        if field is not None:
            details["field"] = field
        if value is not None:
            # Truncate long values
            str_value = str(value)
            details["value"] = str_value[:100] if len(str_value) > 100 else str_value
        if constraints is not None:
            details["constraints"] = constraints

        super().__init__(message, details=details, **kwargs)
        self.field = field
        self.value = value
        self.constraints = constraints or []


class ConfigurationError(OMINotionError):
    """
    Exception for configuration errors.

    Raised when required configuration is missing or invalid.
    """

    def __init__(
        self,
        message: str,
        *,
        missing_keys: Optional[list[str]] = None,
        invalid_keys: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize configuration error.

        Args:
            message: Error message
            missing_keys: List of required configuration keys that are missing
            invalid_keys: Dict of invalid keys and their error messages
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        if missing_keys:
            details["missing_keys"] = missing_keys
        if invalid_keys:
            details["invalid_keys"] = invalid_keys

        super().__init__(message, details=details, **kwargs)
        self.missing_keys = missing_keys or []
        self.invalid_keys = invalid_keys or {}


class RetryableError(OMINotionError):
    """
    Mixin/base for errors that can be retried.

    Used to mark transient errors that may succeed on retry.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: Optional[int] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        """
        Initialize retryable error.

        Args:
            message: Error message
            retry_after: Suggested wait time in seconds before retry
            max_retries: Maximum number of retries recommended
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        if retry_after is not None:
            details["retry_after"] = retry_after
        details["max_retries"] = max_retries

        super().__init__(message, details=details, **kwargs)
        self.retry_after = retry_after
        self.max_retries = max_retries


class RateLimitError(RetryableError):
    """
    Exception for rate limit errors.

    Raised when API rate limits are exceeded.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        service: str = "unknown",
        **kwargs: Any,
    ) -> None:
        """
        Initialize rate limit error.

        Args:
            message: Error message
            service: Service that rate limited us (omi, notion, openai)
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details["service"] = service

        super().__init__(message, details=details, **kwargs)
        self.service = service
