"""
Tests for the enrichment module.

Tests tag generation, priority assignment, metadata generation,
and relationship mapping.
"""

from datetime import datetime, timezone

import pytest

from src.enrichment import EnrichmentModule
from src.models.insight import (
    ActionItem,
    Classification,
    ContentCategory,
    Entity,
    EntityType,
    IntentType,
    PriorityLevel,
    ProcessedInsight,
    QualityScore,
    SentimentResult,
    SentimentType,
    Summary,
    UrgencyLevel,
)


@pytest.fixture
def enrichment_module():
    """Create an enrichment module instance."""
    return EnrichmentModule(max_tags=15, min_tag_relevance=0.3)


@pytest.fixture
def sample_insight():
    """Create a sample processed insight for testing."""
    return ProcessedInsight(
        transcript_id="test_001",
        source_timestamp=datetime.now(timezone.utc),
        original_content="We need to finish the project by next Friday. John will handle the backend work for Acme Corp.",
        classifications=[
            Classification(category=ContentCategory.ACTION_ITEM, confidence=0.85),
            Classification(category=ContentCategory.MEETING, confidence=0.65),
        ],
        primary_category=ContentCategory.ACTION_ITEM,
        entities=[
            Entity(text="next Friday", type=EntityType.DATE, confidence=0.95),
            Entity(text="John", type=EntityType.PERSON, confidence=0.90),
            Entity(text="backend", type=EntityType.TOPIC, confidence=0.80),
            Entity(text="Acme Corp", type=EntityType.ORGANIZATION, confidence=0.85),
        ],
        action_items=[
            ActionItem(
                description="Finish the project",
                assignee="John",
                priority=PriorityLevel.HIGH,
            ),
        ],
        sentiment=SentimentResult(
            sentiment=SentimentType.NEUTRAL,
            score=0.1,
            urgency=UrgencyLevel.MEDIUM,
        ),
        intent=IntentType.ACTIONABLE,
        quality_score=QualityScore(
            information_density=7.0,
            actionability=8.0,
            novelty=6.0,
            clarity=8.0,
            specificity=7.0,
            temporal_relevance=7.0,
        ),
        summary=Summary(
            title="Project deadline discussion",
            executive="Discussion about project deadline with John assigned to backend work for Acme Corp.",
        ),
        participants=["John"],
    )


@pytest.fixture
def related_insight():
    """Create a related insight for testing relationship mapping."""
    return ProcessedInsight(
        transcript_id="test_002",
        source_timestamp=datetime.now(timezone.utc),
        original_content="John is making progress on the backend development for Acme Corp.",
        classifications=[
            Classification(category=ContentCategory.INSIGHT, confidence=0.75),
        ],
        primary_category=ContentCategory.INSIGHT,
        entities=[
            Entity(text="John", type=EntityType.PERSON, confidence=0.90),
            Entity(text="backend", type=EntityType.TOPIC, confidence=0.80),
            Entity(text="Acme Corp", type=EntityType.ORGANIZATION, confidence=0.85),
        ],
        summary=Summary(title="Backend progress update"),
        tags=["backend", "progress", "john", "acme-corp"],
    )


@pytest.fixture
def unrelated_insight():
    """Create an unrelated insight for testing."""
    return ProcessedInsight(
        transcript_id="test_003",
        source_timestamp=datetime.now(timezone.utc),
        original_content="Marketing team will launch the new campaign next month.",
        classifications=[
            Classification(category=ContentCategory.DECISION, confidence=0.80),
        ],
        primary_category=ContentCategory.DECISION,
        entities=[
            Entity(text="Marketing team", type=EntityType.ORGANIZATION, confidence=0.85),
            Entity(text="next month", type=EntityType.DATE, confidence=0.90),
        ],
        summary=Summary(title="Marketing campaign launch"),
        tags=["marketing", "campaign", "launch"],
    )


