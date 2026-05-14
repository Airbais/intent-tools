---
phase: 02-security-hardening
plan: 05
status: complete
completed: 2026-01-23
duration: 3m 7s
tasks_completed: 3/3

subsystem: api-security
tags: [flask-talisman, security-headers, hsts, csp, xss-protection]

dependency_graph:
  requires:
    - 02-03-PLAN.md (CORS configuration)
    - 02-01-PLAN.md (Request validation foundation)
  provides:
    - Security headers on all API responses
    - HSTS for HTTPS enforcement
    - CSP to prevent XSS attacks
    - X-Frame-Options for clickjacking prevention
    - X-Content-Type-Options for MIME sniffing prevention
  affects:
    - API clients (must handle HTTPS redirects in production)
    - Future dashboard hardening (separate Talisman config needed for Dash)

tech_stack:
  added:
    - flask-talisman==1.1.0
  patterns:
    - Security headers via Flask extension
    - Environment-based HTTPS enforcement
    - Restrictive CSP for JSON API

key_files:
  created:
    - automation/security/talisman_config.py
    - automation/tests/test_security_headers.py
  modified:
    - automation/requirements.txt
    - automation/security/__init__.py
    - automation/api_server.py

decisions:
  - decision: "Restrictive CSP for API (default-src: none)"
    rationale: "API serves JSON, no scripts/styles needed"
    alternatives: "Permissive CSP (rejected - unnecessary attack surface)"

  - decision: "TALISMAN_FORCE_HTTPS env var for proxy setups"
    rationale: "Allow HTTPS termination at reverse proxy layer"
    alternatives: "Always force HTTPS (rejected - breaks proxy deployments)"

  - decision: "Separate Talisman config for API vs Dashboard"
    rationale: "Dash requires inline scripts, API doesn't - different CSP needs"
    alternatives: "Single config with permissive CSP (rejected - reduces API security)"

metrics:
  tests_added: 10
  test_coverage: "Security headers, Talisman configuration, env override"
  headers_configured: 5
---

# Phase 2 Plan 5: Flask-Talisman Security Headers Summary

**One-liner:** Browser security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options) via Flask-Talisman with configurable HTTPS enforcement

## What Was Built

Integrated Flask-Talisman to add comprehensive security headers to all API responses:

1. **Talisman Configuration Module** (`automation/security/talisman_config.py`)
   - `configure_talisman(app, force_https)` - Apply security headers to Flask app
   - `get_api_csp()` - Restrictive Content Security Policy for JSON API
   - Environment variable support: `TALISMAN_FORCE_HTTPS=false` for proxy setups
   - Automatic debug mode detection (no HTTPS forcing in development)

2. **API Server Integration** (`automation/api_server.py`)
   - Added Talisman import and configuration call
   - Proper ordering: error handlers → CORS → Talisman
   - All API responses now include security headers

3. **Comprehensive Testing** (`automation/tests/test_security_headers.py`)
   - 10 tests covering all security headers
   - Tests for configuration edge cases (debug mode, env override)
   - Tests on multiple endpoint types (GET, POST, error responses)

## Security Headers Configured

| Header | Value | Purpose |
|--------|-------|---------|
| **X-Frame-Options** | DENY | Prevent clickjacking by blocking iframe embedding |
| **X-Content-Type-Options** | nosniff | Prevent MIME sniffing attacks |
| **Content-Security-Policy** | default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self' | Restrict content sources to prevent XSS |
| **Referrer-Policy** | strict-origin-when-cross-origin | Limit referrer data leakage |
| **Strict-Transport-Security** | max-age=31536000; includeSubDomains; preload | Enforce HTTPS for 1 year (production only) |

## CSP Design Rationale

The API uses a very restrictive CSP because it only serves JSON:

```python
{
    'default-src': "'none'",      # Deny everything by default
    'frame-ancestors': "'none'",  # No embedding (clickjacking)
    'base-uri': "'none'",         # No base tag hijacking
    'form-action': "'self'",      # Forms only submit to same origin
}
```

**Why no script-src, style-src, etc.?**
- API returns JSON, not HTML
- No JavaScript, CSS, fonts, or images needed
- Minimizing attack surface

**Dashboard CSP is separate:**
- Dash requires inline scripts for interactivity
- Dash components need `csp_hashes()` for CSP compliance
- If Phase 3+ adds dashboard hardening, use separate Talisman config

## HTTPS Enforcement Configuration

Talisman force_https behavior:

