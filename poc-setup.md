# POC Setup Guide

Technical setup instructions for the OMI-to-Notion Semantic Intelligence Layer proof of concept.

## 📋 Prerequisites

### Required Accounts & Access

- [ ] **OMI Account**: Access to OMI device or API
- [ ] **Notion Account**: Workspace with admin permissions
- [ ] **Development Environment**: Python 3.9+ or Node.js 16+
- [ ] **API Keys**: Both OMI and Notion integration tokens

### System Requirements

- **OS**: macOS, Linux, or Windows with WSL2
- **RAM**: Minimum 4GB, recommended 8GB
- **Storage**: 2GB free space for dependencies
- **Network**: Stable internet connection for API calls

## 🔧 Installation Steps

### 1. Clone Repository

```bash
git clone https://github.com/britrik/omi-notion-semantic-layer.git
cd omi-notion-semantic-layer
```

### 2. Environment Setup

#### Option A: Python Implementation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**requirements.txt** (create this file):
```txt
notion-client==2.2.1
requests==2.31.0
python-dotenv==1.0.0
spacy==3.7.2
transformers==4.36.0
langchain==0.1.0
openai==1.7.0
pydantic==2.5.0
```

#### Option B: Node.js Implementation

```bash
# Initialize project (if not already done)
npm init -y

# Install dependencies
npm install @notionhq/client axios dotenv
npm install --save-dev typescript @types/node
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy example configuration
cp .env.example .env
```

**.env file structure:**
```env
# OMI Configuration
OMI_API_KEY=your_omi_api_key_here
OMI_API_URL=https://api.omi.example/v1
OMI_WEBHOOK_SECRET=your_webhook_secret

# Notion Configuration
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_DATABASE_ID=your_database_id_here
NOTION_VERSION=2022-06-28

# Processing Configuration
MIN_RELEVANCE_SCORE=5.0
MIN_CONFIDENCE_THRESHOLD=0.65
BATCH_SIZE=10
PROCESSING_MODE=realtime  # or 'batch'

# Optional: AI/ML Services
OPENAI_API_KEY=your_openai_key  # for advanced NLP
HUGGINGFACE_TOKEN=your_hf_token  # for local models

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/processor.log
```

### 4. Notion Database Setup

#### Create Integration

1. Go to https://www.notion.so/my-integrations
2. Click "+ New integration"
3. Name it "OMI Semantic Layer"
4. Select your workspace
5. Copy the "Internal Integration Token"

#### Create Database

1. In Notion, create a new database
2. Name it "OMI Insights"
3. Add the following properties:

**Required Properties:**

| Property Name | Type | Options/Details |
|--------------|------|------------------|
| Title | Title | Auto-populated |
| Type | Select | Action Item, Insight, Decision, Question, Discussion, Knowledge, Idea, Meeting |
| Status | Select | New, In Progress, Completed, Archived |
| Priority | Select | Low, Medium, High, Critical |
| Date | Date | Original conversation date |
| Tags | Multi-select | Auto-populated from content |
| Source | Text | OMI session ID |
| Confidence | Number | 0.0 - 1.0 |
| Participants | Multi-select | People involved |
| Summary | Text | Brief overview |
| Content | Rich text | Full processed transcript |
| Related Pages | Relation | Link to same database |

#### Connect Database to Integration

1. Open your "OMI Insights" database
2. Click "..." menu → "Connections"
3. Select "OMI Semantic Layer" integration
4. Copy the database ID from the URL:
   ```
   https://notion.so/workspace/{database_id}?v=...
   ```

### 5. OMI API Configuration

#### Obtain API Access

1. Log into OMI dashboard
2. Navigate to Settings → API Keys
3. Generate new API key with read permissions
4. Note your user/device ID

#### Configure Webhook (Optional for Real-time)

```bash
# Set webhook URL for OMI to send transcripts
Webhook URL: https://your-domain.com/api/omi-webhook
Events: transcript.completed
```

### 6. NLP Model Setup

#### Download SpaCy Model (Python)

```bash
python -m spacy download en_core_web_lg
```

#### Initialize Local Models (Optional)

```python
# Download transformer models for local processing
from transformers import pipeline

# Sentiment analysis
sentiment = pipeline("sentiment-analysis")

# Text classification
classifier = pipeline("zero-shot-classification")

# Summarization
summarizer = pipeline("summarization")
```

## 🚀 Running the POC

### Development Mode

#### Python:

```bash
# Start the processor
python src/main.py

# Or with specific mode
python src/main.py --mode batch
python src/main.py --mode realtime
```

#### Node.js:

```bash
# Start the processor
node src/index.js

# Or with nodemon for development
npm run dev
```

### Testing the Pipeline

#### 1. Test with Sample Transcript

```bash
# Run test script
python tests/test_pipeline.py

# Or use sample data
python src/main.py --input tests/sample_transcript.json
```

