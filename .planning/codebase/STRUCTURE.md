# Codebase Structure

**Analysis Date:** 2026-01-21

## Directory Layout

```
/home/bill/Localcode/Airbais/tools/
├── automation/              # Automation API server for triggering tools
│   ├── api_server.py       # Flask REST API with job management
│   ├── tools_config.yaml   # Tool registry and configuration
│   ├── test_api.py         # API testing script
│   └── workflows/          # N8N/external workflow definitions
├── dashboard/              # Master dashboard for visualization
│   ├── run_dashboard.py    # Launcher script
│   ├── dashboard.py        # Dash application and layout
│   ├── data_loader.py      # Tool data discovery and loading
│   ├── assets/             # CSS/JS assets
│   └── callbacks.py        # Dash callbacks
├── intentcrawler/          # Website intent analysis tool
│   ├── intentcrawler.py    # CLI entry point
│   ├── config.yaml         # Default configuration
│   ├── src/                # Core modules
│   │   ├── crawler.py      # WebCrawler - HTML parsing and link following
│   │   ├── content_processor.py
│   │   ├── intent_extractor.py
│   │   ├── enhanced_intent_extractor.py
│   │   ├── user_intent_extractor.py
│   │   ├── site_analyzer.py
│   │   ├── llmstxt_formatter.py
│   │   ├── report_generator.py
│   │   └── dashboard.py
│   ├── results/            # Output results by date
│   │   └── 2025-06-26/
│   │       ├── dashboard-data.json
│   │       ├── intent-report.json
│   │       ├── llmstxt/    # Generated llms.txt files
│   │       └── ...
│   └── archive/            # Previous/demo outputs
├── graspevaluator/         # Content quality assessment tool
│   ├── graspevaluator.py   # CLI entry point (delegates to src/main.py)
│   ├── src/                # Core modules
│   │   ├── main.py         # Main CLI handler
│   │   ├── evaluator.py    # GRASPEvaluator
│   │   ├── config_manager.py
│   │   └── ...
│   ├── metrics/            # GRASP dimension scorers
│   │   ├── grounded.py
│   │   ├── readable.py
│   │   ├── accurate.py
│   │   ├── structured.py
│   │   └── polished.py
│   ├── utils/              # Shared utilities
│   │   ├── content_extractor.py
│   │   └── scoring.py
│   ├── config/             # Configuration files
│   ├── results/            # Output results by date
│   └── ...
├── llmevaluator/           # LLM brand mention evaluation tool
│   ├── llmevaluator.py     # CLI entry point (delegates to src/main.py)
│   ├── src/                # Core modules
│   │   ├── main.py
│   │   ├── evaluator.py
│   │   ├── sentiment_analyzer.py
│   │   ├── report_generator.py
│   │   └── ...
│   ├── configs/            # Configuration templates
│   ├── cache/              # LLM response caching
│   ├── results/            # Output results by date
│   └── tests/              # Unit tests
├── geoevaluator/           # Generative Engine Optimization analyzer
│   ├── geoevaluator.py     # CLI entry point
│   ├── src/                # Core modules
│   │   ├── evaluator.py
│   │   ├── crawler.py
│   │   ├── config_manager.py
│   │   ├── utils.py
│   │   └── ...
│   ├── results/            # Output results by date
│   └── tests/              # Unit tests
├── rulesevaluator/         # Rules-based evaluation with RAG
│   ├── rulesevaluator.py   # CLI entry point
│   ├── src/                # Core modules
│   │   ├── evaluator.py    # Main orchestrator
│   │   ├── config_manager.py
│   │   ├── rules_validator.py
│   │   ├── content_ingestor.py
│   │   ├── rag_database.py # ChromaDB integration
│   │   ├── ai_providers.py # OpenAI, Anthropic factory
│   │   ├── website_crawler.py
│   │   ├── cloud_storage.py
│   │   ├── output_generator.py
│   │   └── __init__.py
│   ├── tests/              # Unit tests
│   ├── config.yaml         # Configuration file
│   ├── rules/              # Rules definitions (JSON)
│   ├── chromadb_data/      # Persistent RAG database
│   ├── results/            # Output results by date
│   ├── test_content/       # Test data for evaluation
│   └── ...
├── llmstxtgenerator/       # LLMS.txt file generation
│   ├── llmstxtgenerator.py
│   ├── src/
│   ├── config.yaml
│   ├── results/
│   └── ...
├── CLAUDE.md               # Instructions for Claude (project guidelines)
├── README.md               # Project overview
├── AGENTS.md               # AI agent integration documentation
├── .env                    # Environment variables (secrets - not committed)
├── .gitignore              # Git exclusions
└── .planning/              # GSD planning directory
    └── codebase/           # Generated architecture documentation
        ├── ARCHITECTURE.md
        └── STRUCTURE.md
```