1. **Production (app.debug=False):** Force HTTPS redirects by default
2. **Development (app.debug=True):** No HTTPS forcing by default
3. **Proxy setups:** Set `TALISMAN_FORCE_HTTPS=false` to disable (TLS terminated at proxy)
4. **Explicit override:** Pass `force_https=True/False` to `configure_talisman()`

## Tasks Completed

### Task 1: Create Flask-Talisman Configuration Module
**Commit:** `93bde0b` - feat(02-05): add Flask-Talisman configuration module

**Files created:**
- `automation/security/talisman_config.py` (115 lines)
  - `configure_talisman(app, force_https)` function
  - `get_api_csp()` helper for restrictive CSP
  - Environment variable parsing for HTTPS enforcement
  - Logging for configuration transparency

**Files modified:**
- `automation/requirements.txt` - Added flask-talisman==1.1.0
- `automation/security/__init__.py` - Exported configure_talisman, get_api_csp

**Verification:**
- ✓ Module imports without errors
- ✓ Flask-Talisman installed and available

### Task 2: Integrate Talisman with API Server
**Commit:** `725f535` - feat(02-05): integrate Talisman with API server

**Files modified:**
- `automation/api_server.py`
  - Added talisman_config import
  - Called `configure_talisman(app)` after CORS configuration
  - Removed duplicate `register_error_handlers()` call

**Integration order:**
1. `register_error_handlers(app)` - Sanitize error responses first
2. `configure_cors(app, config)` - Allow cross-origin requests
3. `configure_talisman(app)` - Wrap all responses with security headers

**Verification:**
- ✓ API server imports without errors
- ✓ Talisman configuration logged on startup
- ✓ "Talisman configured with HTTPS enforcement" message appears

### Task 3: Add Tests for Security Headers
**Commit:** `46ccc4d` - test(02-05): add security header tests

**Files created:**
- `automation/tests/test_security_headers.py` (115 lines, 10 tests)

**Test coverage:**

**TestSecurityHeaders class (7 tests):**
1. `test_x_frame_options_deny` - Verify X-Frame-Options: DENY
2. `test_x_content_type_options_nosniff` - Verify X-Content-Type-Options: nosniff
3. `test_content_security_policy_present` - Verify CSP directives
4. `test_referrer_policy_present` - Verify Referrer-Policy
5. `test_strict_transport_security_present` - Check HSTS (documented HTTPS-only behavior)
6. `test_headers_on_error_response` - Headers on 404 (with redirect support)
7. `test_headers_on_post_endpoint` - Headers on POST /intentcrawler/analyze

**TestTalismanConfiguration class (3 tests):**
1. `test_get_api_csp_is_restrictive` - Verify CSP denies everything by default
2. `test_configure_talisman_respects_debug_mode` - force_https=False in debug
3. `test_configure_talisman_env_override` - TALISMAN_FORCE_HTTPS env var works

**Test results:** ✓ All 10 tests pass

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Restrictive CSP for API**
   - **Context:** API only serves JSON, no HTML rendering
   - **Decision:** Use very restrictive CSP (default-src: 'none')
   - **Impact:** Minimal attack surface, prevents XSS even if response mishandled

2. **Configurable HTTPS enforcement**
   - **Context:** Some deployments use reverse proxy for TLS termination
   - **Decision:** Support TALISMAN_FORCE_HTTPS env var to disable redirects
   - **Impact:** Compatible with Nginx/Apache proxy setups, still secure behind proxy

3. **Separate API vs Dashboard Talisman configs**
   - **Context:** Dash requires inline scripts, API doesn't
   - **Decision:** Only configure Talisman for API server, not Dashboard
   - **Impact:** API gets restrictive CSP, Dashboard would need separate config with csp_hashes()

## Integration Points

**Upstream dependencies:**
- Plan 02-03: CORS configuration (Talisman applied after CORS)
- Plan 02-01: Request validation (security headers on validated endpoints)

**Downstream effects:**
- API clients in production must handle HTTPS redirects (302 → HTTPS)
- Any future API key authentication should work with Talisman cookies (http_only=True)
- Dashboard hardening (if added) needs separate Talisman config for Dash components

**Security boundary:**
- API server: Full Talisman protection with restrictive CSP
- Dashboard: No Talisman yet (Dash inline scripts need special handling)

## Testing Strategy

**Test structure:**
- Fixture creates Flask test client with TESTING=True
- Tests use `/health` endpoint (simple, always available)
- Error response test follows redirects to avoid 302/404 ambiguity
- Configuration tests create fresh Flask apps to isolate state

**Edge cases covered:**
- HTTPS redirects in production mode
- Debug mode disables HTTPS forcing
- Environment variable overrides default behavior
- Headers present on GET, POST, and error responses

