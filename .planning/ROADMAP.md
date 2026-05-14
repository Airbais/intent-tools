# Roadmap: Airbais Tools Production Readiness

## Overview

This roadmap transforms the Airbais Tools suite from operational to production-ready through eight incremental phases. Starting with interface contracts to protect dashboard integration, the journey layers security hardening, structured observability, robust error handling, comprehensive testing, careful refactoring of monolithic files, persistent storage migration, and infrastructure improvements. Each phase delivers independently deployable capabilities while maintaining backwards compatibility and existing functionality.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Interface Contracts** - Establish dashboard-data.json schema and validation framework
- [x] **Phase 2: Security Hardening** - Add input validation, CORS, security headers, subprocess protection
- [x] **Phase 3: Structured Logging** - Implement JSON logging with correlation IDs and audit trails
- [x] **Phase 4: Error Handling** - Replace bare exceptions with specific types and proper logging
- [ ] **Phase 5: API Hardening** - Add rate limiting and health check endpoints
- [ ] **Phase 6: Testing Infrastructure** - Build comprehensive test suite before refactoring
- [ ] **Phase 7: Refactoring** - Break apart monolithic files into maintainable modules
- [ ] **Phase 8: Infrastructure** - Migrate to persistent storage and finalize deployment config

## Phase Details

### Phase 1: Interface Contracts
**Goal**: Protect dashboard integration with explicit schema validation preventing breaking changes during all subsequent refactoring
**Depends on**: Nothing (first phase)
**Requirements**: INTF-01, INTF-02, INTF-03, INTF-04
**Success Criteria** (what must be TRUE):
  1. Dashboard-data.json schema defined with required tool_type field and versioning
  2. All 6+ tools include explicit tool_type field; validation enforced on dashboard load
  3. Dashboard loads tool results using explicit tool_type lookup, not heuristics
  4. Integration tests verify dashboard can load dashboard-data.json from each tool
  5. Schema violations logged with clear error messages identifying invalid fields
**Plans**: 4 plans (completed 2026-01-23)

Plans:
- [x] 01-01-PLAN.md — Define JSON Schema and create validator module
- [x] 01-02-PLAN.md — Add tool_type field to all 6 tool output generators
- [x] 01-03-PLAN.md — Update dashboard data_loader with schema-based detection
- [x] 01-04-PLAN.md — Create integration tests for dashboard loading

### Phase 2: Security Hardening
**Goal**: Close critical security gaps with validated inputs, CORS whitelist, security headers, and subprocess protection
**Depends on**: Phase 1 (schema validation established)
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05
**Success Criteria** (what must be TRUE):
  1. API request parameters validated with Pydantic models rejecting malformed input
  2. API error responses sanitized to prevent stack trace leakage to clients
  3. CORS configured with explicit origin whitelist, wildcard disabled by default
  4. Security headers (HSTS, CSP, X-Frame-Options) applied via Flask-Talisman
  5. Subprocess commands validated against whitelist with path canonicalization
**Plans**: 5 plans in 3 waves

Plans:
- [x] 02-01-PLAN.md — Create Pydantic request validation models (Wave 1)
- [x] 02-02-PLAN.md — Create sanitized error handlers (Wave 1)
- [x] 02-03-PLAN.md — Configure CORS with explicit origin whitelist (Wave 1)
- [x] 02-04-PLAN.md — Implement subprocess command whitelist validation (Wave 2)
- [x] 02-05-PLAN.md — Add Flask-Talisman security headers (Wave 3)

### Phase 3: Structured Logging
**Goal**: Enable operational visibility with structured JSON logs, correlation tracking, and audit trails
**Depends on**: Phase 2 (error sanitization provides baseline for log content)
**Requirements**: LOG-01, LOG-02, LOG-03, LOG-04
**Success Criteria** (what must be TRUE):
  1. All log messages output as structured JSON with timestamp, level, context
  2. Every API request tagged with correlation ID propagating through entire operation
  3. API endpoints log request method, path, status code, duration automatically
  4. Tool executions logged with job_id, tool_name, parameters, start/end times
  5. Logs machine-parseable for ELK/CloudWatch ingestion without custom parsing
**Plans**: 5 plans in 3 waves

**Plans**: 5 plans (completed 2026-01-24)

- [x] 03-01-PLAN.md — Configure structlog and create logging module (Wave 1)
- [x] 03-02-PLAN.md — Implement correlation ID middleware (Wave 2)
- [x] 03-03-PLAN.md — Add request/response logging middleware (Wave 2)
- [x] 03-04-PLAN.md — Update tool execution logging (Wave 2)
- [x] 03-05-PLAN.md — Migrate existing loggers to structlog (Wave 3)

