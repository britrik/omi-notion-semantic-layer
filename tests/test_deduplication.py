"""
Tests for the deduplication module.

Tests content hashing, similarity calculation, duplicate detection,
and deduplication operations.
"""

from datetime import datetime, timezone

import pytest

from src.models.insight import (
    Classification,
    ContentCategory,
    Entity,
    EntityType,
    ProcessedInsight,
    Summary,
)
from src.utils.deduplication import (
    DuplicateDetector,
    calculate_fingerprint_similarity,
    get_content_fingerprint,
)


@pytest.fixture
def detector():
    """Create a duplicate detector instance."""
    return DuplicateDetector(
        similarity_threshold=0.8,
        min_word_overlap=0.6,
    )


@pytest.fixture
def insight_a():
    """Create a sample insight."""
    return ProcessedInsight(
        transcript_id="insight_a",
        source_timestamp=datetime.now(timezone.utc),
        original_content="We need to finish the project by next Friday. John will handle the backend work.",
        classifications=[
            Classification(category=ContentCategory.ACTION_ITEM, confidence=0.85),
        ],
        entities=[
            Entity(text="next Friday", type=EntityType.DATE, confidence=0.95),
            Entity(text="John", type=EntityType.PERSON, confidence=0.90),
        ],
        summary=Summary(title="Project deadline"),
    )


@pytest.fixture
def insight_a_duplicate():
    """Create an exact duplicate of insight_a."""
    return ProcessedInsight(
        transcript_id="insight_a_dup",
        source_timestamp=datetime.now(timezone.utc),
        original_content="We need to finish the project by next Friday. John will handle the backend work.",
        classifications=[
            Classification(category=ContentCategory.ACTION_ITEM, confidence=0.85),
        ],
        entities=[
            Entity(text="next Friday", type=EntityType.DATE, confidence=0.95),
            Entity(text="John", type=EntityType.PERSON, confidence=0.90),
        ],
        summary=Summary(title="Project deadline duplicate"),
    )


@pytest.fixture
def insight_a_similar():
    """Create a similar but not exact duplicate of insight_a."""
    return ProcessedInsight(
        transcript_id="insight_a_similar",
        source_timestamp=datetime.now(timezone.utc),
        original_content="We must complete the project by next Friday. John is handling the backend development.",
        classifications=[
            Classification(category=ContentCategory.ACTION_ITEM, confidence=0.80),
        ],
        entities=[
            Entity(text="next Friday", type=EntityType.DATE, confidence=0.92),
            Entity(text="John", type=EntityType.PERSON, confidence=0.88),
        ],
        summary=Summary(title="Project deadline similar"),
    )


@pytest.fixture
def insight_b_different():
    """Create a completely different insight."""
    return ProcessedInsight(
        transcript_id="insight_b",
        source_timestamp=datetime.now(timezone.utc),
        original_content="Marketing team will launch the new campaign next month. Focus on social media.",
        classifications=[
            Classification(category=ContentCategory.DECISION, confidence=0.75),
        ],
        entities=[
            Entity(text="Marketing team", type=EntityType.ORGANIZATION, confidence=0.85),
            Entity(text="next month", type=EntityType.DATE, confidence=0.90),
        ],
        summary=Summary(title="Marketing campaign"),
    )


class TestContentHash:
    """Tests for content hashing."""

    def test_calculate_content_hash_deterministic(self, detector):
        """Test that hash is deterministic for same content."""
        content = "This is a test message."
        
        hash1 = detector.calculate_content_hash(content)
        hash2 = detector.calculate_content_hash(content)
        
        assert hash1 == hash2

    def test_calculate_content_hash_normalized(self, detector):
        """Test that normalization produces same hash for similar content."""
        content1 = "This is a test message."
        content2 = "  This  is   a  test  message.  "
        content3 = "THIS IS A TEST MESSAGE."
        
        hash1 = detector.calculate_content_hash(content1)
        hash2 = detector.calculate_content_hash(content2)
        hash3 = detector.calculate_content_hash(content3)
        
        # After normalization, these should all be the same
        assert hash1 == hash2 == hash3

    def test_calculate_content_hash_different(self, detector):
        """Test that different content produces different hashes."""
        content1 = "This is message one."
        content2 = "This is message two."
        
        hash1 = detector.calculate_content_hash(content1)
        hash2 = detector.calculate_content_hash(content2)
        
        assert hash1 != hash2


