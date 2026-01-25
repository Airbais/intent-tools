# Project Research Summary

**Project:** Airbais Tools Production Hardening
**Domain:** Python Flask REST API & Dash Dashboard Production Readiness
**Researched:** 2026-01-23
**Confidence:** HIGH

## Executive Summary

Production hardening for the Airbais Tools suite requires a defense-in-depth approach focused on preventing catastrophic failures before optimizing for operational excellence. The system is a Flask REST API (automation server) plus Dash dashboard consuming outputs from 6+ independent analysis tools. The critical architectural constraint is the dashboard-data.json contract: any schema changes break the unified dashboard's ability to load tool results.

The recommended approach follows a 7-phase incremental strategy: establish interface contracts first (preventing dashboard breakage), then layer security hardening (input validation, rate limiting, CORS), exception handling improvements, comprehensive testing infrastructure, careful monolithic file refactoring, persistent storage migration, and finally production deployment with Gunicorn/nginx. The 2026 technology landscape favors standardization (Pydantic for validation, structlog for logging, pytest for testing) and pragmatic simplicity (SQLite over Redis for job storage until proven bottleneck).

Key risk mitigation: all tools must validate dashboard-data.json output against a shared schema before any refactoring begins. The codebase has 5 monolithic files (600-2000 lines) requiring incremental extraction using characterization tests, not big-bang rewrites. Security gaps (bare exceptions, subprocess injection vectors, CORS wildcards) must be addressed systematically with logging-first approaches that preserve existing behavior while adding visibility.

## Key Findings

### Recommended Stack

The production stack emphasizes security-first libraries actively maintained in 2026, with clear migration paths from the minimal current setup (Flask 3.0.0, flask-cors 4.0.0, werkzeug 3.0.1, pyyaml 6.0.1). All recommended technologies have verified version numbers and are proven in production Python systems.

**Core technologies:**

- **Pydantic 2.12.5**: Request/response validation with type-based schema enforcement — Superior performance over Marshmallow, native Python typing integration, industry standard for modern APIs, prevents most input-related bugs
- **Flask-Talisman 1.1.0**: Security headers and HTTPS enforcement — Google-maintained, implements OWASP best practices (HSTS, CSP, X-Frame-Options) with minimal configuration
- **Flask-Limiter 4.1.1**: Rate limiting with pluggable backends — De facto standard with 1.7M+ weekly downloads, supports both in-memory (for <100 jobs/sec) and Redis (for high-throughput) backends
- **structlog 25.5.0**: Structured JSON logging — Production-proven since 2013, machine-parseable logs for ELK/CloudWatch, essential for debugging distributed requests with correlation IDs
- **pytest 8.x + pytest-flask 1.3.0**: Testing framework — Industry standard with Flask-specific fixtures, Flask 3.0 compatible, comprehensive plugin ecosystem
- **SQLite 3.x**: Job queue persistence — Zero-config ACID guarantees, disk-backed durability, sufficient for <100 jobs/sec without infrastructure overhead (prefer over Redis until benchmarks prove otherwise)
- **Gunicorn 23.0.0**: Production WSGI server — Battle-tested pre-fork model, released Jan 23 2026, never run Flask dev server in production
- **python-dotenv 1.2.1**: Environment configuration — 12-factor app pattern, never commit secrets to git

**Critical version requirements:**
- All libraries support Python 3.10+ (recommend 3.11 or 3.12 for production)
- Gunicorn 23.0.0 released January 2026 with Python 3.13 support
- Pydantic 2.x has breaking changes from 1.x (type-first API redesign)
- Use dash[testing] not pytest-dash (unmaintained since 2019)

### Expected Features

Production APIs fail not from missing advanced features but from basic gaps: unvalidated inputs, bare exceptions, missing audit trails. The 2026 landscape emphasizes standardization over innovation.

**Must have (table stakes):**