## Directory Purposes

**automation/**
- Purpose: Unified REST API for triggering tools programmatically
- Contains: Flask app, tool configuration registry, job tracking
- Key files: `api_server.py`, `tools_config.yaml`

**dashboard/**
- Purpose: Multi-tool visualization and exploration interface
- Contains: Dash application, data loading logic, callbacks
- Key files: `run_dashboard.py`, `dashboard.py`, `data_loader.py`

**{tool}/**
- Purpose: Individual tool implementation
- Contains: Entry point, config, source code, tests, results
- Pattern: Same for intentcrawler, graspevaluator, llmevaluator, geoevaluator, rulesevaluator

**{tool}/src/**
- Purpose: Core business logic modules
- Contains: Crawlers, extractors, evaluators, validators, formatters, report generators
- Pattern: Separate module per major responsibility

**{tool}/results/**
- Purpose: Timestamped output storage
- Contains: `YYYY-MM-DD/` directories with tool-specific output files
- Key files: `dashboard-data.json` (required for dashboard), tool-specific JSON/HTML/MD files

**rulesevaluator/chromadb_data/**
- Purpose: Persistent vector database for RAG
- Contains: ChromaDB collections organized by evaluation session ID
- Non-standard: Present only in rulesevaluator (uses ChromaDB for semantic search)

## Key File Locations

**Entry Points:**
- `intentcrawler/intentcrawler.py` - Website intent analysis entry point
- `graspevaluator/graspevaluator.py` - Content quality evaluator entry point
- `llmevaluator/llmevaluator.py` - LLM evaluation entry point
- `geoevaluator/geoevaluator.py` - GEO optimizer entry point
- `rulesevaluator/rulesevaluator.py` - Rules-based evaluator entry point
- `automation/api_server.py` - Automation REST API
- `dashboard/run_dashboard.py` - Dashboard launcher

**Configuration:**
- `automation/tools_config.yaml` - Tool registry with parameters and result files
- `intentcrawler/config.yaml` - Intent extraction and crawler settings
- `rulesevaluator/config.yaml` - Evaluation, RAG, and AI provider config
- `graspevaluator/config/` - GRASP evaluator configuration files
- `llmevaluator/configs/` - LLM evaluator configuration templates
- `geoevaluator/config.yaml` - GEO evaluator configuration

**Core Logic:**
- `intentcrawler/src/crawler.py` - WebCrawler with sitemap support
- `intentcrawler/src/intent_extractor.py` - Intent discovery logic
- `rulesevaluator/src/evaluator.py` - Main orchestrator
- `rulesevaluator/src/rag_database.py` - ChromaDB wrapper for RAG
- `rulesevaluator/src/ai_providers.py` - LLM provider factory
- `graspevaluator/src/evaluator.py` - GRASP evaluation logic
- `graspevaluator/metrics/` - Individual dimension scorers

**Testing:**
- `rulesevaluator/tests/` - Unit tests for rules evaluation
- `llmevaluator/tests/` - Unit tests for LLM evaluation
- `geoevaluator/tests/` - Unit tests for GEO evaluation

## Naming Conventions

**Files:**
- `config.yaml` / `config_manager.py` - Configuration management pattern
- `{name}_crawler.py` - Web crawling modules
- `{name}_extractor.py` - Data extraction modules
- `{name}_evaluator.py` - Core evaluation/analysis logic
- `{name}_generator.py` / `output_generator.py` - Report/output generation
- `{name}_validator.py` - Validation and schema checking
- `dashboard-data.json` - Standardized output for dashboard
- `evaluation_results.json` / `{tool}_evaluation_results.json` - Detailed results
- `evaluation_summary.md` / `{tool}_summary.md` - Human-readable summaries

**Directories:**
- `results/{YYYY-MM-DD}/` - Timestamped output directories
- `src/` - Core modules
- `metrics/` / `utils/` - Supporting logic
- `tests/` - Test files
- `config/` / `configs/` - Configuration files
- `chromadb_data/` - Vector database storage

**Python Functions/Classes:**
- `WebCrawler`, `ContentProcessor`, `IntentExtractor` - Object names are PascalCase
- `config_manager.py`, `content_processor.py` - Module names are snake_case
- `extract_intents()`, `crawl()`, `process_content()` - Function names are snake_case
- `dashboard-data.json` - Output files use kebab-case

## Where to Add New Code

**New Feature (New Tool):**
- Primary code: `/home/bill/Localcode/Airbais/tools/{new_tool}/{new_tool}.py` as entry point
- Core logic: `{new_tool}/src/` directory with modular .py files
- Tests: `{new_tool}/tests/` directory with pytest files
- Configuration: `{new_tool}/config.yaml` with YAML structure
- Registration: Add tool to `automation/tools_config.yaml` with metadata

**New Tool Module/Component:**
- Implementation: `{tool}/src/{component_name}.py` for single-file classes/functions
- For complex logic: Split into `{tool}/src/{component_name}/` subdirectory
- Support utilities: `{tool}/utils/{utility_name}.py` for shared helpers

**Utilities/Shared Code:**
- Tool-specific helpers: `{tool}/utils/` directory
- Cross-tool shared code: Create at `/home/bill/Localcode/Airbais/tools/shared/` (if needed)
- Currently no cross-tool sharing - each tool is self-contained

**Dashboard Features:**
- New visualizations: Add to `dashboard/dashboard.py` in setup_layout()
- Data loaders: Extend `dashboard/data_loader.py`
- Callbacks: Add to dashboard.py or callbacks.py file

**API Endpoints:**
- New tool endpoints: Register in `automation/tools_config.yaml`
- Endpoint logic: `automation/api_server.py` already handles generically via config
- No tool-specific API code needed if tool follows CLI conventions

## Special Directories

**{tool}/results/**
- Purpose: Output and historical tracking
- Generated: Yes (created at runtime)
- Committed: No (`.gitignore` excludes results/)
- Structure: YYYY-MM-DD folders with date-specific results
- Retention: Configured per tool (e.g., intentcrawler keeps 7 days by default)

**rulesevaluator/chromadb_data/**
- Purpose: Vector embeddings and semantic search index
- Generated: Yes (created by ChromaDB on first use)
- Committed: No (excluded from git)
- Persistence: Cross-session - reused for RAG context retrieval

**automation/workflows/**
- Purpose: N8N/external workflow definitions
- Generated: No (manually created)
- Committed: Yes
- Usage: Referenced by workflow automation tools

**.planning/codebase/**
- Purpose: Architecture and planning documentation
- Generated: By GSD mapping tools
- Committed: Yes
- Usage: Reference for implementing new features and changes

## Pattern Examples

**Entry Point Pattern** (`intentcrawler/intentcrawler.py`):
```python
import sys
from src.crawler import WebCrawler
from src.intent_extractor import IntentExtractor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--config')
    args = parser.parse_args()

    config = load_config(args.config)
    crawler = WebCrawler(args.url, **config['crawler'])
    # ... process and output
    return output_dir

if __name__ == '__main__':
    main()
```

**Core Module Pattern** (`rulesevaluator/src/evaluator.py`):
```python
class RulesEvaluator:
    def __init__(self, config: ConfigManager):
        self.config = config
        self._init_components()

    def _init_components(self):
        self.rag_db = RAGDatabase(config)
        self.provider = AIProviderFactory.create(config)

    def run_evaluation(self, rules_file: str) -> Dict:
        # Orchestrate multi-step process
        pass
```

**Configuration Pattern** (`intentcrawler/config.yaml`):
```yaml
display_name: "Intent Crawler"
crawler:
  max_pages: 1000
  rate_limit: 2
output:
  base_directory: 'results'
  date_format: '%Y-%m-%d'
```

**Output Pattern** (all tools):
```python
# Generate standardized dashboard data
dashboard_data = {
    'tool': 'intentcrawler',
    'timestamp': datetime.now().isoformat(),
    'summary': {...},
    'metrics': {...},
    'data': {...}
}
# Save to results/{date}/dashboard-data.json
```

---

*Structure analysis: 2026-01-21*
