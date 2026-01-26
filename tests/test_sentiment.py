"""
Tests for the sentiment analyzer.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.models.insight import SentimentResult, SentimentType, UrgencyLevel
from src.semantic.sentiment import SentimentAnalyzer


class TestSentimentAnalyzer:
    """Test cases for SentimentAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> SentimentAnalyzer:
        """Create an analyzer instance without loading the model."""
        return SentimentAnalyzer(
            model_name="cardiffnlp/twitter-roberta-base-sentiment-latest",
        )

    def test_init_default_values(self) -> None:
        """Test analyzer initialization with defaults."""
        analyzer = SentimentAnalyzer()
        assert analyzer.model_name == "cardiffnlp/twitter-roberta-base-sentiment-latest"
        assert analyzer.device is None

    def test_init_custom_values(self) -> None:
        """Test analyzer initialization with custom values."""
        analyzer = SentimentAnalyzer(
            model_name="custom/model",
            device="cpu",
        )
        assert analyzer.model_name == "custom/model"
        assert analyzer.device == "cpu"

    def test_is_loaded_false_initially(self, analyzer: SentimentAnalyzer) -> None:
        """Test that model is not loaded initially."""
        assert analyzer.is_loaded() is False

    @patch("transformers.pipeline")
    def test_analyze_positive(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test positive sentiment detection."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[[
                {"label": "positive", "score": 0.9},
                {"label": "neutral", "score": 0.08},
                {"label": "negative", "score": 0.02},
            ]]
        )

        result = analyzer.analyze("This is fantastic news!")

        assert result.sentiment == SentimentType.POSITIVE
        assert result.score > 0
        assert result.confidence > 0.8

    @patch("transformers.pipeline")
    def test_analyze_negative(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test negative sentiment detection."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[[
                {"label": "negative", "score": 0.85},
                {"label": "neutral", "score": 0.1},
                {"label": "positive", "score": 0.05},
            ]]
        )

        result = analyzer.analyze("This is terrible and frustrating")

        assert result.sentiment == SentimentType.NEGATIVE
        assert result.score < 0

    @patch("transformers.pipeline")
    def test_analyze_neutral(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test neutral sentiment detection."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[[
                {"label": "neutral", "score": 0.8},
                {"label": "positive", "score": 0.15},
                {"label": "negative", "score": 0.05},
            ]]
        )

        result = analyzer.analyze("The meeting is scheduled for 3pm")

        assert result.sentiment == SentimentType.NEUTRAL
        assert result.score == 0.0

    @patch("transformers.pipeline")
    def test_analyze_empty_text(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test analysis with empty text."""
        result = analyzer.analyze("")
        
        assert result.sentiment == SentimentType.NEUTRAL
        assert result.confidence == 0.0

    @patch("transformers.pipeline")
    def test_analyze_includes_urgency(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test that analysis includes urgency detection."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[[{"label": "neutral", "score": 0.8}]]
        )

        result = analyzer.analyze("This needs to be done ASAP!")

        assert result.urgency == UrgencyLevel.CRITICAL

    @patch("transformers.pipeline")
    def test_analyze_includes_emotional_tone(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test that analysis includes emotional tone."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[[{"label": "positive", "score": 0.9}]]
        )

        result = analyzer.analyze("I'm definitely certain this will work!")

        assert result.emotional_tone == "confident"

    def test_detect_urgency_critical(self, analyzer: SentimentAnalyzer) -> None:
        """Test critical urgency detection."""
        assert analyzer.detect_urgency("This is urgent!") == UrgencyLevel.CRITICAL
        assert analyzer.detect_urgency("We need this ASAP") == UrgencyLevel.CRITICAL
        assert analyzer.detect_urgency("Emergency situation") == UrgencyLevel.CRITICAL

    def test_detect_urgency_high(self, analyzer: SentimentAnalyzer) -> None:
        """Test high urgency detection."""
        assert analyzer.detect_urgency("This is important") == UrgencyLevel.HIGH
        assert analyzer.detect_urgency("Due by end of day") == UrgencyLevel.HIGH
        assert analyzer.detect_urgency("Priority task") == UrgencyLevel.HIGH

    def test_detect_urgency_medium(self, analyzer: SentimentAnalyzer) -> None:
        """Test medium urgency detection."""
        assert analyzer.detect_urgency("We intend to do this") == UrgencyLevel.MEDIUM
        assert analyzer.detect_urgency("Plan to do in the coming days") == UrgencyLevel.MEDIUM

    def test_detect_urgency_low(self, analyzer: SentimentAnalyzer) -> None:
        """Test low urgency detection."""
        assert analyzer.detect_urgency("Normal task") == UrgencyLevel.LOW
        assert analyzer.detect_urgency("No rush on this") == UrgencyLevel.LOW

    def test_detect_emotional_tone_confident(
        self,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test confident tone detection."""
        tone = analyzer.detect_emotional_tone("I'm definitely sure about this")
        assert tone == "confident"

    def test_detect_emotional_tone_uncertain(
        self,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test uncertain tone detection."""
        tone = analyzer.detect_emotional_tone("Maybe this could work, perhaps")
        assert tone == "uncertain"

    def test_detect_emotional_tone_frustrated(
        self,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test frustrated tone detection."""
        tone = analyzer.detect_emotional_tone("This is frustrating, the problem persists")
        assert tone == "frustrated"

    def test_detect_emotional_tone_excited(
        self,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test excited tone detection."""
        tone = analyzer.detect_emotional_tone("This is amazing and awesome!")
        assert tone == "excited"

    def test_detect_emotional_tone_neutral(
        self,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test neutral tone (no keywords)."""
        tone = analyzer.detect_emotional_tone("The meeting is at 3pm")
        assert tone is None

    @patch("transformers.pipeline")
    def test_get_sentiment_label(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test getting simple sentiment label."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[[{"label": "positive", "score": 0.9}]]
        )

        label = analyzer.get_sentiment_label("Great work!")

        assert label == "positive"

    @patch("transformers.pipeline")
    def test_batch_analyze(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test batch sentiment analysis."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[[{"label": "positive", "score": 0.9}]]
        )

        results = analyzer.batch_analyze([
            "Great news!",
            "Bad outcome",
            "Normal update",
        ])

        assert len(results) == 3
        assert all(isinstance(r, SentimentResult) for r in results)

    @patch("transformers.pipeline")
    def test_unload(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test unloading the model."""
        # Load the model first
        _ = analyzer.analyzer
        assert analyzer.is_loaded() is True

        # Unload
        analyzer.unload()
        assert analyzer.is_loaded() is False

    @patch("transformers.pipeline")
    def test_truncates_long_text(
        self,
        mock_pipeline_func: MagicMock,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test that very long text is truncated."""
        mock_pipe = MagicMock(
            return_value=[[{"label": "neutral", "score": 0.8}]]
        )
        mock_pipeline_func.return_value = mock_pipe

        long_text = "x" * 1000
        analyzer.analyze(long_text)

        # Verify the truncated text was passed
        call_args = mock_pipe.call_args[0][0]
        assert len(call_args) == 512

    def test_detect_urgency_empty_text(self, analyzer: SentimentAnalyzer) -> None:
        """Test urgency detection with empty text."""
        assert analyzer.detect_urgency("") == UrgencyLevel.LOW
        assert analyzer.detect_urgency(None) == UrgencyLevel.LOW

    def test_detect_emotional_tone_empty_text(
        self,
        analyzer: SentimentAnalyzer,
    ) -> None:
        """Test tone detection with empty text."""
        assert analyzer.detect_emotional_tone("") is None
        assert analyzer.detect_emotional_tone(None) is None
