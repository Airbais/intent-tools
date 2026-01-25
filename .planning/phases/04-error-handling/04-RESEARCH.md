# Phase 4: Error Handling - Research

**Researched:** 2026-01-24
**Domain:** Python Exception Handling, Flask Error Responses, Structured Logging Integration
**Confidence:** HIGH

## Summary

Error handling in Python Flask APIs for 2026 follows well-established patterns with increasing emphasis on specific exception types over bare except blocks. PEP 760 proposes deprecating bare except clauses in Python 3.14, reflecting the community consensus that explicit exception handling is critical for maintainability and debugging.

The standard approach combines custom exception hierarchies with Flask's built-in error handlers, structlog integration for contextual logging, and structured JSON error responses with consistent schemas. The job ID "cleanup" logic found in earlier versions (line 282-288 in git history) is a workaround symptom, not a root cause fix—the actual issue is that job IDs are being validated with Pydantic on retrieval but the validation was added after the cleanup workaround was implemented.

**Primary recommendation:** Define a custom exception hierarchy rooted in a base `AirbaisAPIException` class, replace the single bare except block at line 203 with specific `JSONDecodeError`, integrate exception logging with structlog's `exc_info=True` for full traceback capture, implement a structured error response schema with `error_code`, `message`, and `correlation_id` fields, remove the job ID regex cleanup workaround (Pydantic validation already handles this correctly via `JobIdPath` model), and enforce explicit ISO-8601 datetime serialization at creation time rather than relying on Flask's implicit conversion.

## Current State Analysis

### Bare Exception Handlers

**Location:** `automation/api_server.py:203`

```python
try:
    with open(file_path, 'r') as f:
        data = json.load(f)
        results['metrics'] = {
            'pages_analyzed': data.get('total_pages_analyzed', 0),
            'intents_discovered': data.get('total_intents', 0),
            'processing_time_seconds': None
        }
except:
    pass
```

**Issue:** This is the ONLY bare except block in the automation/ directory. All other exception handlers use specific types (`Exception`, `ValidationError`, `ValueError`, `OSError`).

**Why it exists:** Parsing dashboard-data.json is optional—if the file is malformed or missing keys, tool execution should continue. However, using bare except catches even `KeyboardInterrupt` and `SystemExit`.

**Fix:** Replace with `except (json.JSONDecodeError, KeyError, IOError):` to catch only the expected failures.

### Exception Handlers Using `except Exception`

Found in the following locations:

| File | Line | Context | Specific Type Needed |
|------|------|---------|---------------------|
| `api_server.py` | 43 | Config file loading | `yaml.YAMLError, IOError` |
| `api_server.py` | 220 | Tool execution wrapper | Keep as `Exception` (catch-all for subprocess) |
| `api_server.py` | 291 | Analyze endpoint | Keep as `Exception` (API boundary) |
| `test_*.py` | Multiple | Test scripts | Acceptable for test harness |

**Assessment:** Lines 220 and 291 are appropriate uses of `except Exception` because they are at API boundaries where we want to catch any error, log it with full context via structlog, and return a sanitized error response. Line 43 should be more specific.

### Current Error Response Format

**api_server.py lines 249-252, 262-266:**
```python
return jsonify({
    'error': f'Unknown tool: {tool_name}',
    'available_tools': list(TOOL_CONFIGS.keys())
}), 404
```

**Observations:**
- No consistent schema across endpoints
- No `error_code` field for programmatic handling
- No `correlation_id` included (despite Phase 3 implementing correlation IDs)
- No `request_id` or `timestamp` fields
- Error messages are human-readable but not machine-parseable

**error_handlers.py current structure:**
Already implements sanitized responses and uses structlog. However, it doesn't include correlation_id in responses or use error codes.

### Job ID Issue (ERR-04)

**Historical context from git history (commit 70b09a0, lines 282-288):**

```python
# Clean up job_id - remove any trailing special characters
original_id = job_id
# Remove any non-alphanumeric characters from the end (except hyphens)
job_id = re.sub(r'[^a-zA-Z0-9\-]+$', '', job_id).strip()

if original_id != job_id:
    logger.info(f"Cleaned job_id from '{original_id}' to '{job_id}'")
```

