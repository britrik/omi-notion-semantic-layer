"""
Data models for OMI transcripts.

These models represent the input data structure from OMI devices/API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class Segment(BaseModel):
    """
    A single segment of a transcript.

    Represents one utterance from a speaker with timing information.
    """

    speaker: str = Field(
        description="Speaker identifier or name"
    )
    text: str = Field(
        description="The spoken text content"
    )
    timestamp: float = Field(
        ge=0,
        description="Offset in seconds from transcript start"
    )
    end_timestamp: Optional[float] = Field(
        default=None,
        ge=0,
        description="End offset in seconds (optional)"
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Transcription confidence score"
    )

    @property
    def duration(self) -> Optional[float]:
        """Calculate segment duration if end timestamp is available."""
        if self.end_timestamp is not None:
            return self.end_timestamp - self.timestamp
        return None

    @field_validator("text")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace from text."""
        return v.strip()


class TranscriptMetadata(BaseModel):
    """
    Metadata associated with a transcript.

    Contains additional context about the recording/conversation.
    """

    device_id: Optional[str] = Field(
        default=None,
        description="OMI device identifier"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Recording session identifier"
    )
    language: str = Field(
        default="en",
        description="Primary language of the transcript"
    )
    location: Optional[str] = Field(
        default=None,
        description="Location where conversation took place"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="User-defined tags"
    )
    custom: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata fields"
    )


class Transcript(BaseModel):
    """
    A complete transcript from OMI.

    This is the primary input model for the processing pipeline.
    """

    transcript_id: str = Field(
        description="Unique identifier for the transcript"
    )
    timestamp: datetime = Field(
        description="When the conversation occurred"
    )
    duration: float = Field(
        ge=0,
        description="Total duration in seconds"
    )
    participants: list[str] = Field(
        default_factory=list,
        description="List of participant identifiers"
    )
    content: str = Field(
        description="Full transcript text content"
    )
    segments: list[Segment] = Field(
        default_factory=list,
        description="Individual transcript segments with speaker info"
    )
    metadata: TranscriptMetadata = Field(
        default_factory=TranscriptMetadata,
        description="Additional transcript metadata"
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not empty or whitespace only."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Transcript content cannot be empty")
        return stripped

    @property
    def word_count(self) -> int:
        """Count words in the transcript content."""
        return len(self.content.split())

    @property
    def segment_count(self) -> int:
        """Count number of segments."""
        return len(self.segments)

    @property
    def speaker_count(self) -> int:
        """Count unique speakers in segments."""
        if not self.segments:
            return len(self.participants)
        return len(set(seg.speaker for seg in self.segments))

    @property
    def speakers(self) -> list[str]:
        """Get list of unique speakers."""
        if not self.segments:
            return self.participants
        return list(set(seg.speaker for seg in self.segments))

    def get_speaker_text(self, speaker: str) -> str:
        """
        Get all text from a specific speaker.

        Args:
            speaker: Speaker identifier to filter by

        Returns:
            Concatenated text from the specified speaker
        """
        return " ".join(
            seg.text for seg in self.segments if seg.speaker == speaker
        )

    def get_text_by_time_range(
        self,
        start: float,
        end: float
    ) -> str:
        """
        Get transcript text within a time range.

        Args:
            start: Start time in seconds
            end: End time in seconds

        Returns:
            Concatenated text from segments within the time range
        """
        return " ".join(
            seg.text
            for seg in self.segments
            if start <= seg.timestamp <= end
        )

    def to_plain_text(self, include_speakers: bool = True) -> str:
        """
        Convert transcript to plain text format.

        Args:
            include_speakers: Include speaker labels

        Returns:
            Formatted plain text representation
        """
        if not self.segments:
            return self.content

        lines = []
        for seg in self.segments:
            if include_speakers:
                lines.append(f"{seg.speaker}: {seg.text}")
            else:
                lines.append(seg.text)

        return "\n".join(lines)

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "transcript_id": "test_001",
                "timestamp": "2026-01-06T10:00:00Z",
                "duration": 300,
                "participants": ["User", "Colleague"],
                "content": "Let's discuss the project timeline. We need to finish the prototype by next Friday.",
                "segments": [
                    {
                        "speaker": "User",
                        "text": "Let's discuss the project timeline.",
                        "timestamp": 0,
                    },
                    {
                        "speaker": "User",
                        "text": "We need to finish the prototype by next Friday.",
                        "timestamp": 3,
                    },
                ],
                "metadata": {
                    "device_id": "omi_device_123",
                    "language": "en",
                },
            }
        }
