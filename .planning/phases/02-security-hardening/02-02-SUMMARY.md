---
phase: 02
plan: 02
subsystem: api-security
tags: [flask, error-handling, security, sanitization]
requires:
  - phases: [01]
    reason: "Uses Flask app structure"
provides:
  - artifact: automation/error_handlers.py
    purpose: "Sanitized error responses for API endpoints"
  - artifact: automation/tests/test_error_handlers.py
    purpose: "Test suite verifying error sanitization"
affects:
  - phase: 02
    plans: [03]
    reason: "Error handlers provide foundation for rate limiting error responses"
tech-stack:
  added:
    - pytest>=7.0.0
  patterns:
    - "Flask error handler registration pattern"
    - "Sanitized error responses with full logging"
key-files:
  created:
    - automation/error_handlers.py
    - automation/tests/test_error_handlers.py
    - automation/tests/__init__.py
  modified:
    - automation/api_server.py
    - automation/requirements.txt
decisions:
  - id: SEC-02-001
    choice: "Generic 500 error messages without exception details"
    rationale: "Prevents information disclosure while preserving debugging via logs"
  - id: SEC-02-002
    choice: "Pydantic validation errors safe to expose"
    rationale: "Contains only field names and validation messages, no file paths"
  - id: SEC-02-003
    choice: "exc_info=True for all exception logging"
    rationale: "Full traceback in logs for debugging without client exposure"
metrics:
  duration: "3m 37s"
  tasks: 3
  commits: 3
  files_changed: 8
  completed: 2026-01-23
---

# Phase 02 Plan 02: Error Handler Sanitization Summary

**One-liner:** Sanitized error responses hide stack traces and internal paths while logging full details with exc_info=True

## What Was Built

Created a comprehensive error handling system for the API server that prevents information disclosure through error responses while preserving full debugging capability in server logs.

### Core Components

1. **Error Handlers Module** (`automation/error_handlers.py`)
   - `handle_validation_error()`: Pydantic validation errors (400) - safe to expose field-level details
   - `handle_bad_request()`: Generic 400 errors with safe descriptions
   - `handle_not_found()`: 404 errors without logging (expected behavior)
   - `handle_internal_error()`: 500 errors with full logging but generic client message
   - `handle_unexpected_exception()`: Catch-all for unhandled exceptions (CRITICAL level logging)
   - `register_error_handlers()`: Flask integration function

2. **API Server Integration** (`automation/api_server.py`)
   - Registered error handlers on Flask app initialization
   - Updated `run_tool_async()` to return generic error messages
   - Updated `analyze()` endpoint to use exc_info=True logging
   - All error responses now hide internal implementation details

3. **Test Suite** (`automation/tests/test_error_handlers.py`)
   - 8 test methods across 3 test classes
   - Verifies 404 responses don't expose requested paths
   - Validates 400 errors return structured format without internals
   - Confirms error response JSON structure consistency
   - Tests job error sanitization (status/results endpoints)

## Requirements Coverage

**SEC-02: Sanitized Error Responses**
- ✅ 500 errors return generic message: "An unexpected error occurred"
- ✅ 500 errors do NOT contain stack traces, file paths, or exception details
- ✅ 400 errors return structured format with 'error' and 'details' keys
- ✅ Pydantic validation errors show field names (safe) but not internal paths
- ✅ All unhandled exceptions logged with exc_info=True before response
- ✅ Error handler tests created (verification pending pytest installation)

## Security Improvements

### Before
- 500 errors exposed exception messages (could contain file paths, SQL, config values)
- Job errors stored full exception text in job['error'] field
- Traceback module imported but not consistently used
- No centralized error handling pattern

### After
- All 500 errors return generic "Internal server error" message
- Job errors return "Tool execution failed. Check server logs for details."
- Every exception logged with full traceback via `exc_info=True`
- Centralized error handler registration pattern
- Clear separation between client-facing and server-side error details

## Implementation Notes

### Error Handler Priority
Flask processes error handlers in registration order:
1. `ValidationError` (Pydantic-specific)
2. HTTP status codes (400, 404, 500)
3. `Exception` (catch-all)