**Sample transcript format** (tests/sample_transcript.json):
```json
{
  "transcript_id": "test_001",
  "timestamp": "2026-01-06T00:00:00Z",
  "duration": 300,
  "participants": ["User", "Colleague"],
  "content": "Let's discuss the project timeline. We need to finish the prototype by next Friday. I'll handle the frontend, and you can focus on the API integration. We should also schedule a demo for stakeholders.",
  "segments": [
    {"speaker": "User", "text": "Let's discuss the project timeline.", "timestamp": 0},
    {"speaker": "User", "text": "We need to finish the prototype by next Friday.", "timestamp": 3},
    {"speaker": "User", "text": "I'll handle the frontend, and you can focus on the API integration.", "timestamp": 8},
    {"speaker": "Colleague", "text": "Sounds good. When should we schedule the demo?", "timestamp": 15},
    {"speaker": "User", "text": "We should schedule a demo for stakeholders.", "timestamp": 18}
  ]
}
```

#### 2. Verify Notion Integration

```bash
# Test Notion connection
python tests/test_notion.py

# Should output:
# ✓ Connection successful
# ✓ Database accessible
# ✓ Properties validated
```

#### 3. End-to-End Test

```bash
# Process sample and verify in Notion
python tests/test_e2e.py

# Check Notion database for new entry
```

## 📁 Project Structure

```
omi-notion-semantic-layer/
├── src/
│   ├── main.py                 # Entry point
│   ├── omi_client.py          # OMI API integration
│   ├── notion_client.py       # Notion API integration
│   ├── semantic_processor.py  # NLP and analysis
│   ├── quality_filter.py      # Assessment logic
│   ├── enrichment.py          # Metadata generation
│   └── utils/
│       ├── config.py           # Configuration management
│       └── logger.py           # Logging setup
├── tests/
│   ├── test_pipeline.py       # Pipeline tests
│   ├── test_notion.py         # Notion integration tests
│   ├── test_e2e.py            # End-to-end tests
│   └── sample_transcript.json # Test data
├── logs/                       # Log files
├── .env                        # Environment variables
├── .env.example               # Example configuration
├── requirements.txt           # Python dependencies
├── package.json               # Node.js dependencies
├── README.md                  # Project overview
├── processing-methodology.md  # Assessment criteria
└── poc-setup.md              # This file
```

## 🔍 Troubleshooting

### Common Issues

#### OMI API Connection

**Error**: `401 Unauthorized`
- Verify API key is correct in `.env`
- Check key hasn't expired
- Ensure proper permissions granted

**Error**: `404 Not Found`
- Confirm API URL endpoint
- Check OMI account status

#### Notion API Issues

**Error**: `object_not_found`
- Verify database ID is correct
- Ensure integration is connected to database
- Check integration has read/write permissions

**Error**: `validation_error`
- Review database property types
- Ensure property names match exactly
- Check value formats (dates, numbers, etc.)

#### Processing Errors

**Error**: Model download fails
- Check internet connection
- Try manual download
- Use alternative model weights

**Error**: Out of memory
- Reduce batch size in `.env`
- Use smaller NLP models
- Process transcripts sequentially

### Debug Mode

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python src/main.py --debug

# Check logs
tail -f logs/processor.log
```

## 📊 Monitoring & Logging

### Log Files

- **processor.log**: Main processing events
- **notion.log**: Notion API calls and responses
- **omi.log**: OMI API interactions
- **errors.log**: Error tracking

### Metrics Dashboard (Future)

```bash
# Start metrics server
python src/metrics_server.py

# View at http://localhost:8080/metrics
```

## 🔐 Security Best Practices

1. **Never commit `.env` file** to version control
2. **Rotate API keys** regularly (every 90 days)
3. **Use webhook secrets** to verify OMI requests
4. **Implement rate limiting** to prevent abuse
5. **Sanitize transcript content** before processing
6. **Encrypt logs** containing sensitive data

## 🚦 Next Steps

1. ✅ Complete setup steps above
2. ✅ Test with sample data
3. ✅ Process first real OMI transcript
4. ✅ Review results in Notion
5. ✅ Adjust filters and thresholds in `.env`
6. ✅ Set up automated processing (cron/scheduler)
7. ✅ Implement monitoring and alerts

## 📚 Additional Resources

- [OMI API Documentation](https://omi.example/docs)
- [Notion API Reference](https://developers.notion.com)
- [SpaCy Documentation](https://spacy.io/usage)
- [Project GitHub Issues](https://github.com/britrik/omi-notion-semantic-layer/issues)

## 💬 Support

For setup issues:
1. Check troubleshooting section above
2. Review logs for error messages
3. Open an issue on GitHub with details

---

**Setup Version**: 1.0  
**Last Updated**: January 2026  
**Tested On**: Python 3.11, Node.js 18