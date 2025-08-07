# Rules Evaluator

A sophisticated tool that combines RAG (Retrieval-Augmented Generation) technology with rule-based evaluation to help businesses ensure their AI-generated content meets specific quality and compliance standards.

## Overview

Rules Evaluator ingests content from multiple sources, builds a searchable knowledge base, and then evaluates AI responses against user-defined rules. It provides detailed scoring, comprehensive reports, and actionable insights for improving AI content generation.

## Key Features

- **Multi-Source Content Ingestion**: Supports websites, local files, and cloud storage (Google Drive, OneDrive, Dropbox)
- **RAG Technology**: Uses ChromaDB vector database with OpenAI embeddings for intelligent content retrieval
- **Flexible Rule System**: Define critical, important, expected, and desirable requirements for AI responses
- **Dual AI Provider Support**: Separate AI providers for response generation and evaluation
- **Weighted Scoring**: Sophisticated scoring system with configurable weights by rule type
- **Professional Reports**: HTML, Markdown, JSON, and dashboard-compatible outputs
- **Dashboard Integration**: Seamlessly integrates with Airbais dashboard ecosystem
- **Automation API Support**: Full integration with workflow automation tools

## Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key (for embeddings and AI providers)
- Optional: Anthropic API key, cloud storage credentials

### Installation

```bash
cd rulesevaluator
pip install -r requirements.txt
```

### Basic Usage

1. **Configure your settings** in `config.yaml`:
   ```yaml
   content:
     type: "local"  # or "website" or "cloud"
     local:
       path: "./your-content-directory"
   
   ai_providers:
     response_provider:
       - name: "openai"
         api_key: "${OPENAI_API_KEY}"
         model: "gpt-4-turbo-preview"
   ```

2. **Create a rules file** in `rules/your-rules.json`:
   ```json
   {
     "prompts": [
       {
         "prompt": "Explain our return policy",
         "rules": [
           {
             "ruletype": "critical",
             "ruledescription": "Must mention the 30-day return window"
           }
         ]
       }
     ]
   }
   ```

3. **Run the evaluation**:
   ```bash
   python rulesevaluator.py rules/your-rules.json
   ```

## Rule Types and Scoring

### Rule Types

- **Critical**: Must be satisfied or entire prompt fails (score: 0)
- **Important**: Highly weighted requirements (50% of total score)
- **Expected**: Standard requirements (35% of total score)  
- **Desirable**: Nice-to-have features (15% of total score)

### Scoring System

- **Scale**: 0-100 points
- **Passing Score**: 60 (configurable)
- **Critical Rule Impact**: If any critical rule fails, entire prompt scores 0
- **Weighted Calculation**: Non-critical rules contribute based on their type weights
- **Automatic Normalization**: When not all rule types are present, weights are proportionally adjusted to sum to 100

### Weight Normalization

When a prompt doesn't have all rule types, the scoring system automatically normalizes the weights:

**Example: Prompt with only Important and Expected rules**
- Original weights: Important (50%), Expected (35%), Desirable (15%)
- Only Important and Expected present: Total weight = 85%
- Normalized weights: 
  - Important: 50/85 × 100 = **58.8%**
  - Expected: 35/85 × 100 = **41.2%**
- This ensures scores always range from 0-100

### Scoring Examples

**Example 1: All Rule Types Present**
- Critical: ✅ (allows scoring)
- Important: ✅ (50 points)
- Expected: ✅ (35 points)
- Desirable: ✅ (15 points)
- **Total: 100/100 ✅ PASSED**

**Example 2: Only Important and Expected Rules**
- Important: ✅ (58.8 points - normalized from 50%)
- Expected: ✅ (41.2 points - normalized from 35%)
- **Total: 100/100 ✅ PASSED**

**Example 3: Critical Rule Fails**
- Critical: ❌ (automatic failure)
- Important: ✅ (ignored)
- Expected: ✅ (ignored)
- Desirable: ✅ (ignored)
- **Total: 0/100 ❌ FAILED**

## Content Sources

### Local Files
```yaml
content:
  type: "local"
  local:
    path: "./content"
    recursive: true
    max_depth: 5
    file_patterns:
      - "*.md"
      - "*.html"
      - "*.txt"
      - "*.json"
      - "*.csv"
      - "*.docx"
```

