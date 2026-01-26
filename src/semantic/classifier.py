"""
Content classifier for transcript analysis.

Uses zero-shot classification to categorize content into 8 categories:
Action Items, Insights, Decisions, Questions, Discussions, Knowledge, Ideas, Meetings.
"""

import logging
from functools import lru_cache
from typing import Optional

from src.models.insight import Classification, ContentCategory

logger = logging.getLogger(__name__)


# Category descriptions for zero-shot classification
CATEGORY_DESCRIPTIONS: dict[ContentCategory, str] = {
    ContentCategory.ACTION_ITEM: "task to do, action required, follow-up needed, assignment",
    ContentCategory.INSIGHT: "realization, discovery, observation, learning, understanding",
    ContentCategory.DECISION: "choice made, agreement reached, resolution, commitment",
    ContentCategory.QUESTION: "inquiry, uncertainty, request for information, clarification needed",
    ContentCategory.DISCUSSION: "conversation, debate, exchange of ideas, dialogue",
    ContentCategory.KNOWLEDGE: "fact, information, reference, documentation, explanation",
    ContentCategory.IDEA: "suggestion, proposal, concept, brainstorm, creative thought",
    ContentCategory.MEETING: "scheduled event, gathering, appointment, session, call",
}


class ContentClassifier:
    """
    Classifies text content into predefined categories.
    
    Uses transformers zero-shot classification for flexible, accurate categorization.
    Supports multi-label classification with confidence thresholds.
    """

    def __init__(
        self,
        model_name: str = "facebook/bart-large-mnli",
        confidence_threshold: float = 0.65,
        device: Optional[str] = None,
    ) -> None:
        """
        Initialize the classifier.

        Args:
            model_name: HuggingFace model for zero-shot classification
            confidence_threshold: Minimum confidence for classification (0.0-1.0)
            device: Device to run model on ('cpu', 'cuda', or None for auto)
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.device = device
        self._classifier: Optional[object] = None
        self._labels: list[str] = [cat.value for cat in ContentCategory]

    @property
    def classifier(self) -> object:
        """Lazy load the classification pipeline."""
        if self._classifier is None:
            self._classifier = self._load_classifier()
        return self._classifier

    def _load_classifier(self) -> object:
        """Load the zero-shot classification pipeline."""
        try:
            from transformers import pipeline

            logger.info("Loading classification model: %s", self.model_name)
            
            classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=self.device,
            )
            
            logger.info("Classification model loaded successfully")
            return classifier
            
        except Exception as e:
            logger.error("Failed to load classification model: %s", e)
            raise RuntimeError(f"Failed to load classifier: {e}") from e

    def classify(
        self,
        text: str,
        multi_label: bool = True,
        top_k: Optional[int] = None,
    ) -> list[Classification]:
        """
        Classify text into content categories.

        Args:
            text: Text to classify
            multi_label: Allow multiple category assignments
            top_k: Maximum number of classifications to return (None for all above threshold)

        Returns:
            List of Classification objects sorted by confidence (descending)
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for classification")
            return []

        text = text.strip()
        
        # Truncate very long texts to avoid memory issues
        max_length = 1024
        if len(text) > max_length:
            text = text[:max_length]
            logger.debug("Text truncated to %d characters for classification", max_length)

        try:
            result = self.classifier(
                text,
                self._labels,
                multi_label=multi_label,
            )

            classifications = []
            for label, score in zip(result["labels"], result["scores"]):
                if score >= self.confidence_threshold:
                    category = self._label_to_category(label)
                    if category:
                        classifications.append(
                            Classification(
                                category=category,
                                confidence=round(score, 4),
                            )
                        )

            # Sort by confidence descending
            classifications.sort(key=lambda c: c.confidence, reverse=True)

            # Apply top_k limit if specified
            if top_k is not None and top_k > 0:
                classifications = classifications[:top_k]

            logger.debug(
                "Classified text into %d categories (threshold: %.2f)",
                len(classifications),
                self.confidence_threshold,
            )

            return classifications

        except Exception as e:
            logger.error("Classification failed: %s", e)
            raise RuntimeError(f"Classification failed: {e}") from e

    def classify_with_hypothesis(
        self,
        text: str,
        hypothesis_template: str = "This text is about {}.",
    ) -> list[Classification]:
        """
        Classify using custom hypothesis template.

        Args:
            text: Text to classify
            hypothesis_template: Template with {} placeholder for category

        Returns:
            List of Classification objects
        """
        try:
            result = self.classifier(
                text,
                self._labels,
                hypothesis_template=hypothesis_template,
                multi_label=True,
            )

            classifications = []
            for label, score in zip(result["labels"], result["scores"]):
                if score >= self.confidence_threshold:
                    category = self._label_to_category(label)
                    if category:
                        classifications.append(
                            Classification(
                                category=category,
                                confidence=round(score, 4),
                            )
                        )

            classifications.sort(key=lambda c: c.confidence, reverse=True)
            return classifications

        except Exception as e:
            logger.error("Classification with hypothesis failed: %s", e)
            raise RuntimeError(f"Classification failed: {e}") from e

    def get_primary_category(
        self,
        text: str,
    ) -> Optional[ContentCategory]:
        """
        Get the single most likely category for text.

        Args:
            text: Text to classify

        Returns:
            Primary ContentCategory or None if no classification meets threshold
        """
        classifications = self.classify(text, multi_label=False, top_k=1)
        if classifications:
            return classifications[0].category
        return None

    def batch_classify(
        self,
        texts: list[str],
        multi_label: bool = True,
    ) -> list[list[Classification]]:
        """
        Classify multiple texts efficiently.

        Args:
            texts: List of texts to classify
            multi_label: Allow multiple category assignments

        Returns:
            List of classification lists, one per input text
        """
        if not texts:
            return []

        # Filter empty texts
        valid_texts = [t.strip() for t in texts if t and t.strip()]
        
        if not valid_texts:
            return [[] for _ in texts]

        try:
            results = self.classifier(
                valid_texts,
                self._labels,
                multi_label=multi_label,
            )

            # Handle single result vs list of results
            if isinstance(results, dict):
                results = [results]

            all_classifications = []
            result_idx = 0
            
            for text in texts:
                if not text or not text.strip():
                    all_classifications.append([])
                else:
                    result = results[result_idx]
                    result_idx += 1
                    
                    classifications = []
                    for label, score in zip(result["labels"], result["scores"]):
                        if score >= self.confidence_threshold:
                            category = self._label_to_category(label)
                            if category:
                                classifications.append(
                                    Classification(
                                        category=category,
                                        confidence=round(score, 4),
                                    )
                                )
                    
                    classifications.sort(key=lambda c: c.confidence, reverse=True)
                    all_classifications.append(classifications)

            return all_classifications

        except Exception as e:
            logger.error("Batch classification failed: %s", e)
            raise RuntimeError(f"Batch classification failed: {e}") from e

    @staticmethod
    @lru_cache(maxsize=16)
    def _label_to_category(label: str) -> Optional[ContentCategory]:
        """Convert label string to ContentCategory enum."""
        try:
            return ContentCategory(label)
        except ValueError:
            # Try matching by name
            for category in ContentCategory:
                if category.value.lower() == label.lower():
                    return category
            logger.warning("Unknown category label: %s", label)
            return None

    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._classifier is not None

    def unload(self) -> None:
        """Unload the model to free memory."""
        self._classifier = None
        logger.info("Classification model unloaded")
