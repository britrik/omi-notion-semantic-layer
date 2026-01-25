"""
Sentiment analyzer for transcript analysis.

Provides sentiment classification, urgency detection, and emotional tone analysis.
"""

import logging
import re
from typing import Optional

from src.models.insight import SentimentResult, SentimentType, UrgencyLevel

logger = logging.getLogger(__name__)


# Keywords indicating urgency
URGENCY_PATTERNS: dict[UrgencyLevel, list[str]] = {
    UrgencyLevel.CRITICAL: [
        r"\b(asap|urgent|emergency|critical|immediately|right now|crisis)\b",
        r"\b(must|have to|need to)\b.*\b(today|now|immediately)\b",
    ],
    UrgencyLevel.HIGH: [
        r"\b(important|priority|soon|quickly|deadline)\b",
        r"\b(by end of day|eod|by tomorrow|this week)\b",
    ],
    UrgencyLevel.MEDIUM: [
        r"\b(should|would like|plan to|intend to)\b",
        r"\b(next week|coming days|soon)\b",
    ],
}

# Keywords for emotional tone detection
EMOTIONAL_TONE_KEYWORDS: dict[str, list[str]] = {
    "confident": ["definitely", "certainly", "absolutely", "sure", "confident"],
    "uncertain": ["maybe", "perhaps", "might", "not sure", "uncertain", "possibly"],
    "frustrated": ["frustrated", "annoyed", "irritated", "problem", "issue", "failing"],
    "excited": ["excited", "thrilled", "great", "amazing", "awesome", "fantastic"],
    "concerned": ["worried", "concerned", "anxious", "nervous", "afraid"],
    "neutral": [],
}


class SentimentAnalyzer:
    """
    Analyzes sentiment, urgency, and emotional tone in text.
    
    Uses transformers for sentiment classification with additional
    rule-based analysis for urgency and tone detection.
    """

    def __init__(
        self,
        model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest",
        device: Optional[str] = None,
    ) -> None:
        """
        Initialize the sentiment analyzer.

        Args:
            model_name: HuggingFace model for sentiment analysis
            device: Device to run model on ('cpu', 'cuda', or None for auto)
        """
        self.model_name = model_name
        self.device = device
        self._analyzer: Optional[object] = None

    @property
    def analyzer(self) -> object:
        """Lazy load the sentiment analysis pipeline."""
        if self._analyzer is None:
            self._analyzer = self._load_analyzer()
        return self._analyzer

    def _load_analyzer(self) -> object:
        """Load the sentiment analysis pipeline."""
        try:
            from transformers import pipeline

            logger.info("Loading sentiment model: %s", self.model_name)
            
            analyzer = pipeline(
                "sentiment-analysis",
                model=self.model_name,
                device=self.device,
                top_k=None,  # Return all scores
            )
            
            logger.info("Sentiment model loaded successfully")
            return analyzer
            
        except Exception as e:
            logger.error("Failed to load sentiment model: %s", e)
            raise RuntimeError(f"Failed to load sentiment analyzer: {e}") from e

    def analyze(self, text: str) -> SentimentResult:
        """
        Perform full sentiment analysis on text.

        Args:
            text: Text to analyze

        Returns:
            SentimentResult with sentiment, score, confidence, tone, and urgency
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for sentiment analysis")
            return SentimentResult(
                sentiment=SentimentType.NEUTRAL,
                score=0.0,
                confidence=0.0,
            )

        text = text.strip()
        
        # Truncate long texts
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]

        try:
            # Get sentiment classification
            result = self.analyzer(text)
            
            # Parse model output
            sentiment, score, confidence = self._parse_sentiment_result(result)
            
            # Detect urgency and emotional tone
            urgency = self.detect_urgency(text)
            emotional_tone = self.detect_emotional_tone(text)

            return SentimentResult(
                sentiment=sentiment,
                score=score,
                confidence=confidence,
                emotional_tone=emotional_tone,
                urgency=urgency,
            )

        except Exception as e:
            logger.error("Sentiment analysis failed: %s", e)
            raise RuntimeError(f"Sentiment analysis failed: {e}") from e

    def _parse_sentiment_result(
        self,
        result: list[dict],
    ) -> tuple[SentimentType, float, float]:
        """Parse the raw model output into sentiment, score, and confidence."""
        if not result:
            return SentimentType.NEUTRAL, 0.0, 0.0

        # Result is a list of dicts with 'label' and 'score'
        # Handle both single-result and multi-result formats
        if isinstance(result[0], list):
            result = result[0]

        # Find the highest scoring label
        best_result = max(result, key=lambda x: x["score"])
        label = best_result["label"].lower()
        confidence = best_result["score"]

        # Map model labels to our sentiment types
        if "positive" in label or label in ("pos", "label_2"):
            sentiment = SentimentType.POSITIVE
            score = confidence
        elif "negative" in label or label in ("neg", "label_0"):
            sentiment = SentimentType.NEGATIVE
            score = -confidence
        else:
            sentiment = SentimentType.NEUTRAL
            score = 0.0

        return sentiment, round(score, 4), round(confidence, 4)

    def detect_urgency(self, text: str) -> UrgencyLevel:
        """
        Detect urgency level in text.

        Args:
            text: Text to analyze

        Returns:
            UrgencyLevel (CRITICAL, HIGH, MEDIUM, or LOW)
        """
        if not text:
            return UrgencyLevel.LOW

        text_lower = text.lower()

        # Check patterns from highest to lowest urgency
        for level in [UrgencyLevel.CRITICAL, UrgencyLevel.HIGH, UrgencyLevel.MEDIUM]:
            patterns = URGENCY_PATTERNS.get(level, [])
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    logger.debug("Detected urgency level: %s", level.value)
                    return level

        return UrgencyLevel.LOW

    def detect_emotional_tone(self, text: str) -> Optional[str]:
        """
        Detect the dominant emotional tone in text.

        Args:
            text: Text to analyze

        Returns:
            Emotional tone string or None if neutral
        """
        if not text:
            return None

        text_lower = text.lower()
        tone_scores: dict[str, int] = {}

        for tone, keywords in EMOTIONAL_TONE_KEYWORDS.items():
            if tone == "neutral":
                continue
            
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            
            if score > 0:
                tone_scores[tone] = score

        if not tone_scores:
            return None

        # Return the tone with highest keyword count
        dominant_tone = max(tone_scores, key=lambda t: tone_scores[t])
        logger.debug("Detected emotional tone: %s", dominant_tone)
        return dominant_tone

    def get_sentiment_label(self, text: str) -> str:
        """
        Get simple sentiment label for text.

        Args:
            text: Text to analyze

        Returns:
            'positive', 'neutral', or 'negative'
        """
        result = self.analyze(text)
        return result.sentiment.value

    def batch_analyze(self, texts: list[str]) -> list[SentimentResult]:
        """
        Analyze sentiment for multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of SentimentResult objects
        """
        if not texts:
            return []

        results = []
        for text in texts:
            try:
                results.append(self.analyze(text))
            except Exception as e:
                logger.warning("Failed to analyze text: %s", e)
                results.append(
                    SentimentResult(
                        sentiment=SentimentType.NEUTRAL,
                        score=0.0,
                        confidence=0.0,
                    )
                )

        return results

    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._analyzer is not None

    def unload(self) -> None:
        """Unload the model to free memory."""
        self._analyzer = None
        logger.info("Sentiment model unloaded")
