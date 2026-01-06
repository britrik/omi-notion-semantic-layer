# Processing Methodology

Detailed assessment criteria and methodology for processing OMI transcripts into Notion insights.

## 📐 Processing Pipeline

### Stage 1: Transcript Ingestion

**Input Sources:**
- OMI device real-time streams
- Historical transcript archives
- API-based batch imports

**Data Structure Expected:**
```json
{
  "transcript_id": "unique_id",
  "timestamp": "ISO-8601",
  "duration": "seconds",
  "participants": ["speaker_ids"],
  "content": "full transcript text",
  "segments": [
    {
      "speaker": "id",
      "text": "utterance",
      "timestamp": "offset"
    }
  ],
  "metadata": {}
}
```

### Stage 2: Semantic Analysis

#### 2.1 Content Classification

**Categories:**
- 🎯 **Action Items**: Tasks, commitments, to-dos
- 💡 **Insights**: Key learnings, realizations, discoveries
- 📝 **Decisions**: Choices made, conclusions reached
- ❓ **Questions**: Unresolved queries, research needs
- 🗣️ **Discussions**: Important conversations, debates
- 📚 **Knowledge**: Facts, information, explanations
- 🎨 **Ideas**: Creative concepts, brainstorms
- 👥 **Meetings**: Structured conversations with agenda

**Classification Approach:**
- Multi-label classification (content can belong to multiple categories)
- Confidence scoring (0.0 - 1.0)
- Minimum confidence threshold: 0.65

#### 2.2 Entity Extraction

**Entities to Identify:**
- **People**: Names, roles, relationships
- **Organizations**: Companies, institutions
- **Locations**: Places mentioned
- **Dates/Times**: Temporal references
- **Topics**: Subject matter keywords
- **Products/Projects**: Specific items discussed
- **Concepts**: Abstract ideas and themes

**Extraction Method:**
- Named Entity Recognition (NER)
- Coreference resolution
- Relationship mapping

#### 2.3 Intent & Sentiment Analysis

**Intent Categories:**
- Informational
- Actionable
- Exploratory
- Collaborative
- Reflective

**Sentiment Scoring:**
- Overall sentiment: positive/neutral/negative
- Emotional tone: confident, uncertain, enthusiastic, etc.
- Urgency level: low/medium/high/critical

### Stage 3: Quality Assessment

## ⚖️ Assessment Criteria

### 3.1 Relevance Scoring

**Factors Considered:**

| Factor | Weight | Description |
|--------|--------|-------------|
| Information Density | 25% | Amount of meaningful content per unit |
| Actionability | 20% | Presence of concrete next steps |
| Novelty | 20% | New information vs. redundant content |
| Clarity | 15% | How well-articulated the content is |
| Specificity | 10% | Concrete vs. vague information |
| Temporal Relevance | 10% | Time-sensitivity of content |

**Scoring Formula:**
```
Relevance Score = Σ(Factor_Value × Weight)
Range: 0.0 - 10.0
```

**Thresholds:**
- ≥ 7.0: High priority, immediate sync to Notion
- 5.0 - 6.9: Medium priority, batch sync
- 3.0 - 4.9: Low priority, archive for potential future use
- < 3.0: Discard or minimal logging

### 3.2 Completeness Check

**Required Elements:**
- [ ] Clear context (what is being discussed)
- [ ] Sufficient detail (not just fragments)
- [ ] Coherent narrative (logical flow)
- [ ] Identifiable participants (who said what)
- [ ] Time reference (when did this occur)

**Minimum Standards:**
- At least 3 complete sentences OR
- At least 1 clear action item OR
- At least 1 significant insight/decision

### 3.3 Noise Filtering

**Exclude:**
- Pure small talk with no substance
- Transcription errors and garbled text
- Repetitive content already captured
- Private/sensitive content (based on user settings)
- Technical artifacts (audio glitches, background noise transcription)

**Include:**
- Casual conversations that contain insights
- Brief but impactful exchanges
- Follow-ups to previous conversations

### Stage 4: Enrichment

#### 4.1 Metadata Generation

**Automatic Properties:**
- **Title**: Auto-generated summary (max 100 chars)
- **Tags**: Extracted topics and categories
- **Priority**: Calculated urgency level
- **Type**: Primary content classification
- **Source**: OMI device/session identifier
- **Date**: Original conversation timestamp
- **Duration**: Length of conversation
- **Participants**: Identified speakers

#### 4.2 Summarization

**Summary Types:**

1. **One-liner** (≤ 140 chars)
   - Used for quick scanning and titles
   
2. **Executive Summary** (≤ 500 chars)
   - Key points in bullet format
   
3. **Detailed Synopsis** (≤ 2000 chars)
   - Comprehensive overview with context

**Summarization Principles:**
- Preserve key information
- Maintain speaker attribution for important statements
- Include numerical data and specific details
- Remove filler and redundancy

#### 4.3 Relationship Mapping

**Connection Types:**
- **References**: Mentions of previous conversations
- **Follow-ups**: Continuation of earlier topics
- **Related Topics**: Thematically similar content
- **Project Links**: Associated with specific initiatives
- **People Networks**: Conversations involving same participants

### Stage 5: Notion Database Writing

#### 5.1 Database Schema

**Core Properties:**
- **Title** (text): Auto-generated or extracted
- **Type** (select): Content category
- **Status** (select): New/In Progress/Completed/Archived
- **Priority** (select): Low/Medium/High/Critical
- **Date** (date): Original conversation date
- **Tags** (multi-select): Topic keywords
- **Source** (text): OMI session ID
- **Confidence** (number): Processing confidence score
- **Participants** (multi-select): People involved

**Content Properties:**
- **Summary** (text): Brief overview
- **Full Content** (rich text): Complete processed transcript
- **Action Items** (checklist): Extracted tasks
- **Key Insights** (bulleted list): Main takeaways
- **Entities** (multi-select): Extracted named entities

**Metadata Properties:**
- **Created At** (date): When added to Notion
- **Updated At** (date): Last modification
- **Related Pages** (relation): Connected insights
- **Processing Version** (text): Algorithm version used

#### 5.2 Writing Strategy

**Batch Processing:**
- Group similar content types
- Create parent pages for conversation threads
- Use database relations for connections

**Update Strategy:**
- Check for duplicates before creation
- Update existing pages with new information
- Preserve user modifications

## 🔍 Quality Assurance

### Validation Checks

1. **Pre-Write Validation:**
   - Notion API connectivity
   - Database schema compatibility
   - Property value format validation

2. **Post-Write Validation:**
   - Confirm successful creation
   - Verify data integrity
   - Check relationship links

3. **Periodic Review:**
   - Audit sample of processed content
   - User feedback collection
   - Model performance metrics

### Performance Metrics

**Track:**
- Processing time per transcript
- Accuracy of classifications
- User engagement with insights
- False positive/negative rates
- API error rates

**Target KPIs:**
- 95% classification accuracy
- < 30 seconds processing time
- > 80% user-rated relevance
- < 5% API failure rate

## 🔄 Continuous Improvement

### Feedback Loop

1. **User Signals:**
   - Manual categorization changes
   - Deleted or archived insights
   - Frequently accessed content

2. **Model Retraining:**
   - Incorporate feedback weekly
   - A/B test new classification models
   - Adjust scoring weights based on usage patterns

3. **Rule Refinement:**
   - Update filtering thresholds
   - Add new categories as needed
   - Refine entity extraction rules

---

**Version**: 1.0  
**Last Updated**: January 2026  
**Next Review**: February 2026