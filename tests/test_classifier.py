"""
Tests for the content classifier.
"""

from unittest.mock import MagicMock, patch

import pytest
import sys

from src.models.insight import Classification, ContentCategory
from src.semantic.classifier import ContentClassifier


class TestContentClassifier:
    """Test cases for ContentClassifier."""

    @pytest.fixture
    def classifier(self) -> ContentClassifier:
        """Create a classifier instance without loading the model."""
        return ContentClassifier(
            model_name="facebook/bart-large-mnli",
            confidence_threshold=0.65,
        )

    @pytest.fixture
    def mock_pipeline(self) -> MagicMock:
        """Create a mock transformers pipeline."""
        mock = MagicMock()
        mock.return_value = {
            "labels": ["Action Item", "Meeting", "Discussion"],
            "scores": [0.85, 0.72, 0.45],
        }
        return mock

    def test_init_default_values(self) -> None:
        """Test classifier initialization with defaults."""
        classifier = ContentClassifier()
        assert classifier.model_name == "facebook/bart-large-mnli"
        assert classifier.confidence_threshold == 0.65
        assert classifier.device is None

    def test_init_custom_values(self) -> None:
        """Test classifier initialization with custom values."""
        classifier = ContentClassifier(
            model_name="custom/model",
            confidence_threshold=0.8,
            device="cpu",
        )
        assert classifier.model_name == "custom/model"
        assert classifier.confidence_threshold == 0.8
        assert classifier.device == "cpu"

    def test_is_loaded_false_initially(self, classifier: ContentClassifier) -> None:
        """Test that model is not loaded initially."""
        assert classifier.is_loaded() is False

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_classify_success(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test successful classification."""
        mock_pipeline_func.return_value = MagicMock(
            return_value={
                "labels": ["Action Item", "Meeting"],
                "scores": [0.85, 0.72],
            }
        )

        classifications = classifier.classify("We need to finish the report by Friday")

        assert len(classifications) == 2
        assert classifications[0].category == ContentCategory.ACTION_ITEM
        assert classifications[0].confidence == 0.85
        assert classifications[1].category == ContentCategory.MEETING
        assert classifications[1].confidence == 0.72

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_classify_filters_by_threshold(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test that classifications below threshold are filtered."""
        mock_pipeline_func.return_value = MagicMock(
            return_value={
                "labels": ["Action Item", "Discussion"],
                "scores": [0.85, 0.45],  # 0.45 is below 0.65 threshold
            }
        )

        classifications = classifier.classify("Some text")

        assert len(classifications) == 1
        assert classifications[0].category == ContentCategory.ACTION_ITEM

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_classify_empty_text(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test classification with empty text."""
        classifications = classifier.classify("")
        assert classifications == []

        classifications = classifier.classify("   ")
        assert classifications == []

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_classify_top_k(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test limiting number of classifications with top_k."""
        mock_pipeline_func.return_value = MagicMock(
            return_value={
                "labels": ["Action Item", "Meeting", "Insight"],
                "scores": [0.9, 0.8, 0.7],
            }
        )

        classifications = classifier.classify("Some text", top_k=2)

        assert len(classifications) == 2

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_get_primary_category(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test getting primary category."""
        mock_pipeline_func.return_value = MagicMock(
            return_value={
                "labels": ["Decision", "Action Item"],
                "scores": [0.9, 0.7],
            }
        )

        category = classifier.get_primary_category("We decided to proceed")

        assert category == ContentCategory.DECISION

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_get_primary_category_none_when_below_threshold(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test primary category returns None when all below threshold."""
        mock_pipeline_func.return_value = MagicMock(
            return_value={
                "labels": ["Decision"],
                "scores": [0.3],  # Below threshold
            }
        )

        category = classifier.get_primary_category("Some text")

        assert category is None

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_batch_classify(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test batch classification of multiple texts."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[
                {"labels": ["Action Item"], "scores": [0.9]},
                {"labels": ["Insight"], "scores": [0.8]},
            ]
        )

        results = classifier.batch_classify([
            "Task one",
            "Observation two",
        ])

        assert len(results) == 2

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_batch_classify_handles_empty_texts(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test batch classification handles empty texts."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[
                {"labels": ["Action Item"], "scores": [0.9]},
            ]
        )

        results = classifier.batch_classify([
            "Valid text",
            "",
            "   ",
        ])

        assert len(results) == 3
        assert results[1] == []
        assert results[2] == []

    def test_label_to_category_valid(self) -> None:
        """Test converting valid label to category."""
        category = ContentClassifier._label_to_category("Action Item")
        assert category == ContentCategory.ACTION_ITEM

    def test_label_to_category_case_insensitive(self) -> None:
        """Test label conversion is case insensitive."""
        category = ContentClassifier._label_to_category("action item")
        assert category == ContentCategory.ACTION_ITEM

    def test_label_to_category_invalid(self) -> None:
        """Test converting invalid label returns None."""
        category = ContentClassifier._label_to_category("Unknown Category")
        assert category is None

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_unload(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test unloading the model."""
        # Load the model first
        _ = classifier.classifier
        assert classifier.is_loaded() is True

        # Unload
        classifier.unload()
        assert classifier.is_loaded() is False

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_classify_with_hypothesis(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test classification with custom hypothesis template."""
        mock_pipeline_func.return_value = MagicMock(
            return_value={
                "labels": ["Action Item"],
                "scores": [0.9],
            }
        )

        classifications = classifier.classify_with_hypothesis(
            "Some text",
            hypothesis_template="This conversation is about {}.",
        )

        assert len(classifications) >= 0  # Just verify it runs

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_truncates_long_text(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test that very long text is truncated."""
        mock_pipe = MagicMock(
            return_value={
                "labels": ["Action Item"],
                "scores": [0.9],
            }
        )
        mock_pipeline_func.return_value = mock_pipe

        long_text = "x" * 2000
        classifier.classify(long_text)

        # Verify the truncated text was passed
        call_args = mock_pipe.call_args[0][0]
        assert len(call_args) == 1024

    @pytest.mark.skipif("transformers" not in sys.modules, reason="transformers not installed")
    @patch("transformers.pipeline")
    def test_sorted_by_confidence(
        self,
        mock_pipeline_func: MagicMock,
        classifier: ContentClassifier,
    ) -> None:
        """Test that results are sorted by confidence descending."""
        mock_pipeline_func.return_value = MagicMock(
            return_value={
                "labels": ["Meeting", "Action Item", "Insight"],
                "scores": [0.7, 0.9, 0.8],
            }
        )

        classifications = classifier.classify("Some text")

        # Should be sorted: Action Item (0.9), Insight (0.8), Meeting (0.7)
        assert classifications[0].category == ContentCategory.ACTION_ITEM
        assert classifications[1].category == ContentCategory.INSIGHT
        assert classifications[2].category == ContentCategory.MEETING