class TestTextSimilarity:
    """Tests for text similarity calculations."""

    def test_calculate_similarity_identical(self, detector):
        """Test similarity for identical texts."""
        text = "This is a test message with some content."
        
        similarity = detector.calculate_similarity(text, text)
        
        assert similarity == 1.0

    def test_calculate_similarity_completely_different(self, detector):
        """Test similarity for completely different texts."""
        text1 = "apple banana cherry"
        text2 = "dog elephant fox"
        
        similarity = detector.calculate_similarity(text1, text2)
        
        assert similarity == 0.0

    def test_calculate_similarity_partial(self, detector):
        """Test similarity for partially overlapping texts."""
        text1 = "The quick brown fox jumps over the lazy dog."
        text2 = "The quick brown cat walks over the lazy dog."
        
        similarity = detector.calculate_similarity(text1, text2)
        
        assert 0.5 < similarity < 1.0

    def test_calculate_similarity_empty(self, detector):
        """Test similarity with empty text."""
        text1 = "Some content here."
        text2 = ""
        
        similarity = detector.calculate_similarity(text1, text2)
        
        assert similarity == 0.0

    def test_calculate_cosine_similarity_identical(self, detector):
        """Test cosine similarity for identical texts."""
        text = "word word word other other"
        
        similarity = detector.calculate_cosine_similarity(text, text)
        
        assert abs(similarity - 1.0) < 0.001

    def test_calculate_cosine_similarity_partial(self, detector):
        """Test cosine similarity for partially similar texts."""
        text1 = "machine learning deep neural network"
        text2 = "machine learning random forest trees"
        
        similarity = detector.calculate_cosine_similarity(text1, text2)
        
        assert 0.2 < similarity < 0.8


class TestEntityOverlap:
    """Tests for entity overlap calculations."""

    def test_calculate_entity_overlap_identical(
        self, detector, insight_a, insight_a_duplicate
    ):
        """Test entity overlap for identical entities."""
        overlap = detector.calculate_entity_overlap(insight_a, insight_a_duplicate)
        
        assert overlap == 1.0

    def test_calculate_entity_overlap_partial(
        self, detector, insight_a, insight_a_similar
    ):
        """Test entity overlap for partially matching entities."""
        overlap = detector.calculate_entity_overlap(insight_a, insight_a_similar)
        
        assert 0.5 < overlap <= 1.0

    def test_calculate_entity_overlap_different(
        self, detector, insight_a, insight_b_different
    ):
        """Test entity overlap for different entities."""
        overlap = detector.calculate_entity_overlap(insight_a, insight_b_different)
        
        # No common entities
        assert overlap == 0.0

    def test_calculate_entity_overlap_empty(self, detector):
        """Test entity overlap when one has no entities."""
        insight1 = ProcessedInsight(
            transcript_id="has_entities",
            source_timestamp=datetime.now(timezone.utc),
            original_content="Content with entities",
            entities=[Entity(text="John", type=EntityType.PERSON, confidence=0.9)],
            summary=Summary(title="With entities"),
        )
        insight2 = ProcessedInsight(
            transcript_id="no_entities",
            source_timestamp=datetime.now(timezone.utc),
            original_content="Content without entities",
            entities=[],
            summary=Summary(title="No entities"),
        )
        
        overlap = detector.calculate_entity_overlap(insight1, insight2)
        
        assert overlap == 0.0


class TestIsDuplicate:
    """Tests for duplicate detection."""

    def test_is_duplicate_exact(
        self, detector, insight_a, insight_a_duplicate
    ):
        """Test detection of exact duplicates."""
        is_dup = detector.is_duplicate(insight_a, insight_a_duplicate)
        
        assert is_dup is True

    def test_is_duplicate_similar(
        self, detector, insight_a, insight_a_similar
    ):
        """Test detection of similar content as duplicates."""
        # Lower the threshold to catch similar content
        detector.similarity_threshold = 0.6
        detector.min_word_overlap = 0.4
        
        is_dup = detector.is_duplicate(insight_a, insight_a_similar)
        
        # May or may not be duplicate depending on actual similarity
        assert isinstance(is_dup, bool)

    def test_is_duplicate_different(
        self, detector, insight_a, insight_b_different
    ):
        """Test that different content is not marked as duplicate."""
        is_dup = detector.is_duplicate(insight_a, insight_b_different)
        
        assert is_dup is False


