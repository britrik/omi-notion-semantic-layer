"""
Enrichment module for adding metadata and enhancing processed insights.

Handles automatic generation of tags, priority assignment, relationship
mapping, and other metadata enrichment tasks.
"""

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from src.models.insight import (
    ContentCategory,
    Entity,
    EntityType,
    PriorityLevel,
    ProcessedInsight,
    UrgencyLevel,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EnrichmentModule:
    """
    Enriches processed insights with additional metadata.

    Adds auto-generated tags, calculates priority, maps relationships,
    and generates other metadata to enhance insight value.
    """

    def __init__(
        self,
        max_tags: int = 15,
        min_tag_relevance: float = 0.3,
    ):
        """
        Initialize the enrichment module.

        Args:
            max_tags: Maximum number of tags to generate.
            min_tag_relevance: Minimum relevance score for including a tag.
        """
        self.max_tags = max_tags
        self.min_tag_relevance = min_tag_relevance

        # Common stop words to exclude from tags
        self._stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "as", "is", "was", "are",
            "were", "been", "be", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must",
            "shall", "can", "need", "dare", "ought", "used", "it", "its",
            "that", "this", "these", "those", "i", "you", "he", "she", "we",
            "they", "what", "which", "who", "whom", "where", "when", "why",
            "how", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "just", "also", "now",
            "here", "there", "about", "after", "before", "between", "into",
            "through", "during", "under", "over", "again", "then", "once",
        }

        # Priority keywords by level
        self._priority_keywords = {
            PriorityLevel.CRITICAL: [
                "urgent", "critical", "emergency", "asap", "immediately",
                "blocker", "showstopper", "crisis",
            ],
            PriorityLevel.HIGH: [
                "important", "priority", "deadline", "due", "must",
                "required", "essential", "key", "major",
            ],
            PriorityLevel.MEDIUM: [
                "should", "need", "want", "plan", "schedule",
            ],
            PriorityLevel.LOW: [
                "maybe", "sometime", "eventually", "nice to have",
                "low priority", "when possible",
            ],
        }

        logger.debug(
            f"EnrichmentModule initialized with max_tags={max_tags}"
        )

    def generate_tags(self, insight: ProcessedInsight) -> list[str]:
        """
        Generate relevant tags from an insight.

        Tags are derived from:
        - Entity names (normalized)
        - Categories
        - Key topics from content
        - Intent and sentiment

        Args:
            insight: The insight to generate tags for.

        Returns:
            List of generated tags, sorted by relevance.
        """
        tag_scores: Counter[str] = Counter()

        # Add category-based tags
        if insight.primary_category:
            tag = self._normalize_tag(insight.primary_category.value)
            tag_scores[tag] += 1.0

        for classification in insight.classifications:
            tag = self._normalize_tag(classification.category.value)
            tag_scores[tag] += classification.confidence * 0.5

        # Add entity-based tags
        for entity in insight.entities:
            tag = self._normalize_tag(entity.text)
            if tag and len(tag) >= 2:
                # Weight by entity type importance
                weight = self._entity_tag_weight(entity.type)
                tag_scores[tag] += entity.confidence * weight

        # Add intent-based tag
        if insight.intent:
            tag = self._normalize_tag(insight.intent.value)
            tag_scores[tag] += 0.7

        # Add sentiment-based tags
        if insight.sentiment:
            if insight.sentiment.urgency in {UrgencyLevel.HIGH, UrgencyLevel.CRITICAL}:
                tag_scores["urgent"] += 0.8
            if insight.sentiment.emotional_tone:
                tag = self._normalize_tag(insight.sentiment.emotional_tone)
                tag_scores[tag] += 0.5

        # Extract key terms from content
        content_tags = self._extract_content_tags(insight.original_content)
        for tag, score in content_tags.items():
            tag_scores[tag] += score

        # Filter and sort tags
        filtered_tags = [
            tag for tag, score in tag_scores.items()
            if score >= self.min_tag_relevance
            and tag not in self._stop_words
            and len(tag) >= 2
        ]

        # Sort by score descending
        sorted_tags = sorted(
            filtered_tags,
            key=lambda t: tag_scores[t],
            reverse=True
        )

        result = sorted_tags[:self.max_tags]
        logger.debug(f"Generated {len(result)} tags for {insight.transcript_id}")
        return result

    def _normalize_tag(self, text: str) -> str:
        """Normalize text to a valid tag format."""
        tag = text.lower().strip()
        # Replace spaces and special chars with hyphens
        tag = re.sub(r"[^a-z0-9]+", "-", tag)
        # Remove leading/trailing hyphens
        tag = tag.strip("-")
        return tag

    def _entity_tag_weight(self, entity_type: EntityType) -> float:
        """Get the tag weight for an entity type."""
        weights = {
            EntityType.PROJECT: 1.0,
            EntityType.PRODUCT: 0.9,
            EntityType.TOPIC: 0.8,
            EntityType.ORGANIZATION: 0.7,
            EntityType.PERSON: 0.6,
            EntityType.EVENT: 0.6,
            EntityType.LOCATION: 0.4,
            EntityType.DATE: 0.3,
            EntityType.TIME: 0.2,
            EntityType.MONEY: 0.5,
            EntityType.PERCENT: 0.3,
        }
        return weights.get(entity_type, 0.5)

    def _extract_content_tags(self, content: str) -> dict[str, float]:
        """Extract potential tags from content using simple NLP."""
        tags: Counter[str] = Counter()

        # Extract words (simple tokenization with unicode support)
        words = re.findall(r"\b\w{3,}\b", content.lower(), re.UNICODE)

        # Count word frequencies
        word_freq = Counter(words)
        total_words = len(words)

        if total_words == 0:
            return {}

        # Score words by frequency and length
        for word, count in word_freq.items():
            if word in self._stop_words:
                continue

            # TF-based score
            tf_score = count / total_words

            # Length bonus (longer words often more specific)
            length_bonus = min(1.0, len(word) / 10)

            # Combined score
            score = tf_score * 10 + length_bonus * 0.3

            if score >= 0.1:
                tags[word] = score

        return dict(tags)

    def assign_priority(self, insight: ProcessedInsight) -> PriorityLevel:
        """
        Calculate priority level for an insight.

        Priority is based on:
        - Content category (action items are higher priority)
        - Urgency indicators
        - Time sensitivity
        - Quality score

        Args:
            insight: The insight to prioritize.

        Returns:
            Calculated priority level.
        """
        score = 0.0
        content_lower = insight.original_content.lower()

        # Check for priority keywords (highest priority level wins)
        keyword_found = False
        for level, keywords in self._priority_keywords.items():
            if keyword_found:
                break
            for keyword in keywords:
                if keyword in content_lower:
                    if level == PriorityLevel.CRITICAL:
                        score += 3.0
                    elif level == PriorityLevel.HIGH:
                        score += 2.0
                    elif level == PriorityLevel.MEDIUM:
                        score += 1.0
                    keyword_found = True
                    break  # Exit inner loop

        # Category-based priority boost
        category_boosts = {
            ContentCategory.ACTION_ITEM: 2.0,
            ContentCategory.DECISION: 1.5,
            ContentCategory.QUESTION: 1.0,
            ContentCategory.MEETING: 0.5,
            ContentCategory.INSIGHT: 0.5,
        }
        if insight.primary_category:
            score += category_boosts.get(insight.primary_category, 0.0)

        # Urgency boost from sentiment
        if insight.sentiment:
            urgency_boost = {
                UrgencyLevel.CRITICAL: 3.0,
                UrgencyLevel.HIGH: 2.0,
                UrgencyLevel.MEDIUM: 1.0,
                UrgencyLevel.LOW: 0.0,
            }
            score += urgency_boost.get(insight.sentiment.urgency, 0.0)

        # Quality score influence
        if insight.quality_score:
            if insight.quality_score.actionability >= 8.0:
                score += 1.5
            elif insight.quality_score.actionability >= 6.0:
                score += 0.75

        # Time-sensitive content boost
        date_entities = insight.get_entities_by_type(EntityType.DATE)
        if date_entities:
            score += min(1.5, len(date_entities) * 0.5)

        # Action items boost
        if insight.action_items:
            score += min(2.0, len(insight.action_items) * 0.5)

        # Map score to priority level
        if score >= 6.0:
            priority = PriorityLevel.CRITICAL
        elif score >= 4.0:
            priority = PriorityLevel.HIGH
        elif score >= 2.0:
            priority = PriorityLevel.MEDIUM
        else:
            priority = PriorityLevel.LOW

        logger.debug(
            f"Assigned priority {priority.value} to {insight.transcript_id} "
            f"(score: {score:.2f})"
        )
        return priority

    def generate_metadata(self, insight: ProcessedInsight) -> dict:
        """
        Generate additional metadata for an insight.

        Args:
            insight: The insight to generate metadata for.

        Returns:
            Dictionary of metadata fields.
        """
        metadata = {
            "word_count": len(insight.original_content.split()),
            "entity_count": len(insight.entities),
            "action_item_count": len(insight.action_items),
            "classification_count": len(insight.classifications),
            "participant_count": len(insight.participants),
            "tag_count": len(insight.tags),
        }

        # Entity type counts
        entity_counts = Counter(e.type.value for e in insight.entities)
        metadata["entity_types"] = dict(entity_counts)

        # Category distribution
        if insight.classifications:
            metadata["categories"] = {
                c.category.value: c.confidence
                for c in insight.classifications
            }

        # Time-based metadata
        metadata["processed_at"] = insight.processed_at.isoformat()
        metadata["source_date"] = insight.source_timestamp.date().isoformat()

        # Quality indicators
        if insight.quality_score:
            metadata["quality_total"] = round(
                insight.quality_score.total_score, 2
            )

        # Sentiment summary
        if insight.sentiment:
            metadata["sentiment"] = insight.sentiment.sentiment.value
            metadata["urgency"] = insight.sentiment.urgency.value

        logger.debug(f"Generated metadata for {insight.transcript_id}")
        return metadata

    def map_relationships(
        self,
        insight: ProcessedInsight,
        existing_insights: list[ProcessedInsight],
        similarity_threshold: float = 0.3,
    ) -> list[str]:
        """
        Find related insights based on entity and tag overlap.

        Args:
            insight: The insight to find relationships for.
            existing_insights: List of existing insights to compare against.
            similarity_threshold: Minimum similarity score to consider related.

        Returns:
            List of related insight IDs.
        """
        related_ids = []
        insight_tags = set(insight.tags)
        insight_entities = {
            (e.text.lower(), e.type) for e in insight.entities
        }

        for existing in existing_insights:
            if existing.transcript_id == insight.transcript_id:
                continue

            # Calculate tag overlap
            existing_tags = set(existing.tags)
            tag_overlap = len(insight_tags & existing_tags)
            tag_total = len(insight_tags | existing_tags)
            tag_similarity = tag_overlap / tag_total if tag_total > 0 else 0

            # Calculate entity overlap
            existing_entities = {
                (e.text.lower(), e.type) for e in existing.entities
            }
            entity_overlap = len(insight_entities & existing_entities)
            entity_total = len(insight_entities | existing_entities)
            entity_similarity = (
                entity_overlap / entity_total if entity_total > 0 else 0
            )

            # Category match bonus
            category_bonus = 0.1 if (
                insight.primary_category
                and insight.primary_category == existing.primary_category
            ) else 0

            # Combined similarity
            combined_similarity = (
                tag_similarity * 0.4
                + entity_similarity * 0.5
                + category_bonus
            )

            if combined_similarity >= similarity_threshold:
                related_ids.append(existing.transcript_id)
                logger.debug(
                    f"Found relationship: {insight.transcript_id} -> "
                    f"{existing.transcript_id} (similarity: {combined_similarity:.2f})"
                )

        return related_ids

    def enrich(
        self,
        insight: ProcessedInsight,
        existing_insights: Optional[list[ProcessedInsight]] = None,
    ) -> ProcessedInsight:
        """
        Perform full enrichment on an insight.

        This is the main entry point that applies all enrichment operations.

        Args:
            insight: The insight to enrich.
            existing_insights: Optional list of existing insights for
                             relationship mapping.

        Returns:
            The enriched insight (modified in place).
        """
        logger.info(f"Enriching insight {insight.transcript_id}")

        # Generate tags if not already set or empty
        if not insight.tags:
            insight.tags = self.generate_tags(insight)

        # Calculate priority
        insight.priority = self.assign_priority(insight)

        # Map relationships if existing insights provided
        if existing_insights:
            related = self.map_relationships(insight, existing_insights)
            insight.related_insight_ids.extend(related)
            # Deduplicate
            insight.related_insight_ids = list(set(insight.related_insight_ids))

        # Update processed timestamp
        insight.processed_at = datetime.now(timezone.utc)

        logger.info(
            f"Enrichment complete for {insight.transcript_id}: "
            f"{len(insight.tags)} tags, priority={insight.priority.value}, "
            f"{len(insight.related_insight_ids)} relationships"
        )

        return insight

    def extract_participants(self, insight: ProcessedInsight) -> list[str]:
        """
        Extract participant names from entities and content.

        Args:
            insight: The insight to extract participants from.

        Returns:
            List of participant names.
        """
        participants = set(insight.participants)

        # Add person entities
        for entity in insight.get_entities_by_type(EntityType.PERSON):
            name = entity.normalized or entity.text
            if name and len(name) >= 2:
                participants.add(name)

        return list(participants)
