---
phase: 04-error-handling
plan: "02"
subsystem: automation-api
tags: [flask, error-handling, correlation, structured-responses]

requires:
  - phase: 04-01
    provides: "Custom exception hierarchy and UTC datetime utilities"
  - phase: 03-02
    provides: "Correlation ID middleware and get_correlation_id() function"

provides:
  - Structured error response builder with correlation_id and timestamp
  - Flask error handlers for custom exceptions
  - Consistent error response schema across all error types
  - Integration of correlation IDs into error responses

affects:
  - 04-03  # Error logging will use structured error responses
  - api_server.py  # Will use custom exceptions for error handling

tech-stack:
  added: []
  patterns:
    - "build_error_response() helper for consistent error schema"
    - "Error responses include correlation_id, timestamp, error_code"
    - "All error handlers use build_error_response() for consistency"
    - "Defensive fallback for correlation_id outside request context"

key-files:
  created: []
  modified:
    - path: automation/error_handlers.py
      provides: "Structured error response builder and Flask error handlers"
      exports: ["build_error_response", "handle_airbais_exception", "register_error_handlers"]

decisions:
  - id: correlation-id-fallback
    desc: "Use 'none' as fallback when get_correlation_id() returns empty string"
    rationale: "Ensures correlation_id field is always present in error responses, even outside request context"
    alternatives: "Omit field when empty - rejected for consistent schema"

  - id: error-code-inclusion
    desc: "Include error_code in all error responses for programmatic handling"
    rationale: "Clients can handle specific error types without parsing message strings"
    alternatives: "Only include for custom exceptions - rejected for inconsistency"

  - id: timestamp-in-body
    desc: "Include UTC timestamp in JSON response body, not just headers"
    rationale: "Clients can log exact error time without parsing headers"
    alternatives: "Use Date header only - rejected for convenience"

metrics:
  duration: "2m 30s"
  completed: 2026-01-24
---

# Phase 4 Plan 02: Structured Error Responses Summary

**One-liner:** Structured error response builder with correlation_id, timestamp, and error_code linking Phase 3 correlation tracking to error handling

## What Was Built

Enhanced error_handlers.py with structured error response schema:

1. **build_error_response() helper function:**
   - Constructs consistent JSON error responses
   - Includes correlation_id from Phase 3 middleware (with 'none' fallback)
   - Includes UTC timestamp via utc_now_iso() from Phase 4-01
   - Supports optional error_code and details fields
   - Returns tuple of (jsonify response, status_code)

2. **handle_airbais_exception() handler:**
   - Catches custom AirbaisAPIException subclasses
   - Logs with structured logging (error_code, status_code, full traceback)
   - Uses build_error_response() with exception attributes
   - Registered in Flask error handler chain

3. **Updated all existing handlers:**
   - handle_validation_error() - Uses build_error_response() with VALIDATION_ERROR code
   - handle_bad_request() - Uses build_error_response() with BAD_REQUEST code
   - handle_not_found() - Uses build_error_response() with NOT_FOUND code
   - handle_internal_error() - Uses build_error_response() with INTERNAL_ERROR code
   - handle_unexpected_exception() - Uses build_error_response() with UNEXPECTED_ERROR code

**Error Response Schema:**
```json
{
  "error": "Error type string",
  "message": "Human-readable message",
  "timestamp": "2026-01-24T19:50:02.123456+00:00",
  "correlation_id": "uuid-v4-or-none",
  "error_code": "MACHINE_READABLE_CODE",
  "details": {}  // Optional
}
```

## Tasks Completed

| Task | Name                             | Commit  | Files                      |
|------|----------------------------------|---------|----------------------------|
| 1    | Add build_error_response helper  | 0b0ade3 | automation/error_handlers.py |
| 2    | Add custom exception handler     | 1bed45b | automation/error_handlers.py |

## Deviations from Plan

None - plan executed exactly as written.

## Key Technical Decisions

### Correlation ID Fallback Strategy

**Decision:** Use `get_correlation_id() or 'none'` for defensive fallback.

**Rationale:**
- Outside Flask request context, get_correlation_id() returns empty string
- Empty string is falsy, so `or 'none'` provides meaningful fallback value
- Ensures correlation_id field always present in error responses
- Useful for testing and non-request error scenarios

