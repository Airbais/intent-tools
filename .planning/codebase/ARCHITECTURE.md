# Architecture

**Analysis Date:** 2026-01-21

## Pattern Overview

**Overall:** Modular Plugin Architecture with Unified Dashboard Integration

The Airbais Tools suite implements a plugin-based architecture where each tool operates as an independent module with standardized interfaces. Tools are loosely coupled through a common output schema and orchestrated by two hub systems: a REST API server for automation and a master dashboard for visualization.

**Key Characteristics:**
- Each tool is self-contained with its own dependencies, configuration, and execution flow
- All tools generate standardized `dashboard-data.json` files enabling dynamic UI adaptation
- Results are organized by date (`results/YYYY-MM-DD/`) for historical tracking
- Configuration driven via YAML files with environment variable support
- Multi-layer processing pipeline: Input → Validation → Core Processing → Output Generation
- Async/threaded execution for long-running operations

## Layers

**Tool Layer (Individual Tools):**
- Purpose: Specialized analysis/evaluation of specific aspects (intents, content quality, LLM mentions, etc.)
- Location: `/home/bill/Localcode/Airbais/tools/{tool_name}/`
- Contains: Entry point scripts, src modules, metrics, utils, test files
- Depends on: External libraries (requests, beautifulsoup, openai, etc.), local config
- Used by: Automation API, direct CLI invocation

**Core Processing Layer (src/):**
- Purpose: Business logic modules handling data transformation and analysis
- Location: `{tool}/src/`
- Contains: Crawlers, extractors, evaluators, validators, formatters, report generators
- Depends on: Configuration managers, external APIs, data models
- Used by: Entry points, other modules in same tool

**Utility & Support Layer (utils/, metrics/):**
- Purpose: Shared helper functions, scoring algorithms, content extraction
- Location: `{tool}/utils/` and `{tool}/metrics/`
- Contains: Scoring functions, content processors, helper utilities
- Depends on: Standard libraries and tool-specific dependencies
- Used by: Core processing modules

**Configuration Layer:**
- Purpose: Centralized settings management with YAML parsing
- Location: `{tool}/src/config_manager.py`
- Contains: ConfigManager classes that load, validate, and provide access to settings
- Depends on: YAML parsing, environment variables
- Used by: Entry points and core modules

**Orchestration Layer (automation/):**
- Purpose: Unified API for triggering tools programmatically
- Location: `/home/bill/Localcode/Airbais/tools/automation/`
- Contains: Flask REST API, job management, tool discovery, subprocess execution
- Depends on: Individual tools (via subprocess), configuration from tools_config.yaml
- Used by: External systems (N8N, Zapier, custom workflows), dashboard

**Presentation Layer (dashboard/):**
- Purpose: Unified visualization and exploration interface
- Location: `/home/bill/Localcode/Airbais/tools/dashboard/`
- Contains: Dash application, data loader, visualization components
- Depends on: Dashboard-data.json files from all tools, Plotly, Dash
- Used by: End users viewing results

## Data Flow

**Single Tool Execution Flow:**

1. **User Invocation** → CLI with arguments (URL, config file, output directory)
2. **Configuration Loading** → ConfigManager loads YAML, merges with CLI args
3. **Input Validation** → Validate URLs, rules files, or configuration
4. **Core Processing** → Tool-specific logic (crawl, evaluate, extract, analyze)
5. **Data Transformation** → Process raw data into structured formats
6. **Output Generation** → Multiple formats: JSON, Markdown, HTML, dashboard JSON
7. **Result Storage** → Save to `results/YYYY-MM-DD/` with timestamped files

**Example: IntentCrawler**
```
analyze_website(url)
  → WebCrawler.crawl() → CrawledPage objects
  → ContentProcessor.process_content() → processed_contents dict
  → SiteStructureAnalyzer.analyze() → site_structure data
  → IntentExtractor.extract_intents() → intent_data with discovered intents
  → ReportGenerator.generate_*() → JSON, MD, dashboard-data.json
  → Results written to results/{date}/
```

**Example: RulesEvaluator**
```
run_evaluation(rules_file)
  → RulesValidator.validate_file() → validated rules_data
  → ContentIngestor.ingest() → content_items
  → RAGDatabase.add_content() → chunks in ChromaDB
  → For each prompt:
    → AIProvider.generate_response()
    → RAGDatabase.retrieve_context()
    → EvaluationProvider.evaluate()
  → OutputGenerator.generate_all_outputs() → JSON, HTML, MD, dashboard-data.json
```

**Automation API Flow:**

```
POST /{tool_name}/analyze
  → api_server.py:analyze() validates params
  → create_job() creates job entry with UUID
  → run_tool_async() spawned in background thread
    → subprocess.Popen([python3, tool_script, args])
    → subprocess runs in tool's directory (cwd=tool_dir)
  → Poll /status/{job_id} to track progress
  → Fetch /results/{job_id} when complete
```

**Dashboard Discovery & Display Flow:**