**Analysis:**
1. This cleanup logic was REMOVED in later commits (current version at line 382 total)
2. Pydantic validation was added in Phase 2 (`JobIdPath` model with UUID regex pattern)
3. The "trailing special character" issue was likely caused by:
   - URL encoding issues when job_id passed as path parameter
   - Clients appending trailing slashes or newlines
   - Copy-paste errors including whitespace

**Root cause:** User error, not code generation error. `str(uuid.uuid4())` does NOT add trailing characters (verified with Python test—all UUIDs are exactly 36 characters).

**Current state:** `JobIdPath` Pydantic model validates format on `/status/<job_id>` and `/results/<job_id>` endpoints (lines 303, 336). This is the CORRECT fix.

**Conclusion:** ERR-04 is already FIXED by Pydantic validation in Phase 2. The requirement should be re-scoped to "ensure job ID validation prevents malformed inputs" which is already complete. However, we should add validation at job CREATION to fail fast if something is wrong.

### Datetime Serialization (ERR-05)

**Current implementation (api_server.py):**

```python
'created_at': datetime.now().isoformat(),  # Line 72
'updated_at': datetime.now().isoformat(),  # Line 73, 87
'completed_at': datetime.now().isoformat(),  # Line 216, 231
'timestamp': datetime.now().isoformat(),    # Line 239 (health check)
```

**Assessment:** ✅ Already using explicit `.isoformat()` conversion consistently.

**Potential issue:** `datetime.now()` without timezone is "naive" and won't include timezone offset in ISO format. Best practice is `datetime.now(timezone.utc).isoformat()` to ensure RFC 3339 compliance.

**Fix scope:** Change all `datetime.now()` to `datetime.now(timezone.utc)` and verify `.isoformat()` produces RFC 3339 format with 'Z' suffix.

### Structlog Integration

Phase 3 completed structlog implementation:
- `logger = structlog.get_logger(__name__)` in all modules
- `exc_info=True` already used in error_handlers.py and api_server.py
- Correlation IDs bound to context via `structlog.contextvars`
- Request/response logging middleware active

**Gap:** Error responses don't include correlation_id in JSON body. Clients receive `X-Correlation-ID` header but not in response payload.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| structlog | 24.1.0+ | Exception logging with context | Already integrated in Phase 3, `exc_info=True` captures full tracebacks |
| Pydantic | 2.x | Input validation preventing bad data | Already integrated in Phase 2, prevents malformed job_id |
| Flask | 3.0.0 | Error handler registration | Built-in `@app.errorhandler()` for custom exception mapping |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Built-in `json` | stdlib | JSONDecodeError for parsing | Specific exception for dashboard-data.json parsing |
| Built-in `datetime` | stdlib | timezone.utc for RFC 3339 | Import `timezone` for UTC-aware datetimes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom exception hierarchy | Generic Exception everywhere | Less maintainable, harder to handle errors differently |
| Structured error codes | HTTP status only | No programmatic error handling for clients |
| datetime.now(timezone.utc) | datetime.utcnow() (deprecated) | utcnow() deprecated in Python 3.12+ |

**Installation:**
No new packages required—all necessary libraries already installed.

## Architecture Patterns

### Pattern 1: Custom Exception Hierarchy

**What:** Define application-specific exceptions inheriting from a base class
**When to use:** When different error types need different handling or logging strategies