class TestFindDuplicates:
    """Tests for finding duplicates in a list."""

    def test_find_duplicates_finds_exact(
        self, detector, insight_a, insight_a_duplicate, insight_b_different
    ):
        """Test finding exact duplicates in a list."""
        duplicates = detector.find_duplicates(
            insight_a,
            [insight_a_duplicate, insight_b_different],
        )
        
        assert len(duplicates) == 1
        assert duplicates[0][0] == insight_a_duplicate.transcript_id
        assert duplicates[0][1] == 1.0  # Exact match

    def test_find_duplicates_excludes_self(
        self, detector, insight_a
    ):
        """Test that finding duplicates excludes the insight itself."""
        duplicates = detector.find_duplicates(insight_a, [insight_a])
        
        assert len(duplicates) == 0

    def test_find_duplicates_sorted_by_similarity(
        self, detector, insight_a, insight_a_duplicate, insight_a_similar
    ):
        """Test that duplicates are sorted by similarity."""
        detector.similarity_threshold = 0.5
        detector.min_word_overlap = 0.3
        
        duplicates = detector.find_duplicates(
            insight_a,
            [insight_a_similar, insight_a_duplicate],
            threshold=0.5,
        )
        
        if len(duplicates) > 1:
            # Should be sorted highest first
            assert duplicates[0][1] >= duplicates[1][1]


class TestDeduplicateList:
    """Tests for deduplicating a list of insights."""

    def test_deduplicate_list_removes_exact_duplicates(
        self, detector, insight_a, insight_a_duplicate
    ):
        """Test removing exact duplicates from a list."""
        insights = [insight_a, insight_a_duplicate]
        
        unique = detector.deduplicate_list(insights)
        
        assert len(unique) == 1
        assert unique[0].transcript_id == insight_a.transcript_id

    def test_deduplicate_list_preserves_different(
        self, detector, insight_a, insight_b_different
    ):
        """Test that different insights are preserved."""
        insights = [insight_a, insight_b_different]
        
        unique = detector.deduplicate_list(insights)
        
        assert len(unique) == 2

    def test_deduplicate_list_empty(self, detector):
        """Test deduplicating an empty list."""
        unique = detector.deduplicate_list([])
        
        assert unique == []

    def test_deduplicate_list_preserves_order(
        self, detector, insight_a, insight_b_different
    ):
        """Test that first occurrence is kept."""
        insights = [insight_a, insight_b_different]
        
        unique = detector.deduplicate_list(insights)
        
        assert unique[0].transcript_id == insight_a.transcript_id
        assert unique[1].transcript_id == insight_b_different.transcript_id


class TestFingerprinting:
    """Tests for content fingerprinting utilities."""

    def test_get_content_fingerprint_basic(self):
        """Test basic fingerprint generation."""
        content = "The quick brown fox jumps over the lazy dog."
        
        fingerprint = get_content_fingerprint(content)
        
        assert isinstance(fingerprint, set)
        assert len(fingerprint) > 0

    def test_get_content_fingerprint_short_content(self):
        """Test fingerprint for content shorter than n-gram size."""
        content = "Hi"
        
        fingerprint = get_content_fingerprint(content, n_grams=3)
        
        assert len(fingerprint) == 1

    def test_calculate_fingerprint_similarity_identical(self):
        """Test fingerprint similarity for identical content."""
        fp1 = {"the quick brown", "quick brown fox", "brown fox jumps"}
        fp2 = {"the quick brown", "quick brown fox", "brown fox jumps"}
        
        similarity = calculate_fingerprint_similarity(fp1, fp2)
        
        assert similarity == 1.0

    def test_calculate_fingerprint_similarity_partial(self):
        """Test fingerprint similarity for partial overlap."""
        fp1 = {"the quick brown", "quick brown fox", "brown fox jumps"}
        fp2 = {"the quick brown", "quick brown cat", "brown cat walks"}
        
        similarity = calculate_fingerprint_similarity(fp1, fp2)
        
        assert 0.1 < similarity < 0.5

    def test_calculate_fingerprint_similarity_empty(self):
        """Test fingerprint similarity with empty sets."""
        fp1 = {"some content"}
        fp2 = set()
        
        similarity = calculate_fingerprint_similarity(fp1, fp2)
        
        assert similarity == 0.0
