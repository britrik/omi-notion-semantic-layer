"""
OMI-to-Notion Semantic Intelligence Layer

A semantic processing pipeline that transforms OMI transcripts
into structured, actionable insights within Notion databases.
"""

__version__ = "0.1.0"
__author__ = "OMI Notion Team"

from src.quality_filter import QualityFilter
from src.enrichment import EnrichmentModule
from src.utils.deduplication import DuplicateDetector

__all__ = [
    "QualityFilter",
    "EnrichmentModule",
    "DuplicateDetector",
]