- **Input validation (Pydantic)** — Prevents injection attacks, type errors, malformed data crashes; users expect APIs to reject bad input
- **Structured logging (JSON)** — Required for log aggregation, correlation, debugging; users expect query-able logs
- **Health/readiness endpoints** — Kubernetes and load balancers require /health/live and /health/ready for proper routing
- **Rate limiting** — Prevents abuse, DoS, runaway costs; users expect protection from automated tools
- **Proper error handling** — Specific exceptions with logging prevent silent failures; users expect graceful degradation
- **Request/response logging** — Audit trail for debugging and compliance; users expect visibility
- **Sanitized error messages** — Stack traces expose attack surface; users expect generic "Internal server error" not implementation details
- **CORS configuration** — Required for browser clients; users expect explicit origin whitelist not wildcards
- **Gunicorn production server** — Flask dev server is single-threaded and insecure; users expect production-grade WSGI
- **Dependency pinning** — Unpinned dependencies cause non-deterministic builds; users expect repeatable installations

**Should have (competitive):**

- **Correlation IDs** — Trace single request across logs, services, async jobs; differentiates professional APIs from basic implementations
- **Audit logging** — Compliance (GDPR, HIPAA), security investigations; required for regulated industries
- **Graceful degradation (circuit breakers)** — Service stays partially functional when dependencies fail; prevents cascading failures
- **OpenTelemetry metrics** — Standardized observability (Prometheus, Grafana, Datadog); vendor-neutral export for future flexibility
- **Job persistence (SQLite)** — In-memory storage lost on restart; enables recovery, history tracking, "resume failed job"
- **Async job status updates** — Long-running jobs need progress tracking; improves UX for multi-minute operations
- **Input sanitization** — Beyond validation, prevents injection; critical for subprocess.Popen with user input
- **Schema validation for outputs** — Tools write dashboard-data.json; validate schema to catch breaking changes
- **Nginx reverse proxy** — SSL termination, static serving, load balancing; standard production pattern
- **Environment-based config** — Different settings for dev/staging/prod; supports 12-factor app methodology

**Defer (v2+):**

- **Distributed tracing (full OpenTelemetry)** — High complexity, requires infrastructure (Jaeger); overkill for single-instance API
- **Redis for job storage** — Adds operational complexity; SQLite sufficient until scaling to multiple API instances
- **OAuth/JWT authentication** — Complex to implement correctly; start with API keys, add OAuth when exposing to third-party developers
- **Celery/RQ async framework** — Heavy infrastructure; threading module sufficient for current scale
- **Service mesh (Istio/Linkerd)** — Kubernetes-native, massive complexity; only valuable with 10+ microservices
- **GraphQL API** — More flexible than REST but adds complexity; REST simpler for CRUD operations
- **Multi-region deployment** — Requires database replication; single-region with CDN sufficient initially
- **Custom metrics dashboard** — Duplicates Grafana/Datadog work; export to existing observability platforms

### Architecture Approach

Refactoring monolithic Python files (dashboard.py 2002 lines, polished.py 670 lines, output_generator.py 642 lines) requires incremental Strangler Fig pattern with JSON schema contracts protecting external integration points. The critical architectural constraint is dashboard-data.json: the dashboard consumes this from all 6 tools, using fragile key-based heuristics for tool detection.

**Major components:**

1. **Interface Contract Layer (shared/dashboard_contract.py)** — JSON schema validation enforces dashboard-data.json format across all tools; prevents breaking changes during refactoring; validates tool outputs before writing; enables schema versioning for future evolution
2. **Test Safety Net (tests/)** — Characterization tests capture existing behavior before refactoring; pytest-flask for API testing; pytest-cov for coverage measurement; integration tests verify tool → dashboard flow; mutation testing validates test quality
3. **Module Extraction Strategy** — Extract utilities first (lowest risk: pure functions), then layer separation (UI, data, visualization), finally callbacks (highest risk: shared state); commit after each successful extraction; use Rope/PyCharm automated refactoring where possible
4. **Backwards Compatibility Facades** — Maintain old interfaces during refactoring; use __init__.py exports for import compatibility; deprecation warnings for changed functions; symlinks for file path changes; support multiple schema versions during transition
5. **Production Infrastructure** — Gunicorn WSGI server behind nginx reverse proxy; SQLite for job persistence (WAL mode for concurrency); structured logging with correlation IDs; Flask-Talisman for security headers; Flask-Limiter for rate limiting

**Key patterns:**
- **Safety-first refactoring**: Tests before changes, incremental extraction, continuous integration
- **Interface-first design**: Define module contracts before implementation, validate schemas, maintain backwards compatibility
- **Strangler Fig migration**: New modular code coexists with monolithic code, gradual replacement, no big-bang rewrites

### Critical Pitfalls

