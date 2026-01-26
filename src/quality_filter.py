"""
Quality filter module for assessing and filtering processed insights.

Implements the quality scoring system and filtering logic based on
configurable thresholds to determine which insights should be synced.
"""

import re
from typing import Optional

from src.models.insight import (
    ContentCategory,
    Entity,
    EntityType,
    ProcessedInsight,
    QualityScore,
)
from src.utils.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class QualityFilter:
    """
    Assesses quality of processed insights and filters based on thresholds.

    Uses a weighted scoring formula to calculate relevance:
    - Information Density (25%): Unique concepts and entities per word
    - Actionability (20%): Presence of action items, deadlines, assignments
    - Novelty (20%): New information vs. repeated/common content
    - Clarity (15%): Clear structure, minimal ambiguity
    - Specificity (10%): Concrete details vs. vague statements
    - Temporal Relevance (10%): Time-sensitive information
    """

    def __init__(
        self,
        min_relevance_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        min_content_length: int = 20,
        max_noise_ratio: float = 0.7,
    ):
        """
        Initialize the quality filter.

        Args:
            min_relevance_score: Minimum score (0-10) to pass filter.
                                Defaults to config value.
            min_confidence: Minimum processing confidence. Defaults to config.
            min_content_length: Minimum content length in characters.
            max_noise_ratio: Maximum ratio of noise words to total words.
        """
        settings = get_settings()
        self.min_relevance_score = (
            min_relevance_score
            if min_relevance_score is not None
            else settings.processing.min_relevance_score
        )
        self.min_confidence = (
            min_confidence
            if min_confidence is not None
            else settings.processing.min_confidence_threshold
        )
        self.min_content_length = min_content_length
        self.max_noise_ratio = max_noise_ratio

        # Noise patterns that indicate low-value content
        self._noise_patterns = [
            r"\bum+\b",
            r"\buh+\b",
            r"\bah+\b",
            r"\bhmm+\b",
            r"\byeah+\b",
            r"\bokay+\b",
            r"\bright\b",
            r"\bso\b",
            r"\blike\b",
            r"\byou know\b",
            r"\bi mean\b",
            r"\bactually\b",
            r"\bbasically\b",
        ]
        self._noise_regex = re.compile(
            "|".join(self._noise_patterns), re.IGNORECASE
        )

        # Action indicators for actionability scoring
        self._action_indicators = [
            r"\bneed to\b",
            r"\bshould\b",
            r"\bmust\b",
            r"\bwill\b",
            r"\bhave to\b",
            r"\bgoing to\b",
            r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            r"\bby\s+(next|this)\s+(week|month)\b",
            r"\bdue\b",
            r"\bdeadline\b",
            r"\bfollow[\s-]?up\b",
            r"\bassign\w*\b",
            r"\baction\s+item\b",
            r"\bto[\s-]?do\b",
            r"\btask\b",
        ]
        self._action_regex = re.compile(
            "|".join(self._action_indicators), re.IGNORECASE
        )

        # Temporal indicators for time-sensitivity
        self._temporal_patterns = [
            r"\b(today|tomorrow|yesterday)\b",
            r"\b(this|next|last)\s+(week|month|quarter|year)\b",
            r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b(urgent|asap|immediately|soon)\b",
            r"\bq[1-4]\b",
        ]
        self._temporal_regex = re.compile(
            "|".join(self._temporal_patterns), re.IGNORECASE
        )

        # Specificity indicators
        self._specificity_patterns = [
            r"\b\d+\s*(percent|%|dollars|\$|hours|days|weeks|months)\b",
            r"\b(specifically|exactly|precisely)\b",
            r"\bversion\s+\d+",
            r"\b[A-Z]{2,}[-_]?\d+\b",  # Project codes like PROJ-123
        ]
        self._specificity_regex = re.compile(
            "|".join(self._specificity_patterns), re.IGNORECASE
        )

        logger.debug(
            f"QualityFilter initialized with min_relevance={self.min_relevance_score}, "
            f"min_confidence={self.min_confidence}"
        )

    def calculate_quality_score(self, insight: ProcessedInsight) -> QualityScore:
        """
        Calculate comprehensive quality scores for an insight.

        Args:
            insight: The processed insight to score.

        Returns:
            QualityScore with all component scores populated.
        """
        content = insight.original_content
        word_count = len(content.split())

        if word_count == 0:
            return QualityScore()

        # Calculate individual component scores
        info_density = self._score_information_density(insight, word_count)
        actionability = self._score_actionability(insight, content)
        novelty = self._score_novelty(insight, content)
        clarity = self._score_clarity(insight, content)
        specificity = self._score_specificity(insight, content)
        temporal = self._score_temporal_relevance(insight, content)

        score = QualityScore(
            information_density=info_density,
            actionability=actionability,
            novelty=novelty,
            clarity=clarity,
            specificity=specificity,
            temporal_relevance=temporal,
        )

        logger.debug(
            f"Quality scores for {insight.transcript_id}: "
            f"density={info_density:.2f}, action={actionability:.2f}, "
            f"novelty={novelty:.2f}, clarity={clarity:.2f}, "
            f"specificity={specificity:.2f}, temporal={temporal:.2f}, "
            f"total={score.total_score:.2f}"
        )

        return score

    def _score_information_density(
        self, insight: ProcessedInsight, word_count: int
    ) -> float:
        """
        Score information density based on entities and concepts per word.

        High scores indicate content-rich text with many meaningful entities.
        """
        if word_count == 0:
            return 0.0

        # Count unique entities
        unique_entities = len(set(insight.entities))

        # Count classifications
        classification_count = len(insight.classifications)

        # Calculate density: entities + classifications per 10 words
        density_ratio = (unique_entities + classification_count) / (word_count / 10)

        # Scale to 0-10, with 2+ entities per 10 words being excellent
        score = min(10.0, density_ratio * 5.0)

        # Boost for having diverse entity types
        entity_types = set(e.type for e in insight.entities)
        type_diversity_bonus = min(2.0, len(entity_types) * 0.5)

        return min(10.0, score + type_diversity_bonus)

    def _score_actionability(
        self, insight: ProcessedInsight, content: str
    ) -> float:
        """
        Score actionability based on action items and action language.

        High scores indicate content that requires or suggests actions.
        """
        score = 0.0

        # Direct action items are highly actionable
        action_item_score = min(5.0, len(insight.action_items) * 2.0)
        score += action_item_score

        # Check for action language in content
        action_matches = len(self._action_regex.findall(content))
        action_language_score = min(3.0, action_matches * 0.5)
        score += action_language_score

        # Boost for actionable categories
        actionable_categories = {
            ContentCategory.ACTION_ITEM,
            ContentCategory.DECISION,
        }
        if insight.primary_category in actionable_categories:
            score += 2.0

        # Check for dates (implied deadlines)
        date_entities = insight.get_entities_by_type(EntityType.DATE)
        if date_entities:
            score += min(1.0, len(date_entities) * 0.5)

        return min(10.0, score)

    def _score_novelty(self, insight: ProcessedInsight, content: str) -> float:
        """
        Score novelty based on unique information.

        This is a simplified implementation. A full version would compare
        against previously processed insights.
        """
        score = 5.0  # Start with neutral score

        # Penalize very short content (less likely to be novel)
        word_count = len(content.split())
        if word_count < 10:
            score -= 2.0
        elif word_count > 50:
            score += 1.0

        # Reward diverse entity types (indicates multi-faceted content)
        entity_types = set(e.type for e in insight.entities)
        score += min(2.0, len(entity_types) * 0.5)

        # Reward multiple classifications (content spans multiple categories)
        if len(insight.classifications) > 1:
            score += 1.0

        # Penalize common filler categories
        if insight.primary_category == ContentCategory.DISCUSSION:
            score -= 1.0

        # Reward ideas and insights (typically more novel)
        if insight.primary_category in {
            ContentCategory.IDEA,
            ContentCategory.INSIGHT,
        }:
            score += 1.5

        return max(0.0, min(10.0, score))

    def _score_clarity(self, insight: ProcessedInsight, content: str) -> float:
        """
        Score clarity based on structure and readability.

        High scores indicate well-structured, unambiguous content.
        """
        score = 7.0  # Start with good baseline

        # Penalize very long sentences (average > 30 words)
        sentences = content.split(".")
        if sentences:
            avg_sentence_length = len(content.split()) / max(1, len(sentences))
            if avg_sentence_length > 30:
                score -= 2.0
            elif avg_sentence_length < 15:
                score += 1.0

        # Penalize high noise ratio
        noise_matches = len(self._noise_regex.findall(content))
        word_count = len(content.split())
        if word_count > 0:
            noise_ratio = noise_matches / word_count
            if noise_ratio > 0.1:
                score -= min(3.0, noise_ratio * 10)

        # Reward having a clear summary
        if insight.summary and insight.summary.title:
            score += 1.0

        # Reward high classification confidence
        if insight.classifications:
            avg_confidence = sum(
                c.confidence for c in insight.classifications
            ) / len(insight.classifications)
            if avg_confidence > 0.8:
                score += 1.0
            elif avg_confidence < 0.5:
                score -= 1.0

        return max(0.0, min(10.0, score))

    def _score_specificity(
        self, insight: ProcessedInsight, content: str
    ) -> float:
        """
        Score specificity based on concrete details.

        High scores indicate content with specific, measurable details.
        """
        score = 5.0  # Start with neutral

        # Check for specific patterns (numbers, codes, etc.)
        specificity_matches = len(self._specificity_regex.findall(content))
        score += min(3.0, specificity_matches * 1.0)

        # Reward named entities (specific references)
        person_entities = insight.get_entities_by_type(EntityType.PERSON)
        org_entities = insight.get_entities_by_type(EntityType.ORGANIZATION)
        project_entities = insight.get_entities_by_type(EntityType.PROJECT)

        score += min(1.0, len(person_entities) * 0.3)
        score += min(1.0, len(org_entities) * 0.5)
        score += min(1.5, len(project_entities) * 0.75)

        return max(0.0, min(10.0, score))

    def _score_temporal_relevance(
        self, insight: ProcessedInsight, content: str
    ) -> float:
        """
        Score temporal relevance based on time-sensitive information.

        High scores indicate content with recent/upcoming dates or urgency.
        """
        score = 5.0  # Start with neutral

        # Check for temporal patterns
        temporal_matches = len(self._temporal_regex.findall(content))
        score += min(3.0, temporal_matches * 0.75)

        # Check for date/time entities
        date_entities = insight.get_entities_by_type(EntityType.DATE)
        time_entities = insight.get_entities_by_type(EntityType.TIME)
        score += min(2.0, (len(date_entities) + len(time_entities)) * 0.5)

        # Boost for urgency indicators in sentiment
        if insight.sentiment and insight.sentiment.urgency.value in {
            "high",
            "critical",
        }:
            score += 2.0

        return max(0.0, min(10.0, score))

    def check_completeness(self, insight: ProcessedInsight) -> tuple[bool, list[str]]:
        """
        Verify that an insight meets minimum quality standards.

        Args:
            insight: The insight to check.

        Returns:
            Tuple of (is_complete, list_of_issues).
        """
        issues = []

        # Check content length
        if len(insight.original_content) < self.min_content_length:
            issues.append(
                f"Content too short ({len(insight.original_content)} < {self.min_content_length})"
            )

        # Check for at least one classification
        if not insight.classifications:
            issues.append("No classifications found")

        # Check classification confidence
        if insight.classifications:
            max_confidence = max(c.confidence for c in insight.classifications)
            if max_confidence < self.min_confidence:
                issues.append(
                    f"Low classification confidence ({max_confidence:.2f} < {self.min_confidence})"
                )

        # Check for summary
        if not insight.summary or not insight.summary.title:
            issues.append("Missing summary title")

        return (len(issues) == 0, issues)

    def filter_noise(self, text: str) -> str:
        """
        Remove noise patterns from text.

        Args:
            text: The input text.

        Returns:
            Cleaned text with noise patterns removed.
        """
        cleaned = self._noise_regex.sub("", text)
        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def calculate_noise_ratio(self, text: str) -> float:
        """
        Calculate the ratio of noise words in text.

        Args:
            text: The input text.

        Returns:
            Ratio of noise words to total words (0.0 to 1.0).
        """
        words = text.split()
        if not words:
            return 0.0

        noise_count = len(self._noise_regex.findall(text))
        return min(1.0, noise_count / len(words))

    def should_sync(self, insight: ProcessedInsight) -> bool:
        """
        Determine if an insight should be synced to Notion.

        Args:
            insight: The processed insight.

        Returns:
            True if the insight passes all filters.
        """
        # Check completeness
        is_complete, issues = self.check_completeness(insight)
        if not is_complete:
            logger.debug(
                f"Insight {insight.transcript_id} failed completeness: {issues}"
            )
            return False

        # Check noise ratio
        noise_ratio = self.calculate_noise_ratio(insight.original_content)
        if noise_ratio > self.max_noise_ratio:
            logger.debug(
                f"Insight {insight.transcript_id} too noisy ({noise_ratio:.2f})"
            )
            return False

        # Check relevance score
        if insight.quality_score.total_score < self.min_relevance_score:
            logger.debug(
                f"Insight {insight.transcript_id} below threshold "
                f"({insight.quality_score.total_score:.2f} < {self.min_relevance_score})"
            )
            return False

        logger.info(
            f"Insight {insight.transcript_id} passed filter with "
            f"score {insight.quality_score.total_score:.2f}"
        )
        return True

    def assess(
        self, insight: ProcessedInsight, update_scores: bool = True
    ) -> dict:
        """
        Perform full quality assessment on an insight.

        Args:
            insight: The insight to assess.
            update_scores: Whether to update the insight's quality_score.

        Returns:
            Assessment results dictionary.
        """
        # Calculate quality score
        quality_score = self.calculate_quality_score(insight)

        if update_scores:
            insight.quality_score = quality_score

        # Check completeness
        is_complete, completeness_issues = self.check_completeness(insight)

        # Calculate noise ratio
        noise_ratio = self.calculate_noise_ratio(insight.original_content)

        # Determine if should sync
        should_sync = (
            is_complete
            and noise_ratio <= self.max_noise_ratio
            and quality_score.total_score >= self.min_relevance_score
        )

        return {
            "quality_score": quality_score,
            "total_score": quality_score.total_score,
            "is_complete": is_complete,
            "completeness_issues": completeness_issues,
            "noise_ratio": noise_ratio,
            "should_sync": should_sync,
            "sync_priority": (
                "high"
                if quality_score.total_score >= 7.0
                else "medium"
                if quality_score.total_score >= 5.0
                else "low"
                if quality_score.total_score >= 3.0
                else "none"
            ),
        }
