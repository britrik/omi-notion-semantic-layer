"""
Summarizer for transcript content.

Generates summaries at different lengths:
- Title: One-liner (max 100 chars)
- Executive: Bullet points (max 500 chars)
- Detailed: Full overview (max 2000 chars)
"""

import logging
import re
from typing import Optional

from src.models.insight import Summary

logger = logging.getLogger(__name__)


class Summarizer:
    """
    Generates summaries at different lengths using transformers.
    
    Supports title generation, executive summaries, and detailed synopses.
    Preserves key information and speaker attribution.
    """

    def __init__(
        self,
        model_name: str = "facebook/bart-large-cnn",
        device: Optional[str] = None,
    ) -> None:
        """
        Initialize the summarizer.

        Args:
            model_name: HuggingFace model for summarization
            device: Device to run model on ('cpu', 'cuda', or None for auto)
        """
        self.model_name = model_name
        self.device = device
        self._summarizer: Optional[object] = None

    @property
    def summarizer(self) -> object:
        """Lazy load the summarization pipeline."""
        if self._summarizer is None:
            self._summarizer = self._load_summarizer()
        return self._summarizer

    def _load_summarizer(self) -> object:
        """Load the summarization pipeline."""
        try:
            from transformers import pipeline

            logger.info("Loading summarization model: %s", self.model_name)
            
            summarizer = pipeline(
                "summarization",
                model=self.model_name,
                device=self.device,
            )
            
            logger.info("Summarization model loaded successfully")
            return summarizer
            
        except Exception as e:
            logger.error("Failed to load summarization model: %s", e)
            raise RuntimeError(f"Failed to load summarizer: {e}") from e

    def summarize(
        self,
        text: str,
        include_executive: bool = True,
        include_detailed: bool = False,
    ) -> Summary:
        """
        Generate a complete Summary object for text.

        Args:
            text: Text to summarize
            include_executive: Generate executive summary
            include_detailed: Generate detailed synopsis

        Returns:
            Summary object with title and optional executive/detailed summaries
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for summarization")
            return Summary(title="Empty content")

        text = text.strip()

        try:
            title = self.generate_title(text)
            
            executive = None
            if include_executive and len(text) > 100:
                executive = self.generate_executive_summary(text)
            
            detailed = None
            if include_detailed and len(text) > 200:
                detailed = self.generate_detailed_synopsis(text)

            return Summary(
                title=title,
                executive=executive,
                detailed=detailed,
            )

        except Exception as e:
            logger.error("Summarization failed: %s", e)
            # Fallback to extractive summary
            return Summary(title=self._extractive_title(text))

    def generate_title(self, text: str, max_chars: int = 100) -> str:
        """
        Generate a one-liner title for text.

        Args:
            text: Text to summarize
            max_chars: Maximum characters for title (default 100)

        Returns:
            Short title string
        """
        if not text or not text.strip():
            return "Untitled"

        text = text.strip()
        
        # For very short texts, use as-is
        if len(text) <= max_chars:
            return self._clean_title(text)

        # For short texts, use extractive method
        if len(text) < 200:
            return self._extractive_title(text, max_chars)

        try:
            # Use model for longer texts
            result = self.summarizer(
                text[:1024],  # Limit input length
                max_length=30,
                min_length=5,
                do_sample=False,
            )
            
            summary_text = result[0]["summary_text"]
            title = self._clean_title(summary_text)
            
            # Truncate if still too long
            if len(title) > max_chars:
                title = title[:max_chars - 3].rsplit(" ", 1)[0] + "..."
            
            return title

        except Exception as e:
            logger.warning("Model summarization failed, using extractive: %s", e)
            return self._extractive_title(text, max_chars)

    def generate_executive_summary(self, text: str, max_chars: int = 500) -> str:
        """
        Generate an executive summary with key points.

        Args:
            text: Text to summarize
            max_chars: Maximum characters (default 500)

        Returns:
            Executive summary string
        """
        if not text or not text.strip():
            return ""

        text = text.strip()
        
        if len(text) <= max_chars:
            return text

        try:
            result = self.summarizer(
                text[:2048],
                max_length=150,
                min_length=30,
                do_sample=False,
            )
            
            summary = result[0]["summary_text"]
            
            # Format as bullet points if multiple sentences
            summary = self._format_as_bullets(summary)
            
            # Truncate if needed
            if len(summary) > max_chars:
                summary = summary[:max_chars - 3].rsplit(" ", 1)[0] + "..."
            
            return summary

        except Exception as e:
            logger.warning("Executive summary failed: %s", e)
            return self._extractive_summary(text, max_chars)

    def generate_detailed_synopsis(self, text: str, max_chars: int = 2000) -> str:
        """
        Generate a detailed synopsis of the content.

        Args:
            text: Text to summarize
            max_chars: Maximum characters (default 2000)

        Returns:
            Detailed synopsis string
        """
        if not text or not text.strip():
            return ""

        text = text.strip()
        
        if len(text) <= max_chars:
            return text

        try:
            # For very long texts, chunk and summarize
            if len(text) > 4000:
                return self._summarize_long_text(text, max_chars)

            result = self.summarizer(
                text[:3000],
                max_length=500,
                min_length=100,
                do_sample=False,
            )
            
            synopsis = result[0]["summary_text"]
            
            # Truncate if needed
            if len(synopsis) > max_chars:
                synopsis = synopsis[:max_chars - 3].rsplit(" ", 1)[0] + "..."
            
            return synopsis

        except Exception as e:
            logger.warning("Detailed synopsis failed: %s", e)
            return self._extractive_summary(text, max_chars)

    def _clean_title(self, text: str) -> str:
        """Clean and format text as a title."""
        # Remove speaker labels
        text = re.sub(r"^[A-Za-z]+:\s*", "", text)
        
        # Remove multiple spaces
        text = re.sub(r"\s+", " ", text)
        
        # Remove trailing punctuation except period
        text = text.strip().rstrip(",;:")
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        
        return text

    def _extractive_title(self, text: str, max_chars: int = 100) -> str:
        """Extract a title from the first meaningful sentence."""
        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            # Skip very short sentences
            if len(sentence) < 10:
                continue
            
            # Remove speaker labels
            sentence = re.sub(r"^[A-Za-z]+:\s*", "", sentence)
            
            if len(sentence) <= max_chars:
                return self._clean_title(sentence)
            else:
                # Truncate at word boundary
                truncated = sentence[:max_chars - 3].rsplit(" ", 1)[0] + "..."
                return self._clean_title(truncated)
        
        # Fallback: use first part of text
        return self._clean_title(text[:max_chars - 3] + "...")

    def _extractive_summary(self, text: str, max_chars: int) -> str:
        """Create an extractive summary from key sentences."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not sentences:
            return text[:max_chars]

        # Score sentences by position and length
        scored = []
        for i, sentence in enumerate(sentences):
            # Earlier sentences and moderate length preferred
            position_score = 1.0 / (i + 1)
            length_score = min(1.0, len(sentence) / 100)
            score = position_score * 0.6 + length_score * 0.4
            scored.append((sentence, score))
        
        # Sort by score and select top sentences
        scored.sort(key=lambda x: x[1], reverse=True)
        
        summary = []
        total_length = 0
        for sentence, _ in scored:
            if total_length + len(sentence) + 2 <= max_chars:
                summary.append(sentence)
                total_length += len(sentence) + 2
            else:
                break
        
        return ". ".join(summary) + "." if summary else text[:max_chars]

    def _format_as_bullets(self, text: str) -> str:
        """Format text as bullet points if it contains multiple sentences."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return text
        
        bullets = ["• " + s for s in sentences if len(s) > 10]
        return "\n".join(bullets)

    def _summarize_long_text(self, text: str, max_chars: int) -> str:
        """Summarize very long texts by chunking."""
        # Split into chunks
        chunk_size = 1500
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        
        # Summarize each chunk
        summaries = []
        for chunk in chunks[:4]:  # Limit to first 4 chunks
            try:
                result = self.summarizer(
                    chunk,
                    max_length=100,
                    min_length=20,
                    do_sample=False,
                )
                summaries.append(result[0]["summary_text"])
            except Exception as e:
                logger.warning("Chunk summarization failed: %s", e)
                summaries.append(self._extractive_summary(chunk, 100))
        
        combined = " ".join(summaries)
        
        # Final pass if still too long
        if len(combined) > max_chars:
            try:
                result = self.summarizer(
                    combined,
                    max_length=int(max_chars / 4),
                    min_length=50,
                    do_sample=False,
                )
                return result[0]["summary_text"]
            except Exception:
                return combined[:max_chars - 3] + "..."
        
        return combined

    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._summarizer is not None

    def unload(self) -> None:
        """Unload the model to free memory."""
        self._summarizer = None
        logger.info("Summarization model unloaded")