Five mistakes that cause rewrites, production outages, or data integrity issues:

1. **Breaking dashboard through uncoordinated schema changes** — Tools output different dashboard-data.json formats without schema validation; dashboard uses fragile key-based detection; silent failures when keys renamed. **Avoid:** Establish JSON schema contract FIRST with explicit tool_type field; version schema (schema_version: "1.0"); validate tool outputs before writing; add integration tests loading real dashboard-data.json from each tool; implement backwards compatibility layer in dashboard.

2. **Replacing bare exceptions incorrectly** — Original `except:` caught multiple exception types (IOError, ValueError, KeyError); developer assumes only one type needed; previously-handled errors now crash application. **Avoid:** Add logging BEFORE changing exception types; run comprehensive tests to capture actual exceptions; review 1-2 weeks of production logs; replace incrementally (one except at a time); use exception hierarchy (catch parent exceptions); keep escape hatch pattern with final Exception handler.

3. **Adding tests that don't actually test** — Tests mock everything, removing real behavior; check implementation details not behavior; no error path testing; trivial assertions (assert result is not None); tests pass when code is broken. **Avoid:** Start with characterization tests capturing current behavior; test behavior not implementation; minimize mocking (only external dependencies); test error cases explicitly; use mutation testing (mutmut) to verify tests catch bugs; manually break code to verify test fails.

4. **Refactoring monoliths without safety net** — Large files (dashboard.py 2002 lines) split into modules; hidden coupling (shared state, import order, globals) causes regressions; no tests verify behavior before/after; done in large batches not incrementally. **Avoid:** Add characterization tests BEFORE refactoring; extract one function/class at a time; use automated IDE refactorings first (rename, extract method); run full test suite after each extraction; document dependencies before splitting; use feature flags for gradual deployment.

5. **Input validation that breaks legitimate use cases** — Strict validation blocks edge cases users depend on (e.g., URL must have .com TLD, blocking .io or localhost); no analysis of existing production data; no deprecation period. **Avoid:** Analyze production data before adding validation; validate broadly (accept more formats than expected); fail open with logging (warn but allow); version API (/v2/ with strict validation, /v1/ loose); clear error messages ("URL must include protocol http:// or https://"); deprecation warnings 1-2 months before enforcing.

**Additional moderate pitfalls:**
- JSON serialization errors with datetime/NaN/Decimal (use orjson or custom encoder)
- Rate limiting blocking legitimate users (differentiated limits, user-based not just IP)
- CORS wildcards enabling attacks (whitelist origins explicitly)
- Subprocess command injection (whitelist validation, path canonicalization, avoid shell=True)
- SQLite race conditions without transactions (use context managers, WAL mode, IMMEDIATE transactions)

## Implications for Roadmap

Based on combined research, production hardening should follow dependency-driven phases with interface contracts established first to prevent dashboard breakage. The critical path prioritizes preventing catastrophic failures over operational excellence features.

### Phase 1: Interface Contracts & Safety Net (Week 1)
**Rationale:** Must protect dashboard integration before any tool modifications; creates safety net for all subsequent refactoring
**Delivers:** JSON schema validation, characterization tests, baseline metrics
**Addresses:** Dashboard breakage risk (Pitfall 1), refactoring safety (Pitfall 4)
**Critical outputs:**
- shared/dashboard_contract.py with JSON Schema for dashboard-data.json
- Schema validation integrated into all 6+ tool output generation
- Integration tests loading real dashboard-data.json from each tool
- Characterization tests for api_server.py capturing current behavior
- Baseline complexity metrics (radon cc, radon mi) for files to be refactored

### Phase 2: Security Foundations (Week 1-2)
**Rationale:** Security gaps (CORS wildcards, subprocess injection) are critical vulnerabilities requiring immediate attention
**Delivers:** Input validation, security headers, environment config, initial logging
**Uses:** Pydantic 2.12.5 for validation, Flask-Talisman 1.1.0 for headers, python-dotenv 1.2.1 for config
**Addresses:** Input validation (table stakes), CORS security (Pitfall 8), subprocess injection (Pitfall 9)
**Key tasks:**
- Add Pydantic models for API request/response validation
- Configure Flask-Talisman with security headers (HSTS, CSP, X-Frame-Options)
- Replace CORS wildcard with explicit origin whitelist
- Move secrets to environment variables (API keys, config)
- Add input sanitization for subprocess parameters (whitelist tool names, canonicalize paths)