**Example:**
```python
# automation/exceptions.py
class AirbaisAPIException(Exception):
    """Base exception for Airbais API errors."""
    def __init__(self, message: str, error_code: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class ToolNotFoundError(AirbaisAPIException):
    """Raised when requested tool doesn't exist."""
    def __init__(self, tool_name: str):
        super().__init__(
            message=f"Tool '{tool_name}' not found",
            error_code="TOOL_NOT_FOUND",
            status_code=404
        )
        self.tool_name = tool_name


class ToolExecutionError(AirbaisAPIException):
    """Raised when tool subprocess fails."""
    def __init__(self, tool_name: str, details: str):
        super().__init__(
            message=f"Tool execution failed: {details}",
            error_code="TOOL_EXECUTION_FAILED",
            status_code=500
        )
        self.tool_name = tool_name
        self.details = details


class JobNotFoundError(AirbaisAPIException):
    """Raised when job_id doesn't exist."""
    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job '{job_id}' not found",
            error_code="JOB_NOT_FOUND",
            status_code=404
        )
        self.job_id = job_id


class ConfigurationError(AirbaisAPIException):
    """Raised when configuration is invalid."""
    def __init__(self, details: str):
        super().__init__(
            message=f"Configuration error: {details}",
            error_code="CONFIG_ERROR",
            status_code=500
        )
```

### Pattern 2: Structured Error Response Schema

**What:** Consistent JSON schema for all error responses
**When to use:** All API error responses (4xx and 5xx)

**Example:**
```python
# automation/error_handlers.py (updated)
def build_error_response(
    error: str,
    message: str,
    error_code: str = None,
    status_code: int = 500,
    details: dict = None
) -> tuple:
    """
    Build a structured error response.

    Args:
        error: Error type (e.g., "Not Found", "Internal Server Error")
        message: Human-readable error message
        error_code: Machine-readable error code (e.g., "JOB_NOT_FOUND")
        status_code: HTTP status code
        details: Optional additional error details

    Returns:
        Tuple of (jsonify response, status_code)
    """
    from log_config import get_correlation_id

    response = {
        'error': error,
        'message': message,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'correlation_id': get_correlation_id(),
    }

    if error_code:
        response['error_code'] = error_code

    if details:
        response['details'] = details

    return jsonify(response), status_code


def handle_airbais_exception(e: AirbaisAPIException):
    """Handle custom Airbais exceptions."""
    logger.error(
        "airbais_api_error",
        error_code=e.error_code,
        error=str(e),
        exc_info=True
    )
    return build_error_response(
        error=type(e).__name__,
        message=e.message,
        error_code=e.error_code,
        status_code=e.status_code
    )
```

**Response format:**
```json
{
  "error": "JobNotFoundError",
  "message": "Job 'abc-123' not found",
  "error_code": "JOB_NOT_FOUND",
  "timestamp": "2026-01-24T12:34:56.789000Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Pattern 3: Exception Logging with Context

**What:** Use structlog's `exc_info=True` and bound context for rich error logs
**When to use:** All exception handlers and catch blocks

**Example:**
```python
# In run_tool_async
try:
    logger.info("tool_execution_started", parameters=redact_sensitive(params))
    # ... tool execution ...
except subprocess.CalledProcessError as e:
    logger.error(
        "tool_subprocess_failed",
        return_code=e.returncode,
        stdout=e.stdout[:500] if e.stdout else None,
        stderr=e.stderr[:500] if e.stderr else None,
        exc_info=True  # Captures full traceback
    )
    raise ToolExecutionError(tool_name, f"Exit code {e.returncode}")
except FileNotFoundError as e:
    logger.error(
        "tool_results_not_found",
        expected_path=results_dir,
        exc_info=True
    )
    raise ToolExecutionError(tool_name, "Results directory not found")
```

**Structured log output (JSON):**
```json
{
  "timestamp": "2026-01-24T12:34:56.789Z",
  "level": "error",
  "logger": "automation.api_server",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": "abc-123",
  "tool_name": "intentcrawler",
  "event": "tool_subprocess_failed",
  "return_code": 1,
  "stderr": "Error: Invalid URL format",
  "exception": {
    "exc_type": "CalledProcessError",
    "exc_value": "Command '['python3', 'intentcrawler.py', '--url', 'bad']' returned non-zero exit status 1.",
    "exc_traceback": ["Traceback...", "..."]
  }
}
```

### Pattern 4: UTC-Aware Datetime Serialization

**What:** Always use timezone-aware datetimes with UTC and explicit .isoformat()
**When to use:** All timestamp generation for JSON responses

**Example:**
```python
from datetime import datetime, timezone