### Phase 4: Error Handling
**Goal**: Replace fragile bare exceptions with specific types and comprehensive logging
**Depends on**: Phase 3 (logging infrastructure captures exceptions before replacement)
**Requirements**: ERR-01, ERR-02, ERR-03, ERR-04, ERR-05
**Success Criteria** (what must be TRUE):
  1. No bare except blocks remain in API or tool codebases
  2. All caught exceptions logged with context (file, line, operation details)
  3. API errors returned in structured format with error_code, message, request_id
  4. Job IDs validated on creation to prevent trailing special character bugs
  5. Datetime objects serialized to ISO-8601 format consistently across all outputs
**Plans**: 4 plans (completed 2026-01-24)

Plans:
- [x] 04-01-PLAN.md — Create custom exception hierarchy and UTC datetime utility (Wave 1)
- [x] 04-02-PLAN.md — Update error handlers with structured response schema (Wave 2)
- [x] 04-03-PLAN.md — Replace bare except blocks and integrate custom exceptions (Wave 3)
- [x] 04-04-PLAN.md — Create tests for exceptions and error responses (Wave 4)

### Phase 5: API Hardening
**Goal**: Protect API with rate limiting and provide health checks for deployment infrastructure
**Depends on**: Phase 4 (error handling ensures graceful rate limit failures)
**Requirements**: INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. API endpoints rate-limited per IP with configurable limits per endpoint
  2. Rate limit violations return 429 status with Retry-After header
  3. /health/live endpoint returns 200 when server process is running
  4. /health/ready endpoint returns 200 when server can accept requests
  5. Rate limit exemptions configured for testing and internal automation
**Plans**: 3 plans in 3 waves

Plans:
- [ ] 05-01-PLAN.md — Install Flask-Limiter and create rate limiting module with 429 handler (Wave 1)
- [ ] 05-02-PLAN.md — Apply rate limit decorators and implement health check endpoints (Wave 2)
- [ ] 05-03-PLAN.md — Create tests for rate limiting and health checks (Wave 3)

### Phase 6: Testing Infrastructure
**Goal**: Build comprehensive test safety net before refactoring monolithic files
**Depends on**: Phase 5 (all production behaviors established for testing)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. Characterization tests capture dashboard.py behavior before refactoring starts
  2. API endpoint tests verify happy path and error cases for all routes
  3. Dashboard data loading tests handle malformed JSON, missing files, schema violations
  4. Schema validation tests verify all tools produce valid dashboard-data.json
  5. Exception handling tests verify errors logged correctly on all failure paths
**Plans**: TBD

Plans:
- [ ] TBD during planning phase

### Phase 7: Refactoring
**Goal**: Transform monolithic files into maintainable modules without breaking functionality
**Depends on**: Phase 6 (test safety net prevents regressions)
**Requirements**: REF-01, REF-02, REF-03, REF-04, REF-05, REF-06, REF-07, REF-08
**Success Criteria** (what must be TRUE):
  1. Dashboard.py (2002 lines) split into utils, layout, visualizations, callbacks modules
  2. Polished.py (670 lines) extracted into focused scoring component modules
  3. Output_generator.py (642 lines) split into format-specific generator modules
  4. Structured.py (640 lines) decomposed into individual metric checker modules
  5. Geoevaluator main.py (633 lines) separated into crawler, analyzer, reporter modules
  6. All existing tests pass after each file refactoring without modification
  7. No file exceeds 500 lines after refactoring complete
  8. Import paths maintain backwards compatibility via __init__.py exports
**Plans**: TBD

Plans:
- [ ] TBD during planning phase

### Phase 8: Infrastructure
**Goal**: Enable persistent job storage and finalize production deployment configuration
**Depends on**: Phase 7 (simplified codebase easier to migrate to persistent storage)
**Requirements**: INFRA-01, INFRA-04
**Success Criteria** (what must be TRUE):
  1. Job storage migrated from in-memory dict to SQLite with ACID guarantees
  2. Jobs persist across API server restarts with queryable history
  3. SQLite WAL mode enabled with proper transaction context managers
  4. Dependency versions pinned to specific minor versions in requirements.txt
  5. Job cleanup policy removes completed jobs older than retention period
**Plans**: TBD

Plans:
- [ ] TBD during planning phase

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Interface Contracts | 4/4 | Complete | 2026-01-23 |
| 2. Security Hardening | 5/5 | Complete | 2026-01-23 |
| 3. Structured Logging | 5/5 | Complete | 2026-01-24 |
| 4. Error Handling | 4/4 | Complete | 2026-01-24 |
| 5. API Hardening | 0/3 | Not started | - |
| 6. Testing Infrastructure | 0/TBD | Not started | - |
| 7. Refactoring | 0/TBD | Not started | - |
| 8. Infrastructure | 0/TBD | Not started | - |
