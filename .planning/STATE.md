# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-23)

**Core value:** Tools must be reliable, secure, and maintainable — errors are logged not silenced, inputs are validated, and the codebase is testable.
**Current focus:** Phase 3 Complete - Ready for Phase 4

## Current Position

Phase: 4 of 8 (Error Handling) - COMPLETE
Plan: 4 of 4 complete (04-01, 04-02, 04-03, 04-04 complete)
Status: Phase 4 complete - Ready for Phase 5
Last activity: 2026-01-24 — Completed 04-04-PLAN.md (error handling testing)

Progress: [████░░░░░░] 50.0% (4 of 8 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 18
- Average duration: 3m 9s
- Total execution time: 0.96 hours

**By Phase:**

| Phase                     | Plans | Total   | Avg/Plan |
|---------------------------|-------|---------|----------|
| 01 - Interface Contracts  | 4     | 15m 11s | 3m 48s   |
| 02 - Security Hardening   | 5     | 15m 45s | 3m 9s    |
| 03 - Structured Logging   | 5     | 20m 13s | 4m 3s    |
| 04 - Error Handling       | 4     | 11m 59s | 3m 0s    |

**Recent Trend:**

- Last 5 plans: 04-01 (1m 9s), 04-02 (2m 30s), 04-03 (4m 34s), 04-04 (3m 46s)
- Trend: Phase 4 complete (11m 59s total), maintaining fast velocity

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Phase ordering: Interface contracts first to prevent dashboard breakage during refactoring
- Testing before refactoring: Comprehensive tests (Phase 6) must precede monolithic file splitting (Phase 7)
- SQLite over Redis: Simpler persistence sufficient for single-instance deployment
- Skip async framework: Thread pool executor adequate for current scale
- **[01-01]** JSON Schema approach: Use Draft 2020-12 with tool_type as string enum (simpler than discriminator)
- **[01-01]** Minimal required fields: Only tool_type and timestamp required for backwards-compatible migration
- **[01-01]** Schema flexibility: additionalProperties: true allows tool-specific fields without schema changes
- **[01-02]** tool_type field name: Use 'tool_type' for explicit identification (clearer than 'tool' which was used inconsistently)
- **[01-02]** Backwards compatibility: Keep existing 'tool' field where it exists to avoid breaking changes
- **[01-03]** Validation is observability: Schema validation logs errors but never prevents data loading
- **[01-03]** Three-tier detection: Check tool_type field, then legacy 'tool' field, then heuristics
- **[01-03]** Optional jsonschema dependency: Import with try/except for graceful degradation when missing
- **[01-04]** Pytest over unittest: Cleaner syntax, better fixtures, parametrized test support
- **[01-04]** Graceful test skipping: Integration tests skip if real data files unavailable (environment-agnostic)
- **[01-04]** Test organization: Separate classes for schema validation, loader unit tests, and integration tests
- **[02-01]** Pydantic v2 with Field() constraints: Type safety at API boundary with automatic 400 responses
- **[02-01]** Flask-Pydantic for body, manual for paths: @validate() decorator for body, try/except for path parameters
- **[02-01]** URL validation strictness: Require http/https prefix to reject file:// and relative paths
- **[02-01]** extra='forbid' over extra='ignore': Fail fast on unknown fields to catch typos immediately
- **[02-01]** Constraint bounds rationale: max_pages≤1000, crawl_depth≤10, timeout≤3600s for resource protection
- **[02-04]** Script whitelist from tools_config.yaml: Only known tools execute, preventing command injection
- **[02-04]** Path.resolve() for canonicalization: Follows symlinks to detect path traversal attempts
- **[02-04]** shell=False enforcement: All subprocess calls use list arguments to prevent shell injection
- **[02-04]** Flag whitelist validation: Only documented tool parameters accepted
- **[02-05]** Restrictive CSP for API (default-src: none): API serves JSON, no scripts/styles needed
- **[02-05]** TALISMAN_FORCE_HTTPS env var for proxy setups: Allow HTTPS termination at reverse proxy layer
- **[02-05]** Separate Talisman config for API vs Dashboard: Dash requires inline scripts, API doesn't - different CSP needs
- **[03-01]** Module naming to avoid stdlib shadowing: Use log_config instead of logging to prevent import conflicts
- **[03-01]** Environment detection via sys.stderr.isatty(): Automatic JSON in production, console in development
- **[03-01]** configure_structlog() called at startup: Must configure before any logging occurs
- **[03-02]** X-Correlation-ID standard header: Industry standard for distributed tracing across services
- **[03-02]** UUID v4 for correlation IDs: Universally unique without central coordination
- **[03-02]** structlog.contextvars for binding: Thread-safe automatic inclusion in all logs within request
- **[03-02]** Correlation middleware positioned first: Ensures ID available for all error handlers and middleware
- **[03-03]** Flask hooks for request logging: before_request/after_request simpler than WSGI middleware
- **[03-03]** g.request_start_time for timing: Request-scoped storage for duration calculation
- **[03-03]** SENSITIVE_FIELDS set for redaction: Case-insensitive allowlist catches password/token/api_key variations
- **[03-03]** Recursive redaction: redact_sensitive() handles nested dictionaries in complex request bodies
- **[03-04]** Job context binding: structlog.contextvars.bind_contextvars() for automatic job_id/tool_name inclusion
- **[03-04]** CORRELATION_ID via environment: Pass to subprocesses via env['CORRELATION_ID'] (standard pattern)
- **[03-04]** Event-based logging: Use event name as first param (tool_execution_started, tool_execution_completed)
- **[03-04]** Command logging safety: Log command name and arg count only, not full command string
- **[03-05]** caplog.records for pytest capture: structlog via stdlib logging integration bypasses capsys
- **[04-01]** Exception hierarchy with error codes: Base AirbaisAPIException with error_code and status_code attributes
- **[04-01]** UTC-aware datetime utilities: utc_now_iso() returns RFC 3339 formatted timestamps
- **[04-01]** Semantic exception types: Specific exceptions for each error scenario (ToolNotFound, JobNotFound, etc.)
- **[04-02]** Correlation ID fallback: Use 'none' when get_correlation_id() returns empty string (outside request context)
- **[04-02]** Error code inclusion: All error responses include error_code field for programmatic handling
- **[04-02]** Timestamp in response body: Include UTC timestamp in JSON body for client convenience
- **[04-04]** conftest.py for test env vars: Set TALISMAN_FORCE_HTTPS=false before module imports to fix test environment
- **[04-04]** Integration tests verify end-to-end: HTTP requests test actual error handler registration and response structure
- **[04-04]** RFC 3339 timestamp validation: Parse with datetime.fromisoformat() not string matching for correctness

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1 considerations:**

- ~~Dashboard-data.json schema must be permissive initially to validate existing tool outputs~~ ✓ Done (01-01)
- ~~Tool detection heuristics require documentation before replacement with explicit tool_type field~~ ✓ Done (01-02 - tool_type now explicit)
- ~~Integration tests needed to enforce interface contract~~ ✓ Done (01-04 - 23 tests covering validation and loading)

**Phase 1 COMPLETE** - Interface contracts established and tested. Verified 2026-01-23.

**Phase 2 considerations:**

- ~~Pydantic models need to cover all API endpoints in automation/api_server.py~~ ✓ Done (02-01 - AnalyzeRequest + JobIdPath)
- ~~Subprocess whitelist must cover all tool invocations in tools_config.yaml~~ ✓ Done (02-04 - ALLOWED_SCRIPTS + path validation)
- ~~Flask-Talisman CSP may need adjustment for Dash components (inline scripts)~~ ✓ Done (02-05 - separate configs for API vs Dashboard)

**Phase 2 COMPLETE** - Security hardening established (validation, error handling, CORS, subprocess validation, security headers). Verified 2026-01-23.

**Phase 3 considerations:**

- ~~structlog recommended for JSON logging (from research)~~ ✓ Done (03-01 - configured with JSON/console rendering)
- ~~Correlation IDs need to propagate through subprocess calls~~ ✓ Done (03-02 - middleware generates/preserves correlation IDs)
- ~~API request/response logging should exclude sensitive data~~ ✓ Done (03-03 - request_logger with redaction)
- ~~Tool execution logging needs job_id tracking~~ ✓ Done (03-04 - run_tool_async with structured logging and correlation)
- ~~All existing loggers migrated to structlog~~ ✓ Done (03-05 - error_handlers, security modules migrated)

**Phase 3 COMPLETE** - Structured logging infrastructure established. Verified 2026-01-24.

**Phase 4 considerations:**

- ~~Exception hierarchy ready for Flask error handlers (04-02)~~ ✓ Done (04-02 - handle_airbais_exception registered)
- ~~Structured error response schema with correlation_id and timestamp~~ ✓ Done (04-02 - build_error_response)
- ~~UTC datetime utilities ready to replace naive datetime.now() calls (04-03)~~ ✓ Done (04-03 - utc_now_iso() throughout api_server.py)
- ~~Bare except blocks replaced with specific exception types~~ ✓ Done (04-03 - no bare except blocks remain)
- ~~All logger.error calls include exc_info=True in except blocks~~ ✓ Done (04-03 - full traceback context)
- ~~Comprehensive test coverage for exceptions and error responses~~ ✓ Done (04-04 - 57 tests covering all exception classes and error responses)

**Phase 4 COMPLETE** - Error handling infrastructure established and tested. Verified 2026-01-24.

**Phase 7 considerations:**

- Dashboard callback interdependencies may reveal coupling not visible in static analysis
- Metric evaluator domain logic (grammar checking, semantic HTML) may have refactoring constraints

**Phase 8 considerations:**

- SQLite performance baseline needed to establish migration success criteria
- Job retention policy (30/60/90 days) affects storage and query performance

## Session Continuity

Last session: 2026-01-24 20:03:55 UTC
Stopped at: Completed 04-04-PLAN.md - Error handling testing (exception tests, error response tests, conftest.py)
Resume file: None
