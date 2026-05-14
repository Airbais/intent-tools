# External Integrations

**Analysis Date:** 2026-01-21

## APIs & External Services

**LLM Providers:**
- **OpenAI** - GPT-4, GPT-4-Turbo, text-embedding-3-small
  - SDK/Client: `openai>=1.12.0`
  - Auth: `OPENAI_API_KEY` environment variable
  - Used by: All evaluation tools (`graspevaluator`, `llmevaluator`, `rulesevaluator`, `geoevaluator`)
  - Endpoints: gpt-4-turbo-preview (primary), gpt-4 (fallback)
  - Token counting: `tiktoken` for accurate usage estimation
  - Location: Configured in tool configs and AI provider implementations

- **Anthropic Claude** - Claude 3 Opus, Claude 3 Sonnet
  - SDK/Client: `anthropic>=0.18.0`
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Used by: `llmevaluator`, `rulesevaluator`
  - Models: claude-3-opus-20240229, claude-3-sonnet-20240229
  - Location: `llmevaluator/src/llm_interface.py`, `rulesevaluator/src/ai_providers.py`

**Alternative/Experimental Providers:**
- **Grok API** - Experimental endpoint (partial support)
  - Base URL: `https://api.x.ai/v1`
  - Location: `rulesevaluator/src/ai_providers.py` (stub implementation)
  - Status: Framework present but not fully integrated

## Data Storage

**Databases:**
- **No Traditional Database** - Tools are stateless
  - All state managed in-memory during execution or persisted to JSON files
  - Results stored as JSON files in `results/YYYY-MM-DD/` directories

**Vector Database:**
- **ChromaDB** - Persistent local vector database
  - Type: In-process SQLite with vector store
  - Client: `chromadb>=0.4.22`
  - Connection: Local filesystem persistence
  - Storage location: `./chromadb_data` (configurable in `config.yaml`)
  - Used by: `rulesevaluator` for RAG implementation
  - Collection name: `rules_evaluator` (configurable)
  - Embedding model: `text-embedding-3-small` (OpenAI)
  - Key methods: `get_or_create_collection()`, `reset_collection()`, `search_similar()`
  - Location: `rulesevaluator/src/rag_database.py`

**File Storage:**
- **Local Filesystem Only** - No cloud storage required for operation
  - Results: `{tool}/results/YYYY-MM-DD/` directories
  - Cache: `./cache/` for diskcache
  - ChromaDB: `./chromadb_data/` persistence
  - Configuration: YAML files in each tool directory
  - Generated reports: JSON, HTML, Markdown, CSV formats

**Caching:**
- **Disk Cache** (local files) - `diskcache>=5.6.0`
  - Used by: `llmevaluator` for LLM response caching
  - Location: `./cache` directory
  - TTL: Configurable (default 24 hours)
  - Key use: Prevent duplicate LLM API calls

## Authentication & Identity

**Auth Providers:**

- **OpenAI API Key Authentication**
  - Type: Bearer token in Authorization header
  - Implementation: `openai.OpenAI(api_key=key)`
  - Scope: Full access to configured models
  - Required for: Embeddings, text completion, chat completions

- **Anthropic API Key Authentication**
  - Type: Bearer token
  - Implementation: `anthropic.Anthropic(api_key=key)`
  - Scope: Full access to Claude models
  - Required for: Text generation, evaluation tasks

- **Google OAuth 2.0** (for Google Drive)
  - Type: Service account credentials
  - File: Path specified in `GOOGLE_APPLICATION_CREDENTIALS` environment variable
  - Scope: `https://www.googleapis.com/auth/drive.readonly`
  - Libraries: `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`
  - Used by: `rulesevaluator` CloudStorage module
  - Location: `rulesevaluator/src/cloud_storage.py` (`GoogleDriveSource` class)

- **Microsoft MSAL** (for OneDrive/SharePoint)
  - Type: OAuth 2.0 with MSAL library
  - Library: `msal>=1.24.0`
  - Used by: `rulesevaluator` for OneDrive integration
  - Status: Framework present, requires token provisioning
  - Location: `rulesevaluator/src/cloud_storage.py` (`OneDriveSource` class)

- **Dropbox API Token**
  - Type: Bearer token (access token)
  - Environment variable: `DROPBOX_ACCESS_TOKEN`
  - Library: `dropbox>=11.36.2`
  - Used by: `rulesevaluator` for Dropbox content ingestion
  - Location: `rulesevaluator/src/cloud_storage.py` (`DropboxSource` class)

## Monitoring & Observability

**Error Tracking:**
- Not integrated - No Sentry, Rollbar, or similar service

**Logging:**
- Approach: Standard Python `logging` module with `colorlog` for colored output
  - Configuration: Per-tool logger setup
  - Output: Console (stdout/stderr) and optional file logging
  - Format: Timestamp, logger name, level, message
  - Used in: All tools via `logger.info()`, `logger.error()`, `logger.debug()`
  - Location: Each tool's main modules
  - Progress tracking: `tqdm` for progress bars during long operations

**Metrics & Reporting:**
- No external metrics collection
- Metrics embedded in `dashboard-data.json` output files
- Dashboard consumption: `dashboard/data_loader.py` auto-discovers metrics from tool outputs

## CI/CD & Deployment

**Hosting:**
- Self-hosted (no Platform as a Service integration detected)
- Docker-ready (no Dockerfile present, but structure supports containerization)
- Local development (test scripts provided)

**CI Pipeline:**
- Not detected - No GitHub Actions, GitLab CI, Jenkins, or CircleCI configuration
- Manual testing via provided test scripts: `automation/test_*.py`

