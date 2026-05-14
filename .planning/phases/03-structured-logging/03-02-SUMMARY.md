---
phase: 03-structured-logging
plan: 02
subsystem: api
tags: [correlation-id, request-tracking, middleware, flask, structlog, testing]

# Dependency graph
requires:
  - phase: 03-structured-logging
    plan: 01
    provides: Structlog configuration module
provides:
  - Correlation ID middleware for Flask
  - Automatic UUID generation for untracked requests
  - X-Correlation-ID header preservation and response
  - Correlation ID binding to structlog context variables
  - HTTP metadata (method, path, remote_addr) in log context
affects: [03-03, 03-04, 03-05, api-development, observability, debugging]

# Tech tracking
tech-stack:
  added: []
  patterns: [correlation ID middleware, context binding, before_request/after_request hooks]

key-files:
  created:
    - automation/log_config/correlation.py
    - automation/tests/test_correlation.py
  modified:
    - automation/log_config/__init__.py
    - automation/api_server.py

key-decisions:
  - "Use X-Correlation-ID as standard header name for correlation tracking"
  - "Generate UUID v4 when correlation ID not provided by client"
  - "Bind correlation ID to structlog context vars for automatic inclusion in all logs"
  - "Position correlation middleware first to ensure ID available for all subsequent middleware"

patterns-established:
  - "Correlation middleware must be configured before other middleware"
  - "Use structlog.contextvars.bind_contextvars() for request-scoped context"
  - "Clear context vars at start of each request to prevent leakage"
  - "Store correlation ID in Flask g object for access outside structlog"

# Metrics
duration: 2min
completed: 2026-01-24
---

# Phase 03 Plan 02: Correlation ID Middleware Summary

**Flask middleware generating/preserving correlation IDs with automatic structlog context binding for request tracing**

## Performance

- **Duration:** 2 min 17 sec
- **Started:** 2026-01-24T15:28:04Z
- **Completed:** 2026-01-24T15:30:21Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Correlation ID middleware that generates UUIDs or preserves client-provided IDs
- All logs within a request automatically include correlation_id via structlog context vars
- Response headers include X-Correlation-ID matching request for end-to-end tracing
- Comprehensive test suite (6 tests) covering generation, preservation, and error scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Create correlation ID middleware** - `cad8ce2` (feat)
2. **Task 2: Integrate correlation middleware with API server** - `ddb06ba` (feat)
3. **Task 3: Create tests for correlation ID middleware** - `a105f20` (test)

## Files Created/Modified
- `automation/log_config/correlation.py` - Middleware with bind_correlation_id, add_correlation_header, configure_correlation
- `automation/log_config/__init__.py` - Exports configure_correlation and get_correlation_id
- `automation/api_server.py` - Imports and configures correlation middleware before other middleware
- `automation/tests/test_correlation.py` - 6 tests for ID generation, preservation, uniqueness, error handling

## Decisions Made

**1. X-Correlation-ID as standard header name**
- **Rationale:** Industry standard header name for distributed tracing, compatible with most logging aggregation systems
- **Impact:** Clients can send this header to track requests across multiple services

**2. UUID v4 for generated correlation IDs**
- **Rationale:** Universally unique, no central coordination needed, sufficient randomness for request tracking
- **Impact:** Generated IDs guaranteed unique without database lookups

**3. structlog.contextvars for context binding**
- **Rationale:** Thread-safe, automatic inclusion in all logs within request, works with async code
- **Impact:** No manual correlation ID passing - appears automatically in every log message

**4. Position as first middleware**
- **Rationale:** Ensures correlation ID available for error handlers, CORS, and all other middleware logging
- **Impact:** configure_correlation(app) must be called immediately after Flask app creation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for integration:**
- Plan 03-03 can now use correlation IDs in request/response logging
- Plan 03-04 can propagate correlation IDs to background job execution
- All future API logs will include correlation_id field

**Testing verified:**
- UUID generation works when no correlation ID provided
- Client-provided IDs preserved correctly
- Different requests get unique IDs
- Correlation IDs present on error responses (500, 404)
- Custom (non-UUID) correlation ID formats supported

**No blockers**

---
*Phase: 03-structured-logging*
*Completed: 2026-01-24*
