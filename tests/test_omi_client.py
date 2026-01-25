"""
Tests for the OMI API client.
"""

import hashlib
import hmac
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.omi_client import OMIClient
from src.utils.exceptions import OMIAPIError, RateLimitError


class TestOMIClient:
    """Test suite for OMIClient."""

    @pytest.fixture
    def client(self, mock_env_vars: dict[str, str]) -> OMIClient:
        """Create an OMI client with mocked settings."""
        return OMIClient(
            api_key="test_api_key",
            api_url="https://api.omi.test/v1",
            webhook_secret="test_secret",
        )

    @pytest.fixture
    def mock_transcript_response(self) -> dict:
        """Sample transcript response from API."""
        return {
            "transcript_id": "test_123",
            "timestamp": "2026-01-06T10:00:00Z",
            "duration": 300,
            "participants": ["User", "Colleague"],
            "content": "Hello, this is a test transcript.",
            "segments": [
                {"speaker": "User", "text": "Hello", "timestamp": 0},
                {"speaker": "Colleague", "text": "Hi there", "timestamp": 2},
            ],
            "metadata": {
                "device_id": "device_123",
                "language": "en",
            },
        }

    def test_init_with_explicit_values(self) -> None:
        """Test client initialization with explicit values."""
        client = OMIClient(
            api_key="my_key",
            api_url="https://custom.api.com",
            webhook_secret="my_secret",
        )
        assert client.api_key == "my_key"
        assert client.api_url == "https://custom.api.com"
        assert client.webhook_secret == "my_secret"

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slashes are stripped from API URL."""
        client = OMIClient(api_url="https://api.test.com/v1/")
        assert client.api_url == "https://api.test.com/v1"

    def test_context_manager(self, client: OMIClient) -> None:
        """Test client can be used as context manager."""
        with client as c:
            assert c is client

    @patch.object(httpx.Client, "request")
    def test_fetch_transcript_success(
        self,
        mock_request: MagicMock,
        client: OMIClient,
        mock_transcript_response: dict,
    ) -> None:
        """Test successful transcript fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_transcript_response
        mock_request.return_value = mock_response

        transcript = client.fetch_transcript("test_123")

        assert transcript.transcript_id == "test_123"
        assert transcript.duration == 300
        assert len(transcript.segments) == 2
        assert transcript.segments[0].speaker == "User"
        assert transcript.metadata.device_id == "device_123"

    @patch.object(httpx.Client, "request")
    def test_fetch_transcript_not_found(
        self,
        mock_request: MagicMock,
        client: OMIClient,
    ) -> None:
        """Test 404 error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_request.return_value = mock_response

        with pytest.raises(OMIAPIError) as exc_info:
            client.fetch_transcript("nonexistent")

        assert exc_info.value.status_code == 404
        assert exc_info.value.is_not_found

    @patch.object(httpx.Client, "request")
    def test_fetch_transcript_unauthorized(
        self,
        mock_request: MagicMock,
        client: OMIClient,
    ) -> None:
        """Test 401 error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response

        with pytest.raises(OMIAPIError) as exc_info:
            client.fetch_transcript("test_123")

        assert exc_info.value.status_code == 401
        assert exc_info.value.is_auth_error

    @patch.object(httpx.Client, "request")
    def test_fetch_transcript_rate_limited(
        self,
        mock_request: MagicMock,
        client: OMIClient,
    ) -> None:
        """Test rate limit handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}
        mock_response.text = "Rate limited"
        mock_request.return_value = mock_response

        with pytest.raises(RateLimitError) as exc_info:
            client.fetch_transcript("test_123")

        assert exc_info.value.retry_after == 30
        assert exc_info.value.service == "omi"

    @patch.object(httpx.Client, "request")
    def test_fetch_transcript_server_error(
        self,
        mock_request: MagicMock,
        client: OMIClient,
    ) -> None:
        """Test 500 error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_request.return_value = mock_response

        with pytest.raises(OMIAPIError) as exc_info:
            client.fetch_transcript("test_123")

        assert exc_info.value.status_code == 500
        assert exc_info.value.is_server_error

    @patch.object(httpx.Client, "request")
    def test_fetch_transcripts_batch(
        self,
        mock_request: MagicMock,
        client: OMIClient,
        mock_transcript_response: dict,
    ) -> None:
        """Test batch transcript fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transcripts": [mock_transcript_response, mock_transcript_response]
        }
        mock_request.return_value = mock_response

        transcripts = client.fetch_transcripts(limit=10)

        assert len(transcripts) == 2

    @patch.object(httpx.Client, "request")
    def test_fetch_transcripts_with_date_filters(
        self,
        mock_request: MagicMock,
        client: OMIClient,
        mock_transcript_response: dict,
    ) -> None:
        """Test batch fetch with date filters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"transcripts": []}
        mock_request.return_value = mock_response

        since = datetime(2026, 1, 1, tzinfo=timezone.utc)
        until = datetime(2026, 1, 31, tzinfo=timezone.utc)

        client.fetch_transcripts(since=since, until=until)

        # Verify params were passed
        call_kwargs = mock_request.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert "since" in params
        assert "until" in params

    @patch.object(httpx.Client, "request")
    def test_fetch_transcripts_skips_invalid(
        self,
        mock_request: MagicMock,
        client: OMIClient,
    ) -> None:
        """Test that invalid transcripts are skipped."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transcripts": [
                {"transcript_id": "valid", "timestamp": "2026-01-01T00:00:00Z", "duration": 60, "content": "Valid"},
                {"invalid": "missing required fields"},  # Invalid
            ]
        }
        mock_request.return_value = mock_response

        transcripts = client.fetch_transcripts()

        # Should only return the valid one
        assert len(transcripts) == 1
        assert transcripts[0].transcript_id == "valid"

    def test_validate_webhook_signature_valid(self, client: OMIClient) -> None:
        """Test valid webhook signature validation."""
        payload = b'{"test": "data"}'
        timestamp = "1704531600"

        signed_payload = f"{timestamp}.".encode() + payload
        expected_sig = hmac.new(
            b"test_secret",
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        result = client.validate_webhook_signature(
            payload, expected_sig, timestamp
        )
        assert result is True

    def test_validate_webhook_signature_invalid(self, client: OMIClient) -> None:
        """Test invalid webhook signature detection."""
        payload = b'{"test": "data"}'
        invalid_sig = "invalid_signature"

        result = client.validate_webhook_signature(payload, invalid_sig)
        assert result is False

    def test_validate_webhook_no_secret(self) -> None:
        """Test webhook validation skips when no secret configured."""
        client = OMIClient(webhook_secret="")

        result = client.validate_webhook_signature(b"payload", "any_sig")
        assert result is True  # Should pass when no secret

    @patch.object(httpx.Client, "get")
    def test_health_check_success(
        self,
        mock_get: MagicMock,
        client: OMIClient,
    ) -> None:
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert client.health_check() is True

    @patch.object(httpx.Client, "get")
    def test_health_check_failure(
        self,
        mock_get: MagicMock,
        client: OMIClient,
    ) -> None:
        """Test failed health check."""
        mock_get.side_effect = Exception("Connection failed")

        assert client.health_check() is False

    def test_parse_transcript_with_iso_timestamp(self, client: OMIClient) -> None:
        """Test parsing transcript with ISO timestamp."""
        data = {
            "transcript_id": "test",
            "timestamp": "2026-01-06T10:00:00+00:00",
            "duration": 60,
            "content": "Test content",
        }

        transcript = client._parse_transcript(data)
        assert transcript.transcript_id == "test"
        assert transcript.timestamp.year == 2026

    def test_parse_transcript_with_z_timestamp(self, client: OMIClient) -> None:
        """Test parsing transcript with Z-format timestamp."""
        data = {
            "transcript_id": "test",
            "timestamp": "2026-01-06T10:00:00Z",
            "duration": 60,
            "content": "Test content",
        }

        transcript = client._parse_transcript(data)
        assert transcript.timestamp.tzinfo is not None
