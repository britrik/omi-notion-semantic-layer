"""
Tests for the semantic processor facade.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.models.insight import (
    Classification,
    ContentCategory,
    Entity,
    EntityType,
    IntentType,
    ProcessedInsight,
    SentimentResult,
    SentimentType,
    Summary,
    UrgencyLevel,
)
from src.models.transcript import Transcript
from src.semantic_processor import SemanticProcessor


class TestSemanticProcessor:
    """Test cases for SemanticProcessor."""

    @pytest.fixture
    def processor(self) -> SemanticProcessor:
        """Create a processor instance without loading models."""
        return SemanticProcessor(
            confidence_threshold=0.65,
        )

    @pytest.fixture
    def sample_transcript(self) -> Transcript:
        """Create a sample transcript for testing."""
        return Transcript(
            transcript_id="test_001",
            timestamp=datetime.now(timezone.utc),
            duration=120.0,
            participants=["Alice", "Bob"],
            content="We need to finish the project by Friday. Alice will handle the design.",
        )

    def test_init_default_values(self) -> None:
        """Test processor initialization with defaults."""
        processor = SemanticProcessor()
        assert processor.confidence_threshold == 0.65
        assert processor.device is None

    def test_init_custom_values(self) -> None:
        """Test processor initialization with custom values."""
        processor = SemanticProcessor(
            classifier_model="custom/classifier",
            spacy_model="en_core_web_sm",
            device="cpu",
            confidence_threshold=0.8,
        )
        assert processor.confidence_threshold == 0.8
        assert processor.device == "cpu"

    def test_components_not_loaded_initially(
        self,
        processor: SemanticProcessor,
    ) -> None:
        """Test that no models are loaded initially."""
        loaded = processor.get_loaded_models()
        assert len(loaded) == 0

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_process_transcript(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
        sample_transcript: Transcript,
    ) -> None:
        """Test processing a full transcript."""
        # Setup mocks
        mock_classifier.return_value.classify.return_value = [
            Classification(category=ContentCategory.ACTION_ITEM, confidence=0.9),
        ]
        mock_entity.return_value.extract_entities.return_value = [
            Entity(text="Friday", type=EntityType.DATE, confidence=0.95),
        ]
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL,
            score=0.0,
            confidence=0.8,
            urgency=UrgencyLevel.MEDIUM,
        )
        mock_intent.return_value.detect_intent.return_value = IntentType.ACTIONABLE
        mock_summarizer.return_value.summarize.return_value = Summary(
            title="Project deadline discussion",
        )

        result = processor.process(sample_transcript)

        assert isinstance(result, ProcessedInsight)
        assert result.transcript_id == "test_001"

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_process_uses_cache(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
        sample_transcript: Transcript,
    ) -> None:
        """Test that processing uses cache on second call."""
        mock_classifier.return_value.classify.return_value = []
        mock_entity.return_value.extract_entities.return_value = []
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = None
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        # First call
        result1 = processor.process(sample_transcript)
        
        # Second call should use cache
        result2 = processor.process(sample_transcript)

        assert result1 is result2
        # Classifier should only be called once
        assert mock_classifier.return_value.classify.call_count == 1

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_process_bypasses_cache(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
        sample_transcript: Transcript,
    ) -> None:
        """Test that cache can be bypassed."""
        mock_classifier.return_value.classify.return_value = []
        mock_entity.return_value.extract_entities.return_value = []
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = None
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        # First call
        processor.process(sample_transcript)
        
        # Second call with cache bypass
        processor.process(sample_transcript, use_cache=False)

        # Classifier should be called twice
        assert mock_classifier.return_value.classify.call_count == 2

    def test_clear_cache(self, processor: SemanticProcessor) -> None:
        """Test clearing the cache."""
        processor._cache["test"] = MagicMock()
        assert len(processor._cache) == 1

        processor.clear_cache()

        assert len(processor._cache) == 0

    def test_set_cache_enabled(self, processor: SemanticProcessor) -> None:
        """Test enabling/disabling cache."""
        assert processor._cache_enabled is True

        processor.set_cache_enabled(False)
        assert processor._cache_enabled is False

        processor.set_cache_enabled(True)
        assert processor._cache_enabled is True

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_process_text(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
    ) -> None:
        """Test processing raw text."""
        mock_classifier.return_value.classify.return_value = []
        mock_entity.return_value.extract_entities.return_value = []
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = None
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        result = processor.process_text("Some raw text to process")

        assert isinstance(result, ProcessedInsight)
        assert result.transcript_id == "manual"

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_batch_process(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
    ) -> None:
        """Test batch processing multiple transcripts."""
        mock_classifier.return_value.classify.return_value = []
        mock_entity.return_value.extract_entities.return_value = []
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = None
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        transcripts = [
            Transcript(
                transcript_id=f"test_{i}",
                timestamp=datetime.now(timezone.utc),
                duration=60.0,
                content=f"Content {i}",
            )
            for i in range(3)
        ]

        results = processor.batch_process(transcripts)

        assert len(results) == 3

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_batch_process_handles_errors(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
    ) -> None:
        """Test batch processing handles individual errors gracefully."""
        mock_classifier.return_value.classify.side_effect = [
            [],
            Exception("Processing error"),
            [],
        ]
        mock_entity.return_value.extract_entities.return_value = []
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = None
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        transcripts = [
            Transcript(
                transcript_id=f"test_{i}",
                timestamp=datetime.now(timezone.utc),
                duration=60.0,
                content=f"Content {i}",
            )
            for i in range(3)
        ]

        results = processor.batch_process(transcripts)

        # Errors in classification are caught, so all 3 should be processed
        # The second one will have empty classifications due to error handling
        assert len(results) == 3

    def test_unload_models(self, processor: SemanticProcessor) -> None:
        """Test unloading all models."""
        # Create mock components
        processor._classifier = MagicMock()
        processor._entity_extractor = MagicMock()
        processor._sentiment_analyzer = MagicMock()
        processor._summarizer = MagicMock()
        processor._intent_detector = MagicMock()

        processor.unload_models()

        assert processor._classifier is None
        assert processor._entity_extractor is None
        assert processor._sentiment_analyzer is None
        assert processor._summarizer is None
        assert processor._intent_detector is None

    def test_get_loaded_models(self, processor: SemanticProcessor) -> None:
        """Test getting list of loaded models."""
        # Create mock components with is_loaded method
        mock_classifier = MagicMock()
        mock_classifier.is_loaded.return_value = True
        processor._classifier = mock_classifier

        mock_entity = MagicMock()
        mock_entity.is_loaded.return_value = False
        processor._entity_extractor = mock_entity

        loaded = processor.get_loaded_models()

        assert "classifier" in loaded
        assert "entity_extractor" not in loaded

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_extract_participants(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
    ) -> None:
        """Test participant extraction from transcript and entities."""
        mock_classifier.return_value.classify.return_value = []
        mock_entity.return_value.extract_entities.return_value = [
            Entity(text="Charlie", type=EntityType.PERSON, confidence=0.9),
        ]
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = None
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        transcript = Transcript(
            transcript_id="test_001",
            timestamp=datetime.now(timezone.utc),
            duration=60.0,
            participants=["Alice", "Bob"],
            content="Alice and Bob met with Charlie",
        )

        result = processor.process(transcript)

        assert "Alice" in result.participants
        assert "Bob" in result.participants
        assert "Charlie" in result.participants

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_generate_tags(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
    ) -> None:
        """Test tag generation from entities and classifications."""
        mock_classifier.return_value.classify.return_value = [
            Classification(category=ContentCategory.ACTION_ITEM, confidence=0.9),
        ]
        mock_entity.return_value.extract_entities.return_value = [
            Entity(text="budget", type=EntityType.TOPIC, confidence=0.8),
        ]
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = None
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        transcript = Transcript(
            transcript_id="test_001",
            timestamp=datetime.now(timezone.utc),
            duration=60.0,
            content="We need to review the budget",
        )

        result = processor.process(transcript)

        assert "action-item" in result.tags
        assert "budget" in result.tags

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_quality_score_calculation(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
    ) -> None:
        """Test quality score calculation."""
        mock_classifier.return_value.classify.return_value = [
            Classification(category=ContentCategory.ACTION_ITEM, confidence=0.9),
        ]
        mock_entity.return_value.extract_entities.return_value = [
            Entity(text="Friday", type=EntityType.DATE, confidence=0.9),
            Entity(text="Alice", type=EntityType.PERSON, confidence=0.9),
        ]
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = IntentType.ACTIONABLE
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        transcript = Transcript(
            transcript_id="test_001",
            timestamp=datetime.now(timezone.utc),
            duration=60.0,
            content="Alice needs to finish the report by Friday.",
        )

        result = processor.process(transcript)

        assert result.quality_score.total_score > 0
        assert result.quality_score.actionability > 3.0  # High due to action item

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_primary_category(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
    ) -> None:
        """Test primary category selection."""
        mock_classifier.return_value.classify.return_value = [
            Classification(category=ContentCategory.DECISION, confidence=0.9),
            Classification(category=ContentCategory.ACTION_ITEM, confidence=0.7),
        ]
        mock_entity.return_value.extract_entities.return_value = []
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = None
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        transcript = Transcript(
            transcript_id="test_001",
            timestamp=datetime.now(timezone.utc),
            duration=60.0,
            content="We decided to proceed with option A.",
        )

        result = processor.process(transcript)

        assert result.primary_category == ContentCategory.DECISION

    @patch("src.semantic_processor.ContentClassifier")
    @patch("src.semantic_processor.EntityExtractor")
    @patch("src.semantic_processor.SentimentAnalyzer")
    @patch("src.semantic_processor.IntentDetector")
    @patch("src.semantic_processor.Summarizer")
    def test_graceful_component_failures(
        self,
        mock_summarizer: MagicMock,
        mock_intent: MagicMock,
        mock_sentiment: MagicMock,
        mock_entity: MagicMock,
        mock_classifier: MagicMock,
        processor: SemanticProcessor,
    ) -> None:
        """Test that individual component failures don't crash processing."""
        mock_classifier.return_value.classify.side_effect = Exception("Classifier error")
        mock_entity.return_value.extract_entities.return_value = []
        mock_sentiment.return_value.analyze.return_value = SentimentResult(
            sentiment=SentimentType.NEUTRAL, score=0.0, confidence=0.8
        )
        mock_intent.return_value.detect_intent.return_value = None
        mock_summarizer.return_value.summarize.return_value = Summary(title="Test")

        transcript = Transcript(
            transcript_id="test_001",
            timestamp=datetime.now(timezone.utc),
            duration=60.0,
            content="Test content",
        )

        result = processor.process(transcript)

        # Should still return a result with empty classifications
        assert isinstance(result, ProcessedInsight)
        assert result.classifications == []
