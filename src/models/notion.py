"""
Data models for Notion API integration.

These models handle the mapping between ProcessedInsight
and Notion page properties.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.models.insight import (
    ContentCategory,
    InsightStatus,
    PriorityLevel,
    ProcessedInsight,
)


class NotionRichText(BaseModel):
    """Notion rich text content block."""

    type: str = "text"
    text: dict[str, str] = Field(default_factory=dict)
    annotations: Optional[dict[str, Any]] = None
    plain_text: Optional[str] = None

    @classmethod
    def from_string(cls, content: str) -> "NotionRichText":
        """Create rich text from a plain string."""
        return cls(
            type="text",
            text={"content": content},
            plain_text=content,
        )


class NotionSelectOption(BaseModel):
    """Notion select property option."""

    name: str = Field(description="Option display name")
    color: Optional[str] = Field(
        default=None,
        description="Option color (blue, green, red, etc.)"
    )


class NotionMultiSelect(BaseModel):
    """Notion multi-select property value."""

    options: list[NotionSelectOption] = Field(
        default_factory=list,
        description="Selected options"
    )

    @classmethod
    def from_strings(cls, values: list[str]) -> "NotionMultiSelect":
        """Create multi-select from list of strings."""
        return cls(options=[NotionSelectOption(name=v) for v in values])


class NotionDate(BaseModel):
    """Notion date property value."""

    start: str = Field(description="Start date in ISO format")
    end: Optional[str] = Field(default=None, description="End date (optional)")
    time_zone: Optional[str] = Field(default=None, description="Timezone")

    @classmethod
    def from_datetime(cls, dt: datetime) -> "NotionDate":
        """Create from Python datetime."""
        return cls(start=dt.isoformat())


class NotionPageProperties(BaseModel):
    """
    Properties for a Notion page in the OMI Insights database.

    Maps directly to the database schema defined in poc-setup.md.
    """

    # Core properties
    title: str = Field(
        max_length=100,
        description="Page title (auto-generated summary)"
    )
    type: ContentCategory = Field(
        description="Content type/category"
    )
    status: InsightStatus = Field(
        default=InsightStatus.NEW,
        description="Workflow status"
    )
    priority: PriorityLevel = Field(
        default=PriorityLevel.MEDIUM,
        description="Priority level"
    )

    # Dates
    date: datetime = Field(description="Original conversation date")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When added to Notion"
    )

    # Multi-select properties
    tags: list[str] = Field(
        default_factory=list,
        description="Topic tags"
    )
    participants: list[str] = Field(
        default_factory=list,
        description="People involved"
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Extracted named entities"
    )

    # Text properties
    source: str = Field(description="OMI session/transcript ID")
    summary: str = Field(description="Brief overview")
    content: str = Field(description="Full processed transcript")

    # Number properties
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Processing confidence score"
    )
    relevance_score: float = Field(
        ge=0.0,
        le=10.0,
        description="Calculated relevance score"
    )

    # Relation properties (stored as page IDs)
    related_pages: list[str] = Field(
        default_factory=list,
        description="Related insight page IDs"
    )

    # Metadata
    processing_version: str = Field(
        default="1.0",
        description="Algorithm version used"
    )

    @classmethod
    def from_processed_insight(
        cls,
        insight: ProcessedInsight,
    ) -> "NotionPageProperties":
        """
        Create Notion page properties from a processed insight.

        Args:
            insight: The processed insight to convert

        Returns:
            NotionPageProperties ready for Notion API
        """
        # Get title from summary or generate one
        title = (
            insight.summary.title
            if insight.summary
            else f"Insight from {insight.source_timestamp.strftime('%Y-%m-%d %H:%M')}"
        )

        # Get primary category or default
        primary_type = insight.primary_category or ContentCategory.INSIGHT

        # Extract entity texts for multi-select
        entity_texts = list(set(e.text for e in insight.entities))[:20]  # Limit

        # Get summary text
        summary_text = ""
        if insight.summary:
            summary_text = insight.summary.executive or insight.summary.title

        # Get content
        content = insight.processed_content or insight.original_content

        return cls(
            title=title[:100],  # Ensure max length
            type=primary_type,
            status=insight.status,
            priority=insight.priority,
            date=insight.source_timestamp,
            tags=insight.tags[:20],  # Limit tags
            participants=insight.participants[:10],  # Limit participants
            entities=entity_texts,
            source=insight.transcript_id,
            summary=summary_text[:500] if summary_text else "",
            content=content[:2000],  # Notion has limits
            confidence=insight.confidence,
            relevance_score=insight.relevance_score,
            related_pages=insight.related_insight_ids,
            processing_version=insight.processing_version,
        )

    def to_notion_properties(self) -> dict[str, Any]:
        """
        Convert to Notion API property format.

        Returns:
            Dictionary in Notion API property format
        """
        return {
            "Title": {
                "title": [{"text": {"content": self.title}}]
            },
            "Type": {
                "select": {"name": self.type.value}
            },
            "Status": {
                "select": {"name": self.status.value}
            },
            "Priority": {
                "select": {"name": self.priority.value}
            },
            "Date": {
                "date": {"start": self.date.isoformat()}
            },
            "Tags": {
                "multi_select": [{"name": tag} for tag in self.tags]
            },
            "Participants": {
                "multi_select": [{"name": p} for p in self.participants]
            },
            "Entities": {
                "multi_select": [{"name": e} for e in self.entities]
            },
            "Source": {
                "rich_text": [{"text": {"content": self.source}}]
            },
            "Summary": {
                "rich_text": [{"text": {"content": self.summary}}]
            },
            "Content": {
                "rich_text": [{"text": {"content": self.content}}]
            },
            "Confidence": {
                "number": self.confidence
            },
            "Relevance Score": {
                "number": self.relevance_score
            },
            "Processing Version": {
                "rich_text": [{"text": {"content": self.processing_version}}]
            },
            # Related Pages uses Notion's relation type - requires page IDs
            # Only include if there are related pages to avoid empty relation errors
            **(
                {
                    "Related Pages": {
                        "relation": [{"id": page_id} for page_id in self.related_pages]
                    }
                }
                if self.related_pages
                else {}
            ),
        }

    def to_notion_page_body(self, database_id: str) -> dict[str, Any]:
        """
        Create full Notion page creation body.

        Args:
            database_id: Target Notion database ID

        Returns:
            Complete request body for Notion pages.create()
        """
        return {
            "parent": {"database_id": database_id},
            "properties": self.to_notion_properties(),
        }


class NotionDatabaseSchema(BaseModel):
    """
    Expected Notion database schema for validation.

    Used to verify the target database has the required properties.
    """

    required_properties: dict[str, str] = Field(
        default={
            "Title": "title",
            "Type": "select",
            "Status": "select",
            "Priority": "select",
            "Date": "date",
            "Tags": "multi_select",
            "Source": "rich_text",
            "Confidence": "number",
            "Summary": "rich_text",
            "Content": "rich_text",
        },
        description="Required properties with their types"
    )

    optional_properties: dict[str, str] = Field(
        default={
            "Participants": "multi_select",
            "Entities": "multi_select",
            "Related Pages": "relation",
            "Relevance Score": "number",
            "Processing Version": "rich_text",
            "Created At": "created_time",
            "Updated At": "last_edited_time",
        },
        description="Optional properties with their types"
    )

    def validate_database(
        self,
        database_properties: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate a Notion database has required properties.

        Args:
            database_properties: Properties from Notion database.retrieve()

        Returns:
            Tuple of (is_valid, list_of_missing_properties)
        """
        missing = []

        for prop_name, prop_type in self.required_properties.items():
            if prop_name not in database_properties:
                missing.append(f"{prop_name} ({prop_type})")
            elif database_properties[prop_name].get("type") != prop_type:
                actual_type = database_properties[prop_name].get("type")
                missing.append(
                    f"{prop_name} (expected {prop_type}, got {actual_type})"
                )

        return len(missing) == 0, missing
