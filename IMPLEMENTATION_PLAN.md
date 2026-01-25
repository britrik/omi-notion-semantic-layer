# Implementation Plan: OMI-to-Notion Semantic Intelligence Layer

This document outlines the complete implementation plan for building the codebase as specified in the project documentation.

---

## Table of Contents

1. [Requirements Summary](#requirements-summary)
2. [Technical Design Decisions](#technical-design-decisions)
3. [Implementation Phases](#implementation-phases)
4. [Task Breakdown](#task-breakdown)
5. [File Structure](#file-structure)
6. [Testing Strategy](#testing-strategy)
7. [Definition of Done](#definition-of-done)

---

## Requirements Summary

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Ingest transcripts from OMI API (real-time webhook + batch) | High |
| FR-02 | Parse transcript segments with speaker attribution | High |
| FR-03 | Classify content into 8 categories (Action Items, Insights, Decisions, Questions, Discussions, Knowledge, Ideas, Meetings) | High |
| FR-04 | Extract named entities (people, organizations, dates, topics) | High |
| FR-05 | Perform sentiment and intent analysis | Medium |
| FR-06 | Calculate relevance score using weighted formula | High |
| FR-07 | Filter content based on quality thresholds | High |
| FR-08 | Generate automatic summaries (one-liner, executive, detailed) | Medium |
| FR-09 | Create/update Notion database entries with 15+ properties | High |
| FR-10 | Map relationships between related insights | Medium |
| FR-11 | Support both real-time and batch processing modes | High |
| FR-12 | Provide comprehensive logging and error handling | High |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Processing time per transcript | < 30 seconds |
| NFR-02 | Classification accuracy | > 95% |
| NFR-03 | API failure rate | < 5% |
| NFR-04 | User-rated relevance | > 80% |
| NFR-05 | Support Python 3.9+ | Required |
| NFR-06 | Configurable via environment variables | Required |

### External Dependencies

| Service | Purpose | Required |
|---------|---------|----------|
| OMI API | Transcript source | Yes |
| Notion API | Data destination | Yes |
| OpenAI API | Advanced NLP (optional) | No |
| HuggingFace | Local models (optional) | No |

---

## Technical Design Decisions

### Language & Runtime
- **Python 3.9+** - Primary implementation language
- Rationale: Better NLP ecosystem (SpaCy, Transformers), clearer async patterns for API calls

### Architecture Pattern
- **Modular pipeline architecture** with clear stage separation
- Each stage is a separate module that can be tested independently
- Dependency injection for API clients (enables testing with mocks)

### NLP Approach
- **SpaCy** for entity extraction (fast, accurate, offline capable)
- **Transformers** for classification and summarization
- **Optional OpenAI fallback** for enhanced quality when available

### Configuration Management
- **python-dotenv** for environment variables
- **Pydantic** for configuration validation and type safety

### API Integration
- **notion-client** (official SDK) for Notion operations
- **requests/httpx** for OMI API calls
- Retry logic with exponential backoff for resilience

### Processing Modes
- **Real-time**: Webhook-based, processes immediately on receipt
- **Batch**: Scheduled/manual, processes multiple transcripts

---

## Implementation Phases

### Phase 1: Project Foundation
Setup project structure, configuration, and core utilities.

### Phase 2: API Clients
Implement OMI and Notion API integrations.

### Phase 3: Semantic Processing
Build NLP pipeline for classification, entity extraction, and analysis.

### Phase 4: Quality & Enrichment
Implement filtering logic, scoring, and metadata generation.

### Phase 5: Pipeline Integration
Connect all components into working pipeline with both processing modes.

### Phase 6: Testing & Hardening
Comprehensive tests, error handling, and documentation.

---

## Task Breakdown

### Phase 1: Project Foundation (8 tasks)

#### 1.1 Create Project Configuration Files
- [ ] Create `requirements.txt` with all dependencies
- [ ] Create `.env.example` with documented configuration options
- [ ] Create `.gitignore` for Python project

#### 1.2 Setup Source Directory Structure
- [ ] Create `src/` directory
- [ ] Create `src/utils/` subdirectory
- [ ] Create `tests/` directory
- [ ] Create `logs/` directory (with .gitkeep)

#### 1.3 Implement Configuration Module
- [ ] Create `src/utils/config.py`
  - Load environment variables with python-dotenv
  - Pydantic models for configuration validation
  - Settings for OMI, Notion, processing thresholds
  - Support for different environments (dev/prod)

#### 1.4 Implement Logging Module
- [ ] Create `src/utils/logger.py`
  - Structured logging with timestamps
  - Multiple log levels (DEBUG, INFO, WARNING, ERROR)
  - File and console handlers
  - Separate log files per component (processor, notion, omi, errors)

#### 1.5 Create Base Exception Classes
- [ ] Create `src/utils/exceptions.py`
  - OMIAPIError
  - NotionAPIError
  - ProcessingError
  - ValidationError
  - ConfigurationError

#### 1.6 Create Data Models
- [ ] Create `src/models/` directory
- [ ] Create `src/models/transcript.py`
  - Pydantic models for Transcript, Segment, Metadata
- [ ] Create `src/models/insight.py`
  - Pydantic models for ProcessedInsight, Entity, Classification
- [ ] Create `src/models/notion.py`
  - Pydantic models for NotionPage properties

---

### Phase 2: API Clients (6 tasks)

#### 2.1 Implement OMI Client
- [ ] Create `src/omi_client.py`
  - Initialize with API key and base URL
  - Method: `fetch_transcript(transcript_id)` - Get single transcript
  - Method: `fetch_transcripts(since, limit)` - Batch fetch
  - Method: `validate_webhook_signature(payload, signature)` - Security
  - Retry logic with exponential backoff
  - Proper error handling and logging

#### 2.2 Implement Notion Client
- [ ] Create `src/notion_client.py`
  - Initialize with API key and database ID
  - Method: `create_page(insight)` - Create new insight page
  - Method: `update_page(page_id, insight)` - Update existing page
  - Method: `find_duplicate(transcript_id)` - Check for existing entries
  - Method: `query_related(tags, entities)` - Find related pages
  - Method: `validate_database_schema()` - Verify database setup
  - Property mapping from Insight model to Notion format

#### 2.3 Create API Client Tests
- [ ] Create `tests/test_omi_client.py`
  - Mock API responses
  - Test successful fetch scenarios
  - Test error handling (401, 404, 500)
  - Test retry logic
- [ ] Create `tests/test_notion_client.py`
  - Mock Notion API responses
  - Test page creation
  - Test duplicate detection
  - Test schema validation

---

### Phase 3: Semantic Processing (8 tasks)

#### 3.1 Implement Content Classifier
- [ ] Create `src/semantic/classifier.py`
  - Load classification model (zero-shot or fine-tuned)
  - Method: `classify(text)` - Returns list of (category, confidence) tuples
  - Support 8 categories: Action Items, Insights, Decisions, Questions, Discussions, Knowledge, Ideas, Meetings
  - Multi-label classification support
  - Confidence threshold filtering (default 0.65)

#### 3.2 Implement Entity Extractor
- [ ] Create `src/semantic/entity_extractor.py`
  - Initialize SpaCy model (en_core_web_lg)
  - Method: `extract_entities(text)` - Returns structured entities
  - Entity types: PERSON, ORG, DATE, TIME, GPE, TOPIC, PROJECT
  - Coreference resolution for pronouns
  - Deduplication of extracted entities

#### 3.3 Implement Sentiment Analyzer
- [ ] Create `src/semantic/sentiment.py`
  - Load sentiment analysis model
  - Method: `analyze(text)` - Returns sentiment (positive/neutral/negative)
  - Method: `detect_urgency(text)` - Returns urgency level
  - Method: `detect_emotional_tone(text)` - Returns tone indicators

#### 3.4 Implement Intent Detector
- [ ] Create `src/semantic/intent.py`
  - Method: `detect_intent(text)` - Returns primary intent
  - Intent categories: Informational, Actionable, Exploratory, Collaborative, Reflective
  - Pattern-based detection with ML fallback

#### 3.5 Implement Summarizer
- [ ] Create `src/semantic/summarizer.py`
  - Load summarization model
  - Method: `generate_title(text, max_chars=100)` - One-liner summary
  - Method: `generate_executive_summary(text, max_chars=500)` - Bullet points
  - Method: `generate_detailed_synopsis(text, max_chars=2000)` - Full overview
  - Preserve key information and speaker attribution

#### 3.6 Create Semantic Processor Facade
- [ ] Create `src/semantic_processor.py`
  - Orchestrate all semantic analysis components
  - Method: `process(transcript)` - Full semantic analysis
  - Returns ProcessedInsight with all extracted data
  - Lazy loading of models (load on first use)
  - Caching for repeated analysis

#### 3.7 Create Semantic Processing Tests
- [ ] Create `tests/test_classifier.py`
- [ ] Create `tests/test_entity_extractor.py`
- [ ] Create `tests/test_summarizer.py`
- [ ] Create `tests/test_semantic_processor.py`
  - Test with sample transcripts
  - Verify classification accuracy
  - Verify entity extraction quality

---

### Phase 4: Quality & Enrichment (5 tasks)

#### 4.1 Implement Quality Filter
- [ ] Create `src/quality_filter.py`
  - Method: `calculate_relevance_score(insight)` - Weighted scoring
    - Information Density (25%)
    - Actionability (20%)
    - Novelty (20%)
    - Clarity (15%)
    - Specificity (10%)
    - Temporal Relevance (10%)
  - Method: `check_completeness(insight)` - Verify minimum standards
  - Method: `filter_noise(text)` - Remove low-value content
  - Method: `should_sync(insight)` - Final decision based on thresholds
  - Configurable thresholds from environment

#### 4.2 Implement Enrichment Module
- [ ] Create `src/enrichment.py`
  - Method: `generate_metadata(insight)` - Auto-generate properties
  - Method: `assign_priority(insight)` - Calculate priority level
  - Method: `generate_tags(insight)` - Extract topic tags
  - Method: `map_relationships(insight, existing_insights)` - Find connections
  - Method: `enrich(insight)` - Full enrichment pipeline

#### 4.3 Implement Duplicate Detector
- [ ] Create `src/utils/deduplication.py`
  - Method: `calculate_similarity(text1, text2)` - Text similarity score
  - Method: `find_duplicates(insight, threshold)` - Check against existing
  - Optional: Vector-based semantic similarity

#### 4.4 Create Quality Filter Tests
- [ ] Create `tests/test_quality_filter.py`
  - Test scoring formula
  - Test threshold filtering
  - Test noise detection
- [ ] Create `tests/test_enrichment.py`
  - Test metadata generation
  - Test priority assignment

---

### Phase 5: Pipeline Integration (6 tasks)

#### 5.1 Implement Main Pipeline
- [ ] Create `src/pipeline.py`
  - Class: `ProcessingPipeline`
  - Method: `process_transcript(transcript)` - Full pipeline
    1. Validate input
    2. Semantic processing
    3. Quality assessment
    4. Enrichment
    5. Notion sync (if passes threshold)
  - Method: `process_batch(transcripts)` - Process multiple
  - Progress tracking and logging
  - Error recovery and partial success handling

#### 5.2 Implement Real-time Processor
- [ ] Create `src/realtime_processor.py`
  - Webhook endpoint handler (compatible with Flask/FastAPI)
  - Method: `handle_webhook(payload)` - Process incoming transcript
  - Signature validation
  - Async processing support
  - Rate limiting

#### 5.3 Implement Batch Processor
- [ ] Create `src/batch_processor.py`
  - Method: `run(since, until, limit)` - Batch process transcripts
  - Progress reporting
  - Resume capability (track last processed)
  - Configurable batch size

#### 5.4 Implement Main Entry Point
- [ ] Create `src/main.py`
  - CLI interface with argparse
  - Commands:
    - `--mode realtime` - Start webhook server
    - `--mode batch` - Run batch processing
    - `--input <file>` - Process single file
    - `--debug` - Enable debug logging
  - Graceful shutdown handling
  - Status reporting

#### 5.5 Create Integration Tests
- [ ] Create `tests/test_pipeline.py`
  - End-to-end pipeline test with mocked APIs
  - Test all processing stages
- [ ] Create `tests/test_e2e.py`
  - Full integration test (requires live APIs)
  - Configurable to skip in CI

#### 5.6 Create Sample Test Data
- [ ] Create `tests/fixtures/sample_transcript.json`
- [ ] Create `tests/fixtures/sample_transcript_action_items.json`
- [ ] Create `tests/fixtures/sample_transcript_meeting.json`
- [ ] Create `tests/fixtures/expected_outputs/` directory with expected results

---

### Phase 6: Testing & Hardening (5 tasks)

#### 6.1 Setup Test Framework
- [ ] Create `pytest.ini` or `pyproject.toml` with test configuration
- [ ] Create `tests/conftest.py` with shared fixtures
- [ ] Add test dependencies to requirements.txt (pytest, pytest-cov, pytest-mock)

#### 6.2 Add Comprehensive Error Handling
- [ ] Review all modules for proper try/except blocks
- [ ] Add retry logic where appropriate
- [ ] Ensure all errors are logged with context
- [ ] Create error recovery procedures

#### 6.3 Add Input Validation
- [ ] Validate all external inputs (API responses, webhooks)
- [ ] Sanitize transcript content
- [ ] Validate configuration on startup
- [ ] Add rate limiting for API calls

#### 6.4 Create CI/CD Pipeline
- [ ] Create `.github/workflows/test.yml`
  - Run tests on push/PR
  - Code coverage reporting
  - Linting (flake8/ruff)
  - Type checking (mypy)
- [ ] Create `.github/workflows/release.yml` (optional)

#### 6.5 Final Documentation Updates
- [ ] Update README.md with actual usage instructions
- [ ] Add inline code documentation (docstrings)
- [ ] Create CHANGELOG.md
- [ ] Verify all setup instructions work

---

## File Structure

```
omi-notion-semantic-layer/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point with CLI
│   ├── pipeline.py                # Main processing pipeline
│   ├── omi_client.py              # OMI API client
│   ├── notion_client.py           # Notion API client
│   ├── semantic_processor.py      # Semantic analysis facade
│   ├── quality_filter.py          # Quality assessment & filtering
│   ├── enrichment.py              # Metadata enrichment
│   ├── realtime_processor.py      # Webhook handler
│   ├── batch_processor.py         # Batch processing
│   ├── models/
│   │   ├── __init__.py
│   │   ├── transcript.py          # Transcript data models
│   │   ├── insight.py             # Processed insight models
│   │   └── notion.py              # Notion property models
│   ├── semantic/
│   │   ├── __init__.py
│   │   ├── classifier.py          # Content classification
│   │   ├── entity_extractor.py    # Named entity extraction
│   │   ├── sentiment.py           # Sentiment analysis
│   │   ├── intent.py              # Intent detection
│   │   └── summarizer.py          # Text summarization
│   └── utils/
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       ├── logger.py              # Logging setup
│       ├── exceptions.py          # Custom exceptions
│       └── deduplication.py       # Duplicate detection
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared test fixtures
│   ├── test_omi_client.py
│   ├── test_notion_client.py
│   ├── test_classifier.py
│   ├── test_entity_extractor.py
│   ├── test_summarizer.py
│   ├── test_semantic_processor.py
│   ├── test_quality_filter.py
│   ├── test_enrichment.py
│   ├── test_pipeline.py
│   ├── test_e2e.py
│   └── fixtures/
│       ├── sample_transcript.json
│       ├── sample_transcript_action_items.json
│       ├── sample_transcript_meeting.json
│       └── expected_outputs/
├── logs/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── requirements.txt
├── pytest.ini
├── README.md
├── poc-setup.md
├── processing-methodology.md
└── IMPLEMENTATION_PLAN.md
```

---

## Testing Strategy

### Unit Tests
- Test each module in isolation
- Mock external dependencies (APIs, models)
- Target: 80%+ code coverage

### Integration Tests
- Test component interactions
- Test pipeline stages together
- Use fixture data

### End-to-End Tests
- Full pipeline with real/mock APIs
- Verify Notion page creation
- Manual verification checklist

### Test Data
- Sample transcripts covering all 8 categories
- Edge cases (empty, very long, multilingual)
- Expected output files for comparison

---

## Definition of Done

A task is complete when:

1. **Code Complete**: All specified functionality implemented
2. **Tests Pass**: Unit tests written and passing
3. **Documented**: Docstrings and inline comments added
4. **Logged**: Appropriate logging statements included
5. **Error Handled**: Proper exception handling in place
6. **Reviewed**: Code follows project conventions

The project is production-ready when:

1. All 38 tasks completed
2. All tests passing with >80% coverage
3. Successfully processes sample transcripts end-to-end
4. Documentation updated and accurate
5. CI/CD pipeline operational
6. No critical/high severity bugs

---

## Summary Statistics

| Phase | Tasks | Estimated Complexity |
|-------|-------|---------------------|
| Phase 1: Foundation | 8 | Low |
| Phase 2: API Clients | 6 | Medium |
| Phase 3: Semantic Processing | 8 | High |
| Phase 4: Quality & Enrichment | 5 | Medium |
| Phase 5: Pipeline Integration | 6 | Medium |
| Phase 6: Testing & Hardening | 5 | Medium |
| **Total** | **38** | |

---

*Plan Version: 1.0*
*Created: January 2026*
*Based on: README.md, poc-setup.md, processing-methodology.md*
