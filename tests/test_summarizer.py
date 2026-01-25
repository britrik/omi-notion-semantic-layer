"""
Tests for the summarizer.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.models.insight import Summary
from src.semantic.summarizer import Summarizer


class TestSummarizer:
    """Test cases for Summarizer."""

    @pytest.fixture
    def summarizer(self) -> Summarizer:
        """Create a summarizer instance without loading the model."""
        return Summarizer(
            model_name="facebook/bart-large-cnn",
        )

    def test_init_default_values(self) -> None:
        """Test summarizer initialization with defaults."""
        summarizer = Summarizer()
        assert summarizer.model_name == "facebook/bart-large-cnn"
        assert summarizer.device is None

    def test_init_custom_values(self) -> None:
        """Test summarizer initialization with custom values."""
        summarizer = Summarizer(
            model_name="custom/model",
            device="cpu",
        )
        assert summarizer.model_name == "custom/model"
        assert summarizer.device == "cpu"

    def test_is_loaded_false_initially(self, summarizer: Summarizer) -> None:
        """Test that model is not loaded initially."""
        assert summarizer.is_loaded() is False

    @patch("transformers.pipeline")
    def test_summarize_success(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test successful summarization."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[{"summary_text": "Project discussion with deadline"}]
        )

        summary = summarizer.summarize(
            "We had a long discussion about the project. "
            "The deadline is next Friday. We need to finish the prototype."
        )

        assert isinstance(summary, Summary)
        assert len(summary.title) > 0

    @patch("transformers.pipeline")
    def test_summarize_empty_text(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test summarization with empty text."""
        summary = summarizer.summarize("")
        assert summary.title == "Empty content"

        summary = summarizer.summarize("   ")
        assert summary.title == "Empty content"

    @patch("transformers.pipeline")
    def test_generate_title(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test title generation."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[{"summary_text": "Meeting about quarterly goals"}]
        )

        title = summarizer.generate_title(
            "We discussed our quarterly goals for Q1. "
            "The main focus will be on customer acquisition and retention."
        )

        assert len(title) <= 100
        assert len(title) > 0

    @patch("transformers.pipeline")
    def test_generate_title_short_text(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test title generation with short text."""
        short_text = "Quick sync about the project"
        title = summarizer.generate_title(short_text)
        
        # Short text should be used directly as title
        assert "project" in title.lower() or "sync" in title.lower()

    def test_generate_title_empty(self, summarizer: Summarizer) -> None:
        """Test title generation with empty text."""
        title = summarizer.generate_title("")
        assert title == "Untitled"

    @patch("transformers.pipeline")
    def test_generate_executive_summary(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test executive summary generation."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[{
                "summary_text": "Key points discussed. Action items assigned. Deadline set."
            }]
        )

        long_text = "A" * 200  # Long enough to trigger summarization
        summary = summarizer.generate_executive_summary(long_text)

        assert len(summary) <= 500

    @patch("transformers.pipeline")
    def test_generate_detailed_synopsis(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test detailed synopsis generation."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[{
                "summary_text": "Comprehensive overview of the discussion including "
                "all major points and action items."
            }]
        )

        long_text = "B" * 300  # Long enough to trigger summarization
        synopsis = summarizer.generate_detailed_synopsis(long_text)

        assert len(synopsis) <= 2000

    @patch("transformers.pipeline")
    def test_summarize_includes_executive_by_default(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test that summarize includes executive summary by default."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[{"summary_text": "Summary text"}]
        )

        long_text = "C" * 200
        summary = summarizer.summarize(long_text)

        assert summary.executive is not None

    @patch("transformers.pipeline")
    def test_summarize_excludes_detailed_by_default(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test that summarize excludes detailed by default."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[{"summary_text": "Summary text"}]
        )

        long_text = "D" * 300
        summary = summarizer.summarize(long_text)

        assert summary.detailed is None

    @patch("transformers.pipeline")
    def test_summarize_includes_detailed_when_requested(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test that summarize includes detailed when requested."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[{"summary_text": "Detailed summary text"}]
        )

        long_text = "E" * 300
        summary = summarizer.summarize(long_text, include_detailed=True)

        assert summary.detailed is not None

    @patch("transformers.pipeline")
    def test_unload(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test unloading the model."""
        # Load the model first
        _ = summarizer.summarizer
        assert summarizer.is_loaded() is True

        # Unload
        summarizer.unload()
        assert summarizer.is_loaded() is False

    def test_clean_title_removes_speaker_labels(
        self,
        summarizer: Summarizer,
    ) -> None:
        """Test that speaker labels are removed from titles."""
        cleaned = summarizer._clean_title("John: Let's discuss the project")
        assert not cleaned.startswith("John:")
        assert "project" in cleaned.lower()

    def test_clean_title_removes_extra_spaces(
        self,
        summarizer: Summarizer,
    ) -> None:
        """Test that extra spaces are removed."""
        cleaned = summarizer._clean_title("Too   many    spaces")
        assert "  " not in cleaned

    def test_clean_title_capitalizes_first_letter(
        self,
        summarizer: Summarizer,
    ) -> None:
        """Test that first letter is capitalized."""
        cleaned = summarizer._clean_title("lowercase start")
        assert cleaned[0].isupper()

    def test_extractive_title_uses_first_sentence(
        self,
        summarizer: Summarizer,
    ) -> None:
        """Test extractive title uses first meaningful sentence."""
        text = "Short. This is the main topic of discussion. More details follow."
        title = summarizer._extractive_title(text)
        
        # Should use second sentence (first is too short)
        assert "main topic" in title.lower() or "discussion" in title.lower()

    def test_extractive_title_truncates_long_sentences(
        self,
        summarizer: Summarizer,
    ) -> None:
        """Test extractive title truncates long sentences."""
        long_sentence = "This is a very " + "very " * 50 + "long sentence."
        title = summarizer._extractive_title(long_sentence, max_chars=100)
        
        assert len(title) <= 100
        assert title.endswith("...")

    def test_format_as_bullets(self, summarizer: Summarizer) -> None:
        """Test formatting text as bullets."""
        text = "First point. Second point. Third point."
        bullets = summarizer._format_as_bullets(text)
        
        assert bullets.count("•") == 3
        assert "\n" in bullets

    def test_format_as_bullets_single_sentence(
        self,
        summarizer: Summarizer,
    ) -> None:
        """Test that single sentence is not formatted as bullets."""
        text = "Just one sentence here"
        result = summarizer._format_as_bullets(text)
        
        assert result == text

    @patch("transformers.pipeline")
    def test_summarize_long_text_chunking(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test summarization of very long texts with chunking."""
        mock_pipeline_func.return_value = MagicMock(
            return_value=[{"summary_text": "Chunk summary"}]
        )

        very_long_text = "X" * 5000
        synopsis = summarizer.generate_detailed_synopsis(very_long_text)

        assert len(synopsis) <= 2000

    def test_extractive_summary_selects_best_sentences(
        self,
        summarizer: Summarizer,
    ) -> None:
        """Test that extractive summary selects important sentences."""
        text = (
            "First important sentence about the main topic. "
            "Second sentence with details. "
            "Third sentence continues. "
            "Fourth sentence with more info. "
            "Fifth sentence concludes."
        )
        
        summary = summarizer._extractive_summary(text, max_chars=200)
        
        assert len(summary) <= 200
        assert summary.endswith(".")

    @patch("transformers.pipeline")
    def test_fallback_on_model_error(
        self,
        mock_pipeline_func: MagicMock,
        summarizer: Summarizer,
    ) -> None:
        """Test fallback to extractive summary on model error."""
        mock_pipeline_func.return_value = MagicMock(
            side_effect=Exception("Model error")
        )

        # Should not raise, should use extractive fallback
        summary = summarizer.summarize(
            "This is a test sentence for summarization."
        )

        assert isinstance(summary, Summary)
        assert len(summary.title) > 0
