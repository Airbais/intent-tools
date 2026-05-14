---
phase: 04-error-handling
plan: "01"
subsystem: automation-api
tags: [exceptions, error-handling, datetime, utilities]

requires:
  - 03-05  # Structured logging infrastructure for error logging

provides:
  - Custom exception hierarchy with error codes and HTTP status codes
  - UTC-aware datetime utilities for timestamp generation
  - Foundation for structured error responses

affects:
  - 04-02  # Flask error handlers will consume these exceptions
  - 04-03  # Error logging will use these exception attributes

tech-stack:
  added: []
  patterns:
    - "Custom exception hierarchy with error_code and status_code attributes"
    - "UTC-aware datetime utilities replacing naive datetime.now()"
    - "Semantic exception types for domain errors (tool, job, config, parameter)"

key-files:
  created:
    - path: automation/exceptions.py
      provides: "Custom exception classes for API errors"
      exports: ["AirbaisAPIException", "ToolNotFoundError", "ToolExecutionError", "JobNotFoundError", "ConfigurationError", "InvalidParameterError"]
    - path: automation/utils.py
      provides: "UTC-aware datetime utilities"
      exports: ["utc_now_iso", "utc_now"]
  modified: []

decisions:
  - id: exception-hierarchy
    desc: "Base class AirbaisAPIException with error_code and status_code attributes"
    rationale: "Enables Flask error handlers to generate consistent JSON error responses"
    alternatives: "Use standard exceptions with decorators - rejected for clarity"

  - id: utc-timezone-aware
    desc: "Use datetime.now(timezone.utc) instead of naive datetime.now()"
    rationale: "Prevents timezone bugs and ensures RFC 3339 compliant timestamps"
    alternatives: "Use naive datetimes and document UTC assumption - rejected for safety"

  - id: semantic-exceptions
    desc: "Specific exception types for each error scenario (ToolNotFound, JobNotFound, etc.)"
    rationale: "Type-based error handling clearer than parsing error messages"
    alternatives: "Single exception with error_code parameter - rejected for less type safety"

metrics:
  duration: "1m 9s"
  completed: 2026-01-24
---

# Phase 4 Plan 01: Exception Hierarchy and Utilities Summary

**One-liner:** Custom exception hierarchy with error codes/status codes and UTC-aware datetime utilities for consistent API error handling

## What Was Built

Created two foundational modules for error handling:

1. **automation/exceptions.py** - Custom exception hierarchy:
   - `AirbaisAPIException` base class with `error_code`, `status_code`, `message` attributes
   - `ToolNotFoundError` - 404 when tool not in config
   - `ToolExecutionError` - 500 when tool execution fails
   - `JobNotFoundError` - 404 when job ID not found
   - `ConfigurationError` - 500 for config errors
   - `InvalidParameterError` - 400 for invalid parameters

2. **automation/utils.py** - UTC-aware datetime utilities:
   - `utc_now_iso()` - Returns RFC 3339 formatted timestamp
   - `utc_now()` - Returns timezone-aware datetime object

All exceptions include structured attributes for consistent error responses. Datetime utilities ensure all timestamps are timezone-aware and RFC 3339 compliant.

## Tasks Completed

| Task | Name                             | Commit  | Files                   |
|------|----------------------------------|---------|-------------------------|
| 1    | Create custom exception hierarchy | 7d37942 | automation/exceptions.py |
| 2    | Create datetime utility module    | 08ea4bd | automation/utils.py     |

## Deviations from Plan

None - plan executed exactly as written.

## Key Technical Decisions

### Exception Attribute Design

**Decision:** Store `error_code` (machine-readable) and `status_code` (HTTP) as instance attributes.

**Rationale:** Flask error handlers (04-02) can extract these attributes to generate consistent JSON error responses without string parsing.

**Implementation:**
```python
class AirbaisAPIException(Exception):
    def __init__(self, message: str, error_code: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
```

### UTC Timezone Awareness

**Decision:** Use `datetime.now(timezone.utc)` instead of naive `datetime.now()`.

**Rationale:** Prevents timezone bugs when comparing timestamps across systems. Ensures RFC 3339 compliance for API responses.

**Implementation:**
```python
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
    # Returns: "2026-01-24T19:45:10.229789+00:00"
```

### Semantic Exception Types

**Decision:** Create specific exception classes for each error scenario rather than generic exceptions with error codes.

**Rationale:**
- Type-based error handling clearer in code
- IDE autocomplete shows available exception types
- Each exception can store domain-specific attributes (tool_name, job_id)

**Example:**
```python
raise ToolNotFoundError('intentcrawler')  # Stores tool_name attribute
# vs
raise AirbaisAPIException('Tool not found', 'TOOL_NOT_FOUND', 404)  # No structure
```

## Testing Notes

Verified all exceptions and utilities:
- Exception classes instantiate correctly with expected attributes
- `ToolNotFoundError('test')` produces: `TOOL_NOT_FOUND, 404, Tool 'test' not found`
- `utc_now_iso()` returns RFC 3339 timestamp with `+00:00` timezone offset
- All imports work from automation/ directory

## Next Phase Readiness

**Ready for 04-02:** Flask error handlers can now:
- Catch custom exceptions by type
- Extract `error_code` and `status_code` attributes
- Generate structured JSON error responses

**Ready for 04-03:** Error logging can:
- Use `utc_now_iso()` for consistent timestamps
- Include exception attributes in structured logs
- Replace naive datetime.now() calls throughout codebase

**No blockers:** Both modules are self-contained utilities with no external dependencies beyond Python stdlib.

## Lessons Learned

**Minimal utility modules:** Both files are simple, focused utilities with clear single responsibilities. This makes them easy to import and test.

**Attribute-based design:** Storing error_code and status_code as attributes (rather than in a dict) provides better IDE support and type safety.

**RFC 3339 compliance:** Using `.isoformat()` ensures timestamps are parseable by any RFC 3339 compliant parser, improving API interoperability.