### Phase 3: Structured Logging & Observability (Week 2)
**Rationale:** Logging must be in place BEFORE exception handling changes to understand what exceptions actually occur
**Delivers:** JSON structured logging, correlation IDs, request/response logging
**Uses:** structlog 25.5.0 with JSON formatter
**Addresses:** Operational visibility (table stakes), exception handling preparation (Pitfall 2)
**Key tasks:**
- Configure structlog with JSON renderer for machine-parseable logs
- Add correlation ID middleware (generate UUID per request)
- Implement request/response logging (method, path, status, duration)
- Add logging to existing bare except blocks (don't change exception types yet)
- Set up log aggregation integration (ELK, CloudWatch, or file-based initially)

### Phase 4: Exception Handling Improvement (Week 2-3)
**Rationale:** Now that logging captures actual exceptions, safe to replace bare except with specific types
**Delivers:** Specific exception handling, proper error responses, sanitized error messages
**Addresses:** Error handling (table stakes), exception replacement (Pitfall 2)
**Requires:** Logging infrastructure from Phase 3
**Key tasks:**
- Review logs to identify actual exception types occurring in production
- Replace bare except blocks incrementally (one at a time)
- Use exception hierarchy (catch parent exceptions when multiple types expected)
- Add sanitized error messages for clients (generic "Internal server error")
- Log full exception details server-side with context
- Test error paths explicitly

### Phase 5: Rate Limiting & CORS Hardening (Week 3)
**Rationale:** Security features can be added independently now that core validation and logging are in place
**Delivers:** Rate limiting per-IP and per-endpoint, proper CORS configuration
**Uses:** Flask-Limiter 4.1.1 with in-memory backend initially
**Addresses:** Abuse prevention (table stakes), rate limiting (Pitfall 7)
**Key tasks:**
- Add Flask-Limiter with in-memory storage backend
- Configure per-endpoint rate limits (conservative initially: 10 req/min for heavy operations)
- Add Retry-After headers to 429 responses
- Differentiate limits for authenticated vs anonymous users
- Test rate limiting doesn't block legitimate workflows
- Add exemption mechanism for internal tools/testing

### Phase 6: Testing Infrastructure (Week 3-4)
**Rationale:** Comprehensive tests required before refactoring monolithic files
**Delivers:** pytest suite with >80% coverage, integration tests, test automation
**Uses:** pytest 8.x, pytest-flask 1.3.0, pytest-cov 6.x, dash[testing]
**Addresses:** Testing foundation (table stakes), refactoring safety (Pitfall 3, Pitfall 4)
**Key tasks:**
- Set up pytest with pytest-flask for API testing
- Add unit tests for core logic (validation, data processing)
- Add functional tests for API endpoints (POST /api/run-tool)
- Add integration tests (tool execution → dashboard loading)
- Configure pytest-cov for coverage reporting (target >80%)
- Add dash[testing] for dashboard UI tests
- Consider mutation testing (mutmut) to validate test quality

### Phase 7: Refactoring Monolithic Files (Week 4-6)
**Rationale:** Now safe to refactor with tests in place and interface contracts protecting dashboard
**Delivers:** Modular codebase with files <500 lines, reduced complexity
**Implements:** Module extraction patterns from ARCHITECTURE.md
**Addresses:** Maintainability, refactoring safety (Pitfall 4)
**Requires:** Comprehensive tests from Phase 6, interface contracts from Phase 1
**Priority order:**
1. **dashboard/dashboard.py (2002 lines)** — Extract utilities → layout → callbacks (highest impact)
2. **graspevaluator/metrics/polished.py (670 lines)** — Extract checkers and utilities
3. **rulesevaluator/src/output_generator.py (642 lines)** — Extract format generators
4. **graspevaluator/metrics/structured.py (640 lines)** — Extract checkers
5. **geoevaluator/src/main.py (633 lines)** — Extract crawler, analyzer, reporter

**Incremental approach:**
- Extract utilities first (lowest risk: pure functions)
- Then layer separation (UI, data, visualization)
- Finally callbacks (highest risk: shared state)
- Commit after each successful extraction
- Run full test suite after each change

### Phase 8: Persistent Storage Migration (Week 6-7)
**Rationale:** Job persistence enables recovery across restarts but requires careful transaction handling
**Delivers:** SQLite-backed job storage with proper concurrency handling
**Uses:** SQLite 3.x with WAL mode
**Addresses:** Job persistence (should-have), transaction safety (Pitfall 10)
**Key tasks:**
- Design SQLite schema (jobs table with job_id, tool_name, status, created_at, result_path, error)
- Implement context managers for automatic commit/rollback
- Use IMMEDIATE transactions for writes to prevent SQLITE_BUSY errors
- Enable WAL mode for better concurrency
- Add indexes on job_id, status, created_at
- Migrate from in-memory dict incrementally
- Add job cleanup/archival logic (purge old jobs after 30 days)
- Benchmark performance; migrate to Redis only if SQLite bottleneck proven

### Phase 9: Production Deployment (Week 7-8)
**Rationale:** Final phase deploys hardened system with production infrastructure
**Delivers:** Production-ready deployment with Gunicorn, nginx, monitoring
**Uses:** Gunicorn 23.0.0, nginx (reverse proxy)
**Addresses:** Production server (table stakes), infrastructure (should-have)
**Key tasks:**
- Configure Gunicorn with 2-4x CPU cores workers (gthread worker for I/O-bound tasks)
- Set up nginx reverse proxy (SSL termination, static file serving)
- Configure TLS certificates (Let's Encrypt)
- Set up monitoring and alerting (Sentry, Datadog, or basic log monitoring)
- Configure environment-specific settings (dev/staging/prod)
- Document deployment process
- Create deployment checklist (verify debug mode off, secrets in env vars, etc.)
- Load testing to validate worker configuration

### Phase Ordering Rationale

**Dependency-driven sequence:**
1. Interface contracts must come first to prevent dashboard breakage during all subsequent changes
2. Security (validation, CORS) before exception handling to establish input filtering
3. Logging before exception handling to understand what exceptions actually occur
4. Testing before refactoring to create safety net for structural changes
5. Refactoring before storage migration to avoid refactoring complex persistence code
6. Production deployment last to deploy fully hardened system

**Risk mitigation:**
- Low-risk changes first (logging, validation) build confidence before high-risk refactoring
- Each phase has clear deliverables and rollback points
- No phase requires rewriting work from previous phase
- Parallelizable work identified (rate limiting can happen independently of exception handling)

**Avoid big-bang deployment:**
- Each phase can be deployed independently to production
- Feature flags enable gradual rollout of refactored code
- Backwards compatibility maintained throughout

### Research Flags

**Phases needing deeper research during planning:**

- **Phase 7 (Refactoring):** File-specific refactoring for graspevaluator metrics (polished.py, structured.py) may need domain-specific research on grammar checking and semantic HTML analysis patterns; module extraction order requires careful dependency mapping
- **Phase 8 (Storage Migration):** SQLite concurrency patterns for multi-threaded Flask apps may need additional research; decision point on when to migrate to Redis requires performance benchmarking research

**Phases with standard patterns (skip research-phase):**

- **Phase 1 (Interface Contracts):** JSON Schema validation is well-documented with established patterns
- **Phase 2 (Security):** Pydantic, Flask-Talisman, CORS configuration have extensive documentation and examples
- **Phase 3 (Logging):** structlog implementation is straightforward with official docs
- **Phase 5 (Rate Limiting):** Flask-Limiter has comprehensive documentation with production examples
- **Phase 6 (Testing):** pytest and pytest-flask are industry standard with abundant resources
- **Phase 9 (Deployment):** Gunicorn + nginx deployment is well-documented pattern

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library versions verified with PyPI as of Jan 2026; production-proven technologies with active maintenance; no deprecated or unmaintained dependencies recommended |
| Features | HIGH | Based on comprehensive REST API production best practices research; table stakes features validated across multiple authoritative sources (Real Python, Auth0, Flask docs); anti-features identified through anti-pattern analysis |
| Architecture | HIGH | Refactoring patterns based on established software engineering practices (Strangler Fig, Interface-First Design); JSON Schema contract approach validated by successful large-scale Python projects; module extraction strategy follows Real Python and Flask community consensus |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls identified through codebase analysis (CONCERNS.md) corroborated with web research on common production failures; moderate/minor pitfalls based on Python production best practices; some pitfalls inferred from general principles rather than specific to this codebase |

**Overall confidence:** HIGH

Research drew from Context7 library IDs for official documentation, PyPI for version verification, and authoritative community sources (Real Python, Flask official docs, Google Cloud Platform). All stack recommendations have verified version numbers and proven production track records. Architecture recommendations based on established patterns with successful precedents.

### Gaps to Address

**During Phase 1 planning:**
- **Exact dashboard-data.json schema extraction**: Need to analyze all existing dashboard-data.json files from tools to create comprehensive JSON Schema; initial schema should be permissive (validate existing data before tightening)
- **Tool detection heuristics documentation**: Dashboard uses fragile key-based detection; need to document exact logic before establishing explicit tool_type field

**During Phase 7 planning:**
- **Dashboard callback interdependencies**: Need detailed analysis of shared state between callbacks before extraction; may discover additional coupling not visible in static analysis
- **Metric evaluator domain logic**: Grammar checking (polished.py) and semantic HTML analysis (structured.py) may have domain-specific refactoring constraints; may need domain expert review

**During Phase 8 planning:**
- **SQLite performance baseline**: Need to establish baseline performance metrics for in-memory job storage to compare against SQLite; decision point on Redis migration requires actual throughput measurements not theoretical analysis
- **Job cleanup policy**: Need to define retention policy for completed jobs (30 days? 90 days? indefinite?); affects storage requirements and query performance

**Throughout implementation:**
- **Backwards compatibility verification**: Each phase must verify no breaking changes to existing integrations; automated contract testing should catch most issues but manual verification needed
- **Production data validation**: Test validation and error handling with real production data samples, not just clean test fixtures

## Sources

### Primary (HIGH confidence)

**Official Documentation & PyPI:**
- Pydantic PyPI (2.12.5, Nov 2025) — Type-based validation
- structlog PyPI (25.5.0, Oct 2025) — Structured logging
- Gunicorn PyPI (23.0.0, Jan 2026) — WSGI server
- Bandit PyPI (1.9.3, Jan 2026) — Security scanning
- Flask Official Documentation — Security best practices, deployment
- Dash Official Documentation — Testing, application structure
- python-dotenv PyPI (1.2.1, Jan 2026) — Environment configuration

**Codebase Analysis:**
- `/home/bill/Localcode/Airbais/tools/.planning/codebase/CONCERNS.md` — Technical debt analysis identifying bare exceptions, CORS issues, subprocess security risks, monolithic files
- `/home/bill/Localcode/Airbais/tools/.planning/codebase/ARCHITECTURE.md` — System architecture, data flow, dashboard integration patterns
- `/home/bill/Localcode/Airbais/tools/.planning/PROJECT.md` — Production readiness requirements
- `/home/bill/Localcode/Airbais/tools/CLAUDE.md` — Tool suite overview, architectural patterns

### Secondary (MEDIUM confidence)

**REST API Best Practices:**
- API Development in 2026: Building REST and GraphQL APIs with Python (Nucamp, 2026)
- Best Practices for Flask API Development (Auth0)
- REST API Best Practices: A Guide to Building Robust APIs with Python (Medium)
- Let's build a production-ready REST API (RealWorldML)

**Testing & Refactoring:**
- Refactoring Python Applications for Simplicity (Real Python)
- How to Refactor Complex Codebases: A Practical Guide (freeCodeCamp)
- Python Refactoring: Techniques, Tools, and Best Practices (CodeSee)
- Test-driven development (TDD) guide (monday.com, 2026)

**Security:**
- Flask Security with Talisman (GeeksforGeeks)
- OWASP API Security Top 10
- Python Security Tools Guide (Aikodo Dev, 2026)

**Architecture Patterns:**
- Strangler Fig Pattern for Refactoring (AWS Prescriptive Guidance, Medium)
- Structuring Large Dash Applications (Plotly Community)
- Python Project Structure Best Practices (Dagster, Real Python)

### Tertiary (LOW confidence)

**General Best Practices:**
- 7 Python Best Practices That Made My Code Review-Proof in 2026 (Medium)
- Your Python Code is Slow in 2026: Here's Why (Dev.to)
- Every Python Rate-Limiting Library is Broken (GitHub Gist)

---
*Research completed: 2026-01-23*
*Ready for roadmap: YES*
