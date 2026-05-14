---
phase: 03-structured-logging
plan: 03
subsystem: api
tags: [structlog, flask, middleware, logging, request-response, redaction]

# Dependency graph
requires:
  - phase: 03-01
    provides: structlog configuration with JSON/console rendering
  - phase: 03-02
    provides: Correlation ID middleware for request tracking
provides:
  - Request/response logging middleware with automatic timing
  - Sensitive data redaction for passwords, tokens, API keys
  - Integration with Flask before_request and after_request hooks
affects: [03-04, 03-05, phase-04, phase-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Request/response middleware pattern using Flask hooks
    - Sensitive field redaction via allowlist approach
    - Structured logging with method, path, status_code, duration_ms

key-files:
  created:
    - automation/log_config/request_logger.py
    - automation/tests/test_request_logger.py
  modified:
    - automation/log_config/__init__.py
    - automation/api_server.py

key-decisions:
  - "Use Flask before_request/after_request hooks for automatic logging"
  - "Store start time in g.request_start_time for duration calculation"
  - "Redact sensitive fields via SENSITIVE_FIELDS set (case-insensitive)"
  - "Log to structlog (not stdlib logging) for consistency with 03-01"
  - "Use capsys instead of caplog in tests due to structlog stdout output"

patterns-established:
  - "Middleware configuration: configure_request_logging(app) after configure_correlation"
  - "Sensitive data redaction: redact_sensitive(dict) recursively processes nested dicts"
  - "Request timing: time.time() in before_request, calculate duration in after_request"

# Metrics
duration: 2m 52s
completed: 2026-01-24
---

# Phase 03 Plan 03: Request/Response Logging Summary

**Automatic API request/response logging with method, path, status codes, timing, and sensitive field redaction using structlog**

## Performance

- **Duration:** 2 min 52 sec
- **Started:** 2026-01-24T15:28:06Z
- **Completed:** 2026-01-24T15:30:58Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Created request_logger.py middleware with structlog-based logging
- Integrated middleware into API server after correlation middleware
- Implemented sensitive data redaction for passwords, tokens, API keys, etc.
- Added comprehensive tests (13 tests) for redaction and integration
- All API requests now logged with method, path, endpoint, content_type at start
- All API responses logged with status_code, duration_ms at completion

## Task Commits

Each task was committed atomically:

1. **Task 1: Create request/response logging middleware** - `c2962c7` (feat)
2. **Task 2: Integrate request logging with API server** - `b411fac` (feat)
3. **Task 3: Create tests for request logging** - `bad722d` (test)

## Files Created/Modified

- `automation/log_config/request_logger.py` - Request/response middleware with timing and redaction
- `automation/log_config/__init__.py` - Exports configure_request_logging and redact_sensitive
- `automation/api_server.py` - Calls configure_request_logging(app) after correlation middleware
- `automation/tests/test_request_logger.py` - 13 tests for redaction and integration

## Decisions Made

1. **Flask hooks for middleware**: Used before_request and after_request hooks instead of custom WSGI middleware for simplicity and Flask integration
2. **g.request_start_time for timing**: Store start time in Flask's g object (request-scoped) to calculate duration in after_request
3. **SENSITIVE_FIELDS set**: Case-insensitive allowlist approach catches password, token, api_key variations
4. **Recursive redaction**: redact_sensitive() handles nested dictionaries for complex request bodies
5. **capsys in tests**: Use pytest's capsys instead of caplog because structlog outputs to stdout (not stdlib logging)

## Deviations from Plan

None - plan executed exactly as written.

Note: Plan mentioned that 03-02 would integrate configure_correlation() into api_server.py. This was already complete when execution began, so Task 2 only needed to add configure_request_logging() after it.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Request/response logging middleware complete and tested
- Ready for 03-04 (job runner logging) to add job_id tracking to tool execution
- Ready for 03-05 (log aggregation) to collect logs from multiple sources
- All API requests now automatically logged with timing and sensitive data redaction
- Middleware order established: correlation → request_logging → error_handlers → CORS → Talisman

---
*Phase: 03-structured-logging*
*Completed: 2026-01-24*
