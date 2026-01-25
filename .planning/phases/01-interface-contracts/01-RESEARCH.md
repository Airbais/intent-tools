# Phase 1: Interface Contracts - Research

**Researched:** 2026-01-23
**Domain:** JSON Schema validation in Python multi-tool dashboard systems
**Confidence:** HIGH

## Summary

This research investigates how to implement explicit schema validation for the Airbais Tools dashboard-data.json format to replace heuristic tool detection with a robust contract system. The investigation covered JSON schema libraries, backwards compatibility strategies, migration patterns, and multi-producer/single-consumer patterns.

**Current State:** The dashboard uses heuristic detection (lines 142-195 in data_loader.py) checking for specific key combinations to identify tool types. Each tool generates dashboard-data.json independently with no schema validation.

**Standard Approach:** Use Python's jsonschema library (v4.26.0, released Jan 2026) with Draft 2020-12 specification to define and validate a common schema with a required `tool_type` discriminator field. Implement backwards-compatible migration using default values and optional fields for legacy data.

**Primary recommendation:** Define JSON Schema with required `tool_type` field using string enum (not just string type), implement validation at dashboard load time with graceful degradation for legacy files, and backfill existing files with explicit tool_type during migration phase.

## Standard Stack

The established libraries/tools for JSON schema validation in Python:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| jsonschema | 4.26.0 (Jan 2026) | Schema validation | Official Python implementation, 10k+ GitHub stars, supports all draft versions including latest Draft 2020-12, full format validation support |
| python-jsonschema | 4.26.0 | Same as above | Canonical implementation maintained by json-schema.org Python team |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsonschema-rs | 0.40.0 (Jan 2026) | High-performance Rust-based validation | When validating 100k+ records, 10x faster but less mature |
| Pydantic | 2.x | Data parsing with validation | When building models, not pure schema validation; 5-50x faster but different use case |
| jsonschema-default | 1.8.1 | Apply default values from schema | Migration scenarios to backfill missing required fields |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| jsonschema | Pydantic | Pydantic is 10x faster but designed for parsing/models, not validating arbitrary JSON against schemas; different mental model |
| jsonschema | jsonschema-rs | 10x performance but less mature, potential compatibility issues; only if performance bottleneck proven |
| string type | enum type | Enum provides stricter validation but harder to extend; use enum with versioning strategy |

**Installation:**
```bash
pip install jsonschema>=4.26.0
# Optional: for format validation (email, uri, etc.)
pip install jsonschema[format]
# Optional: for applying defaults during migration
pip install jsonschema-default
```

## Architecture Patterns

### Recommended Project Structure
```
.planning/
├── schemas/
│   ├── dashboard-data.schema.json    # Main schema definition
│   └── versions/
│       ├── v1.0.0.schema.json        # Versioned schemas for compatibility
│       └── v1.1.0.schema.json
dashboard/
├── schema_validator.py               # Validation logic
├── data_loader.py                    # Updated loader with validation
└── schema_migrations.py              # Migration utilities
```

### Pattern 1: Schema Definition with Discriminator
**What:** Define JSON Schema with required `tool_type` discriminator field
**When to use:** Multi-tool systems where consumer needs to route/render based on producer type
**Example:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://airbais.com/schemas/dashboard-data/v1.0.0",
  "title": "Airbais Dashboard Data",
  "description": "Common schema for all Airbais tool outputs",
  "type": "object",
  "required": ["tool_type", "timestamp", "summary", "metrics", "data"],
  "properties": {
    "tool_type": {
      "type": "string",
      "enum": [
        "intentcrawler",
        "graspevaluator",
        "llmevaluator",
        "geoevaluator",
        "rulesevaluator",
        "llmstxtgenerator"
      ],
      "description": "Identifies which tool generated this data"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "summary": {
      "type": "object",
      "description": "Tool-specific summary data"
    },
    "metrics": {
      "type": "object",
      "description": "Tool-specific metrics"
    },
    "data": {
      "type": "object",
      "description": "Tool-specific detailed data"
    }
  },
  "additionalProperties": true
}
```
**Source:** [JSON Schema Specification Draft 2020-12](https://json-schema.org/draft/2020-12) and [OpenAPI Discriminator Pattern](https://redocly.com/learn/openapi/discriminator)

### Pattern 2: Validation at Load Time with Error Handling
**What:** Validate on dashboard data load with graceful degradation
**When to use:** Consumer-side validation to protect dashboard from malformed data
**Example:**
```python
# Source: jsonschema documentation patterns
from jsonschema import validate, ValidationError, Draft202012Validator
import json
from pathlib import Path

