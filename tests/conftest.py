"""
Pytest configuration and shared fixtures for the test suite.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.models.transcript import Segment, Transcript, TranscriptMetadata
from src.models.insight import (
    Classification,
    ContentCategory,
    Entity,
    EntityType,
    InsightStatus,
    PriorityLevel,
    ProcessedInsight,
    QualityScore,
    Summary,
)


# =============================================================================
# Path Fixtures
# =============================================================================


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_transcript_path(fixtures_dir: Path) -> Path:
    """Get path to sample transcript JSON."""
    return fixtures_dir / "sample_transcript.json"


# =============================================================================
# Transcript Fixtures
# =============================================================================


@pytest.fixture
def sample_segment() -> Segment:
    """Create a sample transcript segment."""
    return Segment(
        speaker="User",
        text="Let's discuss the project timeline.",
        timestamp=0.0,
        end_timestamp=3.0,
        confidence=0.95,
    )


@pytest.fixture
def sample_segments() -> list[Segment]:
    """Create a list of sample segments."""
    return [
        Segment(
            speaker="User",
            text="Let's discuss the project timeline.",
            timestamp=0.0,
        ),
        Segment(
            speaker="User",
            text="We need to finish the prototype by next Friday.",
            timestamp=3.0,
        ),
        Segment(
            speaker="User",
            text="I'll handle the frontend, and you can focus on the API integration.",
            timestamp=8.0,
        ),
        Segment(
            speaker="Colleague",
            text="Sounds good. When should we schedule the demo?",
            timestamp=15.0,
        ),
        Segment(
            speaker="User",
            text="We should schedule a demo for stakeholders.",
            timestamp=18.0,
        ),
    ]


@pytest.fixture
def sample_transcript(sample_segments: list[Segment]) -> Transcript:
    """Create a sample transcript."""
    return Transcript(
        transcript_id="test_001",
        timestamp=datetime(2026, 1, 6, 10, 0, 0, tzinfo=timezone.utc),
        duration=300.0,
        participants=["User", "Colleague"],
        content="Let's discuss the project timeline. We need to finish the prototype by next Friday. I'll handle the frontend, and you can focus on the API integration. Sounds good. When should we schedule the demo? We should schedule a demo for stakeholders.",
        segments=sample_segments,
        metadata=TranscriptMetadata(
            device_id="omi_device_123",
            session_id="session_456",
            language="en",
            tags=["project", "planning"],
        ),
    )


@pytest.fixture
def minimal_transcript() -> Transcript:
    """Create a minimal transcript with just required fields."""
    return Transcript(
        transcript_id="minimal_001",
        timestamp=datetime.now(timezone.utc),
        duration=60.0,
        content="This is a minimal transcript for testing.",
    )


# =============================================================================
# Insight Fixtures
# =============================================================================


@pytest.fixture
def sample_entities() -> list[Entity]:
    """Create sample extracted entities."""
    return [
        Entity(text="next Friday", type=EntityType.DATE, confidence=0.95),
        Entity(text="prototype", type=EntityType.PROJECT, confidence=0.88),
        Entity(text="stakeholders", type=EntityType.PERSON, confidence=0.75),
    ]


@pytest.fixture
def sample_classifications() -> list[Classification]:
    """Create sample classifications."""
    return [
        Classification(
            category=ContentCategory.ACTION_ITEM,
            confidence=0.85,
            reasoning="Contains explicit tasks and assignments",
        ),
        Classification(
            category=ContentCategory.MEETING,
            confidence=0.72,
            reasoning="Structured conversation with multiple participants",
        ),
    ]


@pytest.fixture
def sample_quality_score() -> QualityScore:
    """Create a sample quality score."""
    return QualityScore(
        information_density=7.5,
        actionability=8.0,
        novelty=6.0,
        clarity=8.5,
        specificity=7.0,
        temporal_relevance=9.0,
    )


@pytest.fixture
def sample_processed_insight(
    sample_transcript: Transcript,
    sample_entities: list[Entity],
    sample_classifications: list[Classification],
    sample_quality_score: QualityScore,
) -> ProcessedInsight:
    """Create a sample processed insight."""
    return ProcessedInsight(
        transcript_id=sample_transcript.transcript_id,
        source_timestamp=sample_transcript.timestamp,
        classifications=sample_classifications,
        primary_category=ContentCategory.ACTION_ITEM,
        entities=sample_entities,
        quality_score=sample_quality_score,
        summary=Summary(
            title="Project timeline discussion with deadline",
            executive="Team discussed prototype deadline for next Friday. Assigned frontend and API tasks. Demo to be scheduled for stakeholders.",
        ),
        tags=["project", "deadline", "prototype", "demo", "planning"],
        participants=sample_transcript.participants,
        priority=PriorityLevel.HIGH,
        status=InsightStatus.NEW,
        original_content=sample_transcript.content,
        confidence=0.85,
    )


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Set up mock environment variables."""
    env_vars = {
        "OMI_API_KEY": "test_omi_key",
        "OMI_API_URL": "https://api.omi.test/v1",
        "NOTION_API_KEY": "secret_test_notion_key",
        "NOTION_DATABASE_ID": "test_database_id",
        "MIN_RELEVANCE_SCORE": "5.0",
        "MIN_CONFIDENCE_THRESHOLD": "0.65",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "development",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_omi_response() -> dict[str, Any]:
    """Create a mock OMI API response."""
    return {
        "transcript_id": "omi_transcript_123",
        "timestamp": "2026-01-06T10:00:00Z",
        "duration": 300,
        "participants": ["User", "Colleague"],
        "content": "Sample transcript content.",
        "segments": [
            {"speaker": "User", "text": "Hello", "timestamp": 0},
            {"speaker": "Colleague", "text": "Hi there", "timestamp": 2},
        ],
    }


@pytest.fixture
def mock_notion_client() -> MagicMock:
    """Create a mock Notion client."""
    client = MagicMock()
    client.pages.create.return_value = {"id": "page_123", "url": "https://notion.so/page_123"}
    client.pages.update.return_value = {"id": "page_123"}
    client.databases.query.return_value = {"results": []}
    client.databases.retrieve.return_value = {
        "properties": {
            "Title": {"type": "title"},
            "Type": {"type": "select"},
            "Status": {"type": "select"},
            "Priority": {"type": "select"},
            "Date": {"type": "date"},
            "Tags": {"type": "multi_select"},
            "Source": {"type": "rich_text"},
            "Confidence": {"type": "number"},
            "Summary": {"type": "rich_text"},
            "Content": {"type": "rich_text"},
        }
    }
    return client


# =============================================================================
# Helper Functions
# =============================================================================


def load_fixture_json(fixtures_dir: Path, filename: str) -> dict[str, Any]:
    """Load a JSON fixture file."""
    filepath = fixtures_dir / filename
    if filepath.exists():
        with open(filepath) as f:
            return json.load(f)
    return {}
