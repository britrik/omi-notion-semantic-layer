"""
Data models for the OMI-to-Notion Semantic Intelligence Layer.

This package contains Pydantic models for:
- transcript: OMI transcript data structures
- insight: Processed insight and analysis results
- notion: Notion page property mappings
"""

from src.models.transcript import (
    Transcript,
    Segment,
    TranscriptMetadata,
)
from src.models.insight import (
    ProcessedInsight,
    Classification,
    Entity,
    EntityType,
    SentimentResult,
    IntentType,
    ContentCategory,
    PriorityLevel,
    InsightStatus,
)
from src.models.notion import (
    NotionPageProperties,
    NotionSelectOption,
    NotionMultiSelect,
)

__all__ = [
    # Transcript models
    "Transcript",
    "Segment",
    "TranscriptMetadata",
    # Insight models
    "ProcessedInsight",
    "Classification",
    "Entity",
    "EntityType",
    "SentimentResult",
    "IntentType",
    "ContentCategory",
    "PriorityLevel",
    "InsightStatus",
    # Notion models
    "NotionPageProperties",
    "NotionSelectOption",
    "NotionMultiSelect",
]