class DashboardDataValidator:
    def __init__(self, schema_path: Path):
        with open(schema_path) as f:
            self.schema = json.load(f)
        self.validator = Draft202012Validator(self.schema)

    def validate_data(self, data: dict) -> tuple[bool, list[str]]:
        """Validate dashboard data, return (is_valid, errors)"""
        errors = []
        for error in self.validator.iter_errors(data):
            errors.append(f"{error.json_path}: {error.message}")
        return len(errors) == 0, errors

    def validate_with_fallback(self, data: dict) -> dict:
        """Validate and inject defaults for missing required fields"""
        is_valid, errors = self.validate_data(data)

        if not is_valid and "tool_type" not in data:
            # Fallback to heuristic detection for legacy files
            data["tool_type"] = self._detect_tool_type_heuristic(data)
            self.logger.warning(f"Applied heuristic tool_type: {data['tool_type']}")

        return data
```
**Source:** [jsonschema validation documentation](https://python-jsonschema.readthedocs.io/en/stable/validate/)

### Pattern 3: Schema Registry Pattern (Multi-Producer/Single-Consumer)
**What:** Centralized schema management where multiple tools (producers) write to common format consumed by dashboard
**When to use:** When you have 3+ independent producers and need to enforce contracts
**Example:**
```python
# Source: Kafka Schema Registry pattern adapted for file-based system
class SchemaRegistry:
    """Centralized schema management for multi-tool dashboard"""

    def __init__(self, schema_dir: Path):
        self.schemas = {}
        self._load_schemas(schema_dir)

    def validate_tool_output(self, tool_type: str, data: dict) -> bool:
        """Validate that tool output conforms to registered schema"""
        if tool_type not in self.schemas:
            raise ValueError(f"Unknown tool_type: {tool_type}")

        base_schema = self.schemas["base"]
        tool_schema = self.schemas[tool_type]

        # Validate against base schema first
        validate(data, base_schema)

        # Then validate tool-specific fields
        validate(data.get("data", {}), tool_schema)

        return True
```
**Source:** [Schema Registry pattern documentation](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)

### Anti-Patterns to Avoid
- **Validating string type without enum:** Using `"type": "string"` for tool_type allows any string value, defeating the purpose of explicit contracts. Always use enum for discriminator fields.
- **Required fields without migration path:** Adding required fields breaks existing data. Use optional fields with defaults, or implement explicit migration.
- **Heuristic detection alongside schema validation:** Don't maintain both systems long-term. Use heuristics only as temporary fallback during migration.
- **Schema without $schema declaration:** Always specify `"$schema"` to lock draft version and prevent ambiguity.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON validation | Custom if/else checks on keys | jsonschema library | Schema validation has edge cases (nested objects, array types, format validation, $ref resolution) that took years to standardize across Draft 2020-12 |
| Default value injection | Manual dict.setdefault() | jsonschema-default | Handles nested defaults, conditional defaults, and schema $ref resolution correctly |
| Schema versioning | Timestamp-based filenames | Semantic versioning in $id | Industry standard for schema evolution, tooling understands semver |
| Error reporting | Exception with string message | ValidationError.iter_errors() | Provides json_path, schema_path, and structured error tree for UX |
| Format validation | Regex on strings | jsonschema format keyword | Handles email, uri, ipv4, date-time with battle-tested patterns |

**Key insight:** JSON Schema is deceptively complex. Simple schemas are easy, but handling $ref, $defs, conditional validation, format checking, and backwards compatibility requires a mature library. The jsonschema library encodes 10+ years of edge case handling.

## Common Pitfalls

### Pitfall 1: Adding Required Fields Without Migration Strategy
**What goes wrong:** Existing dashboard-data.json files break when schema adds required fields
**Why it happens:** Schema validation is "fail-fast" by default - missing required field = ValidationError
**How to avoid:**
1. Make new fields optional initially: `"required": ["tool_type"]` then expand later
2. Use default values: Set `"default": "unknown"` in schema and apply with jsonschema-default
3. Implement explicit migration: Backfill existing files before enforcing validation
**Warning signs:** ValidationError raised on previously working files after schema update

### Pitfall 2: Enum vs String for tool_type
**What goes wrong:** Using `"type": "string"` allows typos like "llmEvaluator" vs "llmevaluator"
**Why it happens:** Developers assume string type provides enough validation
**How to avoid:** Always use enum for discriminator fields:
```json
{
  "tool_type": {
    "type": "string",
    "enum": ["intentcrawler", "graspevaluator", "llmevaluator", "geoevaluator", "rulesevaluator", "llmstxtgenerator"]
  }
}
```
**Warning signs:** Dashboard fails to render tool-specific views due to unrecognized tool_type

### Pitfall 3: Schema Draft Version Mismatch
**What goes wrong:** Schema uses Draft 2020-12 features but validator defaults to Draft 7
**Why it happens:** Not specifying `$schema` in JSON, or using wrong validator class
**How to avoid:**
1. Always include `"$schema": "https://json-schema.org/draft/2020-12/schema"` in JSON
2. Use `Draft202012Validator` class explicitly or let library auto-detect from `$schema`
3. Test with multiple draft versions if supporting legacy schemas
**Warning signs:** Keywords like `prefixItems` not recognized, validation behaves unexpectedly

### Pitfall 4: Forgetting Format Validation Opt-In
**What goes wrong:** Schema defines `"format": "date-time"` but validation passes invalid dates
**Why it happens:** Format validation requires explicit opt-in via FormatChecker
**How to avoid:**
```python
from jsonschema import Draft202012Validator, FormatChecker

