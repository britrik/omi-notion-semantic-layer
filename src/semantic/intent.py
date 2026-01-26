"""
Intent detector for transcript analysis.

Classifies the primary intent of conversation segments into categories:
Informational, Actionable, Exploratory, Collaborative, Reflective.
"""

import logging
import re
from typing import Optional

from src.models.insight import IntentType

logger = logging.getLogger(__name__)


# Pattern-based intent detection rules
INTENT_PATTERNS: dict[IntentType, list[str]] = {
    IntentType.ACTIONABLE: [
        r"\b(need to|have to|must|should|will|going to|let's|let us)\b",
        r"\b(please|can you|could you|would you)\b",
        r"\b(do|complete|finish|submit|send|create|update|delete|fix|implement)\b",
        r"\b(action item|todo|task|assignment)\b",
        r"\b(by|before|deadline|due|asap)\b.*\b(date|time|day|week|month)\b",
    ],
    IntentType.INFORMATIONAL: [
        r"\b(is|are|was|were|has|have|had)\b.*\b(that|this|it|the)\b",
        r"\b(here's|here is|this is|that is|the)\b.*\b(information|data|result|answer)\b",
        r"\b(according to|based on|as per|per the)\b",
        r"\b(fyi|for your information|note that|keep in mind)\b",
        r"\b(update|status|report|summary)\b",
    ],
    IntentType.EXPLORATORY: [
        r"\b(what if|how about|maybe|perhaps|could we|might we)\b",
        r"\b(wondering|curious|thinking about|considering)\b",
        r"\b(explore|investigate|research|look into|try)\b",
        r"\b(option|alternative|possibility|idea)\b",
        r"^(what|how|why|when|where|who)\b.*\?$",
    ],
    IntentType.COLLABORATIVE: [
        r"\b(together|collaborate|work with|team up|join|partner)\b",
        r"\b(we should|we could|we can|we need|let's|let us)\b",
        r"\b(discuss|brainstorm|share|align|sync|meet)\b",
        r"\b(feedback|input|thoughts|opinion|review)\b",
        r"\b(agree|consensus|decision|vote)\b",
    ],
    IntentType.REFLECTIVE: [
        r"\b(learned|realized|noticed|observed|discovered)\b",
        r"\b(in hindsight|looking back|retrospect|reflection)\b",
        r"\b(should have|could have|would have)\b",
        r"\b(lesson|insight|takeaway|key learning)\b",
        r"\b(improvement|better|next time|going forward)\b",
    ],
}

# Weighted keywords for scoring each intent
INTENT_KEYWORDS: dict[IntentType, dict[str, float]] = {
    IntentType.ACTIONABLE: {
        "need": 1.5, "must": 2.0, "should": 1.0, "will": 0.8,
        "action": 2.0, "task": 1.5, "deadline": 1.5, "asap": 2.0,
        "complete": 1.5, "finish": 1.5, "submit": 1.5, "implement": 1.5,
    },
    IntentType.INFORMATIONAL: {
        "information": 1.5, "data": 1.0, "report": 1.5, "status": 1.5,
        "update": 1.0, "note": 1.0, "result": 1.0, "summary": 1.5,
        "fyi": 2.0, "context": 1.0, "background": 1.0,
    },
    IntentType.EXPLORATORY: {
        "explore": 1.5, "investigate": 1.5, "research": 1.5, "idea": 1.5,
        "option": 1.0, "alternative": 1.0, "possibility": 1.0,
        "wondering": 1.5, "curious": 1.5, "might": 0.8, "perhaps": 1.0,
    },
    IntentType.COLLABORATIVE: {
        "together": 2.0, "collaborate": 2.0, "team": 1.5, "discuss": 1.5,
        "share": 1.0, "feedback": 1.5, "input": 1.0, "align": 1.5,
        "brainstorm": 2.0, "meet": 1.0, "sync": 1.0,
    },
    IntentType.REFLECTIVE: {
        "learned": 2.0, "realized": 1.5, "lesson": 2.0, "insight": 1.5,
        "hindsight": 2.0, "retrospect": 2.0, "improvement": 1.5,
        "reflection": 2.0, "takeaway": 1.5, "observed": 1.0,
    },
}