# WRONG (naive datetime, no timezone)
'created_at': datetime.now().isoformat()
# Output: "2026-01-24T12:34:56.789123" (no Z or offset)

# CORRECT (UTC-aware, RFC 3339 compliant)
'created_at': datetime.now(timezone.utc).isoformat()
# Output: "2026-01-24T12:34:56.789123+00:00"

# Helper function
def utc_now_iso() -> str:
    """Get current UTC time as ISO 8601 / RFC 3339 string."""
    return datetime.now(timezone.utc).isoformat()
```

### Anti-Patterns to Avoid

- **Bare except blocks:** PEP 760 proposes deprecating these in Python 3.14. Always specify exception types.
- **Catching Exception at business logic level:** Only catch Exception at API boundaries (endpoints). Deeper logic should use specific exceptions.
- **Logging and re-raising without context:** Use `exc_info=True` to preserve traceback. Don't just `logger.error(str(e))`.
- **datetime.utcnow():** Deprecated in Python 3.12+. Use `datetime.now(timezone.utc)` instead.
- **Returning stack traces to clients:** Security risk (SEC-02). Log internally, return sanitized messages.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Error code constants | Scattered string literals | Exception class attributes | Centralized, type-safe, autocomplete-friendly |
| Custom JSON encoders for datetime | json.JSONEncoder subclass | Explicit `.isoformat()` at creation | Simpler, more explicit, less magic |
| Job ID validation regex | Manual regex in every endpoint | Pydantic `JobIdPath` model | Already done, centralizes validation |
| Correlation ID in responses | Manual header parsing | `get_correlation_id()` from log_config | Already available, consistent with logging |

**Key insight:** Phase 2 and Phase 3 already built the infrastructure. Phase 4 is about USING it correctly, not building new systems.

## Common Pitfalls

### Pitfall 1: Forgetting exc_info=True

**What goes wrong:** Exception logged without traceback, making debugging impossible

**Why it happens:** Developer adds `logger.error()` but forgets the critical `exc_info=True` parameter

**How to avoid:**
```python
# BAD - no traceback
except ValueError as e:
    logger.error("validation_failed", error=str(e))

# GOOD - full traceback
except ValueError as e:
    logger.error("validation_failed", error=str(e), exc_info=True)
```

**Warning signs:** Log messages show error text but no file/line numbers or call stack

### Pitfall 2: Catching Too Broadly Then Handling Specifically

**What goes wrong:** Catch Exception but then inspect type manually, defeating the purpose of multiple except blocks

**Why it happens:** Misunderstanding of Python's exception handling order

**How to avoid:**
```python
# BAD - single handler with type checking
try:
    result = risky_operation()
except Exception as e:
    if isinstance(e, ValueError):
        handle_validation_error()
    elif isinstance(e, IOError):
        handle_io_error()
    else:
        handle_unknown()

# GOOD - specific handlers
try:
    result = risky_operation()
except ValueError as e:
    logger.error("validation_failed", exc_info=True)
    handle_validation_error()
except IOError as e:
    logger.error("io_failed", exc_info=True)
    handle_io_error()
except Exception as e:
    logger.critical("unexpected_error", exc_info=True)
    handle_unknown()
```

**Warning signs:** Long if-elif chains inside except blocks

### Pitfall 3: Not Including Correlation ID in Error Responses

**What goes wrong:** Client receives error but can't provide correlation ID when reporting issue

**Why it happens:** Correlation ID is in headers and logs but not response body

**How to avoid:**
```python
# Import correlation ID getter
from log_config import get_correlation_id

# Include in all error responses
response = {
    'error': 'Tool execution failed',
    'correlation_id': get_correlation_id()  # Links to logs
}
```

**Warning signs:** Support tickets say "I got an error" but can't reference specific request in logs

### Pitfall 4: Timezone-Naive Datetimes in JSON

**What goes wrong:** Timestamps lack timezone info, causing ambiguity across systems

**Why it happens:** Using `datetime.now()` instead of `datetime.now(timezone.utc)`

**How to avoid:**
```python
from datetime import datetime, timezone

