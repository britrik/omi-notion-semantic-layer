"""
Entity extractor for transcript analysis.

Uses SpaCy for named entity recognition with support for
custom entity types relevant to conversation analysis.
"""

import logging
import re
from collections import Counter
from typing import Optional

from src.models.insight import Entity, EntityType

logger = logging.getLogger(__name__)


# Mapping from SpaCy entity labels to our EntityType
SPACY_TO_ENTITY_TYPE: dict[str, EntityType] = {
    "PERSON": EntityType.PERSON,
    "ORG": EntityType.ORGANIZATION,
    "GPE": EntityType.LOCATION,
    "LOC": EntityType.LOCATION,
    "DATE": EntityType.DATE,
    "TIME": EntityType.TIME,
    "MONEY": EntityType.MONEY,
    "PERCENT": EntityType.PERCENT,
    "EVENT": EntityType.EVENT,
    "PRODUCT": EntityType.PRODUCT,
    "WORK_OF_ART": EntityType.PRODUCT,
    "FAC": EntityType.LOCATION,
}

# Patterns for custom entity extraction
PROJECT_PATTERNS = [
    r"\b(?:project|initiative|program)\s+([A-Z][a-zA-Z0-9\s-]+)",
    r"\b([A-Z][a-zA-Z0-9]+)\s+(?:project|initiative|program)\b",
]

TOPIC_KEYWORDS = [
    "budget", "deadline", "timeline", "milestone", "release",
    "sprint", "planning", "review", "retrospective", "standup",
    "meeting", "presentation", "demo", "launch", "deployment",
]