**Implementation:**
```python
response = {
    'correlation_id': get_correlation_id() or 'none',
}
```

**Verified:** Test confirms 'none' value when outside request context.

### Error Code Standardization

**Decision:** Include error_code in ALL error responses, not just custom exceptions.

**Rationale:**
- Provides consistent programmatic error handling for clients
- Each error handler assigns appropriate code (VALIDATION_ERROR, BAD_REQUEST, etc.)
- Clients can switch on error_code instead of parsing message strings
- Future-proofs API for error categorization

**Example codes:**
- `VALIDATION_ERROR` - Pydantic validation failures
- `BAD_REQUEST` - Generic 400 errors
- `NOT_FOUND` - 404 resources
- `INTERNAL_ERROR` - 500 errors
- `UNEXPECTED_ERROR` - Unhandled exceptions
- `JOB_NOT_FOUND`, `TOOL_NOT_FOUND`, etc. - Custom exceptions

### Timestamp in Response Body

**Decision:** Include timestamp in JSON body, not relying solely on HTTP Date header.

**Rationale:**
- Convenience: Clients get structured timestamp without header parsing
- Logging: Error timestamp can be logged alongside error message
- RFC 3339: ISO format is universally parseable
- Consistency: All error metadata in single JSON object

**Implementation:**
```python
response = {
    'timestamp': utc_now_iso(),  # "2026-01-24T19:50:02.123456+00:00"
}
```

## Integration Points

### Phase 3 Correlation Tracking
- Imports `get_correlation_id()` from `log_config/correlation.py`
- Correlation ID automatically included in all error responses
- Links client errors to server logs via correlation_id field

### Phase 4-01 Exception Hierarchy
- Imports `AirbaisAPIException` from `exceptions.py`
- handle_airbais_exception() catches all custom exception subclasses
- Extracts error_code and status_code attributes for response

### Phase 4-01 UTC Utilities
- Imports `utc_now_iso()` from `utils.py`
- All error responses include RFC 3339 compliant timestamps
- Replaces need for naive datetime.now()

## Testing Verification

All components verified:

1. **build_error_response():**
   - Returns tuple of (jsonify response, status_code)
   - Includes correlation_id with 'none' fallback outside request context
   - Includes UTC timestamp in ISO 8601 format
   - Includes error_code when provided
   - Includes details when provided

2. **handle_airbais_exception():**
   - Catches JobNotFoundError correctly
   - Returns 404 status code
   - Includes JOB_NOT_FOUND error_code
   - Includes correlation_id and timestamp
   - Logs error with exc_info=True

3. **Updated handlers:**
   - handle_not_found() returns NOT_FOUND error_code
   - handle_bad_request() returns BAD_REQUEST error_code
   - All responses include correlation_id and timestamp

## Next Phase Readiness

**Ready for 04-03:** Error logging can now:
- Reference structured error response format
- Ensure consistency between logged errors and API responses
- Use correlation_id for tracing errors across logs

**Ready for api_server.py refactoring:**
- Custom exceptions can be raised instead of manual jsonify() calls
- Error handlers automatically convert to structured responses
- Correlation IDs automatically included without manual header extraction

**No blockers:** All error handlers updated and tested. Error response schema is consistent across all error types.

## Files Modified

**automation/error_handlers.py:**
- Added imports: `get_correlation_id`, `utc_now_iso`, `AirbaisAPIException`
- Created `build_error_response()` helper (39 lines)
- Created `handle_airbais_exception()` handler
- Updated 5 existing handlers to use build_error_response()
- Registered AirbaisAPIException handler in Flask app

**Net changes:** +102 lines (39 build_error_response, 30 handle_airbais_exception, 33 refactored handlers)

## Lessons Learned

**Defensive programming:** The `or 'none'` fallback for correlation_id ensures graceful handling of edge cases (testing, background jobs, non-request contexts).

**Consistency through helpers:** Refactoring all handlers to use build_error_response() ensures schema consistency and makes future changes easier (change one function, update all responses).

**Schema-first design:** Defining structured error response schema upfront (error, message, timestamp, correlation_id, error_code) provides clear contract for API clients and future error handlers.

---
*Phase: 04-error-handling*
*Plan: 02*
*Completed: 2026-01-24*
