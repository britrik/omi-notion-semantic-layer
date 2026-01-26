"""
Tests for the quality filter module.

Tests quality scoring, completeness checking, noise filtering,
and sync decision logic.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.models.insight import (
    ActionItem,
    Classification,
    ContentCategory,
    Entity,
    EntityType,
    PriorityLevel,
    ProcessedInsight,
    QualityScore,
    SentimentResult,
    SentimentType,
    Summary,
    UrgencyLevel,
)
from src.quality_filter import QualityFilter


@pytest.fixture
def quality_filter():
    """Create a quality filter instance with default settings."""
    return QualityFilter(
        min_relevance_score=5.0,
        min_confidence=0.65,
        min_content_length=20,
        max_noise_ratio=0.7,
    )


@pytest.fixture
def sample_insight():
    """Create a sample processed insight for testing."""
    return ProcessedInsight(
        transcript_id="test_001",
        source_timestamp=datetime.now(timezone.utc),
        original_content="We need to finish the project by next Friday. John will handle the backend work.",
        classifications=[
            Classification(category=ContentCategory.ACTION_ITEM, confidence=0.85),
            Classification(category=ContentCategory.MEETING, confidence=0.65),
        ],
        primary_category=ContentCategory.ACTION_ITEM,
        entities=[
            Entity(text="next Friday", type=EntityType.DATE, confidence=0.95),
            Entity(text="John", type=EntityType.PERSON, confidence=0.90),
            Entity(text="backend work", type=EntityType.TOPIC, confidence=0.75),
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
        summary=Summary(
            title="Project deadline and assignment discussion",
            executive="Discussion about project deadline with John assigned to backend.",
        ),
        tags=["project", "deadline", "backend"],
        participants=["John"],
    )


@pytest.fixture
def low_quality_insight():
    """Create a low-quality insight for testing."""
    return ProcessedInsight(
        transcript_id="test_002",
        source_timestamp=datetime.now(timezone.utc),
        original_content="Um, yeah, so like, you know, basically, uh...",
        classifications=[
            Classification(category=ContentCategory.DISCUSSION, confidence=0.4),
        ],
        primary_category=ContentCategory.DISCUSSION,
        entities=[],
        summary=Summary(title="Filler conversation"),
    )


class TestQualityScoreCalculation:
    """Tests for quality score calculation."""

    def test_calculate_quality_score_high_quality(
        self, quality_filter, sample_insight
    ):
        """Test scoring of high-quality insight."""
        score = quality_filter.calculate_quality_score(sample_insight)

        assert isinstance(score, QualityScore)
        assert 0.0 <= score.information_density <= 10.0
        assert 0.0 <= score.actionability <= 10.0
        assert 0.0 <= score.novelty <= 10.0
        assert 0.0 <= score.clarity <= 10.0
        assert 0.0 <= score.specificity <= 10.0
        assert 0.0 <= score.temporal_relevance <= 10.0
        assert 0.0 <= score.total_score <= 10.0

    def test_calculate_quality_score_low_quality(
        self, quality_filter, low_quality_insight
    ):
        """Test scoring of low-quality insight."""
        score = quality_filter.calculate_quality_score(low_quality_insight)

        assert isinstance(score, QualityScore)
        # Low quality content should have lower overall score
        assert score.total_score < 5.0
        assert score.actionability < 3.0

    def test_calculate_quality_score_empty_content(self, quality_filter):
        """Test scoring with empty content."""
        insight = ProcessedInsight(
            transcript_id="empty",
            source_timestamp=datetime.now(timezone.utc),
            original_content="",
            summary=Summary(title="Empty"),
        )

        score = quality_filter.calculate_quality_score(insight)

        assert score.total_score == 0.0

    def test_information_density_scoring(self, quality_filter):
        """Test information density scoring with varied entity counts."""
        # High density: many entities in short text
        high_density = ProcessedInsight(
            transcript_id="high_density",
            source_timestamp=datetime.now(timezone.utc),
            original_content="John met with Acme Corp about Project Alpha on Monday.",
            entities=[
                Entity(text="John", type=EntityType.PERSON, confidence=0.9),
                Entity(text="Acme Corp", type=EntityType.ORGANIZATION, confidence=0.9),
                Entity(text="Project Alpha", type=EntityType.PROJECT, confidence=0.85),
                Entity(text="Monday", type=EntityType.DATE, confidence=0.95),
            ],
            classifications=[
                Classification(category=ContentCategory.MEETING, confidence=0.8),
            ],
            summary=Summary(title="Meeting"),
        )

        # Low density: few entities in longer text
        low_density = ProcessedInsight(
            transcript_id="low_density",
            source_timestamp=datetime.now(timezone.utc),
            original_content="We talked about things and stuff for a while and it was okay.",
            entities=[],
            classifications=[
                Classification(category=ContentCategory.DISCUSSION, confidence=0.6),
            ],
            summary=Summary(title="Discussion"),
        )

        high_score = quality_filter.calculate_quality_score(high_density)
        low_score = quality_filter.calculate_quality_score(low_density)

        assert high_score.information_density > low_score.information_density

    def test_actionability_scoring(self, quality_filter, sample_insight):
        """Test actionability scoring with action items."""
        score = quality_filter.calculate_quality_score(sample_insight)

        # Sample insight has action items and action language
        assert score.actionability >= 3.0

    def test_temporal_relevance_scoring(self, quality_filter):
        """Test temporal relevance scoring with dates."""
        time_sensitive = ProcessedInsight(
            transcript_id="time_sensitive",
            source_timestamp=datetime.now(timezone.utc),
            original_content="The deadline is tomorrow and we need to finish ASAP urgently.",
            entities=[
                Entity(text="tomorrow", type=EntityType.DATE, confidence=0.95),
            ],
            sentiment=SentimentResult(
                sentiment=SentimentType.NEUTRAL,
                score=0.0,
                urgency=UrgencyLevel.HIGH,
            ),
            summary=Summary(title="Urgent deadline"),
        )

        score = quality_filter.calculate_quality_score(time_sensitive)

        assert score.temporal_relevance >= 6.0


class TestCompletenessCheck:
    """Tests for completeness verification."""

    def test_check_completeness_valid(self, quality_filter, sample_insight):
        """Test completeness check on valid insight."""
        is_complete, issues = quality_filter.check_completeness(sample_insight)

        assert is_complete is True
        assert len(issues) == 0

    def test_check_completeness_short_content(self, quality_filter):
        """Test completeness check on short content."""
        short_insight = ProcessedInsight(
            transcript_id="short",
            source_timestamp=datetime.now(timezone.utc),
            original_content="Hi",
            summary=Summary(title="Short"),
        )

        is_complete, issues = quality_filter.check_completeness(short_insight)

        assert is_complete is False
        assert any("too short" in issue for issue in issues)

    def test_check_completeness_no_classifications(self, quality_filter):
        """Test completeness check with no classifications."""
        no_class = ProcessedInsight(
            transcript_id="no_class",
            source_timestamp=datetime.now(timezone.utc),
            original_content="This is some content without classifications.",
            classifications=[],
            summary=Summary(title="No classifications"),
        )

        is_complete, issues = quality_filter.check_completeness(no_class)

        assert is_complete is False
        assert any("No classifications" in issue for issue in issues)

    def test_check_completeness_low_confidence(self, quality_filter):
        """Test completeness check with low confidence classifications."""
        low_conf = ProcessedInsight(
            transcript_id="low_conf",
            source_timestamp=datetime.now(timezone.utc),
            original_content="This is some content with low confidence.",
            classifications=[
                Classification(category=ContentCategory.DISCUSSION, confidence=0.3),
            ],
            summary=Summary(title="Low confidence"),
        )

        is_complete, issues = quality_filter.check_completeness(low_conf)

        assert is_complete is False
        assert any("confidence" in issue.lower() for issue in issues)

    def test_check_completeness_no_summary(self, quality_filter):
        """Test completeness check without summary."""
        no_summary = ProcessedInsight(
            transcript_id="no_summary",
            source_timestamp=datetime.now(timezone.utc),
            original_content="This is content without a summary title.",
            classifications=[
                Classification(category=ContentCategory.DISCUSSION, confidence=0.8),
            ],
        )

        is_complete, issues = quality_filter.check_completeness(no_summary)

        assert is_complete is False
        assert any("summary" in issue.lower() for issue in issues)


class TestNoiseFiltering:
    """Tests for noise detection and filtering."""

    def test_filter_noise(self, quality_filter):
        """Test noise filtering removes filler words."""
        noisy_text = "Um, so like, you know, basically, uh, we should meet."
        cleaned = quality_filter.filter_noise(noisy_text)

        assert "um" not in cleaned.lower()
        assert "uh" not in cleaned.lower()
        assert "like" not in cleaned.lower()
        assert "should meet" in cleaned.lower()

    def test_calculate_noise_ratio_high(self, quality_filter):
        """Test noise ratio calculation on noisy text."""
        noisy_text = "Um yeah so like basically um uh you know"
        ratio = quality_filter.calculate_noise_ratio(noisy_text)

        assert ratio > 0.5

    def test_calculate_noise_ratio_low(self, quality_filter):
        """Test noise ratio calculation on clean text."""
        clean_text = "The project deadline is next Friday and we need to complete it."
        ratio = quality_filter.calculate_noise_ratio(clean_text)

        assert ratio < 0.2

    def test_calculate_noise_ratio_empty(self, quality_filter):
        """Test noise ratio on empty text."""
        ratio = quality_filter.calculate_noise_ratio("")

        assert ratio == 0.0


class TestShouldSync:
    """Tests for sync decision logic."""

    def test_should_sync_valid_insight(self, quality_filter, sample_insight):
        """Test sync decision for valid insight."""
        # First calculate and set quality score
        sample_insight.quality_score = quality_filter.calculate_quality_score(
            sample_insight
        )

        # Ensure score is above threshold
        sample_insight.quality_score = QualityScore(
            information_density=7.0,
            actionability=8.0,
            novelty=6.0,
            clarity=8.0,
            specificity=7.0,
            temporal_relevance=7.0,
        )

        should_sync = quality_filter.should_sync(sample_insight)

        assert should_sync is True

    def test_should_sync_low_quality(self, quality_filter, low_quality_insight):
        """Test sync decision for low quality insight."""
        low_quality_insight.quality_score = quality_filter.calculate_quality_score(
            low_quality_insight
        )

        should_sync = quality_filter.should_sync(low_quality_insight)

        assert should_sync is False

    def test_should_sync_too_noisy(self, quality_filter):
        """Test sync decision for very noisy content."""
        noisy = ProcessedInsight(
            transcript_id="noisy",
            source_timestamp=datetime.now(timezone.utc),
            original_content="Um um um yeah like basically uh you know so um yeah um",
            classifications=[
                Classification(category=ContentCategory.DISCUSSION, confidence=0.8),
            ],
            summary=Summary(title="Noisy"),
        )
        noisy.quality_score = QualityScore(
            information_density=6.0,
            actionability=6.0,
            novelty=6.0,
            clarity=6.0,
            specificity=6.0,
            temporal_relevance=6.0,
        )

        should_sync = quality_filter.should_sync(noisy)

        assert should_sync is False


class TestAssess:
    """Tests for full assessment."""

    def test_assess_updates_scores(self, quality_filter, sample_insight):
        """Test that assess updates insight's quality_score."""
        original_score = sample_insight.quality_score

        result = quality_filter.assess(sample_insight, update_scores=True)

        assert sample_insight.quality_score != original_score
        assert "quality_score" in result
        assert "should_sync" in result

    def test_assess_returns_complete_results(self, quality_filter, sample_insight):
        """Test that assess returns all expected fields."""
        result = quality_filter.assess(sample_insight)

        assert "quality_score" in result
        assert "total_score" in result
        assert "is_complete" in result
        assert "completeness_issues" in result
        assert "noise_ratio" in result
        assert "should_sync" in result
        assert "sync_priority" in result

    def test_assess_priority_levels(self, quality_filter):
        """Test sync priority level assignment."""
        high_priority = ProcessedInsight(
            transcript_id="high",
            source_timestamp=datetime.now(timezone.utc),
            original_content="Critical urgent deadline tomorrow must complete immediately.",
            classifications=[
                Classification(category=ContentCategory.ACTION_ITEM, confidence=0.9),
            ],
            summary=Summary(title="Critical"),
        )

        result = quality_filter.assess(high_priority)

        # Priority should be one of the expected values
        assert result["sync_priority"] in {"high", "medium", "low", "none"}