class TestTagGeneration:
    """Tests for tag generation."""

    def test_generate_tags_basic(self, enrichment_module, sample_insight):
        """Test basic tag generation."""
        tags = enrichment_module.generate_tags(sample_insight)

        assert isinstance(tags, list)
        assert len(tags) > 0
        assert len(tags) <= enrichment_module.max_tags

    def test_generate_tags_includes_category(self, enrichment_module, sample_insight):
        """Test that tags include category-based tags."""
        tags = enrichment_module.generate_tags(sample_insight)

        # Should include action-item tag
        assert any("action" in tag for tag in tags)

    def test_generate_tags_includes_entities(self, enrichment_module, sample_insight):
        """Test that tags include entity-based tags."""
        tags = enrichment_module.generate_tags(sample_insight)

        # Should include some entity-based tags
        entity_texts = [e.text.lower() for e in sample_insight.entities]
        has_entity_tag = any(
            any(part in tag for part in text.split())
            for tag in tags
            for text in entity_texts
        )
        assert has_entity_tag

    def test_generate_tags_normalized(self, enrichment_module, sample_insight):
        """Test that tags are properly normalized."""
        tags = enrichment_module.generate_tags(sample_insight)

        for tag in tags:
            # Tags should be lowercase
            assert tag == tag.lower()
            # Tags should not have leading/trailing hyphens
            assert not tag.startswith("-")
            assert not tag.endswith("-")
            # Tags should not have spaces
            assert " " not in tag

    def test_generate_tags_respects_max_limit(self, enrichment_module):
        """Test that tag generation respects max limit."""
        enrichment_module.max_tags = 5

        insight = ProcessedInsight(
            transcript_id="many_entities",
            source_timestamp=datetime.now(timezone.utc),
            original_content="John Mary Alice Bob Charlie Dave Eve Frank met at Acme Corp Microsoft Google Apple to discuss Project Alpha Beta Gamma.",
            entities=[
                Entity(text="John", type=EntityType.PERSON, confidence=0.9),
                Entity(text="Mary", type=EntityType.PERSON, confidence=0.9),
                Entity(text="Alice", type=EntityType.PERSON, confidence=0.9),
                Entity(text="Bob", type=EntityType.PERSON, confidence=0.9),
                Entity(text="Charlie", type=EntityType.PERSON, confidence=0.9),
                Entity(text="Acme Corp", type=EntityType.ORGANIZATION, confidence=0.9),
                Entity(text="Microsoft", type=EntityType.ORGANIZATION, confidence=0.9),
                Entity(text="Google", type=EntityType.ORGANIZATION, confidence=0.9),
                Entity(text="Project Alpha", type=EntityType.PROJECT, confidence=0.9),
                Entity(text="Project Beta", type=EntityType.PROJECT, confidence=0.9),
            ],
            classifications=[
                Classification(category=ContentCategory.MEETING, confidence=0.8),
            ],
            summary=Summary(title="Big meeting"),
        )

        tags = enrichment_module.generate_tags(insight)

        assert len(tags) <= 5

    def test_generate_tags_empty_insight(self, enrichment_module):
        """Test tag generation with empty insight."""
        empty_insight = ProcessedInsight(
            transcript_id="empty",
            source_timestamp=datetime.now(timezone.utc),
            original_content="",
            summary=Summary(title="Empty"),
        )

        tags = enrichment_module.generate_tags(empty_insight)

        # Should still return a list (possibly with category tag)
        assert isinstance(tags, list)