## Next Phase Readiness

**Blockers:** None

**Considerations for future phases:**

1. **Phase 3 (Logging & Monitoring):**
   - Log security header violations if CSP reports enabled
   - Monitor HTTPS redirect rates (should be 0 after clients adapt)

2. **Phase 5 (Rate Limiting):**
   - Rate limiter should work with Talisman (no header conflicts)
   - Consider rate limiting HTTPS redirects separately from API calls

3. **Phase 8 (Dashboard Hardening):**
   - If adding Talisman to Dashboard, use `csp_hashes()` for Dash scripts
   - Dashboard CSP will be more permissive than API CSP
   - Test Dash components work with security headers

**Current security posture:**
- ✅ Input validation (02-01)
- ✅ Error sanitization (02-02)
- ✅ CORS (02-03)
- ✅ Subprocess validation (02-04)
- ✅ Security headers (02-05)
- ⏳ Rate limiting (02-06, next)

## Production Deployment Notes

**Environment variables:**
- `TALISMAN_FORCE_HTTPS=false` - Disable HTTPS forcing (for proxy setups)
- Default: HTTPS enforced in production (app.debug=False)

**Proxy configurations:**
- **Nginx/Apache with TLS:** Set TALISMAN_FORCE_HTTPS=false
- **Direct Flask deployment:** Leave default (HTTPS enforced)
- **Development:** Automatic (no HTTPS forcing in debug mode)

**HSTS implications:**
- Once browser sees HSTS header, it enforces HTTPS for 1 year
- Test in staging before enabling in production
- Use `includeSubDomains` carefully (applies to all subdomains)
- Consider HSTS preload list submission for high-security sites

**CSP monitoring:**
- Current config: `content_security_policy_report_only=False` (enforced)
- For gradual rollout: Set to True to log violations without blocking
- Add `report-uri` directive to collect CSP violation reports

## Success Criteria Met

✅ **Must-haves:**
1. API responses include X-Frame-Options: DENY header
2. API responses include X-Content-Type-Options: nosniff header
3. API responses include Strict-Transport-Security header (in production)
4. CSP configured to prevent XSS attacks

✅ **Technical requirements:**
1. Flask-Talisman 1.1.0 added to requirements.txt
2. configure_talisman() applies security headers to Flask app
3. X-Frame-Options: DENY prevents clickjacking
4. X-Content-Type-Options: nosniff prevents MIME sniffing
5. Content-Security-Policy restricts content sources
6. Referrer-Policy: strict-origin-when-cross-origin limits referrer data
7. HSTS configured for production (1 year max-age)
8. force_https configurable via environment variable for proxy setups
9. All 10 security header tests pass

## Lessons Learned

1. **Talisman + Test Client HTTPS Redirects**
   - Issue: Talisman force_https caused 302 redirects in tests (expected 404)
   - Solution: Use `follow_redirects=True` in test client requests
   - Lesson: Test HTTP behavior separately from HTTPS enforcement behavior

2. **API vs Dashboard CSP Differences**
   - Insight: JSON API can use very restrictive CSP, Dash cannot
   - Approach: Separate Talisman configs for API server vs Dashboard
   - Benefit: Maximum security for API without breaking Dashboard interactivity

3. **Environment Variable Timing**
   - Challenge: Setting TALISMAN_FORCE_HTTPS after app import has no effect
   - Solution: Document env var must be set before Flask app creation
   - Alternative: Pass force_https parameter explicitly for testing

## Files Changed Summary

**Created (2 files):**
- `automation/security/talisman_config.py` - Security headers configuration
- `automation/tests/test_security_headers.py` - Security header tests

**Modified (3 files):**
- `automation/requirements.txt` - Added flask-talisman dependency
- `automation/security/__init__.py` - Export Talisman functions
- `automation/api_server.py` - Integrate Talisman with Flask app

**Total changes:** 5 files, 230+ lines added

## Commit History

1. `93bde0b` - feat(02-05): add Flask-Talisman configuration module
2. `725f535` - feat(02-05): integrate Talisman with API server
3. `46ccc4d` - test(02-05): add security header tests

## Verification Commands

```bash
# Import Talisman module
python3 -c "import sys; sys.path.insert(0, 'automation'); from security.talisman_config import configure_talisman"

# Check API server integration
grep "configure_talisman" automation/api_server.py

# Run security header tests
python3 -m pytest automation/tests/test_security_headers.py -v

# Manual server test (with server running)
curl -v http://localhost:8888/health 2>&1 | grep -i "x-frame-options\|x-content-type\|content-security-policy"
```

Expected output:
```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'
```