### Website Crawling
```yaml
content:
  type: "website"
  website:
    url: "https://example.com"
    max_pages: 50
    crawl_depth: 3
    respect_robots: true
    delay_between_requests: 1.0
```

### Cloud Storage
```yaml
content:
  type: "cloud"
  cloud:
    provider: "google_drive"  # or "onedrive", "dropbox"
    folder_id: "your-folder-id"
    recursive: true
    max_depth: 5
```

## AI Provider Configuration

### OpenAI
```yaml
ai_providers:
  response_provider:
    - name: "openai"
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4-turbo-preview"
      temperature: 0.7
      max_tokens: 2000
```

### Anthropic
```yaml
ai_providers:
  evaluation_provider:
    - name: "anthropic"
      api_key: "${ANTHROPIC_API_KEY}"
      model: "claude-3-opus-20240229"
      temperature: 0.3
      max_tokens: 1000
```

### Grok
```yaml
ai_providers:
  response_provider:
    - name: "grok"
      api_key: "${GROK_API_KEY}"
      model: "grok-beta"
```

## Command Line Options

```bash
python rulesevaluator.py [OPTIONS] RULES_FILE

Arguments:
  RULES_FILE    Path to JSON rules file

Options:
  --config PATH           Configuration file (default: config.yaml)
  --content-source TYPE   Override content source (website/local/cloud)
  --output PATH          Output directory for results
  --log-level LEVEL      Logging level (DEBUG/INFO/WARNING/ERROR)
  --no-cache            Disable response caching
  --dry-run             Validate configuration without running evaluation
```

## Output Files

Each evaluation run generates multiple output files in `results/YYYY-MM-DD/`:

- **evaluation_results.json**: Complete evaluation data
- **evaluation_summary.md**: Executive summary report
- **evaluation_report.html**: Professional HTML report with styling
- **dashboard-data.json**: Dashboard-compatible metrics
- **ai_responses.log**: Detailed AI response logs (if enabled)

## Rules File Format

### Basic Structure
```json
{
  "prompts": [
    {
      "prompt": "Question or instruction text",
      "rules": [
        {
          "ruletype": "critical|important|expected|desirable",
          "ruledescription": "What the response must/should contain"
        }
      ]
    }
  ]
}
```

### Validation Rules
1. Must have at least one prompt
2. Each prompt must have at least one rule
3. Rule types must be: critical, important, expected, or desirable
4. All fields are required and must be non-empty strings

### Example Rules File
```json
{
  "prompts": [
    {
      "prompt": "Explain our return policy",
      "rules": [
        {
          "ruletype": "critical",
          "ruledescription": "Must mention the 30-day return window"
        },
        {
          "ruletype": "important", 
          "ruledescription": "Should explain the refund process and timeline"
        },
        {
          "ruletype": "expected",
          "ruledescription": "Should mention condition requirements for returns"
        },
        {
          "ruletype": "desirable",
          "ruledescription": "Include customer service contact information"
        }
      ]
    },
    {
      "prompt": "What are the key features of our premium subscription?",
      "rules": [
        {
          "ruletype": "critical",
          "ruledescription": "Must list at least 3 core premium features"
        },
        {
          "ruletype": "important",
          "ruledescription": "Should mention the pricing or value proposition"
        }
      ]
    }
  ]
}
```

## Dashboard Integration

Rules Evaluator automatically generates `dashboard-data.json` with:

- **Summary Metrics**: Pass rates, scores, failure counts
- **Rule Type Breakdown**: Performance by rule category
- **Recommendations**: AI-generated improvement suggestions
- **Individual Results**: Per-prompt evaluation details

## Automation API

The tool integrates with the Airbais automation API for workflow automation:

```bash
# Start evaluation via API
curl -X POST http://localhost:8888/tools/rulesevaluator/run \
  -H "Content-Type: application/json" \
  -d '{"rules_file": "rules/example_rules.json"}'

# Check job status
curl http://localhost:8888/jobs/{job_id}

# Get results
curl http://localhost:8888/jobs/{job_id}/results
```

## Advanced Configuration

### Custom Evaluation Prompt
```yaml
evaluation_prompt: |
  You are an expert evaluator. Analyze the AI response against the given rules.
  
  For each rule, determine satisfaction level and assign scores:
  - Fully satisfied: 100%
  - Mostly satisfied: 75%
  - Partially satisfied: 50%
  - Minimally satisfied: 25%
  - Not satisfied: 0%
```