class TestPriorityAssignment:
    """Tests for priority assignment."""

    def test_assign_priority_high_urgency(self, enrichment_module):
        """Test priority assignment with high urgency keywords."""
        urgent_insight = ProcessedInsight(
            transcript_id="urgent",
            source_timestamp=datetime.now(timezone.utc),
            original_content="This is critical and needs immediate attention ASAP!",
            classifications=[
                Classification(category=ContentCategory.ACTION_ITEM, confidence=0.9),
            ],
            primary_category=ContentCategory.ACTION_ITEM,
            sentiment=SentimentResult(
                sentiment=SentimentType.NEUTRAL,
                score=0.0,
                urgency=UrgencyLevel.CRITICAL,
            ),
            summary=Summary(title="Critical"),
        )

        priority = enrichment_module.assign_priority(urgent_insight)

        assert priority in {PriorityLevel.HIGH, PriorityLevel.CRITICAL}

    def test_assign_priority_action_item_boost(self, enrichment_module):
        """Test priority boost for action items."""
        action_insight = ProcessedInsight(
            transcript_id="action",
            source_timestamp=datetime.now(timezone.utc),
            original_content="We need to review the document.",
            classifications=[
                Classification(category=ContentCategory.ACTION_ITEM, confidence=0.85),
            ],
            primary_category=ContentCategory.ACTION_ITEM,
            action_items=[
                ActionItem(description="Review document", priority=PriorityLevel.MEDIUM),
            ],
            summary=Summary(title="Review"),
        )

        discussion_insight = ProcessedInsight(
            transcript_id="discussion",
            source_timestamp=datetime.now(timezone.utc),
            original_content="We talked about various topics.",
            classifications=[
                Classification(category=ContentCategory.DISCUSSION, confidence=0.85),
            ],
            primary_category=ContentCategory.DISCUSSION,
            summary=Summary(title="Discussion"),
        )

        action_priority = enrichment_module.assign_priority(action_insight)
        discussion_priority = enrichment_module.assign_priority(discussion_insight)

        # Action item should have higher priority
        priority_order = [
            PriorityLevel.LOW,
            PriorityLevel.MEDIUM,
            PriorityLevel.HIGH,
            PriorityLevel.CRITICAL,
        ]
        action_idx = priority_order.index(action_priority)
        discussion_idx = priority_order.index(discussion_priority)

        assert action_idx >= discussion_idx

    def test_assign_priority_deadline_boost(self, enrichment_module):
        """Test priority boost for content with deadlines."""
        deadline_insight = ProcessedInsight(
            transcript_id="deadline",
            source_timestamp=datetime.now(timezone.utc),
            original_content="Must be completed by next Monday. It's due soon.",
            classifications=[
                Classification(category=ContentCategory.ACTION_ITEM, confidence=0.8),
            ],
            primary_category=ContentCategory.ACTION_ITEM,
            entities=[
                Entity(text="next Monday", type=EntityType.DATE, confidence=0.95),
            ],
            summary=Summary(title="Deadline"),
        )

        priority = enrichment_module.assign_priority(deadline_insight)

        assert priority in {PriorityLevel.MEDIUM, PriorityLevel.HIGH, PriorityLevel.CRITICAL}


class TestMetadataGeneration:
    """Tests for metadata generation."""

    def test_generate_metadata_basic(self, enrichment_module, sample_insight):
        """Test basic metadata generation."""
        metadata = enrichment_module.generate_metadata(sample_insight)

        assert isinstance(metadata, dict)
        assert "word_count" in metadata
        assert "entity_count" in metadata
        assert "action_item_count" in metadata

    def test_generate_metadata_word_count(self, enrichment_module, sample_insight):
        """Test word count in metadata."""
        metadata = enrichment_module.generate_metadata(sample_insight)

        expected_words = len(sample_insight.original_content.split())
        assert metadata["word_count"] == expected_words

    def test_generate_metadata_entity_types(self, enrichment_module, sample_insight):
        """Test entity type breakdown in metadata."""
        metadata = enrichment_module.generate_metadata(sample_insight)

        assert "entity_types" in metadata
        assert isinstance(metadata["entity_types"], dict)

    def test_generate_metadata_sentiment(self, enrichment_module, sample_insight):
        """Test sentiment info in metadata."""
        metadata = enrichment_module.generate_metadata(sample_insight)

        assert "sentiment" in metadata
        assert "urgency" in metadata

    def test_generate_metadata_dates(self, enrichment_module, sample_insight):
        """Test date fields in metadata."""
        metadata = enrichment_module.generate_metadata(sample_insight)

        assert "processed_at" in metadata
        assert "source_date" in metadata


