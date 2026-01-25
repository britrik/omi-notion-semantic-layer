"""
Tests for the Notion API client.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from notion_client.errors import APIResponseError

from src.models.insight import (
    ContentCategory,
    InsightStatus,
    PriorityLevel,
    ProcessedInsight,
    QualityScore,
    Summary,
)
from src.notion_client import NotionClient
from src.utils.exceptions import NotionAPIError, RateLimitError


class TestNotionClient:
    """Test suite for NotionClient."""

    @pytest.fixture
    def client(self, mock_env_vars: dict[str, str]) -> NotionClient:
        """Create a Notion client with mocked settings."""
        return NotionClient(
            api_key="test_notion_key",
            database_id="test_database_id",
        )

    @pytest.fixture
    def sample_insight(self) -> ProcessedInsight:
        """Create a sample processed insight."""
        return ProcessedInsight(
            transcript_id="test_transcript_123",
            source_timestamp=datetime(2026, 1, 6, 10, 0, 0, tzinfo=timezone.utc),
            primary_category=ContentCategory.ACTION_ITEM,
            quality_score=QualityScore(
                information_density=7.0,
                actionability=8.0,
                novelty=6.0,
                clarity=7.5,
                specificity=7.0,
                temporal_relevance=8.0,
            ),
            summary=Summary(
                title="Test insight title",
                executive="This is a test executive summary.",
            ),
            tags=["test", "project", "demo"],
            participants=["User", "Colleague"],
            priority=PriorityLevel.HIGH,
            status=InsightStatus.NEW,
            original_content="This is the original transcript content.",
            confidence=0.85,
        )

    def test_init_with_explicit_values(self) -> None:
        """Test client initialization with explicit values."""
        client = NotionClient(
            api_key="my_key",
            database_id="my_db_id",
        )
        assert client.api_key == "my_key"
        assert client.database_id == "my_db_id"

    @patch("src.notion_client.NotionSDKClient")
    def test_create_page_success(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
        sample_insight: ProcessedInsight,
    ) -> None:
        """Test successful page creation."""
        mock_instance = MagicMock()
        mock_instance.pages.create.return_value = {
            "id": "page_123",
            "url": "https://notion.so/page_123",
        }
        client._client = mock_instance

        result = client.create_page(sample_insight)

        assert result["id"] == "page_123"
        assert result["success"] is True
        mock_instance.pages.create.assert_called_once()

    @patch("src.notion_client.NotionSDKClient")
    def test_create_page_api_error(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
        sample_insight: ProcessedInsight,
    ) -> None:
        """Test page creation with API error."""
        mock_instance = MagicMock()

        error = APIResponseError(
            MagicMock(status_code=400),
            message="Validation error",
            code="validation_error",
        )
        mock_instance.pages.create.side_effect = error
        client._client = mock_instance

        with pytest.raises(NotionAPIError) as exc_info:
            client.create_page(sample_insight)

        assert exc_info.value.error_code == "validation_error"

    @patch("src.notion_client.NotionSDKClient")
    def test_create_page_rate_limited(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
        sample_insight: ProcessedInsight,
    ) -> None:
        """Test rate limit handling during page creation."""
        mock_instance = MagicMock()

        error = APIResponseError(
            MagicMock(status_code=429),
            message="Rate limited",
            code="rate_limited",
        )
        mock_instance.pages.create.side_effect = error
        client._client = mock_instance

        with pytest.raises(RateLimitError) as exc_info:
            client.create_page(sample_insight)

        assert exc_info.value.service == "notion"

    @patch("src.notion_client.NotionSDKClient")
    def test_update_page_success(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
        sample_insight: ProcessedInsight,
    ) -> None:
        """Test successful page update."""
        mock_instance = MagicMock()
        mock_instance.pages.update.return_value = {
            "id": "page_123",
            "url": "https://notion.so/page_123",
        }
        client._client = mock_instance

        result = client.update_page("page_123", sample_insight)

        assert result["id"] == "page_123"
        assert result["success"] is True

    @patch("src.notion_client.NotionSDKClient")
    def test_find_duplicate_found(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
    ) -> None:
        """Test finding an existing duplicate."""
        mock_instance = MagicMock()
        mock_instance.databases.query.return_value = {
            "results": [{"id": "existing_page_123"}]
        }
        client._client = mock_instance

        result = client.find_duplicate("test_transcript_123")

        assert result == "existing_page_123"

    @patch("src.notion_client.NotionSDKClient")
    def test_find_duplicate_not_found(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
    ) -> None:
        """Test when no duplicate exists."""
        mock_instance = MagicMock()
        mock_instance.databases.query.return_value = {"results": []}
        client._client = mock_instance

        result = client.find_duplicate("new_transcript")

        assert result is None

    @patch("src.notion_client.NotionSDKClient")
    def test_query_related_by_tags(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
    ) -> None:
        """Test querying related pages by tags."""
        mock_instance = MagicMock()
        mock_instance.databases.query.return_value = {
            "results": [
                {
                    "id": "related_page_1",
                    "url": "https://notion.so/page1",
                    "properties": {
                        "Title": {"title": [{"plain_text": "Related Page 1"}]}
                    },
                },
                {
                    "id": "related_page_2",
                    "url": "https://notion.so/page2",
                    "properties": {
                        "Title": {"title": [{"plain_text": "Related Page 2"}]}
                    },
                },
            ]
        }
        client._client = mock_instance

        results = client.query_related(tags=["project", "demo"])

        assert len(results) == 2
        assert results[0]["id"] == "related_page_1"
        assert results[0]["title"] == "Related Page 1"

    @patch("src.notion_client.NotionSDKClient")
    def test_query_related_empty(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
    ) -> None:
        """Test querying related pages with no filters."""
        result = client.query_related()
        assert result == []

    @patch("src.notion_client.NotionSDKClient")
    def test_validate_database_schema_valid(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test schema validation with valid database."""
        client._client = mock_notion_client

        is_valid, missing = client.validate_database_schema()

        assert is_valid is True
        assert missing == []

    @patch("src.notion_client.NotionSDKClient")
    def test_validate_database_schema_missing_props(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
    ) -> None:
        """Test schema validation with missing properties."""
        mock_instance = MagicMock()
        mock_instance.databases.retrieve.return_value = {
            "properties": {
                "Title": {"type": "title"},
                # Missing other required properties
            }
        }
        client._client = mock_instance

        is_valid, missing = client.validate_database_schema()

        assert is_valid is False
        assert len(missing) > 0

    @patch("src.notion_client.NotionSDKClient")
    def test_create_or_update_creates_new(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
        sample_insight: ProcessedInsight,
    ) -> None:
        """Test create_or_update creates new page when no duplicate."""
        mock_instance = MagicMock()
        mock_instance.databases.query.return_value = {"results": []}
        mock_instance.pages.create.return_value = {
            "id": "new_page",
            "url": "https://notion.so/new_page",
        }
        client._client = mock_instance

        result = client.create_or_update(sample_insight)

        assert result["id"] == "new_page"
        assert result["operation"] == "created"

    @patch("src.notion_client.NotionSDKClient")
    def test_create_or_update_updates_existing(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
        sample_insight: ProcessedInsight,
    ) -> None:
        """Test create_or_update updates when duplicate exists."""
        mock_instance = MagicMock()
        mock_instance.databases.query.return_value = {
            "results": [{"id": "existing_page"}]
        }
        mock_instance.pages.update.return_value = {
            "id": "existing_page",
            "url": "https://notion.so/existing_page",
        }
        client._client = mock_instance

        result = client.create_or_update(sample_insight)

        assert result["id"] == "existing_page"
        assert result["operation"] == "updated"

    @patch("src.notion_client.NotionSDKClient")
    def test_archive_page(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
    ) -> None:
        """Test page archiving."""
        mock_instance = MagicMock()
        mock_instance.pages.update.return_value = {"id": "page_123"}
        client._client = mock_instance

        result = client.archive_page("page_123")

        assert result["id"] == "page_123"
        assert result["archived"] is True
        mock_instance.pages.update.assert_called_with(
            page_id="page_123",
            archived=True,
        )

    @patch("src.notion_client.NotionSDKClient")
    def test_health_check_success(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
    ) -> None:
        """Test successful health check."""
        mock_instance = MagicMock()
        mock_instance.databases.retrieve.return_value = {"id": "db_123"}
        client._client = mock_instance

        assert client.health_check() is True

    @patch("src.notion_client.NotionSDKClient")
    def test_health_check_failure(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
    ) -> None:
        """Test failed health check."""
        mock_instance = MagicMock()
        mock_instance.databases.retrieve.side_effect = Exception("Not found")
        client._client = mock_instance

        assert client.health_check() is False

    @patch("src.notion_client.NotionSDKClient")
    def test_get_page(
        self,
        mock_sdk_client: MagicMock,
        client: NotionClient,
    ) -> None:
        """Test retrieving a page."""
        mock_instance = MagicMock()
        mock_instance.pages.retrieve.return_value = {
            "id": "page_123",
            "properties": {},
        }
        client._client = mock_instance

        result = client.get_page("page_123")

        assert result["id"] == "page_123"
        mock_instance.pages.retrieve.assert_called_with(page_id="page_123")