class EntityExtractor:
    """
    Extracts named entities from text using SpaCy.
    
    Supports standard NER entities plus custom extraction for
    topics and project names relevant to conversation analysis.
    """

    def __init__(
        self,
        model_name: str = "en_core_web_lg",
        min_confidence: float = 0.7,
    ) -> None:
        """
        Initialize the entity extractor.

        Args:
            model_name: SpaCy model to use (en_core_web_sm, en_core_web_md, en_core_web_lg)
            min_confidence: Minimum confidence for entity extraction (0.0-1.0)
        """
        self.model_name = model_name
        self.min_confidence = min_confidence
        self._nlp: Optional[object] = None

    @property
    def nlp(self) -> object:
        """Lazy load the SpaCy model."""
        if self._nlp is None:
            self._nlp = self._load_model()
        return self._nlp

    def _load_model(self) -> object:
        """Load the SpaCy NLP model."""
        try:
            import spacy

            logger.info("Loading SpaCy model: %s", self.model_name)
            
            try:
                nlp = spacy.load(self.model_name)
            except OSError:
                logger.warning(
                    "Model %s not found, downloading...", self.model_name
                )
                from spacy.cli import download
                download(self.model_name)
                nlp = spacy.load(self.model_name)
            
            logger.info("SpaCy model loaded successfully")
            return nlp
            
        except Exception as e:
            logger.error("Failed to load SpaCy model: %s", e)
            raise RuntimeError(f"Failed to load SpaCy model: {e}") from e

    def extract_entities(
        self,
        text: str,
        include_custom: bool = True,
    ) -> list[Entity]:
        """
        Extract named entities from text.

        Args:
            text: Text to analyze
            include_custom: Include custom entity types (topics, projects)

        Returns:
            List of Entity objects, deduplicated
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for entity extraction")
            return []

        text = text.strip()
        
        try:
            doc = self.nlp(text)
            entities: list[Entity] = []

            # Extract SpaCy entities
            for ent in doc.ents:
                entity_type = SPACY_TO_ENTITY_TYPE.get(ent.label_)
                if entity_type:
                    entity = Entity(
                        text=ent.text,
                        type=entity_type,
                        normalized=self._normalize_entity(ent.text, entity_type),
                        start_char=ent.start_char,
                        end_char=ent.end_char,
                        confidence=0.9,  # SpaCy doesn't provide confidence scores
                        metadata={"spacy_label": ent.label_},
                    )
                    entities.append(entity)

            # Extract custom entities if enabled
            if include_custom:
                entities.extend(self._extract_projects(text))
                entities.extend(self._extract_topics(text, doc))

            # Filter entities by min_confidence
            entities = [e for e in entities if e.confidence >= self.min_confidence]

            # Deduplicate entities
            entities = self._deduplicate_entities(entities)

            logger.debug("Extracted %d entities from text", len(entities))
            return entities

        except Exception as e:
            logger.error("Entity extraction failed: %s", e)
            raise RuntimeError(f"Entity extraction failed: {e}") from e

    def extract_entities_by_type(
        self,
        text: str,
        entity_types: list[EntityType],
    ) -> list[Entity]:
        """
        Extract only specific entity types.

        Args:
            text: Text to analyze
            entity_types: List of EntityTypes to extract

        Returns:
            Filtered list of Entity objects
        """
        all_entities = self.extract_entities(text)
        return [e for e in all_entities if e.type in entity_types]

    def extract_people(self, text: str) -> list[str]:
        """
        Extract person names from text.

        Args:
            text: Text to analyze

        Returns:
            List of unique person names
        """
        entities = self.extract_entities_by_type(text, [EntityType.PERSON])
        return list(set(e.normalized or e.text for e in entities))

    def extract_organizations(self, text: str) -> list[str]:
        """
        Extract organization names from text.

        Args:
            text: Text to analyze

        Returns:
            List of unique organization names
        """
        entities = self.extract_entities_by_type(text, [EntityType.ORGANIZATION])
        return list(set(e.normalized or e.text for e in entities))

    def extract_dates(self, text: str) -> list[str]:
        """
        Extract date references from text.

        Args:
            text: Text to analyze

        Returns:
            List of date strings
        """
        entities = self.extract_entities_by_type(text, [EntityType.DATE])
        return [e.text for e in entities]

    def _extract_projects(self, text: str) -> list[Entity]:
        """Extract project names using regex patterns."""
        entities = []
        
        for pattern in PROJECT_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                project_name = match.group(1).strip()
                if len(project_name) >= 2:  # Minimum length filter
                    entities.append(
                        Entity(
                            text=project_name,
                            type=EntityType.PROJECT,
                            normalized=project_name.title(),
                            start_char=match.start(1),
                            end_char=match.end(1),
                            confidence=0.75,
                            metadata={"extraction_method": "regex"},
                        )
                    )
        
        return entities

    def _extract_topics(self, text: str, doc: object) -> list[Entity]:
        """Extract topic keywords from text."""
        entities = []
        text_lower = text.lower()
        
        for keyword in TOPIC_KEYWORDS:
            if keyword in text_lower:
                # Find the position in original text
                start = text_lower.find(keyword)
                if start != -1:
                    original_word = text[start:start + len(keyword)]
                    entities.append(
                        Entity(
                            text=original_word,
                            type=EntityType.TOPIC,
                            normalized=keyword.title(),
                            start_char=start,
                            end_char=start + len(keyword),
                            confidence=0.8,
                            metadata={"extraction_method": "keyword"},
                        )
                    )
        
        # Extract noun phrases as potential topics
        if hasattr(doc, "noun_chunks"):
            for chunk in doc.noun_chunks:
                # Filter to significant noun phrases
                if len(chunk.text) > 3 and chunk.root.pos_ in ("NOUN", "PROPN"):
                    # Avoid already extracted entities
                    if not any(
                        chunk.start_char == e.start_char for e in entities
                    ):
                        entities.append(
                            Entity(
                                text=chunk.text,
                                type=EntityType.TOPIC,
                                normalized=chunk.text.title(),
                                start_char=chunk.start_char,
                                end_char=chunk.end_char,
                                confidence=0.6,
                                metadata={"extraction_method": "noun_chunk"},
                            )
                        )
        
        return entities

    def _normalize_entity(self, text: str, entity_type: EntityType) -> str:
        """Normalize entity text based on type."""
        text = text.strip()
        
        if entity_type == EntityType.PERSON:
            # Title case for names
            return text.title()
        elif entity_type == EntityType.ORGANIZATION:
            # Preserve original casing for orgs (acronyms, etc.)
            return text
        elif entity_type in (EntityType.DATE, EntityType.TIME):
            # Keep as-is for dates/times
            return text.lower()
        else:
            return text.title()

    def _deduplicate_entities(self, entities: list[Entity]) -> list[Entity]:
        """
        Remove duplicate entities, keeping highest confidence.
        
        Uses text + type as the deduplication key.
        """
        seen: dict[tuple[str, EntityType], Entity] = {}
        
        for entity in entities:
            key = (entity.text.lower(), entity.type)
            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity
        
        return list(seen.values())

    def get_entity_summary(self, text: str) -> dict[str, list[str]]:
        """
        Get a summary of entities grouped by type.

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping entity type names to lists of entities
        """
        entities = self.extract_entities(text)
        summary: dict[str, list[str]] = {}
        
        for entity in entities:
            type_name = entity.type.value
            if type_name not in summary:
                summary[type_name] = []
            
            normalized = entity.normalized or entity.text
            if normalized not in summary[type_name]:
                summary[type_name].append(normalized)
        
        return summary

    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._nlp is not None

    def unload(self) -> None:
        """Unload the model to free memory."""
        self._nlp = None
        logger.info("SpaCy model unloaded")
