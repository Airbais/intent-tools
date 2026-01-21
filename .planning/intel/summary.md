# Codebase Intelligence Summary

Last updated: 2025-01-21T10:00:00Z
Indexed files: 58

## Language

- **Primary:** Python (98%)
- **Secondary:** JavaScript (2% - theme toggles only)

## Naming Conventions

- Class/export naming: **PascalCase** (75% of 68 exports)
- File naming: **snake_case** (100% of files)
- Functions: **snake_case** (e.g., `setup_logging`, `load_config`, `main`)

## Key Directories

- `src/`: Core source modules per tool (35 files)
- `metrics/`: GRASP metric implementations (5 files)
- `utils/`: Utility functions (3 files)
- `automation/`: REST API server (6 files)
- `dashboard/`: Unified visualization (4 files)

## File Patterns

- `*evaluator.py`: Main evaluation entry points (5 tools)
- `*_manager.py`: Configuration managers (5 files)
- `*_generator.py`: Report/output generators (3 files)
- `*_extractor.py`: Content/intent extractors (4 files)

## Architecture

- **Pattern:** Modular self-contained tools
- **Output:** `dashboard-data.json` in `results/YYYY-MM-DD/`
- **Shared:** Dashboard (visualization), Automation API (orchestration)

## Core Classes

- `WebCrawler`: Web crawling (intentcrawler, geoevaluator, llmstxtgenerator)
- `ConfigManager`: Configuration loading (all tools)
- `*Evaluator`: Main evaluation logic per tool
- `MasterDashboard`: Unified results visualization
- `AIProviderFactory`: LLM provider abstraction (rulesevaluator)

Total exports: 68
