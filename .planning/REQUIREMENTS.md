# Requirements: Airbais Tools Production Readiness

**Defined:** 2026-01-23
**Core Value:** Tools must be reliable, secure, and maintainable — errors are logged not silenced, inputs are validated, and the codebase is testable.

## v1 Requirements

### Interface Contract

- [x] **INTF-01**: Define JSON schema for dashboard-data.json with required `tool_type` field
- [x] **INTF-02**: Update all tools to include explicit `tool_type` in output
- [x] **INTF-03**: Replace heuristic tool detection in dashboard with schema validation
- [x] **INTF-04**: Add schema validation on dashboard data load

### Security

- [x] **SEC-01**: Add Pydantic validation for all API request parameters
- [x] **SEC-02**: Sanitize error messages before returning to API clients (no stack traces)
- [x] **SEC-03**: Configure CORS with explicit origin whitelist (default disabled)
- [x] **SEC-04**: Add Flask-Talisman security headers (HSTS, CSP, X-Frame-Options)
- [x] **SEC-05**: Validate subprocess command parameters with whitelist

### Error Handling

- [x] **ERR-01**: Replace bare exception handlers with specific exception types
- [x] **ERR-02**: Log all caught exceptions with context (file, line, operation)
- [x] **ERR-03**: Implement structured error response format for API
- [x] **ERR-04**: Fix job ID cleanup — investigate and fix root cause of trailing characters
- [x] **ERR-05**: Fix datetime serialization — explicit ISO-8601 conversion

### Logging

- [x] **LOG-01**: Implement structlog for structured JSON logging
- [x] **LOG-02**: Add correlation IDs to track requests across operations
- [x] **LOG-03**: Add request/response logging for API endpoints
- [x] **LOG-04**: Add audit logging for tool executions

### Testing

- [ ] **TEST-01**: Add characterization tests for dashboard.py before refactoring
- [ ] **TEST-02**: Add API endpoint tests (happy path and error cases)
- [ ] **TEST-03**: Add dashboard data loading tests (malformed JSON, missing files)
- [ ] **TEST-04**: Add schema validation tests for dashboard-data.json output
- [ ] **TEST-05**: Add tests for exception handling paths

### Refactoring

- [ ] **REF-01**: Extract dashboard utilities to dashboard/utils.py
- [ ] **REF-02**: Extract dashboard layout to dashboard/layout.py
- [ ] **REF-03**: Extract dashboard visualizations to dashboard/visualizations.py
- [ ] **REF-04**: Extract dashboard callbacks to dashboard/callbacks/
- [ ] **REF-05**: Break apart polished.py (670 lines) into scoring modules
- [ ] **REF-06**: Break apart output_generator.py (642 lines) into format modules
- [ ] **REF-07**: Break apart structured.py (640 lines) into metric modules
- [ ] **REF-08**: Break apart geoevaluator main.py (633 lines) into modules

### Infrastructure

- [ ] **INFRA-01**: Migrate job storage from in-memory dict to SQLite
- [ ] **INFRA-02**: Add rate limiting to API endpoints (Flask-Limiter)
- [ ] **INFRA-03**: Add health check endpoints (/health/live, /health/ready)
- [ ] **INFRA-04**: Pin dependency versions to specific minor versions

## v2 Requirements

Deferred to future release. Not in current roadmap.

### Performance
- **PERF-01**: Implement lazy loading for ML models (load on first use)
- **PERF-02**: Add pagination to dashboard data loading
- **PERF-03**: Add connection pooling to crawlers
- **PERF-04**: Implement concurrent crawling option

### Advanced Security
- **SEC-06**: API key authentication
- **SEC-07**: Request signing for webhooks

### Observability
- **OBS-01**: OpenTelemetry metrics collection
- **OBS-02**: Distributed tracing

## Out of Scope

| Feature | Reason |
|---------|--------|
| OAuth/JWT authentication | CORS + rate limiting sufficient for v1; adds complexity |
| Celery/RQ async framework | Thread pool executor sufficient for current scale |
| Redis for job storage | SQLite simpler, sufficient for single-instance |
| Horizontal scaling | Future milestone after v1 stability proven |
| Migration to hosted vector DB | Future milestone; ChromaDB sufficient for now |
| Mobile/responsive dashboard | Future milestone; focus on stability first |
| New tool development | Stability first, features later |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INTF-01 | Phase 1 | Complete |
| INTF-02 | Phase 1 | Complete |
| INTF-03 | Phase 1 | Complete |
| INTF-04 | Phase 1 | Complete |
| SEC-01 | Phase 2 | Complete |
| SEC-02 | Phase 2 | Complete |
| SEC-03 | Phase 2 | Complete |
| SEC-04 | Phase 2 | Complete |
| SEC-05 | Phase 2 | Complete |
| LOG-01 | Phase 3 | Complete |
| LOG-02 | Phase 3 | Complete |
| LOG-03 | Phase 3 | Complete |
| LOG-04 | Phase 3 | Complete |
| ERR-01 | Phase 4 | Complete |
| ERR-02 | Phase 4 | Complete |
| ERR-03 | Phase 4 | Complete |
| ERR-04 | Phase 4 | Complete |
| ERR-05 | Phase 4 | Complete |
| INFRA-02 | Phase 5 | Pending |
| INFRA-03 | Phase 5 | Pending |
| TEST-01 | Phase 6 | Pending |
| TEST-02 | Phase 6 | Pending |
| TEST-03 | Phase 6 | Pending |
| TEST-04 | Phase 6 | Pending |
| TEST-05 | Phase 6 | Pending |
| REF-01 | Phase 7 | Pending |
| REF-02 | Phase 7 | Pending |
| REF-03 | Phase 7 | Pending |
| REF-04 | Phase 7 | Pending |
| REF-05 | Phase 7 | Pending |
| REF-06 | Phase 7 | Pending |
| REF-07 | Phase 7 | Pending |
| REF-08 | Phase 7 | Pending |
| INFRA-01 | Phase 8 | Pending |
| INFRA-04 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-23*
*Last updated: 2026-01-24 after Phase 4 completion*