```
MasterDashboard.__init__()
  → ToolDataLoader.discover_tools() scans all {tool}/results/*/dashboard-data.json
  → Available tools and runs populated dynamically
  → Dash app renders with tool dropdowns
  → On tool/date selection:
    → Load JSON data
    → Render tool-specific visualization (intents chart, quality scores, etc.)
    → Support theme toggle, filtering
```

**State Management:**

- **Tool Results**: Persistent JSON files in timestamped directories
- **API Jobs**: In-memory job dictionary (with threading.Lock for safety)
- **RAG Database**: ChromaDB persistent storage in `rulesevaluator/chromadb_data/`
- **Cache**: Tool-specific caching (e.g., LLM response caching in llmevaluator)

## Key Abstractions

**ConfigManager Pattern:**
- Purpose: Abstract YAML configuration with environment variable support
- Examples: `intentcrawler/src/config_manager.py`, `rulesevaluator/src/config_manager.py`
- Pattern: Load YAML → dict, provide get() method with defaults, support overrides

**Crawler/Extractor Pattern:**
- Purpose: Common pattern for web crawling and data extraction
- Examples: `WebCrawler` (intentcrawler), `ContentIngestor` (rulesevaluator)
- Pattern: Iterate through sources → Extract content → Return structured objects

**Validator Pattern:**
- Purpose: Validate input data against schemas before processing
- Examples: `RulesValidator` (rulesevaluator), embedded validation in GRASPEvaluator
- Pattern: Check structure → Check required fields → Return (is_valid, data, errors)

**Evaluator/Processor Pattern:**
- Purpose: Core analysis logic with async support where needed
- Examples: `GRASPEvaluator`, `RulesEvaluator`, `IntentExtractor`
- Pattern: Accept input → Transform/analyze → Return structured results dict

**ReportGenerator/OutputGenerator Pattern:**
- Purpose: Transform evaluation results into multiple output formats
- Examples: `ReportGenerator` (intentcrawler), `OutputGenerator` (rulesevaluator)
- Pattern: Accept results dict → Generate multiple files → Return file paths

**Dashboard Data Schema:**
- Purpose: Standardized format for all tools to share results with dashboard
- Location: Generated as `dashboard-data.json` in results directory
- Pattern: `{ "tool": "...", "timestamp": "...", "summary": {...}, "metrics": {...}, "data": {...} }`

## Entry Points

**CLI Entry Points (Direct Execution):**

- `intentcrawler/intentcrawler.py` - Positional: URL, optional: --config, --output, --dashboard
- `graspevaluator/graspevaluator.py` - Delegates to src/main.py, accepts --url, --config, --output
- `llmevaluator/llmevaluator.py` - Delegates to src/main.py, config-driven
- `geoevaluator/geoevaluator.py` - Accepts --url or config file with various options
- `rulesevaluator/rulesevaluator.py` - Positional: rules_file, optional: --config, --output, --dry-run
- `llmstxtgenerator/llmstxtgenerator.py` - Generates standardized llms.txt files

**API Entry Points (Automation Server):**

- `automation/api_server.py:main()` - Flask app on port 8888
- Routes: `/{tool}/analyze`, `/status/{job_id}`, `/results/{job_id}`, `/health`, `/jobs`
- Configuration: `automation/tools_config.yaml` defines tool metadata, params, result files

**Dashboard Entry Point:**

- `dashboard/run_dashboard.py` - Launcher script
- Imports: `MasterDashboard` from dashboard.py
- Runs Dash app on http://127.0.0.1:8050

## Error Handling

**Strategy:** Graceful degradation with informative logging

**Patterns:**

- **Validation Errors**: Return structured (is_valid, data, errors) tuples before processing
- **Processing Errors**: Try/except blocks with logging, partial results if possible
- **API Errors**: Return HTTP status codes with JSON error messages including details
- **Job Errors**: Store in job dict under `error` field, persist with `status: 'failed'`

**Example (rulesevaluator):**
```python
try:
    is_valid, rules_data, errors = validator.validate_file(rules_file)
    if not is_valid:
        logger.error("Rules validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        return 1
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    return 1
```

## Cross-Cutting Concerns

**Logging:**
- Standard Python logging module configured in each entry point
- Colored logging with colorlog where available
- Optional file logging configured via YAML
- Log formats: timestamp - name - level - message

**Validation:**
- Input validation at entry points (URL validation, rules file validation)
- Schema validation in core modules (JSON rules, content structure)
- Tool-specific validators: RulesValidator, config validators

**Authentication:**
- API key management via environment variables (OPENAI_API_KEY, etc.)
- Passed to AIProvider factories and embedders
- No explicit auth on API endpoints (automation server assumes trusted network)

**Results Organization:**
- All tools create `results/{YYYY-MM-DD}/` directories
- Cleanup logic removes old results based on retention config
- dashboard-data.json is the canonical format for dashboard integration

---

*Architecture analysis: 2026-01-21*