### RAG Database Settings
```yaml
rag:
  persist_directory: "./chromadb_data"
  collection_name: "rules_evaluator"
  embedding_model: "text-embedding-3-small"
  chunk_size: 1000
  chunk_overlap: 200
  update_strategy: "overwrite"  # or "update"
```

### Performance Tuning
```yaml
general:
  enable_cache: true
  cache_dir: "./cache"
  cache_ttl_hours: 24
  max_concurrent_requests: 5
  timeout_seconds: 30
```

## Environment Variables

### Using .env File (Recommended)

Create a `.env` file in the rulesevaluator directory with your API keys:

```bash
# Copy .env.example to .env and fill in your keys
cp .env.example .env
```

Edit `.env` with your actual credentials:
```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional AI providers
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
GROK_API_KEY=xai-your-grok-key-here

# Cloud storage (only if using cloud content sources)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
ONEDRIVE_CLIENT_ID=your-onedrive-client-id
ONEDRIVE_CLIENT_SECRET=your-onedrive-client-secret
ONEDRIVE_TENANT_ID=your-azure-tenant-id
DROPBOX_ACCESS_TOKEN=your-dropbox-access-token
```

### Manual Environment Variables

Alternatively, set environment variables directly:

```bash
# Required
export OPENAI_API_KEY="your-openai-key"

# Optional AI providers
export ANTHROPIC_API_KEY="your-anthropic-key"
export GROK_API_KEY="your-grok-key"

# Cloud storage (if using)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export ONEDRIVE_CLIENT_ID="your-client-id"
export ONEDRIVE_CLIENT_SECRET="your-client-secret"
export ONEDRIVE_TENANT_ID="your-tenant-id"
export DROPBOX_ACCESS_TOKEN="your-access-token"
```

### Cloud Storage Setup

#### Google Drive
1. Create a Google Cloud project
2. Enable the Google Drive API
3. Create a service account and download the JSON key file
4. Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of the JSON file
5. Share your Google Drive folder with the service account email

#### OneDrive
1. Register an application in Azure Active Directory
2. Configure API permissions for Microsoft Graph (Files.Read.All)
3. Create a client secret
4. Set the three OneDrive environment variables

#### Dropbox
1. Create a Dropbox app at https://www.dropbox.com/developers
2. Generate an access token
3. Set `DROPBOX_ACCESS_TOKEN` environment variable

## Testing

Run the test suite:

```bash
# Unit tests
pytest tests/

# Integration tests (requires API keys)
pytest tests/test_integration.py -m integration

# Test automation API integration
python automation/test_rulesevaluator.py
```

## Troubleshooting

### Common Issues

**"No content ingested"**
- Check file paths and permissions
- Verify file formats are supported
- Check recursive settings and depth limits

**"OpenAI API key required"**
- Set OPENAI_API_KEY environment variable
- Verify API key is valid and has sufficient credits

**"ChromaDB initialization failed"**  
- Ensure write permissions to persist_directory
- Check disk space availability
- Verify ChromaDB dependencies installed

**"Rules validation failed"**
- Check JSON syntax in rules file
- Verify all required fields are present
- Ensure rule types are valid

### Performance Tips

1. **Optimize Chunk Size**: Smaller chunks (500-1000) for precise matching, larger chunks (1500-2000) for broader context
2. **Use Caching**: Enable caching for repeated evaluations during development
3. **Limit Content**: Start with smaller content sets to test rules before full evaluation
4. **Monitor Costs**: Track API usage, especially with large content sets

## Best Practices

### Rule Creation
1. **Be Specific**: Clear, testable rule descriptions work better
2. **Use Critical Sparingly**: Only for absolute requirements
3. **Balance Rule Types**: Mix different importance levels
4. **Test Iteratively**: Start small and refine rules based on results

### Content Preparation
1. **Clean Content**: Remove unnecessary formatting and noise
2. **Relevant Sources**: Focus on content that should inform AI responses
3. **Update Regularly**: Keep content current for accurate evaluations

### Evaluation Workflow
1. **Dry Run First**: Use --dry-run to validate configuration
2. **Review Results**: Check both individual prompts and overall metrics
3. **Iterate on Rules**: Refine rules based on evaluation insights
4. **Monitor Trends**: Track performance over time

## Support

For issues and questions:
- Check the troubleshooting section above
- Review generated log files for detailed error information
- Ensure all prerequisites and environment variables are properly configured