**Deployment:**
- Direct Python script execution
- Flask API server: `python3 automation/api_server.py`
- Dashboard: `python3 dashboard/run_dashboard.py`
- Tools: Individual invocation via CLI

## Environment Configuration

**Required env vars:**
```
OPENAI_API_KEY          # OpenAI API key (critical)
ANTHROPIC_API_KEY       # Anthropic API key (critical)
```

**Optional env vars:**
```
GOOGLE_API_KEY                      # Google API key
GOOGLE_APPLICATION_CREDENTIALS      # Path to service account JSON for Drive
AZURE_OPENAI_ENDPOINT               # Azure OpenAI endpoint
AZURE_OPENAI_API_KEY                # Azure OpenAI API key
DROPBOX_ACCESS_TOKEN                # Dropbox API token
ONEDRIVE_TOKEN                      # Microsoft Graph token
```

**Secrets location:**
- `.env` file in project root (not committed to git per `.gitignore`)
- Environment-specific: Development uses local `.env`
- Production: Secrets injected via environment variables or secret management system

## Webhooks & Callbacks

**Incoming Webhooks:**
- None detected - Tools do not expose inbound webhook endpoints

**Outgoing Webhooks:**
- None detected - Tools do not send webhooks to external services

**REST API Callbacks:**
- **N8N/Zapier Integration:** Automation API accepts JSON payloads
  - Endpoint: `http://localhost:8888/<tool_name>/analyze` (POST)
  - Pattern: Fire-and-forget with job tracking
  - Status endpoint: `http://localhost:8888/status/<job_id>` (GET)
  - Results endpoint: `http://localhost:8888/results/<job_id>` (GET)
  - Async execution: Jobs run in background threads
  - Location: `automation/api_server.py`

## API Server

**Flask API (`automation/api_server.py`):**

- **Port:** 8888 (configurable via `tools_config.yaml`)
- **CORS:** Enabled for N8N/Zapier compatibility
- **Endpoints:**
  - `GET /health` - Health check with active job count
  - `POST /<tool_name>/analyze` - Trigger tool analysis
  - `GET /status/<job_id>` - Poll job status
  - `GET /results/<job_id>` - Retrieve job results
  - `GET /jobs` - List all jobs

**Job System:**
- In-memory job storage (not persisted across restarts)
- Job states: queued → running → completed/failed
- Job cleanup: Configurable retention (default 24 hours)
- Max jobs in memory: Configurable (default 1000)

## Tool Integration Pattern

**Tool Registration:**
- Defined in `automation/tools_config.yaml`
- Each tool has:
  - Script path (`module_path`, `script`)
  - Parameters (required, optional)
  - Result files to collect
  - Custom timeouts

**Tool Discovery:**
- Dashboard auto-discovers tools by scanning `results/*/dashboard-data.json`
- No manual registration needed for visualization

**Result Output:**
- Standardized schema: All tools produce `dashboard-data.json`
- Fields: `tool`, `timestamp`, `summary`, `metrics`, `recommendations`, `data`
- Format: JSON (consumed by dashboard and API)

## External Data Sources

**Content Sources Supported by RulesEvaluator:**

1. **Website Crawling** - HTTP GET requests
   - Library: `requests` or `httpx` (httpx in rulesevaluator)
   - Respects robots.txt via `RobotFileParser`
   - Configurable delay between requests
   - User-Agent headers for browser identification

2. **Google Drive**
   - API: Google Drive v3
   - Auth: Service account credentials
   - Access: Read-only
   - Supported types: PDF, DOCX, Markdown, HTML, TXT, JSON, CSV
   - Location: `rulesevaluator/src/cloud_storage.py` (GoogleDriveSource)

3. **OneDrive/SharePoint**
   - API: Microsoft Graph API
   - Auth: MSAL token-based
   - Status: Framework present, partial implementation
   - Location: `rulesevaluator/src/cloud_storage.py` (OneDriveSource)

4. **Dropbox**
   - API: Dropbox Files API
   - Auth: Bearer token
   - Supported types: Files only (recursive directory traversal)
   - Location: `rulesevaluator/src/cloud_storage.py` (DropboxSource)

5. **Local Filesystem**
   - Direct file system access
   - Pattern matching for file types
   - Recursive directory traversal
   - Supported extensions: .md, .html, .txt, .json, .csv, .docx, .pdf

## LLM Integration Pattern

All tools follow standardized LLM integration:

1. **Configuration Loading** - YAML config with provider settings
2. **Provider Abstraction** - Base class `AIProvider` with implementations:
   - `OpenAIProvider` - `rulesevaluator/src/ai_providers.py`
   - `AnthropicProvider` - `rulesevaluator/src/ai_providers.py`
3. **Retry Logic** - Tenacity with exponential backoff
4. **Token Counting** - tiktoken for OpenAI cost estimation
5. **System Prompts** - Context-aware system messages for each task
6. **Response Parsing** - JSON extraction from LLM responses

## Rate Limiting & Quotas

**OpenAI API:**
- Default exponential backoff: 3 retries, 4-10 second wait
- Implementation: Tenacity `@retry` decorator
- No client-side rate limiting (relies on provider rate limits)

**Anthropic API:**
- Same retry strategy as OpenAI
- Token limits enforced per request

**Tool-level Timeouts:**
- Configured per tool in `tools_config.yaml`
- Examples:
  - intentcrawler: 900s (15 min)
  - graspevaluator: 600s (10 min)
  - llmevaluator: 1200s (20 min)
  - rulesevaluator: 900s (15 min)

---

*Integration audit: 2026-01-21*
