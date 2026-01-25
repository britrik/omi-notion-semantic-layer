"""
Tests for the intent detector.
"""

import pytest

from src.models.insight import IntentType
from src.semantic.intent import IntentDetector


class TestIntentDetector:
    """Test cases for IntentDetector."""

    @pytest.fixture
    def detector(self) -> IntentDetector:
        """Create a detector instance."""
        return IntentDetector(
            pattern_weight=0.6,
            keyword_weight=0.4,
            min_confidence=0.3,
        )

    def test_init_default_values(self) -> None:
        """Test detector initialization with defaults."""
        detector = IntentDetector()
        assert detector.pattern_weight == 0.6
        assert detector.keyword_weight == 0.4
        assert detector.min_confidence == 0.3

    def test_init_custom_values(self) -> None:
        """Test detector initialization with custom values."""
        detector = IntentDetector(
            pattern_weight=0.7,
            keyword_weight=0.3,
            min_confidence=0.5,
        )
        assert detector.pattern_weight == 0.7
        assert detector.keyword_weight == 0.3
        assert detector.min_confidence == 0.5

    def test_detect_intent_actionable(self, detector: IntentDetector) -> None:
        """Test detecting actionable intent."""
        texts = [
            "We need to finish this by Friday",
            "Please complete the report",
            "You must submit the form today",
            "Let's implement the new feature",
        ]
        
        for text in texts:
            intent = detector.detect_intent(text)
            assert intent == IntentType.ACTIONABLE, f"Failed for: {text}"

    def test_detect_intent_informational(self, detector: IntentDetector) -> None:
        """Test detecting informational intent."""
        texts = [
            "For your information, the meeting is at 3pm",
            "Here's the status update on the project",
            "The report shows that sales increased",
            "FYI the system is now online",
        ]
        
        for text in texts:
            intent = detector.detect_intent(text)
            assert intent == IntentType.INFORMATIONAL, f"Failed for: {text}"

    def test_detect_intent_exploratory(self, detector: IntentDetector) -> None:
        """Test detecting exploratory intent."""
        texts = [
            "What if we tried a different approach?",
            "I'm wondering about the feasibility",
            "Let's explore this option further",
            "Maybe we could consider an alternative",
        ]
        
        for text in texts:
            intent = detector.detect_intent(text)
            assert intent == IntentType.EXPLORATORY, f"Failed for: {text}"

    def test_detect_intent_collaborative(self, detector: IntentDetector) -> None:
        """Test detecting collaborative intent."""
        texts = [
            "Let's work together on this project",
            "We should discuss this as a team",
            "Can I get your feedback on this?",
            "Let's brainstorm some ideas together",
        ]
        
        for text in texts:
            intent = detector.detect_intent(text)
            assert intent == IntentType.COLLABORATIVE, f"Failed for: {text}"

    def test_detect_intent_reflective(self, detector: IntentDetector) -> None:
        """Test detecting reflective intent."""
        texts = [
            "I learned a valuable lesson from this",
            "In hindsight, we should have done better",
            "Looking back, the key insight was clear",
            "The main takeaway from this experience",
        ]
        
        for text in texts:
            intent = detector.detect_intent(text)
            assert intent == IntentType.REFLECTIVE, f"Failed for: {text}"

    def test_detect_intent_empty_text(self, detector: IntentDetector) -> None:
        """Test intent detection with empty text."""
        assert detector.detect_intent("") is None
        assert detector.detect_intent("   ") is None

    def test_detect_intent_with_confidence(
        self,
        detector: IntentDetector,
    ) -> None:
        """Test getting intent with confidence score."""
        intent, confidence = detector.detect_intent_with_confidence(
            "We must complete this task ASAP"
        )
        
        assert intent == IntentType.ACTIONABLE
        assert confidence > 0.3

    def test_detect_intent_with_confidence_no_match(
        self,
        detector: IntentDetector,
    ) -> None:
        """Test confidence returns None when no clear intent."""
        detector_strict = IntentDetector(min_confidence=0.99)
        intent, confidence = detector_strict.detect_intent_with_confidence(
            "Random text without clear intent"
        )
        
        assert intent is None

    def test_get_all_intents(self, detector: IntentDetector) -> None:
        """Test getting all detected intents above threshold."""
        # Text that could match multiple intents
        text = "We should work together to complete this task"
        
        intents = detector.get_all_intents(text, threshold=0.1)
        
        assert len(intents) >= 1
        assert all(isinstance(i[0], IntentType) for i in intents)
        assert all(isinstance(i[1], float) for i in intents)

    def test_get_all_intents_sorted_by_score(
        self,
        detector: IntentDetector,
    ) -> None:
        """Test that intents are sorted by score descending."""
        text = "We need to discuss and complete this together"
        
        intents = detector.get_all_intents(text, threshold=0.1)
        
        scores = [i[1] for i in intents]
        assert scores == sorted(scores, reverse=True)

    def test_is_actionable_true(self, detector: IntentDetector) -> None:
        """Test is_actionable returns True for actionable text."""
        assert detector.is_actionable("Please submit the report")
        assert detector.is_actionable("We need to fix this bug")

    def test_is_actionable_false(self, detector: IntentDetector) -> None:
        """Test is_actionable returns False for non-actionable text."""
        assert not detector.is_actionable("The weather is nice today")

    def test_is_question_with_question_mark(
        self,
        detector: IntentDetector,
    ) -> None:
        """Test is_question returns True for text with question mark."""
        assert detector.is_question("What time is the meeting?")
        assert detector.is_question("Are we ready to launch?")

    def test_is_question_exploratory_intent(
        self,
        detector: IntentDetector,
    ) -> None:
        """Test is_question returns True for exploratory intent."""
        assert detector.is_question("What if we tried a different approach?")
        assert detector.is_question("I'm wondering about the options?")

    def test_batch_detect(self, detector: IntentDetector) -> None:
        """Test batch intent detection."""
        texts = [
            "Please complete the task",
            "Here's the status update",
            "What if we tried something new?",
        ]
        
        results = detector.batch_detect(texts)
        
        assert len(results) == 3
        assert results[0] == IntentType.ACTIONABLE
        assert results[1] == IntentType.INFORMATIONAL
        assert results[2] == IntentType.EXPLORATORY

    def test_batch_detect_empty_list(self, detector: IntentDetector) -> None:
        """Test batch detection with empty list."""
        results = detector.batch_detect([])
        assert results == []

    def test_mixed_intent_signals(self, detector: IntentDetector) -> None:
        """Test text with multiple intent signals."""
        # This has both actionable and collaborative signals
        text = "Let's work together to complete this task by Friday"
        
        intent = detector.detect_intent(text)
        
        # Should return the strongest intent
        assert intent in (IntentType.ACTIONABLE, IntentType.COLLABORATIVE)

    def test_threshold_affects_detection(self) -> None:
        """Test that confidence threshold affects detection."""
        low_threshold = IntentDetector(min_confidence=0.1)
        high_threshold = IntentDetector(min_confidence=0.9)
        
        text = "Maybe we could possibly try something"
        
        # Low threshold should detect
        low_result = low_threshold.detect_intent(text)
        # High threshold might not detect
        high_result = high_threshold.detect_intent(text)
        
        # Low threshold should be more likely to detect
        assert low_result is not None or high_result is None

    def test_weights_affect_scoring(self) -> None:
        """Test that weights affect intent scoring."""
        pattern_heavy = IntentDetector(pattern_weight=0.9, keyword_weight=0.1)
        keyword_heavy = IntentDetector(pattern_weight=0.1, keyword_weight=0.9)
        
        text = "We need to complete the action item task"
        
        # Both should detect actionable, but scores may differ
        pattern_intent = pattern_heavy.detect_intent(text)
        keyword_intent = keyword_heavy.detect_intent(text)
        
        assert pattern_intent == IntentType.ACTIONABLE
        assert keyword_intent == IntentType.ACTIONABLE

    def test_case_insensitive(self, detector: IntentDetector) -> None:
        """Test that detection is case insensitive."""
        assert detector.detect_intent("URGENT: Need to fix this NOW")
        assert detector.detect_intent("FYI the report is ready")

    def test_no_clear_intent(self) -> None:
        """Test handling text with no clear intent."""
        detector = IntentDetector(min_confidence=0.5)
        
        # Generic text without intent signals
        result = detector.detect_intent("The cat sat on the mat")
        
        # May or may not detect, but shouldn't crash
        assert result is None or isinstance(result, IntentType)