validator = Draft202012Validator(schema, format_checker=FormatChecker())
# OR
validate(data, schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
```
**Warning signs:** Invalid email/uri/date values pass validation despite format declaration

### Pitfall 5: Backwards Incompatible Schema Changes
**What goes wrong:** Dashboard breaks when tools update their schema version
**Why it happens:** Not following backwards-compatible evolution rules
**How to avoid:**
1. **Adding fields:** Always make them optional (don't add to `required`)
2. **Removing fields:** Keep for 1+ versions with deprecated flag before removing
3. **Renaming fields:** Add new field, keep old deprecated, remove after transition
4. **Changing types:** Use oneOf to support both old and new types during transition
**Warning signs:** Newer tool versions break older dashboard, or vice versa

## Code Examples

Verified patterns from official sources:

### Basic Validation with Error Handling
```python
# Source: https://python-jsonschema.readthedocs.io/en/stable/validate/
from jsonschema import validate, ValidationError, Draft202012Validator
import json

# Load schema
with open("dashboard-data.schema.json") as f:
    schema = json.load(f)

# Load data
with open("intentcrawler/results/2025-01-23/dashboard-data.json") as f:
    data = json.load(f)

# Validate
try:
    validate(data, schema)
    print("✓ Data is valid")
except ValidationError as e:
    print(f"✗ Validation failed:")
    print(f"  Path: {e.json_path}")
    print(f"  Error: {e.message}")
```

### Collecting All Errors (Don't Fail Fast)
```python
# Source: https://python-jsonschema.readthedocs.io/en/stable/validate/
from jsonschema import Draft202012Validator

validator = Draft202012Validator(schema)

errors = list(validator.iter_errors(data))
if errors:
    print(f"Found {len(errors)} validation errors:")
    for error in errors:
        print(f"  • {error.json_path}: {error.message}")
else:
    print("✓ Data is valid")
```

### Validation with Format Checking
```python
# Source: https://python-jsonschema.readthedocs.io/en/stable/validate/
from jsonschema import validate, Draft202012Validator

# Enable format validation (email, uri, date-time, etc.)
validate(
    data,
    schema,
    format_checker=Draft202012Validator.FORMAT_CHECKER
)
```

### Applying Defaults for Migration
```python
# Source: https://github.com/mnboos/jsonschema-default
from jsonschema_default import apply_defaults

# Schema with defaults
schema = {
    "type": "object",
    "properties": {
        "tool_type": {
            "type": "string",
            "default": "unknown"
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        }
    },
    "required": ["tool_type", "timestamp"]
}

# Legacy data missing tool_type
legacy_data = {
    "timestamp": "2025-01-23T10:00:00Z",
    "summary": {}
}

# Apply defaults from schema
migrated_data = apply_defaults(legacy_data, schema)
# Result: {"tool_type": "unknown", "timestamp": "2025-01-23T10:00:00Z", "summary": {}}
```

### Schema Evolution Pattern (Backwards Compatible)
```python
# Source: Schema evolution best practices
# https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html

# V1.0.0 - Initial schema
v1_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://airbais.com/schemas/dashboard-data/v1.0.0",
    "type": "object",
    "required": ["timestamp", "summary", "metrics", "data"],
    "properties": {
        "timestamp": {"type": "string", "format": "date-time"},
        "summary": {"type": "object"},
        "metrics": {"type": "object"},
        "data": {"type": "object"}
    }
}

# V1.1.0 - Add tool_type (BACKWARDS COMPATIBLE)
v1_1_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://airbais.com/schemas/dashboard-data/v1.1.0",
    "type": "object",
    "required": ["timestamp", "summary", "metrics", "data"],  # DON'T add tool_type yet
    "properties": {
        "tool_type": {
            "type": "string",
            "enum": ["intentcrawler", "graspevaluator", "llmevaluator", "geoevaluator", "rulesevaluator", "llmstxtgenerator"]
        },
        "timestamp": {"type": "string", "format": "date-time"},
        "summary": {"type": "object"},
        "metrics": {"type": "object"},
        "data": {"type": "object"}
    }
}

