"""
Deduplication utilities for detecting duplicate insights.

Provides text similarity calculations and duplicate detection
to prevent redundant entries in Notion.
"""

import hashlib
import re
from collections import Counter
from typing import Optional

from src.models.insight import ProcessedInsight
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DuplicateDetector:
    """
    Detects duplicate or near-duplicate insights.

    Uses multiple similarity metrics:
    - Exact hash matching for identical content
    - Jaccard similarity for word overlap
    - Entity overlap for semantic similarity
    """

    def __init__(
        self,
        similarity_threshold: float = 0.8,
        min_word_overlap: float = 0.6,
    ):
        """
        Initialize the duplicate detector.

        Args:
            similarity_threshold: Overall similarity threshold for duplicates.
            min_word_overlap: Minimum word overlap ratio for consideration.
        """
        self.similarity_threshold = similarity_threshold
        self.min_word_overlap = min_word_overlap

        # Cache for content hashes
        self._hash_cache: dict[str, str] = {}

        logger.debug(
            f"DuplicateDetector initialized with threshold={similarity_threshold}"
        )

    def calculate_content_hash(self, content: str) -> str:
        """
        Calculate a normalized hash for content.

        Normalizes the content before hashing to catch near-duplicates
        that differ only in whitespace or case.

        Args:
            content: The text content to hash.

        Returns:
            SHA-256 hash of normalized content.
        """
        # Normalize content
        normalized = self._normalize_text(content)

        # Calculate hash
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        return content_hash

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        normalized = text.lower()
        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)
        # Remove punctuation except apostrophes in contractions
        normalized = re.sub(r"[^\w\s']", "", normalized)
        # Strip
        normalized = normalized.strip()
        return normalized

    def _get_word_set(self, text: str) -> set[str]:
        """Extract unique words from text."""
        normalized = self._normalize_text(text)
        words = set(normalized.split())
        return words

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts.

        Uses Jaccard similarity on word sets.

        Args:
            text1: First text to compare.
            text2: Second text to compare.

        Returns:
            Similarity score from 0.0 to 1.0.
        """
        words1 = self._get_word_set(text1)
        words2 = self._get_word_set(text2)

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        jaccard = intersection / union if union > 0 else 0.0

        return jaccard

    def calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts.

        Uses term frequency vectors.

        Args:
            text1: First text to compare.
            text2: Second text to compare.

        Returns:
            Cosine similarity from 0.0 to 1.0.
        """
        words1 = self._normalize_text(text1).split()
        words2 = self._normalize_text(text2).split()

        if not words1 or not words2:
            return 0.0

        # Build term frequency vectors
        counter1 = Counter(words1)
        counter2 = Counter(words2)

        # Get all unique terms
        all_terms = set(counter1.keys()) | set(counter2.keys())

        # Calculate dot product and magnitudes
        dot_product = sum(counter1[term] * counter2[term] for term in all_terms)

        magnitude1 = sum(count ** 2 for count in counter1.values()) ** 0.5
        magnitude2 = sum(count ** 2 for count in counter2.values()) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        cosine = dot_product / (magnitude1 * magnitude2)
        return cosine

    def calculate_entity_overlap(
        self,
        insight1: ProcessedInsight,
        insight2: ProcessedInsight,
    ) -> float:
        """
        Calculate entity overlap between two insights.

        Args:
            insight1: First insight to compare.
            insight2: Second insight to compare.

        Returns:
            Entity overlap ratio from 0.0 to 1.0.
        """
        entities1 = {(e.text.lower(), e.type) for e in insight1.entities}
        entities2 = {(e.text.lower(), e.type) for e in insight2.entities}

        if not entities1 or not entities2:
            return 0.0

        intersection = len(entities1 & entities2)
        union = len(entities1 | entities2)

        return intersection / union if union > 0 else 0.0

    def is_duplicate(self, insight1: ProcessedInsight, insight2: ProcessedInsight) -> bool:
        """
        Check if two insights are duplicates.

        Uses multiple similarity metrics with weighted combination.

        Args:
            insight1: First insight to compare.
            insight2: Second insight to compare.

        Returns:
            True if insights are considered duplicates.
        """
        # Quick check: exact hash match
        hash1 = self.calculate_content_hash(insight1.original_content)
        hash2 = self.calculate_content_hash(insight2.original_content)

        if hash1 == hash2:
            logger.debug(
                f"Exact duplicate found: {insight1.transcript_id} == {insight2.transcript_id}"
            )
            return True

        # Calculate text similarity
        text_similarity = self.calculate_similarity(
            insight1.original_content,
            insight2.original_content,
        )

        # Early exit if text is very different
        if text_similarity < self.min_word_overlap:
            return False

        # Calculate cosine similarity for more nuanced comparison
        cosine_similarity = self.calculate_cosine_similarity(
            insight1.original_content,
            insight2.original_content,
        )

        # Calculate entity overlap
        entity_overlap = self.calculate_entity_overlap(insight1, insight2)

        # Weighted combination
        combined_score = (
            text_similarity * 0.4
            + cosine_similarity * 0.4
            + entity_overlap * 0.2
        )

        is_dup = combined_score >= self.similarity_threshold

        if is_dup:
            logger.debug(
                f"Near-duplicate found: {insight1.transcript_id} ~ {insight2.transcript_id} "
                f"(score: {combined_score:.2f})"
            )

        return is_dup

    def find_duplicates(
        self,
        insight: ProcessedInsight,
        existing_insights: list[ProcessedInsight],
        threshold: Optional[float] = None,
    ) -> list[tuple[str, float]]:
        """
        Find potential duplicates among existing insights.

        Args:
            insight: The insight to check.
            existing_insights: List of existing insights to compare against.
            threshold: Optional custom similarity threshold.

        Returns:
            List of (transcript_id, similarity_score) tuples for duplicates.
        """
        threshold = threshold or self.similarity_threshold
        duplicates = []

        insight_hash = self.calculate_content_hash(insight.original_content)

        for existing in existing_insights:
            if existing.transcript_id == insight.transcript_id:
                continue

            # Check exact hash match
            existing_hash = self.calculate_content_hash(existing.original_content)
            if insight_hash == existing_hash:
                duplicates.append((existing.transcript_id, 1.0))
                continue

            # Calculate combined similarity
            text_sim = self.calculate_similarity(
                insight.original_content,
                existing.original_content,
            )

            if text_sim < self.min_word_overlap:
                continue

            cosine_sim = self.calculate_cosine_similarity(
                insight.original_content,
                existing.original_content,
            )

            entity_sim = self.calculate_entity_overlap(insight, existing)

            combined = text_sim * 0.4 + cosine_sim * 0.4 + entity_sim * 0.2

            if combined >= threshold:
                duplicates.append((existing.transcript_id, combined))

        # Sort by similarity (highest first)
        duplicates.sort(key=lambda x: x[1], reverse=True)

        if duplicates:
            logger.info(
                f"Found {len(duplicates)} potential duplicates for {insight.transcript_id}"
            )

        return duplicates

    def deduplicate_list(
        self,
        insights: list[ProcessedInsight],
    ) -> list[ProcessedInsight]:
        """
        Remove duplicates from a list of insights.

        Keeps the first occurrence of each unique insight.

        Args:
            insights: List of insights to deduplicate.

        Returns:
            Deduplicated list of insights.
        """
        if not insights:
            return []

        unique_insights = []
        seen_hashes = set()

        for insight in insights:
            content_hash = self.calculate_content_hash(insight.original_content)

            # Check exact duplicates
            if content_hash in seen_hashes:
                logger.debug(f"Removing exact duplicate: {insight.transcript_id}")
                continue

            # Check near-duplicates against already accepted insights
            is_near_dup = False
            for existing in unique_insights:
                if self.is_duplicate(insight, existing):
                    logger.debug(
                        f"Removing near-duplicate: {insight.transcript_id} ~ {existing.transcript_id}"
                    )
                    is_near_dup = True
                    break

            if not is_near_dup:
                unique_insights.append(insight)
                seen_hashes.add(content_hash)

        removed_count = len(insights) - len(unique_insights)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicates from {len(insights)} insights")

        return unique_insights


def get_content_fingerprint(content: str, n_grams: int = 3) -> set[str]:
    """
    Generate n-gram fingerprint for content.

    Useful for detecting similar content with different word order.

    Args:
        content: The text content.
        n_grams: Size of n-grams to generate.

    Returns:
        Set of n-gram fingerprints.
    """
    normalized = content.lower()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    words = normalized.split()

    if len(words) < n_grams:
        return {" ".join(words)}

    fingerprints = set()
    for i in range(len(words) - n_grams + 1):
        ngram = " ".join(words[i : i + n_grams])
        fingerprints.add(ngram)

    return fingerprints


def calculate_fingerprint_similarity(fp1: set[str], fp2: set[str]) -> float:
    """
    Calculate similarity between two fingerprint sets.

    Args:
        fp1: First fingerprint set.
        fp2: Second fingerprint set.

    Returns:
        Similarity ratio from 0.0 to 1.0.
    """
    if not fp1 or not fp2:
        return 0.0

    intersection = len(fp1 & fp2)
    union = len(fp1 | fp2)

    return intersection / union if union > 0 else 0.0
