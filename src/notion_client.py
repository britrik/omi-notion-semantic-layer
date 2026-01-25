"""
Notion API client for managing insight pages.

Provides methods for:
- Creating and updating pages
- Duplicate detection
- Finding related pages
- Database schema validation
"""

from typing import Any, Optional

from notion_client import Client as NotionSDKClient
from notion_client.errors import APIResponseError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.models.insight import ProcessedInsight
from src.models.notion import NotionDatabaseSchema, NotionPageProperties
from src.utils.config import get_settings
from src.utils.exceptions import NotionAPIError, RateLimitError
from src.utils.logger import get_logger

logger = get_logger("notion")


class NotionClient:
    """
    Client for interacting with the Notion API.

    Handles page creation, updates, queries, and schema validation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        database_id: Optional[str] = None,
    ) -> None:
        """
        Initialize the Notion client.

        Args:
            api_key: Notion integration token. Defaults to config value.
            database_id: Target database ID. Defaults to config value.
        """
        settings = get_settings()
        self.api_key = api_key or settings.notion.api_key
        self.database_id = database_id or settings.notion.database_id

        if not self.api_key:
            logger.warning("Notion API key not configured")

        self._client = NotionSDKClient(auth=self.api_key)
        self._schema = NotionDatabaseSchema()

    def _handle_api_error(self, e: APIResponseError, context: str = "") -> None:
        """
        Convert Notion API errors to our exception types.

        Args:
            e: The API response error
            context: Additional context for logging

        Raises:
            RateLimitError: If rate limited
            NotionAPIError: For other API errors
        """
        status = e.status
        code = e.code
        message = str(e)

        if status == 429:
            logger.warning(f"Notion rate limited: {context}")
            raise RateLimitError(
                "Notion API rate limit exceeded",
                service="notion",
                retry_after=60,
            )

        logger.error(f"Notion API error ({context}): {code} - {message}")
        raise NotionAPIError(
            message,
            status_code=status,
            error_code=code,
        )

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True,
    )
    def create_page(self, insight: ProcessedInsight) -> dict[str, Any]:
        """
        Create a new Notion page from a processed insight.

        Args:
            insight: The processed insight to create a page for

        Returns:
            Created page data including ID and URL

        Raises:
            NotionAPIError: On API errors
        """
        logger.info(f"Creating page for insight: {insight.transcript_id}")

        # Convert insight to Notion properties
        properties = NotionPageProperties.from_processed_insight(insight)
        page_body = properties.to_notion_page_body(self.database_id)

        try:
            response = self._client.pages.create(**page_body)
            page_id = response.get("id", "")
            page_url = response.get("url", "")
            logger.info(f"Created page: {page_id}")
            return {
                "id": page_id,
                "url": page_url,
                "success": True,
            }
        except APIResponseError as e:
            self._handle_api_error(e, f"create_page({insight.transcript_id})")
            raise  # For type checker - _handle_api_error always raises

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True,
    )
    def update_page(
        self,
        page_id: str,
        insight: ProcessedInsight,
    ) -> dict[str, Any]:
        """
        Update an existing Notion page.

        Args:
            page_id: The Notion page ID to update
            insight: The processed insight with updated data

        Returns:
            Updated page data

        Raises:
            NotionAPIError: On API errors
        """
        logger.info(f"Updating page: {page_id}")

        properties = NotionPageProperties.from_processed_insight(insight)

        try:
            response = self._client.pages.update(
                page_id=page_id,
                properties=properties.to_notion_properties(),
            )
            logger.info(f"Updated page: {page_id}")
            return {
                "id": response.get("id", ""),
                "url": response.get("url", ""),
                "success": True,
            }
        except APIResponseError as e:
            self._handle_api_error(e, f"update_page({page_id})")
            raise

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True,
    )
    def find_duplicate(self, transcript_id: str) -> Optional[str]:
        """
        Check if an insight for this transcript already exists.

        Args:
            transcript_id: The source transcript ID to check

        Returns:
            Page ID if duplicate exists, None otherwise

        Raises:
            NotionAPIError: On API errors
        """
        logger.debug(f"Checking for duplicate: {transcript_id}")

        try:
            response = self._client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Source",
                    "rich_text": {
                        "equals": transcript_id,
                    },
                },
                page_size=1,
            )

            results = response.get("results", [])
            if results:
                page_id = results[0].get("id")
                logger.info(f"Found duplicate page: {page_id}")
                return page_id

            return None

        except APIResponseError as e:
            self._handle_api_error(e, f"find_duplicate({transcript_id})")
            raise

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True,
    )
    def query_related(
        self,
        tags: Optional[list[str]] = None,
        entities: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Find related pages by tags or entities.

        Args:
            tags: Tags to search for (OR logic)
            entities: Entity names to search for (OR logic)
            limit: Maximum number of results

        Returns:
            List of related page summaries

        Raises:
            NotionAPIError: On API errors
        """
        logger.debug(f"Querying related pages (tags={tags}, entities={entities})")

        # Build filter for tags
        filters = []

        if tags:
            for tag in tags[:5]:  # Limit to avoid overly complex queries
                filters.append({
                    "property": "Tags",
                    "multi_select": {"contains": tag},
                })

        if entities:
            for entity in entities[:5]:
                filters.append({
                    "property": "Entities",
                    "multi_select": {"contains": entity},
                })

        if not filters:
            return []

        # Use OR for combining filters
        query_filter: dict[str, Any]
        if len(filters) == 1:
            query_filter = filters[0]
        else:
            query_filter = {"or": filters}

        try:
            response = self._client.databases.query(
                database_id=self.database_id,
                filter=query_filter,
                page_size=limit,
                sorts=[{"timestamp": "last_edited_time", "direction": "descending"}],
            )

            results = []
            for page in response.get("results", []):
                page_id = page.get("id", "")
                props = page.get("properties", {})

                # Extract title (with bounds check for empty arrays)
                title = ""
                title_prop = props.get("Title", {})
                title_array = title_prop.get("title", [])
                if title_array:
                    title = title_array[0].get("plain_text", "")

                results.append({
                    "id": page_id,
                    "title": title,
                    "url": page.get("url", ""),
                })

            logger.debug(f"Found {len(results)} related pages")
            return results

        except APIResponseError as e:
            self._handle_api_error(e, "query_related")
            raise

    def validate_database_schema(self) -> tuple[bool, list[str]]:
        """
        Verify the target database has the required properties.

        Returns:
            Tuple of (is_valid, list_of_missing_properties)

        Raises:
            NotionAPIError: On API errors
        """
        logger.info(f"Validating database schema: {self.database_id}")

        try:
            response = self._client.databases.retrieve(
                database_id=self.database_id
            )

            db_properties = response.get("properties", {})
            is_valid, missing = self._schema.validate_database(db_properties)

            if is_valid:
                logger.info("Database schema is valid")
            else:
                logger.warning(f"Missing properties: {missing}")

            return is_valid, missing

        except APIResponseError as e:
            self._handle_api_error(e, "validate_database_schema")
            raise

    def create_or_update(self, insight: ProcessedInsight) -> dict[str, Any]:
        """
        Create a new page or update existing if duplicate found.

        Args:
            insight: The processed insight

        Returns:
            Page data with operation type

        Raises:
            NotionAPIError: On API errors
        """
        # Check for existing page
        existing_page_id = self.find_duplicate(insight.transcript_id)

        if existing_page_id:
            result = self.update_page(existing_page_id, insight)
            result["operation"] = "updated"
        else:
            result = self.create_page(insight)
            result["operation"] = "created"

        return result

    def get_page(self, page_id: str) -> dict[str, Any]:
        """
        Retrieve a page by ID.

        Args:
            page_id: The Notion page ID

        Returns:
            Page data

        Raises:
            NotionAPIError: On API errors
        """
        try:
            return self._client.pages.retrieve(page_id=page_id)
        except APIResponseError as e:
            self._handle_api_error(e, f"get_page({page_id})")
            raise

    def archive_page(self, page_id: str) -> dict[str, Any]:
        """
        Archive (soft delete) a page.

        Args:
            page_id: The Notion page ID

        Returns:
            Updated page data

        Raises:
            NotionAPIError: On API errors
        """
        logger.info(f"Archiving page: {page_id}")

        try:
            self._client.pages.update(
                page_id=page_id,
                archived=True,
            )
            return {"id": page_id, "archived": True}
        except APIResponseError as e:
            self._handle_api_error(e, f"archive_page({page_id})")
            raise

    def health_check(self) -> bool:
        """
        Check if the Notion API is accessible and database exists.

        Returns:
            True if healthy, False otherwise
        """
        try:
            self._client.databases.retrieve(database_id=self.database_id)
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
