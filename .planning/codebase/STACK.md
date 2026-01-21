# Technology Stack

**Analysis Date:** 2026-01-21

## Languages

**Primary:**
- Python 3.12.3 - All tool implementations, API servers, and automation framework

**Secondary:**
- JavaScript/TypeScript (minimal) - Dashboard CSS/HTML assets only, no TypeScript configuration detected

## Runtime

**Environment:**
- Python 3.12.3
- No explicit version management file (.python-version, pyenv config)
- Target: Linux (development) and containerizable for production

**Package Manager:**
- pip (standard Python package manager)
- Lockfile: No `requirements.lock` or `Pipfile.lock` detected; uses pinned versions in `requirements.txt` files per tool

## Frameworks

**Core:**
- Flask 3.0.0 - REST API server for automation (`automation/api_server.py`)
  - Flask-CORS 4.0.0 - CORS handling for N8N/Zapier integration
- Dash 2.14.0+ - Web framework for master dashboard visualization (`dashboard/`)
- Plotly 5.17.0+ - Interactive charting for dashboard and tool outputs

**Content Processing:**
- BeautifulSoup4 4.12.0+ - HTML/XML parsing
- Trafilatura 1.6.0 - Content extraction from web pages
- Newspaper3k 0.2.8 - Article content parsing
- HTML2Text 2020.1.16 - HTML to Markdown conversion
- lxml 4.9.0+ - XML/HTML parsing library (optional for Beautiful Soup)

**Web Crawling:**
- requests 2.31.0+ - HTTP client for fetching pages
- Selenium 4.15.0 - Browser automation for JavaScript-heavy sites
- httpx 0.25.0+ - Modern async HTTP client (used in RulesEvaluator)

**Testing:**
- pytest 7.4.0 - Test framework (`rulesevaluator/tests/`)
- pytest-asyncio 0.21.0 - Async test support

**Build/Development:**
- black 23.0.0 - Code formatter (optional, not in build pipeline)
- flake8 6.0.0 - Linter (optional, not in build pipeline)

**NLP/ML:**
- NLTK 3.8.0 - Natural language processing
- spaCy 3.6.0 - Advanced NLP and text processing
- scikit-learn 1.3.0 - Machine learning utilities
- Transformers 4.30.0+ - Hugging Face transformer models
- Sentence-Transformers 2.2.0 - Semantic sentence embeddings
- Gensim 4.3.0 - Topic modeling and similarity
- TextStat 0.7.3+ - Text readability metrics
- TextBlob 0.17.1 - Simplified NLP tasks
- Markdown2 2.4.0 - Markdown processing

**Text Processing:**
- tiktoken 0.8.0 - OpenAI token counting
- python-dateutil 2.8.2 - Date/time utilities
- chardet 5.0.0 - Character encoding detection
- validators 0.22.0 - URL/email validation

## Key Dependencies

**Critical:**

- **openai 1.12.0+** - OpenAI API client
  - Why: Core LLM provider used in all evaluation tools
  - Used by: `graspevaluator`, `llmevaluator`, `rulesevaluator`

- **anthropic 0.18.0+** - Anthropic Claude API client
  - Why: Alternative LLM provider for multi-model evaluation
  - Used by: `llmevaluator`, `rulesevaluator`

- **chromadb 0.4.22+** - Vector database for RAG
  - Why: Enables semantic search and retrieval-augmented generation
  - Used by: `rulesevaluator` (`src/rag_database.py`)
  - Key config: `OPENAI_API_KEY` required for embeddings

- **langchain 0.1.0+** - LLM orchestration framework
  - Why: Chains prompts and manages LLM interactions
  - Used by: `rulesevaluator`

- **tenacity 8.2.0+** - Retry logic with exponential backoff
  - Why: Handles transient API failures with configurable strategies
  - Used by: All tools making external API calls

**Infrastructure:**

- **pyyaml 6.0.1** - YAML parsing
  - Configuration loading from `config.yaml` in each tool
  - Tools config in `automation/tools_config.yaml`

- **python-dotenv 1.0.0** - Environment variable loading
  - All tools load `.env` for API keys

- **requests-cache 1.1.0** - HTTP response caching
  - Optional caching layer for repeated requests

- **diskcache 5.6.0** - File-based caching
  - Used by `llmevaluator` for prompt response caching
  - LLM response cache with `cache_expire_hours` configuration

- **pandas 2.0.0+** - Data manipulation and analysis
  - Report generation and data processing across tools