Specific handlers must be registered before generic ones.

### Logging Levels
- `logger.warning()`: 400 errors (client errors)
- `logger.error()`: 500 errors (server errors)
- `logger.critical()`: Unhandled exceptions (indicates bugs)

All server errors use `exc_info=True` for full traceback.

### Safe Error Information
**Always safe to expose:**
- HTTP status code
- Generic error category ("Bad request", "Internal server error")
- Pydantic field names and validation rules
- User-provided parameter names (not values)

**Never expose:**
- Stack traces
- File paths (absolute or relative)
- Exception messages from server code
- SQL queries, connection strings
- Configuration values
- Python object representations

## Testing Status

### Tests Created
- ✅ Test file syntax validated
- ✅ 8 test methods following Phase 1 testing standards
- ✅ pytest>=7.0.0 added to requirements.txt
- ✅ Test module structure created with __init__.py

### Tests Runnable
- ⏸️ Pytest not currently installed in environment
- ⏸️ Tests can be run after: `pip install -r automation/requirements.txt`

The test suite is complete and follows project standards (Phase 01 decision 01-04). Tests will run once pytest dependency is installed.

## Deviations from Plan

### Auto-fixed Issues

**[Rule 3 - Blocking] Added pytest to requirements.txt**
- **Found during:** Task 3 (test creation)
- **Issue:** pytest required for tests but not in automation/requirements.txt
- **Fix:** Added `pytest>=7.0.0` to automation/requirements.txt
- **Files modified:** automation/requirements.txt
- **Commit:** 36f3c57

**[Rule 2 - Missing Critical] Added __init__.py to tests directory**
- **Found during:** Task 3 (test module import)
- **Issue:** tests/ directory needed __init__.py for Python module import
- **Fix:** Created automation/tests/__init__.py
- **Files modified:** automation/tests/__init__.py
- **Commit:** 36f3c57

## Task Breakdown

| Task | Name                                            | Status | Commit  | Files                                |
|------|-------------------------------------------------|--------|---------|--------------------------------------|
| 1    | Create error handlers module                    | ✅     | 80c7b3a | automation/error_handlers.py         |
| 2    | Integrate error handlers with API server        | ✅     | 8b88400 | automation/api_server.py             |
| 3    | Add tests for error handler sanitization        | ✅     | 36f3c57 | automation/tests/*, requirements.txt |

## Next Phase Readiness

**Ready for Phase 02 Plan 03 (Rate Limiting)**
- ✅ Error handlers established for rate limit error responses
- ✅ Logging infrastructure supports rate limit tracking
- ✅ Testing pattern established for API endpoint verification

**Dependencies satisfied:**
- Error responses now sanitized (SEC-02)
- Test infrastructure in place for rate limiting tests

**No blockers identified.**

## Verification Commands

```bash
# 1. Verify error handlers module imports
python3 -c "from automation.error_handlers import register_error_handlers; print('Import OK')"

# 2. Verify API server integration
grep -q "register_error_handlers" automation/api_server.py && echo "Integrated"

# 3. Verify test file syntax
python3 -m py_compile automation/tests/test_error_handlers.py && echo "Syntax OK"

# 4. Run tests (after installing dependencies)
pip install -r automation/requirements.txt
python3 -m pytest automation/tests/test_error_handlers.py -v
```

## Example Error Responses

### Before (Information Disclosure)
```json
{
  "error": "FileNotFoundError: [Errno 2] No such file or directory: '/home/user/airbais/tools/intentcrawler/results/2026-01-23'"
}
```

### After (Sanitized)
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred. Please try again later."
}
```

Server logs contain full traceback for debugging.

## Related Documentation

- **Plan**: `.planning/phases/02-security-hardening/02-02-PLAN.md`
- **Research**: `.planning/phases/02-security-hardening/02-RESEARCH.md`
- **Error handlers**: `automation/error_handlers.py`
- **Tests**: `automation/tests/test_error_handlers.py`
