"""
Tests for the entity extractor.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.models.insight import Entity, EntityType
from src.semantic.entity_extractor import EntityExtractor


class MockSpacyEntity:
    """Mock SpaCy entity."""

    def __init__(
        self,
        text: str,
        label: str,
        start_char: int = 0,
        end_char: int = 0,
    ) -> None:
        self.text = text
        self.label_ = label
        self.start_char = start_char
        self.end_char = end_char or len(text)


class MockSpacyDoc:
    """Mock SpaCy document."""

    def __init__(self, entities: list[MockSpacyEntity]) -> None:
        self.ents = entities
        self._noun_chunks: list[MagicMock] = []

    @property
    def noun_chunks(self) -> list[MagicMock]:
        return self._noun_chunks


class TestEntityExtractor:
    """Test cases for EntityExtractor."""

    @pytest.fixture
    def extractor(self) -> EntityExtractor:
        """Create an extractor instance without loading the model."""
        return EntityExtractor(
            model_name="en_core_web_lg",
            min_confidence=0.7,
        )

    def test_init_default_values(self) -> None:
        """Test extractor initialization with defaults."""
        extractor = EntityExtractor()
        assert extractor.model_name == "en_core_web_lg"
        assert extractor.min_confidence == 0.7

    def test_init_custom_values(self) -> None:
        """Test extractor initialization with custom values."""
        extractor = EntityExtractor(
            model_name="en_core_web_sm",
            min_confidence=0.8,
        )
        assert extractor.model_name == "en_core_web_sm"
        assert extractor.min_confidence == 0.8

    def test_is_loaded_false_initially(self, extractor: EntityExtractor) -> None:
        """Test that model is not loaded initially."""
        assert extractor.is_loaded() is False

    @patch("spacy.load")
    def test_extract_entities_success(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test successful entity extraction."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("John Smith", "PERSON", 0, 10),
            MockSpacyEntity("Acme Corp", "ORG", 15, 24),
            MockSpacyEntity("next Friday", "DATE", 30, 41),
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        entities = extractor.extract_entities(
            "John Smith from Acme Corp will present next Friday"
        )

        assert len(entities) >= 3
        
        person_entities = [e for e in entities if e.type == EntityType.PERSON]
        assert len(person_entities) >= 1
        assert any(e.text == "John Smith" for e in person_entities)

    @patch("spacy.load")
    def test_extract_entities_empty_text(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test extraction with empty text."""
        entities = extractor.extract_entities("")
        assert entities == []

        entities = extractor.extract_entities("   ")
        assert entities == []

    @patch("spacy.load")
    def test_extract_entities_by_type(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test extracting only specific entity types."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("John", "PERSON", 0, 4),
            MockSpacyEntity("Acme", "ORG", 10, 14),
            MockSpacyEntity("Friday", "DATE", 20, 26),
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        entities = extractor.extract_entities_by_type(
            "John at Acme on Friday",
            [EntityType.PERSON],
        )

        assert len(entities) >= 1
        for entity in entities:
            assert entity.type == EntityType.PERSON

    @patch("spacy.load")
    def test_extract_people(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test extracting person names."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("Alice", "PERSON", 0, 5),
            MockSpacyEntity("Bob", "PERSON", 10, 13),
            MockSpacyEntity("Acme", "ORG", 20, 24),
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        people = extractor.extract_people("Alice and Bob at Acme")

        assert "Alice" in people
        assert "Bob" in people
        assert "Acme" not in people

    @patch("spacy.load")
    def test_extract_organizations(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test extracting organization names."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("Google", "ORG", 0, 6),
            MockSpacyEntity("Microsoft", "ORG", 11, 20),
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        orgs = extractor.extract_organizations("Google and Microsoft partnership")

        assert "Google" in orgs
        assert "Microsoft" in orgs

    @patch("spacy.load")
    def test_extract_dates(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test extracting date references."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("next Friday", "DATE", 0, 11),
            MockSpacyEntity("January 15", "DATE", 15, 25),
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        dates = extractor.extract_dates("next Friday and January 15")

        assert "next Friday" in dates
        assert "January 15" in dates

    @patch("spacy.load")
    def test_get_entity_summary(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test getting entity summary grouped by type."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("John", "PERSON", 0, 4),
            MockSpacyEntity("Google", "ORG", 8, 14),
            MockSpacyEntity("Friday", "DATE", 20, 26),
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        summary = extractor.get_entity_summary("John at Google on Friday")

        assert EntityType.PERSON.value in summary
        assert EntityType.ORGANIZATION.value in summary
        assert EntityType.DATE.value in summary

    @patch("spacy.load")
    def test_deduplicates_entities(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test that duplicate entities are removed."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("John", "PERSON", 0, 4),
            MockSpacyEntity("john", "PERSON", 10, 14),  # Same person, different case
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        entities = extractor.extract_entities("John meets john again")

        person_entities = [e for e in entities if e.type == EntityType.PERSON]
        assert len(person_entities) == 1

    @patch("spacy.load")
    def test_extract_projects(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test extracting project names from text."""
        mock_doc = MockSpacyDoc([])  # No SpaCy entities
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        entities = extractor.extract_entities(
            "We're working on Project Phoenix and the Apollo initiative"
        )

        project_entities = [e for e in entities if e.type == EntityType.PROJECT]
        assert len(project_entities) >= 1

    @patch("spacy.load")
    def test_extract_topics(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test extracting topic keywords from text."""
        mock_doc = MockSpacyDoc([])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        entities = extractor.extract_entities(
            "The deadline for the budget review is next week"
        )

        topic_entities = [e for e in entities if e.type == EntityType.TOPIC]
        topic_texts = [e.normalized or e.text for e in topic_entities]
        
        assert any("deadline" in t.lower() for t in topic_texts) or \
               any("budget" in t.lower() for t in topic_texts)

    @patch("spacy.load")
    def test_unload(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test unloading the model."""
        mock_spacy.load.return_value = MagicMock()
        
        # Load the model first
        _ = extractor.nlp
        assert extractor.is_loaded() is True

        # Unload
        extractor.unload()
        assert extractor.is_loaded() is False

    @patch("spacy.load")
    def test_entity_normalization(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test that entities are normalized correctly."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("john smith", "PERSON", 0, 10),
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        entities = extractor.extract_entities("john smith is here")

        person_entities = [e for e in entities if e.type == EntityType.PERSON]
        assert len(person_entities) == 1
        assert person_entities[0].normalized == "John Smith"

    @patch("spacy.load")
    def test_include_custom_false(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test extracting without custom entities."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("John", "PERSON", 0, 4),
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        entities = extractor.extract_entities(
            "John on Project Apollo deadline",
            include_custom=False,
        )

        # Should only have SpaCy entities, not custom PROJECT/TOPIC
        project_entities = [e for e in entities if e.type == EntityType.PROJECT]
        assert len(project_entities) == 0

    @patch("spacy.load")
    def test_spacy_label_mapping(
        self,
        mock_spacy: MagicMock,
        extractor: EntityExtractor,
    ) -> None:
        """Test that SpaCy labels are mapped correctly."""
        mock_doc = MockSpacyDoc([
            MockSpacyEntity("New York", "GPE", 0, 8),
            MockSpacyEntity("Empire State Building", "FAC", 10, 31),
            MockSpacyEntity("$1000", "MONEY", 35, 40),
        ])
        mock_nlp = MagicMock(return_value=mock_doc)
        mock_spacy.load.return_value = mock_nlp

        entities = extractor.extract_entities("New York Empire State Building $1000")

        types = {e.type for e in entities}
        assert EntityType.LOCATION in types
        assert EntityType.MONEY in types