- **jinja2 3.1.2+** - Template rendering
  - HTML report generation in `geoevaluator` and other tools

**Cloud Storage:**

- **google-api-python-client 2.100.0** - Google Drive API
  - Used by: `rulesevaluator` (`src/cloud_storage.py`)
  - Auth: `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`

- **dropbox 11.36.2** - Dropbox API
  - Used by: `rulesevaluator` for Dropbox content ingestion

- **msal 1.24.0** - Microsoft authentication
  - Used by: `rulesevaluator` for OneDrive/SharePoint support

- **msgraph-core 0.2.2** - Microsoft Graph API
  - Used by: `rulesevaluator` for OneDrive integration

**Utilities:**

- **tqdm 4.65.0+** - Progress bars for long-running operations
- **colorlog 6.7.0** - Colored logging output
- **urllib3 2.0.0+** - Low-level HTTP client (via requests)
- **Werkzeug 3.0.1** - WSGI utilities for Flask

## Configuration

**Environment Variables:**

Critical (required in `.env`):
- `OPENAI_API_KEY` - OpenAI API key for GPT models
- `ANTHROPIC_API_KEY` - Anthropic Claude API key

Optional:
- `GOOGLE_API_KEY` - Google API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google service account JSON (for Drive access)
- `DROPBOX_ACCESS_TOKEN` - Dropbox API token
- `ONEDRIVE_TOKEN` - OneDrive/Microsoft Graph token

**Build & Runtime Config Files:**

- `.env` - Environment variables (template provided, actual values not committed)
- `automation/tools_config.yaml` - Tool registry, parameters, and API timeouts
- `rulesevaluator/config.yaml` - Default Rules Evaluator configuration
- `rulesevaluator/config_example.yaml` - Example configuration template
- `graspevaluator/config/grasp_config.yaml` - GRASP evaluation metrics configuration
- Tool-specific YAML configs in each tool's `config/` directory

**Requirements Files (per tool):**

- `automation/requirements.txt` - Flask, PyYAML, requests
- `graspevaluator/requirements.txt` - BeautifulSoup4, requests, textstat, openai, python-dotenv
- `llmevaluator/requirements.txt` - openai, anthropic, textblob, markdown, pandas, tenacity, diskcache
- `intentcrawler/requirements.txt` - beautifulsoup4, requests, trafilatura, lxml, pandas, dash
- `geoevaluator/requirements.txt` - requests, beautifulsoup4, lxml, readability, textstat, pandas, plotly
- `llmstxtgenerator/requirements.txt` - requests, beautifulsoup4, lxml, pyyaml, pandas, tiktoken, openai, anthropic
- `rulesevaluator/requirements.txt` - Comprehensive: pyyaml, requests, tenacity, openai, anthropic, chromadb, langchain, cloud storage libraries, pytest

## Platform Requirements

**Development:**
- Python 3.12.3
- pip with internet access for package installation
- Linux/macOS/Windows environment
- API credentials for OpenAI and Anthropic
- Optional: Google service account credentials for Drive integration

**Production:**
- Python 3.12.3 runtime
- Docker container support (no Dockerfile present, but structure allows containerization)
- 2+ GB RAM minimum for ChromaDB and NLP models
- Network access to OpenAI, Anthropic APIs
- Optional: S3, Google Drive, Dropbox for content sources
- Deployment targets:
  - Self-hosted Linux server
  - Docker container
  - Cloud functions (with appropriate timeout configuration)

## Caching Strategy

**Disk-based Caching:**
- `llmevaluator` uses `diskcache` for LLM response caching
  - Location: `./cache` directory by default
  - TTL: `cache_expire_hours` configurable (default 24 hours)

**Vector Database Persistence:**
- ChromaDB (`rulesevaluator`) persists to `./chromadb_data` directory
  - Collection: `rules_evaluator` (configurable)
  - Embedding model: `text-embedding-3-small` (OpenAI)

**Request-level Caching:**
- Optional `requests-cache` integration for HTTP responses
- Not globally enabled, tool-specific implementation

## API Integration Pattern

All tools follow standardized patterns for external API integration:

1. **API Key Management:** Environment variables with dotenv loading
2. **Retry Strategy:** Tenacity with exponential backoff (3 attempts default)
3. **Error Handling:** Try-except blocks with logging
4. **Timeout Configuration:** Per-tool timeouts in `tools_config.yaml`
5. **Response Caching:** Tool-specific (llmevaluator uses diskcache, others use no caching)

---

*Stack analysis: 2026-01-21*
