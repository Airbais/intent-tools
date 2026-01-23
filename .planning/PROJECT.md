# Airbais Tools Production Readiness

## What This Is

A comprehensive production readiness initiative for the Airbais Tools suite — a collection of specialized tools that help brands optimize their presence in LLMs and AI systems. This milestone addresses security vulnerabilities, stability issues, test coverage gaps, and maintainability concerns identified in the codebase analysis, preparing the suite for production deployment.

## Core Value

The tools must be reliable, secure, and maintainable — errors are logged not silenced, inputs are validated, and the codebase is testable so changes don't break the interconnected dashboard.

## Requirements

### Validated

Existing capabilities inferred from codebase:

- ✓ IntentCrawler analyzes website intents and generates structured reports — existing
- ✓ GRASP Evaluator assesses content quality across 5 dimensions — existing
- ✓ LLM Evaluator tests brand mentions across multiple LLM providers — existing
- ✓ GEO Evaluator analyzes location-based optimization — existing
- ✓ LLMS.txt Generator creates AI-friendly site summaries — existing
- ✓ Rules Evaluator validates content against custom rules with RAG — existing
- ✓ Unified dashboard displays results from all tools dynamically — existing
- ✓ Automation API allows programmatic tool execution via REST — existing
- ✓ All tools generate standardized dashboard-data.json — existing
- ✓ Date-based results organization with historical tracking — existing

### Active

Security hardening:
- [ ] Replace bare exception handlers with specific types and logging
- [ ] Add input validation for all API parameters (type, length, format)
- [ ] Sanitize error messages before returning to API clients
- [ ] Configure CORS with explicit origin whitelist (default disabled)
- [ ] Validate subprocess command parameters (whitelist, path canonicalization)

Bug fixes:
- [ ] Fix job ID cleanup — investigate root cause of trailing special characters
- [ ] Fix datetime serialization — explicit ISO-8601 conversion at creation
- [ ] Ensure all caught exceptions are logged, not silently swallowed

Testing foundation:
- [ ] Add comprehensive tests for API server endpoints (happy path + error cases)
- [ ] Add tests for dashboard data loading (malformed JSON, missing files, edge cases)
- [ ] Add tests for LLM provider failover logic
- [ ] Add tests for crawler robustness (timeouts, SSL errors, redirects)
- [ ] Add schema validation tests for dashboard-data.json output

Dashboard/tool interface:
- [ ] Define explicit dashboard-data.json schema with required `tool_type` field
- [ ] Update all tools to include `tool_type` in output
- [ ] Replace heuristic tool detection with explicit field lookup
- [ ] Add schema validation on dashboard load

Refactoring:
- [ ] Break apart dashboard.py (2002 lines) into focused modules
- [ ] Break apart polished.py (670 lines) into scoring components
- [ ] Break apart output_generator.py (642 lines) into format-specific modules
- [ ] Break apart structured.py (640 lines) into metric modules
- [ ] Break apart geoevaluator main.py (633 lines) into orchestration modules

Infrastructure improvements:
- [ ] Migrate job storage from in-memory dict to persistent storage (SQLite)
- [ ] Add rate limiting to API endpoints
- [ ] Add audit logging for API requests
- [ ] Implement result validation with checksums

Performance:
- [ ] Implement lazy loading for ML models (load on first use, unload on timeout)
- [ ] Add pagination to dashboard data loading
- [ ] Add connection pooling to crawlers

Dependencies:
- [ ] Pin SDK versions to specific minor versions (openai, anthropic, chromadb)
- [ ] Add Python version constraints to project configuration
- [ ] Document dependency update process

### Out of Scope

- New tool development — focus is on hardening existing tools
- New features for existing tools — stability first
- Migration to hosted vector DB (Pinecone, Weaviate) — future milestone
- Horizontal scaling / load balancer setup — future milestone
- Mobile/responsive dashboard redesign — future milestone
- OAuth/JWT API authentication — future milestone (CORS + rate limiting sufficient for v1)
- Async execution framework (Celery/RQ) — future milestone, thread pool executor sufficient for now

## Context

**Current State:**
- 6 tools operational with shared dashboard integration
- Codebase mapped on 2026-01-21 with comprehensive concerns documented
- Tools are interconnected through standardized dashboard-data.json output
- Automation API enables external workflow integration (N8N, Zapier)

**Technical Environment:**
- Python-based tools with Flask API and Dash dashboard
- ChromaDB for vector storage (rulesevaluator)
- Multiple LLM providers (OpenAI, Anthropic) with provider abstraction
- Date-based result storage pattern across all tools

**Key Interdependencies:**
- Dashboard reads dashboard-data.json from all tools — changes to output format affect dashboard
- Automation API spawns tools via subprocess — changes to CLI interfaces affect API
- Tools share patterns (ConfigManager, Crawler, Validator) but not code — changes can be tool-isolated

**Approach:**
- Define interface contract (dashboard-data.json schema) first
- Parallel work on dashboard and tools after interface stabilized
- Grouped changes with integration tests between each phase
- Quality over speed — take time needed to do it right

## Constraints

- **Interface Stability**: Dashboard-data.json schema changes must be backwards compatible or coordinated across all tools simultaneously
- **No Feature Regression**: All existing tool functionality must continue working through refactoring
- **Test Coverage First**: Add tests for critical paths before refactoring those paths
- **Incremental Commits**: Each phase should be independently deployable

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite for job storage | Simpler than Redis, sufficient for single-instance, file-based persistence | — Pending |
| Parallel dashboard/tools work | Faster than sequential, enabled by interface contract | — Pending |
| Full refactor of large files | Production code should be maintainable and testable | — Pending |
| Skip async framework (Celery) | Thread pool executor sufficient for current scale | — Pending |

---
*Last updated: 2026-01-23 after initialization*
