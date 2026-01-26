"""
Semantic processor facade.

Orchestrates all semantic analysis components to transform
raw transcripts into processed insights.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.models.insight import (
    Classification,
    ContentCategory,
    Entity,
    IntentType,
    ProcessedInsight,
    QualityScore,
    SentimentResult,
    Summary,
)
from src.models.transcript import Transcript
from src.semantic.classifier import ContentClassifier
from src.semantic.entity_extractor import EntityExtractor
from src.semantic.intent import IntentDetector
from src.semantic.sentiment import SentimentAnalyzer
from src.semantic.summarizer import Summarizer

logger = logging.getLogger(__name__)


class SemanticProcessor:
    """
    Orchestrates semantic analysis of transcripts.
    
    Coordinates classifier, entity extractor, sentiment analyzer,
    intent detector, and summarizer to produce ProcessedInsight objects.
    
    Supports lazy loading of models and caching for efficiency.
    """

    def __init__(
        self,
        classifier_model: str = "facebook/bart-large-mnli",
        spacy_model: str = "en_core_web_lg",
        sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest",
        summarizer_model: str = "facebook/bart-large-cnn",
        device: Optional[str] = None,
        confidence_threshold: float = 0.65,
    ) -> None:
        """
        Initialize the semantic processor.

        Args:
            classifier_model: Model for content classification
            spacy_model: SpaCy model for entity extraction
            sentiment_model: Model for sentiment analysis
            summarizer_model: Model for summarization
            device: Device for ML models ('cpu', 'cuda', or None for auto)
            confidence_threshold: Minimum confidence for classifications
        """
        self.device = device
        self.confidence_threshold = confidence_threshold
        
        # Lazy-loaded components
        self._classifier: Optional[ContentClassifier] = None
        self._entity_extractor: Optional[EntityExtractor] = None
        self._sentiment_analyzer: Optional[SentimentAnalyzer] = None
        self._intent_detector: Optional[IntentDetector] = None
        self._summarizer: Optional[Summarizer] = None
        
        # Model configurations
        self._classifier_model = classifier_model
        self._spacy_model = spacy_model
        self._sentiment_model = sentiment_model
        self._summarizer_model = summarizer_model
        
        # Processing cache
        self._cache: dict[str, ProcessedInsight] = {}
        self._cache_enabled = True

    @property
    def classifier(self) -> ContentClassifier:
        """Lazy load the content classifier."""
        if self._classifier is None:
            self._classifier = ContentClassifier(
                model_name=self._classifier_model,
                confidence_threshold=self.confidence_threshold,
                device=self.device,
            )
        return self._classifier

    @property
    def entity_extractor(self) -> EntityExtractor:
        """Lazy load the entity extractor."""
        if self._entity_extractor is None:
            self._entity_extractor = EntityExtractor(
                model_name=self._spacy_model,
            )
        return self._entity_extractor

    @property
    def sentiment_analyzer(self) -> SentimentAnalyzer:
        """Lazy load the sentiment analyzer."""
        if self._sentiment_analyzer is None:
            self._sentiment_analyzer = SentimentAnalyzer(
                model_name=self._sentiment_model,
                device=self.device,
            )
        return self._sentiment_analyzer

    @property
    def intent_detector(self) -> IntentDetector:
        """Lazy load the intent detector."""
        if self._intent_detector is None:
            self._intent_detector = IntentDetector()
        return self._intent_detector

    @property
    def summarizer(self) -> Summarizer:
        """Lazy load the summarizer."""
        if self._summarizer is None:
            self._summarizer = Summarizer(
                model_name=self._summarizer_model,
                device=self.device,
            )
        return self._summarizer

    def process(
        self,
        transcript: Transcript,
        use_cache: bool = True,
    ) -> ProcessedInsight:
        """
        Perform full semantic analysis on a transcript.

        Args:
            transcript: Transcript to process
            use_cache: Use cached result if available

        Returns:
            ProcessedInsight with all extracted data
        """
        # Check cache
        cache_key = transcript.transcript_id
        if use_cache and self._cache_enabled and cache_key in self._cache:
            logger.debug("Using cached result for transcript %s", cache_key)
            return self._cache[cache_key]

        logger.info("Processing transcript %s", transcript.transcript_id)
        start_time = datetime.now(timezone.utc)

        try:
            content = transcript.content
            
            # Run all analysis components
            classifications = self._classify_content(content)
            primary_category = self._get_primary_category(classifications)
            entities = self._extract_entities(content)
            sentiment = self._analyze_sentiment(content)
            intent = self._detect_intent(content)
            summary = self._generate_summary(content)
            
            # Extract participants from transcript or entities
            participants = self._extract_participants(transcript, entities)
            
            # Generate tags from entities and content
            tags = self._generate_tags(entities, classifications)
            
            # Calculate initial quality score (basic metrics)
            quality_score = self._calculate_quality_score(
                content, classifications, entities
            )
            
            # Build processed insight
            insight = ProcessedInsight(
                transcript_id=transcript.transcript_id,
                source_timestamp=transcript.timestamp,
                classifications=classifications,
                primary_category=primary_category,
                entities=entities,
                sentiment=sentiment,
                intent=intent,
                quality_score=quality_score,
                summary=summary,
                tags=tags,
                participants=participants,
                original_content=content,
                processed_content=content,  # Could be cleaned version
                processed_at=datetime.now(timezone.utc),
            )
            
            # Calculate processing time
            processing_time = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds()
            
            logger.info(
                "Processed transcript %s in %.2f seconds",
                transcript.transcript_id,
                processing_time,
            )
            
            # Cache result
            if self._cache_enabled:
                self._cache[cache_key] = insight
            
            return insight

        except Exception as e:
            logger.error(
                "Failed to process transcript %s: %s",
                transcript.transcript_id,
                e,
            )
            raise RuntimeError(f"Semantic processing failed: {e}") from e

    def process_text(self, text: str, transcript_id: str = "manual") -> ProcessedInsight:
        """
        Process raw text without a full Transcript object.

        Args:
            text: Text content to process
            transcript_id: Identifier for the text

        Returns:
            ProcessedInsight with all extracted data
        """
        transcript = Transcript(
            transcript_id=transcript_id,
            timestamp=datetime.now(timezone.utc),
            duration=0.0,
            content=text,
        )
        return self.process(transcript, use_cache=False)

    def _classify_content(self, content: str) -> list[Classification]:
        """Classify content into categories."""
        try:
            return self.classifier.classify(content)
        except Exception as e:
            logger.warning("Classification failed: %s", e)
            return []

    def _get_primary_category(
        self,
        classifications: list[Classification],
    ) -> Optional[ContentCategory]:
        """Get the primary category from classifications."""
        if classifications:
            return classifications[0].category
        return None

    def _extract_entities(self, content: str) -> list[Entity]:
        """Extract named entities from content."""
        try:
            return self.entity_extractor.extract_entities(content)
        except Exception as e:
            logger.warning("Entity extraction failed: %s", e)
            return []

    def _analyze_sentiment(self, content: str) -> Optional[SentimentResult]:
        """Analyze sentiment of content."""
        try:
            return self.sentiment_analyzer.analyze(content)
        except Exception as e:
            logger.warning("Sentiment analysis failed: %s", e)
            return None

    def _detect_intent(self, content: str) -> Optional[IntentType]:
        """Detect primary intent of content."""
        try:
            return self.intent_detector.detect_intent(content)
        except Exception as e:
            logger.warning("Intent detection failed: %s", e)
            return None

    def _generate_summary(self, content: str) -> Optional[Summary]:
        """Generate summaries of content."""
        try:
            return self.summarizer.summarize(content)
        except Exception as e:
            logger.warning("Summarization failed: %s", e)
            return None

    def _extract_participants(
        self,
        transcript: Transcript,
        entities: list[Entity],
    ) -> list[str]:
        """Extract participant names from transcript and entities."""
        participants = set(transcript.participants)
        
        # Add speakers from segments
        for segment in transcript.segments:
            participants.add(segment.speaker)
        
        # Add person entities
        from src.models.insight import EntityType
        for entity in entities:
            if entity.type == EntityType.PERSON:
                participants.add(entity.normalized or entity.text)
        
        return list(participants)

    def _generate_tags(
        self,
        entities: list[Entity],
        classifications: list[Classification],
    ) -> list[str]:
        """Generate tags from entities and classifications."""
        tags = set()
        
        # Add category names as tags
        for classification in classifications:
            tags.add(classification.category.value.lower().replace(" ", "-"))
        
        # Add topic entities as tags
        from src.models.insight import EntityType
        for entity in entities:
            if entity.type in (EntityType.TOPIC, EntityType.PROJECT):
                tag = (entity.normalized or entity.text).lower()
                if len(tag) >= 3:  # Skip very short tags
                    tags.add(tag)
        
        return list(tags)[:20]  # Limit to 20 tags

    def _calculate_quality_score(
        self,
        content: str,
        classifications: list[Classification],
        entities: list[Entity],
    ) -> QualityScore:
        """Calculate initial quality score based on content analysis."""
        # Information density: based on entities and word count
        word_count = len(content.split())
        entity_count = len(entities)
        info_density = min(10.0, (entity_count / max(1, word_count / 50)) * 5 + 3)
        
        # Actionability: based on classification confidence for actionable categories
        actionability = 3.0
        for classification in classifications:
            if classification.category in (
                ContentCategory.ACTION_ITEM,
                ContentCategory.DECISION,
            ):
                actionability = max(actionability, classification.confidence * 10)
        
        # Clarity: based on average sentence length
        sentences = content.split(".")
        avg_sentence_len = word_count / max(1, len(sentences))
        clarity = 10.0 - min(5.0, abs(avg_sentence_len - 15) / 3)
        
        # Specificity: based on entity count
        specificity = min(10.0, entity_count * 2)
        
        # Novelty and temporal relevance: default values
        novelty = 5.0
        temporal_relevance = 7.0
        
        return QualityScore(
            information_density=round(info_density, 2),
            actionability=round(actionability, 2),
            novelty=round(novelty, 2),
            clarity=round(clarity, 2),
            specificity=round(specificity, 2),
            temporal_relevance=round(temporal_relevance, 2),
        )

    def batch_process(
        self,
        transcripts: list[Transcript],
    ) -> list[ProcessedInsight]:
        """
        Process multiple transcripts.

        Args:
            transcripts: List of transcripts to process

        Returns:
            List of ProcessedInsight objects
        """
        results = []
        for transcript in transcripts:
            try:
                result = self.process(transcript)
                results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to process transcript %s: %s",
                    transcript.transcript_id,
                    e,
                )
        return results

    def clear_cache(self) -> None:
        """Clear the processing cache."""
        self._cache.clear()
        logger.info("Processing cache cleared")

    def set_cache_enabled(self, enabled: bool) -> None:
        """Enable or disable caching."""
        self._cache_enabled = enabled
        logger.info("Caching %s", "enabled" if enabled else "disabled")

    def unload_models(self) -> None:
        """Unload all models to free memory."""
        if self._classifier:
            self._classifier.unload()
            self._classifier = None
        if self._entity_extractor:
            self._entity_extractor.unload()
            self._entity_extractor = None
        if self._sentiment_analyzer:
            self._sentiment_analyzer.unload()
            self._sentiment_analyzer = None
        if self._summarizer:
            self._summarizer.unload()
            self._summarizer = None
        self._intent_detector = None
        
        logger.info("All semantic processing models unloaded")

    def get_loaded_models(self) -> list[str]:
        """Get list of currently loaded models."""
        loaded = []
        if self._classifier and self._classifier.is_loaded():
            loaded.append("classifier")
        if self._entity_extractor and self._entity_extractor.is_loaded():
            loaded.append("entity_extractor")
        if self._sentiment_analyzer and self._sentiment_analyzer.is_loaded():
            loaded.append("sentiment_analyzer")
        if self._intent_detector:
            loaded.append("intent_detector")
        if self._summarizer and self._summarizer.is_loaded():
            loaded.append("summarizer")
        return loaded