# BAD - naive datetime
'timestamp': datetime.now().isoformat()
# "2026-01-24T12:34:56.789123" (ambiguous - what timezone?)

# GOOD - UTC-aware
'timestamp': datetime.now(timezone.utc).isoformat()
# "2026-01-24T12:34:56.789123+00:00" (unambiguous)
```

**Warning signs:** Different systems interpret timestamps differently, time arithmetic fails

### Pitfall 5: Exposing Internal Errors to API Clients

**What goes wrong:** Raw exception messages leak file paths, internal structure, SQL queries

**Why it happens:** Using `str(e)` directly in API responses

**How to avoid:**
```python
# BAD - exposes internals
except FileNotFoundError as e:
    return jsonify({'error': str(e)}), 500
    # Returns: "No such file or directory: '/opt/airbais/config/secrets.yaml'"

# GOOD - sanitized message
except FileNotFoundError as e:
    logger.error("config_not_found", path=config_path, exc_info=True)
    return jsonify({
        'error': 'Configuration error',
        'message': 'Required configuration file not found'
    }), 500
```

**Warning signs:** Error responses contain file paths, environment variables, or internal IDs

## Code Examples

### Example 1: Replace Bare Except (api_server.py line 203)

**Current (WRONG):**
```python
try:
    with open(file_path, 'r') as f:
        data = json.load(f)
        results['metrics'] = {
            'pages_analyzed': data.get('total_pages_analyzed', 0),
            'intents_discovered': data.get('total_intents', 0),
            'processing_time_seconds': None
        }
except:
    pass
```

**Fixed (CORRECT):**
```python
try:
    with open(file_path, 'r') as f:
        data = json.load(f)
        results['metrics'] = {
            'pages_analyzed': data.get('total_pages_analyzed', 0),
            'intents_discovered': data.get('total_intents', 0),
            'processing_time_seconds': None
        }
except (json.JSONDecodeError, KeyError, IOError) as e:
    # Dashboard metrics are optional - log and continue
    logger.debug(
        "dashboard_metrics_parse_failed",
        file_path=file_path,
        error=str(e),
        exc_info=True
    )
```

### Example 2: Add Custom Exception to run_tool_async

**Current:**
```python
if process.returncode != 0:
    raise Exception(f"Tool execution failed: {stderr}")
```

**Fixed:**
```python
from exceptions import ToolExecutionError

if process.returncode != 0:
    logger.error(
        "tool_subprocess_failed",
        return_code=process.returncode,
        stderr=stderr[:500],  # Limit log size
        exc_info=True
    )
    raise ToolExecutionError(tool_name, f"Exit code {process.returncode}")
```

### Example 3: Structured Error Response (analyze endpoint)

**Current:**
```python
except Exception as e:
    logger.error("analyze_start_failed", error=str(e), exc_info=True)
    return jsonify({
        'error': 'Failed to start analysis',
        'message': 'Please check server logs for details'
    }), 500
```

**Fixed:**
```python
from log_config import get_correlation_id
from datetime import datetime, timezone

except Exception as e:
    logger.error("analyze_start_failed", error=str(e), exc_info=True)
    return jsonify({
        'error': 'Internal Server Error',
        'error_code': 'ANALYSIS_START_FAILED',
        'message': 'Failed to start analysis',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'correlation_id': get_correlation_id()
    }), 500
```

### Example 4: Fix Datetime Serialization

**Current:**
```python
jobs[job_id] = {
    'created_at': datetime.now().isoformat(),
    'updated_at': datetime.now().isoformat(),
}
```

**Fixed:**
```python
from datetime import datetime, timezone