class IntentDetector:
    """
    Detects the primary intent of text content.
    
    Uses a combination of pattern matching and keyword scoring
    to classify text into intent categories.
    """

    def __init__(
        self,
        pattern_weight: float = 0.6,
        keyword_weight: float = 0.4,
        min_confidence: float = 0.3,
    ) -> None:
        """
        Initialize the intent detector.

        Args:
            pattern_weight: Weight for pattern-based scoring (0.0-1.0)
            keyword_weight: Weight for keyword-based scoring (0.0-1.0)
            min_confidence: Minimum score to assign an intent
        """
        self.pattern_weight = pattern_weight
        self.keyword_weight = keyword_weight
        self.min_confidence = min_confidence

    def detect_intent(self, text: str) -> Optional[IntentType]:
        """
        Detect the primary intent of text.

        Args:
            text: Text to analyze

        Returns:
            Primary IntentType or None if no clear intent detected
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for intent detection")
            return None

        scores = self._score_all_intents(text)
        
        if not scores:
            return None

        # Get the highest scoring intent
        best_intent = max(scores, key=lambda i: scores[i])
        best_score = scores[best_intent]

        if best_score >= self.min_confidence:
            logger.debug(
                "Detected intent: %s (score: %.2f)",
                best_intent.value,
                best_score,
            )
            return best_intent

        logger.debug("No clear intent detected (best score: %.2f)", best_score)
        return None

    def detect_intent_with_confidence(
        self,
        text: str,
    ) -> tuple[Optional[IntentType], float]:
        """
        Detect intent with confidence score.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (IntentType or None, confidence score)
        """
        if not text or not text.strip():
            return None, 0.0

        scores = self._score_all_intents(text)
        
        if not scores:
            return None, 0.0

        best_intent = max(scores, key=lambda i: scores[i])
        best_score = scores[best_intent]

        if best_score >= self.min_confidence:
            return best_intent, best_score

        return None, best_score

    def get_all_intents(
        self,
        text: str,
        threshold: float = 0.2,
    ) -> list[tuple[IntentType, float]]:
        """
        Get all detected intents above threshold.

        Args:
            text: Text to analyze
            threshold: Minimum score threshold

        Returns:
            List of (IntentType, score) tuples, sorted by score descending
        """
        if not text or not text.strip():
            return []

        scores = self._score_all_intents(text)
        
        results = [
            (intent, score)
            for intent, score in scores.items()
            if score >= threshold
        ]
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results

    def _score_all_intents(self, text: str) -> dict[IntentType, float]:
        """Calculate scores for all intent types."""
        text_lower = text.lower()
        scores: dict[IntentType, float] = {}

        for intent_type in IntentType:
            pattern_score = self._score_patterns(text_lower, intent_type)
            keyword_score = self._score_keywords(text_lower, intent_type)
            
            # Combine scores with weights
            combined_score = (
                pattern_score * self.pattern_weight
                + keyword_score * self.keyword_weight
            )
            
            # Normalize to 0-1 range
            scores[intent_type] = min(1.0, combined_score)

        return scores

    def _score_patterns(self, text: str, intent_type: IntentType) -> float:
        """Score text based on pattern matches."""
        patterns = INTENT_PATTERNS.get(intent_type, [])
        
        if not patterns:
            return 0.0

        matches = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1

        # Normalize by number of patterns
        return min(1.0, matches / len(patterns) * 2)  # Multiply by 2 for sensitivity

    def _score_keywords(self, text: str, intent_type: IntentType) -> float:
        """Score text based on keyword presence and weights."""
        keywords = INTENT_KEYWORDS.get(intent_type, {})
        
        if not keywords:
            return 0.0

        total_weight = 0.0
        max_possible = sum(keywords.values())

        for keyword, weight in keywords.items():
            if keyword in text:
                total_weight += weight

        # Normalize to 0-1 range
        return min(1.0, total_weight / max_possible * 2) if max_possible > 0 else 0.0

    def is_actionable(self, text: str) -> bool:
        """
        Check if text contains actionable content.

        Args:
            text: Text to analyze

        Returns:
            True if the text is actionable
        """
        intent = self.detect_intent(text)
        return intent == IntentType.ACTIONABLE

    def is_question(self, text: str) -> bool:
        """
        Check if text is a question (exploratory intent).

        Args:
            text: Text to analyze

        Returns:
            True if the text is a question
        """
        # Quick check for question marks
        if "?" in text:
            return True

        intent = self.detect_intent(text)
        return intent == IntentType.EXPLORATORY

    def batch_detect(
        self,
        texts: list[str],
    ) -> list[Optional[IntentType]]:
        """
        Detect intents for multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of IntentType or None for each text
        """
        return [self.detect_intent(text) for text in texts]
