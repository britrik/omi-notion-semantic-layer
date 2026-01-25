"""
Data models for processed insights.

These models represent the output of semantic processing,
including classifications, entities, and enriched metadata.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field


class ContentCategory(str, Enum):
    """Categories for classifying transcript content."""

    ACTION_ITEM = "Action Item"
    INSIGHT = "Insight"
    DECISION = "Decision"
    QUESTION = "Question"
    DISCUSSION = "Discussion"
    KNOWLEDGE = "Knowledge"
    IDEA = "Idea"
    MEETING = "Meeting"


class EntityType(str, Enum):
    """Types of named entities that can be extracted."""

    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "GPE"
    DATE = "DATE"
    TIME = "TIME"
    TOPIC = "TOPIC"
    PROJECT = "PROJECT"
    PRODUCT = "PRODUCT"
    EVENT = "EVENT"
    MONEY = "MONEY"
    PERCENT = "PERCENT"


class IntentType(str, Enum):
    """Types of conversational intent."""

    INFORMATIONAL = "Informational"
    ACTIONABLE = "Actionable"
    EXPLORATORY = "Exploratory"
    COLLABORATIVE = "Collaborative"
    REFLECTIVE = "Reflective"


class SentimentType(str, Enum):
    """Sentiment classification."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class UrgencyLevel(str, Enum):
    """Urgency levels for content."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PriorityLevel(str, Enum):
    """Priority levels for insights."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class InsightStatus(str, Enum):
    """Status of an insight in the workflow."""

    NEW = "New"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


class Entity(BaseModel):
    """
    A named entity extracted from text.
    """

    text: str = Field(description="The entity text as it appears")
    type: EntityType = Field(description="Type of entity")
    normalized: Optional[str] = Field(
        default=None,
        description="Normalized/canonical form of the entity"
    )
    start_char: Optional[int] = Field(
        default=None,
        ge=0,
        description="Start character position in source text"
    )
    end_char: Optional[int] = Field(
        default=None,
        ge=0,
        description="End character position in source text"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional entity metadata"
    )

    def __hash__(self) -> int:
        """Allow entities to be used in sets."""
        return hash((self.text.lower(), self.type))

    def __eq__(self, other: object) -> bool:
        """Check equality based on text and type."""
        if not isinstance(other, Entity):
            return False
        return self.text.lower() == other.text.lower() and self.type == other.type


class Classification(BaseModel):
    """
    A content classification result.
    """

    category: ContentCategory = Field(description="The assigned category")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation for the classification"
    )


class SentimentResult(BaseModel):
    """
    Sentiment analysis result.
    """

    sentiment: SentimentType = Field(description="Overall sentiment")
    score: float = Field(
        ge=-1.0,
        le=1.0,
        description="Sentiment score (-1 to 1)"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Analysis confidence"
    )
    emotional_tone: Optional[str] = Field(
        default=None,
        description="Detected emotional tone (confident, uncertain, etc.)"
    )
    urgency: UrgencyLevel = Field(
        default=UrgencyLevel.LOW,
        description="Detected urgency level"
    )


class QualityScore(BaseModel):
    """
    Quality assessment scores for an insight.

    Based on the weighted scoring formula from the methodology.
    """

    information_density: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Information density score (weight: 25%)"
    )
    actionability: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Actionability score (weight: 20%)"
    )
    novelty: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Novelty score (weight: 20%)"
    )
    clarity: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Clarity score (weight: 15%)"
    )
    specificity: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Specificity score (weight: 10%)"
    )
    temporal_relevance: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Temporal relevance score (weight: 10%)"
    )

    @computed_field
    @property
    def total_score(self) -> float:
        """
        Calculate weighted total relevance score.

        Returns:
            Weighted score from 0.0 to 10.0
        """
        return (
            self.information_density * 0.25
            + self.actionability * 0.20
            + self.novelty * 0.20
            + self.clarity * 0.15
            + self.specificity * 0.10
            + self.temporal_relevance * 0.10
        )


class Summary(BaseModel):
    """
    Generated summaries at different lengths.
    """

    title: str = Field(
        max_length=100,
        description="One-liner title (max 100 chars)"
    )
    executive: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Executive summary (max 500 chars)"
    )
    detailed: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Detailed synopsis (max 2000 chars)"
    )