# V1.2.0 - Make tool_type required (after migration period)
v1_2_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://airbais.com/schemas/dashboard-data/v1.2.0",
    "type": "object",
    "required": ["tool_type", "timestamp", "summary", "metrics", "data"],  # NOW require it
    "properties": {
        "tool_type": {
            "type": "string",
            "enum": ["intentcrawler", "graspevaluator", "llmevaluator", "geoevaluator", "rulesevaluator", "llmstxtgenerator"]
        },
        "timestamp": {"type": "string", "format": "date-time"},
        "summary": {"type": "object"},
        "metrics": {"type": "object"},
        "data": {"type": "object"}
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Draft 7 items keyword | Draft 2020-12 prefixItems + items | JSON Schema 2020-12 | Clearer array vs tuple validation, easier learning curve |
| $recursiveRef | $dynamicRef/$dynamicAnchor | JSON Schema 2020-12 | More powerful schema composition patterns |
| Manual default injection | jsonschema-default library | 2019 | Automated defaults handling with nested support |
| format-only validation | format-annotation + format-assertion | JSON Schema 2020-12 | Separate documentation vs validation concerns |
| Python 3.8+ support | Python 3.10+ only | jsonschema 4.26.0 (Jan 2026) | Leverages modern Python features, drops legacy support |

**Deprecated/outdated:**
- **_RefResolver class**: Fully deprecated in jsonschema 4.x, replaced by referencing.Registry for $ref resolution
- **Draft 4/6 as primary:** Should use Draft 2020-12 for new schemas (though library supports all versions)
- **validate() without format_checker:** Format validation now requires explicit opt-in
- **String-only enum values:** Draft 2020-12 supports mixed types in enum, enables better validation patterns

## Open Questions

Things that couldn't be fully resolved:

1. **Should schema include tool-specific validation?**
   - What we know: Base schema can define common structure, tool-specific schemas can validate `data` object
   - What's unclear: Whether to maintain separate schemas per tool or single schema with conditional validation
   - Recommendation: Start with base schema only, add tool-specific schemas if validation needs emerge (YAGNI principle)

2. **How to handle schema version in existing files?**
   - What we know: Files don't currently include schema version metadata
   - What's unclear: Whether to add schema_version field or infer from file structure
   - Recommendation: Add optional `schema_version` field (defaults to "1.0.0" if missing) for future evolution

3. **Performance impact of validation on dashboard load?**
   - What we know: jsonschema is synchronous, jsonschema-rs is 10x faster but less mature
   - What's unclear: Whether validation will create perceived latency on dashboard load
   - Recommendation: Measure first, optimize later. If < 100ms per file, no issue. If > 500ms, consider jsonschema-rs or async validation

## Sources

### Primary (HIGH confidence)
- [jsonschema 4.26.0 documentation](https://python-jsonschema.readthedocs.io/) - Official Python implementation
- [JSON Schema Specification Draft 2020-12](https://json-schema.org/draft/2020-12) - Official specification
- [jsonschema PyPI page](https://pypi.org/project/jsonschema/) - Release info and installation
- [Schema Validation docs](https://python-jsonschema.readthedocs.io/en/stable/validate/) - Official validation guide
- [Handling Validation Errors](https://python-jsonschema.readthedocs.io/en/stable/errors/) - Error handling patterns

### Secondary (MEDIUM confidence)
- [JSON Schema Enumerated Values](https://json-schema.org/understanding-json-schema/reference/enum) - Enum best practices
- [OpenAPI Discriminator Guide](https://redocly.com/learn/openapi/discriminator) - Discriminator pattern usage
- [Schema Evolution in Data Pipelines](https://dataengineeracademy.com/module/best-practices-for-managing-schema-evolution-in-data-pipelines/) - Evolution strategies
- [Confluent Schema Registry](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html) - Multi-producer patterns
- [Data Contracts in 2026](https://atlan.com/data-contracts/) - Modern data contract tooling

### Tertiary (LOW confidence)
- [Python Data Validation Comparison](https://dev.to/anirudhann/data-validation-libraries-analysis-comparison-using-python-31a4) - Pydantic vs jsonschema performance claims (needs verification with current versions)
- [jsonschema-default library](https://github.com/mnboos/jsonschema-default) - Defaults handling (small GitHub project, verify behavior)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - jsonschema is official Python implementation, well-documented, actively maintained (Jan 2026 release)
- Architecture: HIGH - Patterns sourced from official docs, OpenAPI spec, and Confluent Schema Registry (industry standards)
- Pitfalls: HIGH - Based on official FAQ, GitHub issues, and schema evolution best practices

**Research date:** 2026-01-23
**Valid until:** ~60 days (stable domain, but library updates may introduce new features)

**Key Assumptions:**
- Dashboard loads files synchronously (validation latency matters)
- All tools are Python-based (can import jsonschema)
- No existing schema versioning or migration system
- Current detection heuristics work but are brittle
- Tools generate files independently (no coordination)
