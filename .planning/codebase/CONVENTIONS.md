# Coding Conventions

**Analysis Date:** 2026-01-21

## Naming Patterns

**Files:**
- Lowercase with underscores for modules: `config_manager.py`, `rules_validator.py`, `content_ingestor.py`
- PascalCase for tool directories: `rulesevaluator/`, `graspevaluator/`, `intentcrawler/`
- Main entry point: `[toolname].py` at package root (e.g., `rulesevaluator.py`)
- Private/internal modules in `src/` subdirectory
- Tests in `tests/` subdirectory with `test_*.py` naming

**Functions:**
- snake_case for all function names: `generate_response()`, `validate_file()`, `_init_components()`
- Private functions prefixed with single underscore: `_validate_structure()`, `_substitute_recursive()`
- Methods and functions use descriptive action verbs: `setup_logging()`, `run_evaluation()`, `calculate_score()`

**Variables:**
- snake_case for variables and parameters: `config_path`, `rules_file`, `content_items`
- UPPERCASE_WITH_UNDERSCORES for module-level constants: `VALID_RULE_TYPES = {'critical', 'important', 'expected', 'desirable'}`
- Instance variables use snake_case: `self.config`, `self.validator`, `self.rules_data`

**Types:**
- PascalCase for class names: `RulesValidator`, `ConfigManager`, `ContentProcessor`, `AIProvider`, `OpenAIProvider`
- Type hints use full module paths from `typing`: `Dict[str, Any]`, `List[str]`, `Optional[str]`, `Tuple[bool, List[str]]`

## Code Style

**Formatting:**
- Follows PEP 8 conventions (implicit via development patterns, not explicitly enforced with a tool)
- Line length: No hard enforced limit, but lines typically kept under 100-120 characters
- Four spaces for indentation
- Black formatter referenced in requirements.txt but not enforced in ci/cd

**Linting:**
- Flake8 available (in requirements.txt) but not enforced
- No `.flake8` or `setup.cfg` config files found
- Code follows PEP 8 implicitly but enforcement is optional

## Import Organization

**Order:**
1. Future imports (if any): None observed
2. Standard library imports: `os`, `sys`, `logging`, `json`, `asyncio`, `tempfile`, `pathlib.Path`, etc.
3. Third-party imports: `yaml`, `requests`, `openai`, `anthropic`, `chromadb`, `beautifulsoup4`, `colorlog`, `tenacity`
4. Local/relative imports: `.config_manager`, `.rules_validator`, `.evaluator`

**Pattern:**
```python
# Standard library
import logging
import json
from pathlib import Path
from typing import Dict, Any, List

# Third-party
import openai
import yaml
from tenacity import retry, stop_after_attempt

# Local
from .config_manager import ConfigManager
from .rules_validator import RulesValidator
```

**Path Aliases:**
- Direct relative imports using dot notation: `from .config_manager import ConfigManager`
- No path aliases observed (no PYTHONPATH manipulation except in entry points)
- Entry points add parent directories to sys.path for initial bootstrap: `sys.path.append(str(Path(__file__).parent))`

## Error Handling

**Patterns:**
- Specific exception catching: `except json.JSONDecodeError`, `except FileNotFoundError`, `except ValueError`
- Logging errors with context: `logger.error(f"Error: {e}", exc_info=True)`
- Graceful degradation with defaults: `config.get('key', default_value)`
- Validation functions return tuples: `(is_valid, data, errors)` in `RulesValidator.validate_file()`
- Raise exceptions for configuration issues: `raise ValueError("Missing required section")` in `ConfigManager`
- API call retry mechanism using `@retry` decorator: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))`

## Logging

**Framework:** Python's built-in `logging` module

**Patterns:**
- Logger created per module: `logger = logging.getLogger(__name__)`
- Color-enhanced logging in entry points using `colorlog`: `colorlog.ColoredFormatter()` with color levels
- Logging levels: DEBUG, INFO, WARNING, ERROR used consistently
- Info-level for major operations: `logger.info("Starting evaluation process")`
- Debug-level for detailed steps: `logger.debug("Generating response for: ...")`
- Error-level with stack traces: `logger.error(f"Error: {e}", exc_info=True)`
- Warning-level for non-critical issues: `logger.warning("Environment variable not found")`

## Comments

**When to Comment:**
- Used sparingly; code is generally self-documenting
- Comments explain "why" not "what" (implementation logic)
- Inline comments for non-obvious logic: `# Store original for reporting`
- Comments in simple processing steps: `# If CSV parsing fails, return as-is`

**JSDoc/TSDoc:**
- Not applicable (Python codebase)
- Docstrings used following Python conventions
- Triple-quoted docstrings on classes and functions

## Function Design

**Size:**
- Methods typically 10-40 lines
- Longer methods (50-100 lines) reserved for orchestration: `_calculate_prompt_score()` is ~100 lines, handles complex scoring logic
- Short utility methods 5-15 lines: `_generate_id()`, `process_text()`

**Parameters:**
- Functions use type hints: `def validate_file(self, file_path: str) -> Tuple[bool, Dict[str, Any], List[str]]:`
- Parameters ordered: required first, optional with defaults last
- Dict/config parameters often use `**kwargs` for flexibility or explicit dict: `config: Dict[str, Any]`

**Return Values:**
- Explicit tuple returns for multi-value results: `(is_valid, data, errors)`
- Dict returns for complex structures: `Dict[str, Any]`
- Single boolean or string returns for simple operations
- Methods often return `self` for chaining (not observed) or None for mutations

## Module Design

**Exports:**
- Modules export main classes and factories: `RulesValidator`, `ConfigManager`, `AIProviderFactory`
- Abstract base classes provided for extension: `class ContentSource(ABC)`, `class AIProvider(ABC)`
- Factory patterns for creating instances: `AIProviderFactory.create(config)`

**Barrel Files:**
- `__init__.py` files exist but typically minimal or empty
- Direct imports from specific modules: `from src.rules_validator import RulesValidator`
- No heavy re-exports or aggregation patterns observed

## Code Organization Principles

**Modularity:**
- Each tool is independent with its own `src/`, `tests/`, `requirements.txt`
- Shared patterns replicated across tools (config_manager, evaluator pattern)
- No cross-tool imports observed

**Abstraction:**
- Abstract base classes define interfaces: `AIProvider`, `ContentSource`
- Implementations inherit and override: `OpenAIProvider(AIProvider)`, `AnthropicProvider(AIProvider)`
- Factory pattern for provider creation avoids conditional logic

**Configuration:**
- YAML-based configuration files with environment variable substitution
- `${ENV_VAR}` syntax in config files replaced at runtime
- Validation in `ConfigManager._validate_config()` ensures required sections present

---

*Convention analysis: 2026-01-21*