class TestRelationshipMapping:
    """Tests for relationship mapping."""

    def test_map_relationships_finds_related(
        self, enrichment_module, sample_insight, related_insight
    ):
        """Test that relationship mapping finds related insights."""
        # Set tags on sample insight
        sample_insight.tags = ["action-item", "backend", "john", "acme-corp"]

        relationships = enrichment_module.map_relationships(
            sample_insight,
            [related_insight],
            similarity_threshold=0.2,
        )

        # Should find the related insight
        assert len(relationships) > 0
        assert related_insight.transcript_id in relationships

    def test_map_relationships_excludes_self(
        self, enrichment_module, sample_insight
    ):
        """Test that relationship mapping excludes self."""
        sample_insight.tags = ["test", "tags"]

        relationships = enrichment_module.map_relationships(
            sample_insight,
            [sample_insight],
            similarity_threshold=0.1,
        )

        assert sample_insight.transcript_id not in relationships

    def test_map_relationships_excludes_unrelated(
        self, enrichment_module, sample_insight, unrelated_insight
    ):
        """Test that relationship mapping excludes unrelated insights."""
        sample_insight.tags = ["backend", "john", "acme-corp"]

        relationships = enrichment_module.map_relationships(
            sample_insight,
            [unrelated_insight],
            similarity_threshold=0.5,  # Higher threshold
        )

        # Should not find unrelated insight (different entities/tags)
        assert unrelated_insight.transcript_id not in relationships


class TestEnrich:
    """Tests for the full enrichment pipeline."""

    def test_enrich_generates_tags(self, enrichment_module, sample_insight):
        """Test that enrich generates tags if not present."""
        sample_insight.tags = []

        enriched = enrichment_module.enrich(sample_insight)

        assert len(enriched.tags) > 0

    def test_enrich_sets_priority(self, enrichment_module, sample_insight):
        """Test that enrich sets priority."""
        enriched = enrichment_module.enrich(sample_insight)

        assert enriched.priority is not None
        assert isinstance(enriched.priority, PriorityLevel)

    def test_enrich_maps_relationships(
        self, enrichment_module, sample_insight, related_insight
    ):
        """Test that enrich maps relationships when existing insights provided."""
        sample_insight.tags = ["backend", "john", "acme-corp"]

        enriched = enrichment_module.enrich(
            sample_insight,
            existing_insights=[related_insight],
        )

        # May or may not find relationships depending on threshold
        assert isinstance(enriched.related_insight_ids, list)

    def test_enrich_updates_timestamp(self, enrichment_module, sample_insight):
        """Test that enrich updates processed timestamp."""
        original_time = sample_insight.processed_at

        enriched = enrichment_module.enrich(sample_insight)

        # Timestamp should be updated
        assert enriched.processed_at >= original_time

    def test_enrich_preserves_existing_tags(self, enrichment_module, sample_insight):
        """Test that enrich preserves existing tags."""
        sample_insight.tags = ["existing", "tags"]

        enriched = enrichment_module.enrich(sample_insight)

        # Should preserve existing tags (since tags were not empty)
        assert "existing" in enriched.tags
        assert "tags" in enriched.tags


class TestExtractParticipants:
    """Tests for participant extraction."""

    def test_extract_participants_from_entities(
        self, enrichment_module, sample_insight
    ):
        """Test extracting participants from person entities."""
        participants = enrichment_module.extract_participants(sample_insight)

        assert "John" in participants

    def test_extract_participants_preserves_existing(
        self, enrichment_module, sample_insight
    ):
        """Test that existing participants are preserved."""
        sample_insight.participants = ["Existing Participant"]

        participants = enrichment_module.extract_participants(sample_insight)

        assert "Existing Participant" in participants
        assert "John" in participants

    def test_extract_participants_empty(self, enrichment_module):
        """Test extracting participants when none exist."""
        empty_insight = ProcessedInsight(
            transcript_id="empty",
            source_timestamp=datetime.now(timezone.utc),
            original_content="No participants mentioned.",
            summary=Summary(title="Empty"),
        )

        participants = enrichment_module.extract_participants(empty_insight)

        assert isinstance(participants, list)