class ActionItem(BaseModel):
    """
    An action item extracted from the transcript.
    """

    description: str = Field(description="What needs to be done")
    assignee: Optional[str] = Field(
        default=None,
        description="Person responsible"
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="When it's due"
    )
    priority: PriorityLevel = Field(
        default=PriorityLevel.MEDIUM,
        description="Priority level"
    )
    completed: bool = Field(
        default=False,
        description="Whether the item is completed"
    )


class ProcessedInsight(BaseModel):
    """
    A fully processed insight ready for Notion.

    This is the primary output model of the semantic processing pipeline.
    """

    # Source information
    transcript_id: str = Field(description="Source transcript ID")
    source_timestamp: datetime = Field(description="Original conversation timestamp")

    # Classifications
    classifications: list[Classification] = Field(
        default_factory=list,
        description="Content classifications with confidence"
    )
    primary_category: Optional[ContentCategory] = Field(
        default=None,
        description="Primary content category"
    )

    # Extracted information
    entities: list[Entity] = Field(
        default_factory=list,
        description="Extracted named entities"
    )
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Extracted action items"
    )

    # Analysis results
    sentiment: Optional[SentimentResult] = Field(
        default=None,
        description="Sentiment analysis result"
    )
    intent: Optional[IntentType] = Field(
        default=None,
        description="Detected intent"
    )

    # Quality assessment
    quality_score: QualityScore = Field(
        default_factory=QualityScore,
        description="Quality assessment scores"
    )

    # Summaries
    summary: Optional[Summary] = Field(
        default=None,
        description="Generated summaries"
    )

    # Enriched metadata
    tags: list[str] = Field(
        default_factory=list,
        description="Auto-generated tags"
    )
    participants: list[str] = Field(
        default_factory=list,
        description="Conversation participants"
    )
    priority: PriorityLevel = Field(
        default=PriorityLevel.MEDIUM,
        description="Calculated priority"
    )
    status: InsightStatus = Field(
        default=InsightStatus.NEW,
        description="Workflow status"
    )

    # Content
    original_content: str = Field(description="Original transcript content")
    processed_content: Optional[str] = Field(
        default=None,
        description="Processed/cleaned content"
    )

    # Relationships
    related_insight_ids: list[str] = Field(
        default_factory=list,
        description="IDs of related insights"
    )

    # Processing metadata
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When processing completed"
    )
    processing_version: str = Field(
        default="1.0",
        description="Processing algorithm version"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Overall processing confidence"
    )

    @computed_field
    @property
    def relevance_score(self) -> float:
        """Get the overall relevance score."""
        return self.quality_score.total_score

    @property
    def should_sync(self) -> bool:
        """
        Determine if this insight should be synced to Notion.

        Based on minimum relevance score threshold (default 5.0).
        """
        return self.relevance_score >= 5.0

    @property
    def sync_priority(self) -> str:
        """
        Get sync priority based on relevance score.

        Returns:
            'high' (>= 7.0), 'medium' (5.0-6.9), 'low' (3.0-4.9), 'none' (< 3.0)
        """
        score = self.relevance_score
        if score >= 7.0:
            return "high"
        elif score >= 5.0:
            return "medium"
        elif score >= 3.0:
            return "low"
        return "none"

    def get_entities_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self.entities if e.type == entity_type]

    def get_top_tags(self, limit: int = 10) -> list[str]:
        """Get top tags, limited to specified count."""
        return self.tags[:limit]

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "transcript_id": "test_001",
                "source_timestamp": "2026-01-06T10:00:00Z",
                "classifications": [
                    {"category": "Action Item", "confidence": 0.85},
                    {"category": "Meeting", "confidence": 0.72},
                ],
                "primary_category": "Action Item",
                "entities": [
                    {"text": "next Friday", "type": "DATE", "confidence": 0.95},
                ],
                "quality_score": {
                    "information_density": 7.5,
                    "actionability": 8.0,
                    "novelty": 6.0,
                    "clarity": 8.5,
                    "specificity": 7.0,
                    "temporal_relevance": 9.0,
                },
                "summary": {
                    "title": "Project timeline discussion with deadline",
                },
                "tags": ["project", "deadline", "prototype"],
                "priority": "High",
                "original_content": "We need to finish the prototype by next Friday.",
            }
        }