jobs[job_id] = {
    'created_at': datetime.now(timezone.utc).isoformat(),
    'updated_at': datetime.now(timezone.utc).isoformat(),
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bare except blocks | Specific exception types | PEP 760 (deprecation in 3.14) | Forced explicit error handling |
| datetime.utcnow() | datetime.now(timezone.utc) | Python 3.12 (deprecated) | Explicit timezone awareness |
| Generic error messages | Structured error codes | 2020s API standards | Machine-readable errors |
| Plain text logs | Structured JSON logs | Completed in Phase 3 | ELK/CloudWatch compatibility |
| HTTP status only | Status + error_code + correlation_id | Modern observability | Better debugging and tracing |

**Deprecated/outdated:**
- `datetime.utcnow()`: Use `datetime.now(timezone.utc)` instead
- Bare `except:` clauses: Will be deprecated in Python 3.14 per PEP 760
- Returning internal exceptions to clients: Security anti-pattern per OWASP

## Open Questions

### Question 1: Job ID Validation at Creation Time

**What we know:**
- `JobIdPath` validates on retrieval (/status, /results)
- `create_job()` uses `str(uuid.uuid4())` which always produces valid UUIDs
- Historical cleanup logic removed after Pydantic validation added

**What's unclear:**
- Should we add validation at job creation to verify UUID format?
- Is there a scenario where str(uuid.uuid4()) could fail?

**Recommendation:** Add assertion in create_job() to verify format, but this is defensive programming—not fixing a real bug. The real issue (trailing chars from clients) is already fixed by Pydantic.

### Question 2: Should Error Codes Be Enums or Strings?

**What we know:**
- String literals work but require manual consistency
- Python Enums provide type safety and autocomplete

**What's unclear:**
- Does using Enums complicate JSON serialization?
- Are string literals sufficient for this codebase size?

**Recommendation:** Use string literals stored as class attributes on exception classes. Simpler than Enums and provides centralization. Example: `ToolNotFoundError.error_code = "TOOL_NOT_FOUND"`.

### Question 3: Global Error Handler vs. Per-Endpoint Returns?

**What we know:**
- Flask's `@app.errorhandler()` can catch exceptions globally
- Per-endpoint try/except gives fine-grained control
- Current code uses both approaches

**What's unclear:**
- Should custom exceptions be raised and caught globally?
- Or should endpoints catch and build responses locally?

**Recommendation:** Hybrid approach—raise custom exceptions from business logic, catch them in global handlers for consistency, but allow endpoints to override when specific context needed.

## Plan Breakdown Recommendation

Based on the research findings and current codebase state:

### Plan 04-01: Create Custom Exception Hierarchy
**Tasks:**
1. Create `automation/exceptions.py` with base `AirbaisAPIException`
2. Define domain exceptions: `ToolNotFoundError`, `ToolExecutionError`, `JobNotFoundError`, `ConfigurationError`
3. Add error_code and status_code attributes to each
4. Write unit tests for exception instantiation

**Why first:** Foundation for other plans, no dependencies

### Plan 04-02: Update Error Response Schema
**Tasks:**
1. Create `build_error_response()` helper in error_handlers.py
2. Add correlation_id to all error responses via `get_correlation_id()`
3. Add timestamp (UTC-aware) to all error responses
4. Add error_code field to structured responses
5. Update existing error handlers to use new schema
6. Write tests for error response format

**Why second:** Defines the contract before implementation changes

### Plan 04-03: Replace Bare Except and Add Specific Handlers
**Tasks:**
1. Replace bare except at line 203 with specific exceptions
2. Update config loading (line 43) to catch `yaml.YAMLError, IOError`
3. Update run_tool_async to raise custom exceptions instead of generic Exception
4. Add custom exception handlers to Flask app
5. Write tests for exception handling paths

**Why third:** Uses exceptions from 04-01 and schema from 04-02

### Plan 04-04: Fix Datetime Serialization to UTC
**Tasks:**
1. Import `timezone` from datetime module
2. Replace all `datetime.now()` with `datetime.now(timezone.utc)`
3. Verify `.isoformat()` produces RFC 3339 format with timezone
4. Create helper function `utc_now_iso()` for consistency
5. Write tests for datetime format in responses

**Why fourth:** Independent of exception changes, simple targeted fix

### Plan 04-05: Add Job ID Creation Validation (Optional Defensive)
**Tasks:**
1. Add UUID format assertion in `create_job()`
2. Log warning if format doesn't match expected pattern
3. Add test for job_id format validation
4. Document that this is defensive—real fix was Pydantic in Phase 2

**Why last:** Nice-to-have defensive programming, not fixing actual bug

## Sources

### Primary (HIGH confidence)

#### Exception Handling Best Practices
- [6 Best Practices for Python Exception Handling - Qodo.ai](https://www.qodo.ai/blog/6-best-practices-for-python-exception-handling/)
- [Python Custom Exceptions: How to Create and Organize Them - Jacob Padilla](https://jacobpadilla.com/articles/custom-python-exceptions)
- [PEP 760 – No More Bare Excepts](https://peps.python.org/pep-0760/)
- [Do not use bare except, specify exception instead (E722) - Flake8](https://www.flake8rules.com/rules/E722.html)
- [Avoiding the Pitfalls: Common Anti-patterns in Exception Handling in Python - Medium](https://medium.com/@jefmoura/avoiding-the-pitfalls-common-anti-patterns-in-exception-handling-in-python-12139e05b6)

#### Flask Error Responses
- [Flask Error Handling Patterns - Better Stack Community](https://betterstack.com/community/guides/scaling-python/flask-error-handling/)
- [Flask API Exception Handling with Custom HTTP Response Codes - Medium](https://medium.com/datasparq-technology/flask-api-exception-handling-with-custom-http-response-codes-c51a82a51a0f)
- [Error Handling - APIFlask](https://apiflask.com/error-handling/)

#### Datetime Serialization
- [Best Practices to Serialize Datetime in Python JSON - Machinet](https://www.machinet.net/tutorial-eng/best-practices-to-serialize-datetime-in-python-json)
- [5 Best Ways to Serialize and Deserialize Python Datetime to JSON - Finxter](https://blog.finxter.com/5-best-ways-to-serialize-and-deserialize-python-datetime-to-json/)
- [ISO 8601 vs RFC 3339: The JSON Date Format Standard Guide - ToolsHRef](https://toolshref.com/iso-8601-vs-rfc-3339-json-api-dates/)

#### Structlog Exception Logging
- [A Comprehensive Guide to Python Logging with Structlog - Better Stack](https://betterstack.com/community/guides/logging/structlog/)
- [Exceptions — structlog 25.5.0 documentation](https://www.structlog.org/en/stable/exceptions.html)
- [Logging Best Practices — structlog 25.5.0 documentation](https://www.structlog.org/en/stable/logging-best-practices.html)

#### UUID Validation
- [Flask-UUID · PyPI](https://pypi.org/project/Flask-UUID/)
- [Tips and Tricks - Flask URL Variables - TestDriven.io](https://testdriven.io/tips/24431240-a8bf-437d-82ba-72507d4fb5a0/)

### Secondary (MEDIUM confidence)

- Codebase analysis: `.planning/codebase/CONCERNS.md` - Documented job ID cleanup issue
- Git history: Commit 70b09a0 showing regex cleanup workaround at lines 282-288
- Phase 3 research: Structlog integration complete with exc_info support

## Metadata

**Confidence breakdown:**
- Exception hierarchy patterns: HIGH - Well-established Python best practices, PEP 760 official
- Structured error responses: HIGH - Industry standard for REST APIs, multiple authoritative sources
- Datetime serialization: HIGH - Python stdlib documentation, RFC 3339 standard
- Job ID issue root cause: HIGH - Code inspection + git history shows Pydantic already fixes it
- Bare except locations: HIGH - Direct code analysis via Grep tool

**Research date:** 2026-01-24
**Valid until:** 90 days (stable domain, standards-based)

**Key findings validated against:**
- Current codebase (`automation/` directory inspection)
- Git history (cleanup logic analysis)
- Python official documentation (datetime, exceptions)
- Industry standards (RFC 3339, REST API patterns)
- Phase 2 and Phase 3 implementation (Pydantic validation, structlog logging)
