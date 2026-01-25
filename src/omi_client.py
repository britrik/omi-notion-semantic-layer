"""
OMI API client for fetching transcripts.

Provides methods for:
- Fetching single transcripts
- Batch fetching transcripts
- Webhook signature validation
- Retry logic with exponential backoff
"""

import hashlib
import hmac
from datetime import datetime
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.models.transcript import Segment, Transcript, TranscriptMetadata
from src.utils.config import get_settings
from src.utils.exceptions import OMIAPIError, RateLimitError, ValidationError
from src.utils.logger import get_logger

logger = get_logger("omi")


class OMIClient:
    """
    Client for interacting with the OMI API.

    Handles authentication, request retries, and response parsing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize the OMI client.

        Args:
            api_key: OMI API key. Defaults to config value.
            api_url: OMI API base URL. Defaults to config value.
            webhook_secret: Secret for webhook signature validation.
            timeout: Request timeout in seconds.
        """
        settings = get_settings()
        self.api_key = api_key or settings.omi.api_key
        self.api_url = (api_url or settings.omi.api_url).rstrip("/")
        self.webhook_secret = webhook_secret or settings.omi.webhook_secret
        self.timeout = timeout

        if not self.api_key:
            logger.warning("OMI API key not configured")

        self._client = httpx.Client(
            base_url=self.api_url,
            headers=self._build_headers(),
            timeout=timeout,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "OMIClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments passed to httpx

        Returns:
            HTTP response

        Raises:
            OMIAPIError: On API errors
            RateLimitError: When rate limited
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        logger.debug(f"Making {method} request to {url}")

        try:
            response = self._client.request(method, endpoint, **kwargs)
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {url}")
            raise OMIAPIError(
                "Request timed out",
                endpoint=endpoint,
                cause=e,
            )
        except httpx.NetworkError as e:
            logger.error(f"Network error: {url} - {e}")
            raise OMIAPIError(
                "Network error occurred",
                endpoint=endpoint,
                cause=e,
            )

        # Handle error responses
        if response.status_code == 429:
            retry_after_header = response.headers.get("Retry-After", "60")
            try:
                retry_after = int(retry_after_header)
            except (ValueError, TypeError):
                retry_after = 60
            logger.warning(f"Rate limited, retry after {retry_after}s")
            raise RateLimitError(
                "OMI API rate limit exceeded",
                service="omi",
                retry_after=retry_after,
            )

        if response.status_code >= 400:
            error_body = response.text
            logger.error(
                f"API error {response.status_code}: {error_body[:200]}"
            )
            raise OMIAPIError(
                f"OMI API error: {response.status_code}",
                status_code=response.status_code,
                response_body=error_body,
                endpoint=endpoint,
            )

        return response

    def fetch_transcript(self, transcript_id: str) -> Transcript:
        """
        Fetch a single transcript by ID.

        Args:
            transcript_id: Unique transcript identifier

        Returns:
            Parsed Transcript object

        Raises:
            OMIAPIError: On API errors
            ValidationError: If response data is invalid
        """
        logger.info(f"Fetching transcript: {transcript_id}")

        response = self._make_request("GET", f"/transcripts/{transcript_id}")
        data = response.json()

        return self._parse_transcript(data)

    def fetch_transcripts(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transcript]:
        """
        Fetch multiple transcripts with optional filtering.

        Args:
            since: Only fetch transcripts after this time
            until: Only fetch transcripts before this time
            limit: Maximum number of transcripts to fetch
            offset: Offset for pagination

        Returns:
            List of Transcript objects

        Raises:
            OMIAPIError: On API errors
        """
        logger.info(f"Fetching transcripts (limit={limit}, offset={offset})")

        params: dict[str, Any] = {
            "limit": min(limit, 100),  # Cap at 100 per request
            "offset": offset,
        }

        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()

        response = self._make_request("GET", "/transcripts", params=params)
        data = response.json()

        # Handle paginated response
        transcripts_data = data.get("transcripts", data.get("results", []))
        if isinstance(data, list):
            transcripts_data = data

        transcripts = []
        for item in transcripts_data:
            try:
                transcripts.append(self._parse_transcript(item))
            except (ValidationError, ValueError) as e:
                logger.warning(f"Skipping invalid transcript: {e}")
                continue

        logger.info(f"Fetched {len(transcripts)} transcripts")
        return transcripts

    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Validate a webhook request signature.

        Args:
            payload: Raw request body bytes
            signature: Signature from X-OMI-Signature header
            timestamp: Timestamp from X-OMI-Timestamp header (optional)

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping validation")
            return True

        # Build signed payload
        signed_payload = payload
        if timestamp:
            signed_payload = f"{timestamp}.".encode() + payload

        # Compute expected signature
        expected = hmac.new(
            self.webhook_secret.encode(),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures (timing-safe)
        is_valid = hmac.compare_digest(expected, signature)

        if not is_valid:
            logger.warning("Invalid webhook signature")

        return is_valid

    def _parse_transcript(self, data: dict[str, Any]) -> Transcript:
        """
        Parse API response data into a Transcript object.

        Args:
            data: Raw API response data

        Returns:
            Parsed Transcript object

        Raises:
            ValidationError: If data is invalid
        """
        try:
            # Parse segments
            segments = []
            for seg_data in data.get("segments", []):
                segments.append(
                    Segment(
                        speaker=seg_data.get("speaker", "Unknown"),
                        text=seg_data.get("text", ""),
                        timestamp=float(seg_data.get("timestamp", 0)),
                        end_timestamp=seg_data.get("end_timestamp"),
                        confidence=seg_data.get("confidence"),
                    )
                )

            # Parse metadata
            meta_data = data.get("metadata", {})
            metadata = TranscriptMetadata(
                device_id=meta_data.get("device_id"),
                session_id=meta_data.get("session_id"),
                language=meta_data.get("language", "en"),
                location=meta_data.get("location"),
                tags=meta_data.get("tags", []),
                custom=meta_data.get("custom", {}),
            )

            # Parse timestamp
            timestamp_str = data.get("timestamp")
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
            elif isinstance(timestamp_str, datetime):
                timestamp = timestamp_str
            else:
                logger.warning(
                    f"Missing or invalid timestamp in transcript data, using current time"
                )
                timestamp = datetime.now()

            return Transcript(
                transcript_id=data.get("transcript_id", data.get("id", "")),
                timestamp=timestamp,
                duration=float(data.get("duration", 0)),
                participants=data.get("participants", []),
                content=data.get("content", ""),
                segments=segments,
                metadata=metadata,
            )

        except Exception as e:
            raise ValidationError(
                f"Failed to parse transcript: {e}",
                field="transcript",
                cause=e,
            )

    def health_check(self) -> bool:
        """
        Check if the OMI API is accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self._client.get("/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
