# Phase 5: API Hardening - Research

**Researched:** 2026-01-24
**Domain:** Flask API rate limiting and health check endpoints
**Confidence:** HIGH

## Summary

This research investigated Flask-Limiter for rate limiting and health check endpoint patterns for Kubernetes deployments. The standard approach uses Flask-Limiter (v4.1.1) with Redis storage backend for production, per-endpoint rate limit decorators with IP-based identification, and separate /health/live and /health/ready endpoints following Kubernetes probe conventions.

Flask-Limiter integrates seamlessly with existing Flask error handlers through the 429 error handler pattern, automatically includes Retry-After headers, and supports IP whitelisting via request_filter decorators. Health checks should distinguish between liveness (process running) and readiness (can accept traffic), with liveness being lightweight and readiness checking dependencies.

**Primary recommendation:** Use Flask-Limiter with Redis storage (or in-memory for testing), configure per-endpoint limits via decorators, integrate with existing build_error_response() for 429 errors, implement separate /health/live (lightweight) and /health/ready (dependency checks) endpoints, and exempt health checks from rate limiting.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask-Limiter | 4.1.1 | Rate limiting for Flask apps | Official Flask extension, supports multiple storage backends, per-endpoint configuration, automatic 429 responses with Retry-After headers |
| flask-healthz | latest | Kubernetes health check endpoints | Purpose-built for K8s liveness/readiness probes, minimal configuration, follows K8s conventions |
| Redis | 6.x+ | Rate limit storage backend | Production-ready persistence, handles distributed rate limiting across workers, industry standard for Flask-Limiter |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| werkzeug.middleware.proxy_fix.ProxyFix | 3.0.1 (bundled) | Extract real IP behind proxies | When deployed behind reverse proxy/load balancer to prevent IP spoofing |
| limits | latest (Flask-Limiter dependency) | Storage backend abstraction | Automatically installed with Flask-Limiter, provides Redis/Memcached/MongoDB adapters |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| flask-healthz | Manual endpoints | flask-healthz provides K8s-specific conventions and simplifies configuration vs manual implementation |
| Redis storage | In-memory storage | In-memory only works for single-process dev, fails with multiple workers (each worker has separate memory) |
| Flask-Limiter | Custom rate limiting | Flask-Limiter is battle-tested with automatic header management, storage backends, and 429 handling vs building from scratch |

**Installation:**
```bash
pip install Flask-Limiter redis flask-healthz
```

## Architecture Patterns

### Recommended Integration Structure
```
automation/
├── api_server.py           # Initialize limiter, configure health checks
├── error_handlers.py       # Add 429 handler using build_error_response()
├── rate_limiting/          # NEW: Rate limiting configuration
│   ├── __init__.py
│   ├── config.py           # Limiter initialization, IP whitelist
│   └── limits.py           # Centralized limit definitions
└── health/                 # NEW: Health check logic
    ├── __init__.py
    ├── liveness.py         # Lightweight "is process alive" check
    └── readiness.py        # Dependency checks (can accept traffic)
```

### Pattern 1: Flask-Limiter Initialization with ProxyFix
**What:** Initialize Flask-Limiter with storage backend and key function
**When to use:** Always in production, configure based on deployment environment
**Example:**
```python
# Source: https://flask-limiter.readthedocs.io/en/stable/configuration.html
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure ProxyFix if behind reverse proxy (prevents IP spoofing)
# x_for=1 means trust 1 proxy layer (adjust based on infrastructure)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

limiter = Limiter(
    key_func=get_remote_address,  # Rate limit by IP
    app=app,
    default_limits=["200 per day", "50 per hour"],  # Conservative defaults
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
    storage_options={},
    strategy="fixed-window",  # or "moving-window" for smoother limits
    headers_enabled=True,  # Include X-RateLimit-* headers
)
```

### Pattern 2: Per-Endpoint Rate Limits
**What:** Configure different rate limits for different endpoints based on cost
**When to use:** Analyze endpoints are expensive (long-running), status/results are cheap
**Example:**
```python
# Source: https://flask-limiter.readthedocs.io/en/stable/recipes.html
from flask import Flask, jsonify
from flask_limiter import Limiter

# Expensive analysis endpoint - strict limits
@app.route('/<tool_name>/analyze', methods=['POST'])
@limiter.limit("10 per hour")  # Override defaults with stricter limit
def analyze(tool_name):
    # Start long-running analysis
    pass

# Cheap status check - lenient limits
@app.route('/status/<job_id>', methods=['GET'])
@limiter.limit("100 per minute")  # Allow frequent polling
def get_status(job_id):
    # Quick database lookup
    pass

# Health checks - exempt from rate limiting
@app.route('/health/live')
@limiter.exempt
def health_live():
    return jsonify({"status": "ok"}), 200
```

### Pattern 3: IP Whitelisting for Testing/Automation
**What:** Exempt specific IPs from rate limiting using request filters
**When to use:** Internal automation, CI/CD, trusted monitoring systems
**Example:**
```python
# Source: https://flask-limiter.readthedocs.io/en/stable/recipes.html
import os
from flask import request

# Load whitelist from environment variable
RATE_LIMIT_WHITELIST = os.getenv("RATE_LIMIT_WHITELIST", "127.0.0.1").split(",")

@limiter.request_filter
def ip_whitelist():
    """Exempt whitelisted IPs from all rate limits."""
    client_ip = request.remote_addr
    return client_ip in RATE_LIMIT_WHITELIST

# Alternative: Header-based whitelisting for internal services
@limiter.request_filter
def internal_service_whitelist():
    """Exempt requests with valid internal API key."""
    return request.headers.get("X-Internal-API-Key") == os.getenv("INTERNAL_API_KEY")
```

### Pattern 4: Custom 429 Error Response Integration
**What:** Integrate Flask-Limiter with existing error_handlers.py build_error_response()
**When to use:** Maintain consistent error format across all API errors
**Example:**
```python
# Source: https://flask-limiter.readthedocs.io/en/stable/recipes.html
# In error_handlers.py

from flask import jsonify

def handle_rate_limit_exceeded(e):
    """
    Handle 429 rate limit exceeded errors.

    Flask-Limiter automatically includes Retry-After header.
    We just need to format the response consistently.
    """
    logger.warning(
        "rate_limit_exceeded",
        limit=str(e.description),
        client_ip=request.remote_addr
    )

    # Extract retry-after value from exception if available
    retry_after = getattr(e, 'retry_after', None)

    return build_error_response(
        error='Rate limit exceeded',
        message=f'Too many requests. {e.description}',
        status_code=429,
        error_code='RATE_LIMIT_EXCEEDED',
        details={'retry_after_seconds': retry_after} if retry_after else None
    )

# Register with Flask app
app.register_error_handler(429, handle_rate_limit_exceeded)
```

### Pattern 5: Health Check Endpoints (Liveness vs Readiness)
**What:** Separate endpoints for K8s liveness and readiness probes
**When to use:** Always when deploying to Kubernetes or container orchestration
**Example:**
```python
# Source: https://github.com/fedora-infra/flask-healthz
from flask_healthz import healthz, HealthError

# Register healthz blueprint
app.register_blueprint(healthz, url_prefix="/health")

# Configure check functions
app.config.update({
    "HEALTHZ": {
        "live": "automation.health.liveness.check",
        "ready": "automation.health.readiness.check",
    }
})

# automation/health/liveness.py
def check():
    """Liveness check: Is the process running?

    Should be extremely lightweight - no external calls.
    K8s will restart container if this fails.
    """
    # Just return - process is alive if we get here
    pass

# automation/health/readiness.py
def check():
    """Readiness check: Can we accept traffic?

    Check dependencies but use short timeouts.
    K8s will remove from load balancer if this fails.
    """
    # Check Redis connection (rate limit storage)
    try:
        # Quick ping to storage backend
        limiter.storage.check()
    except Exception:
        raise HealthError("Rate limit storage unavailable")

    # Check job storage (if using external DB)
    # Add other dependency checks as needed
```

### Anti-Patterns to Avoid

- **Using in-memory storage in production with multiple workers:** Each worker process has separate memory, so "10/hour" becomes "10*num_workers/hour". Use Redis/Memcached instead.

- **Not configuring ProxyFix behind reverse proxies:** Clients can spoof X-Forwarded-For headers to bypass rate limits. Always configure ProxyFix with correct num_proxies when behind load balancers.

- **Heavy liveness checks:** Liveness probes that make external calls or database queries can fail due to temporary issues, causing unnecessary container restarts. Keep liveness lightweight.

- **Rate limiting health checks:** Health check endpoints should be exempt from rate limiting so K8s probes don't fail due to rate limits, causing cascading failures.

- **Not including Retry-After header:** Clients need to know when they can retry. Flask-Limiter includes this automatically in 429 responses when using default error handler.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting algorithm | Custom counter with time windows | Flask-Limiter with storage backend | Handles distributed rate limiting, sliding windows, shared storage, automatic header management, edge cases like clock skew |
| IP extraction from proxies | Parse X-Forwarded-For manually | werkzeug ProxyFix middleware | Prevents IP spoofing, handles multiple proxy layers, validates header chains, avoids security vulnerabilities |
| Health check endpoints | Custom /health routes | flask-healthz blueprint | Follows K8s conventions, separates liveness/readiness, handles error signaling, JSON response format |
| Storage backends for rate limits | Custom Redis/Memcached client | limits library (Flask-Limiter dependency) | Abstraction over multiple backends, connection pooling, fallback strategies, error handling |
| Rate limit headers | Manual X-RateLimit-* calculation | Flask-Limiter headers_enabled=True | Automatic Retry-After, X-RateLimit-Limit/Remaining/Reset headers, spec-compliant format |

**Key insight:** Rate limiting has complex edge cases (distributed systems, clock skew, storage failures, IP spoofing) that Flask-Limiter handles out-of-the-box. Custom implementations often miss these cases and create security vulnerabilities or inconsistent behavior across workers.

## Common Pitfalls

### Pitfall 1: In-Memory Storage in Production with Multiple Workers
**What goes wrong:** Rate limits don't work correctly - each worker process has its own memory, so limits are multiplied by worker count.

**Why it happens:** In-memory storage (memory://) is the default and works fine in development (single process). Developers forget to change storage_uri when deploying with Gunicorn/uWSGI which spawn multiple workers.

**How to avoid:**
- Always use Redis/Memcached in production
- Set RATELIMIT_STORAGE_URI environment variable
- Test with multiple workers during staging
- Configure in-memory fallback for development only

**Warning signs:**
- Rate limits seem ineffective (users making 10x expected requests)
- Limits vary per request (different workers responding)
- X-RateLimit-Remaining doesn't match expected values

### Pitfall 2: IP Spoofing Without ProxyFix Configuration
**What goes wrong:** Malicious users bypass rate limits by setting fake X-Forwarded-For headers.

**Why it happens:** When behind a reverse proxy (Nginx, AWS ALB, etc.), request.remote_addr is the proxy's IP, not the client. Developers use get_remote_address which checks X-Forwarded-For, but without ProxyFix, clients can forge this header.

**How to avoid:**
- Always configure ProxyFix when behind reverse proxy
- Set x_for parameter to number of trusted proxy layers
- Never trust X-Forwarded-For without validation
- Test with curl -H "X-Forwarded-For: 1.2.3.4" to verify protection

**Warning signs:**
- Single client appears to come from many IPs
- Rate limits ineffective against sophisticated attackers
- Logs show suspicious X-Forwarded-For patterns

### Pitfall 3: Rate Limiting Health Check Endpoints
**What goes wrong:** Kubernetes liveness/readiness probes fail due to rate limits, causing cascading pod restarts and service outages.

**Why it happens:** Developers apply default rate limits to all endpoints, forgetting that K8s makes frequent health check requests (every few seconds). Health checks hit rate limits, fail, and K8s restarts the pod repeatedly.

**How to avoid:**
- Always exempt health check endpoints with @limiter.exempt
- Configure probes with initialDelaySeconds to avoid startup race
- Monitor health check success rates separately from application metrics
- Test health checks under load (simulate K8s probe frequency)

**Warning signs:**
- Pods restarting frequently for no apparent reason
- "CrashLoopBackOff" in K8s with no application errors
- Health check endpoints returning 429 in logs

### Pitfall 4: Heavy Liveness Checks Causing Unnecessary Restarts
**What goes wrong:** Liveness probes check external dependencies (database, Redis), which fail temporarily, causing K8s to restart healthy containers.

**Why it happens:** Confusion between liveness (is process alive) and readiness (can accept traffic). Developers put all dependency checks in liveness, so transient external issues trigger restarts instead of just removing pod from load balancer.

**How to avoid:**
- Liveness: Only check if process is running (no external calls)
- Readiness: Check dependencies, database connections, etc.
- Set appropriate failureThreshold (3-5) to tolerate transient failures
- Use short timeouts (1-2s) for readiness checks

**Warning signs:**
- Container restarts during database maintenance
- Healthy pods restarting due to temporary network blips
- Loss of request context/in-memory state during restarts

### Pitfall 5: Not Handling RateLimitExceeded in Error Handler
**What goes wrong:** Flask-Limiter raises RateLimitExceeded, but without custom error handler, response format doesn't match existing API error structure, breaking client expectations.

**Why it happens:** Flask-Limiter has default 429 behavior, but projects with custom error response formats (like build_error_response()) need explicit 429 handler registration.

**How to avoid:**
- Register 429 error handler in register_error_handlers()
- Use build_error_response() for consistent format
- Include correlation_id, timestamp, error_code in 429 responses
- Log rate limit violations with structlog

**Warning signs:**
- 429 responses have different JSON structure than 400/404/500
- Clients can't parse 429 error responses
- Missing correlation_id in rate limit error logs

## Code Examples

Verified patterns from official sources:

### Complete Flask-Limiter Setup with Redis
```python
# Source: https://flask-limiter.readthedocs.io/en/stable/configuration.html
import os
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# CRITICAL: Configure ProxyFix if behind reverse proxy
# x_for=1: Trust 1 proxy layer (adjust for your infrastructure)
if os.getenv("BEHIND_PROXY", "false").lower() == "true":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "redis://localhost:6379"),
    strategy="fixed-window",
    headers_enabled=True,  # Include X-RateLimit-* headers
)
```

### Per-Endpoint Rate Limit Configuration
```python
# Source: https://flask-limiter.readthedocs.io/en/stable/recipes.html
from flask_limiter import Limiter

# Expensive endpoint - strict limit
@app.route('/<tool_name>/analyze', methods=['POST'])
@limiter.limit("10 per hour", per_method=True)  # 10 POST requests per hour
def analyze(tool_name):
    """Start tool analysis - expensive operation."""
    return jsonify({"job_id": "..."}), 202

# Status polling - lenient limit
@app.route('/status/<job_id>', methods=['GET'])
@limiter.limit("100 per minute")  # Allow frequent polling
def get_status(job_id):
    """Check job status - cheap operation."""
    return jsonify({"status": "running"}), 200

# List endpoint - moderate limit
@app.route('/jobs', methods=['GET'])
@limiter.limit("30 per minute")
def list_jobs():
    """List all jobs - moderate cost."""
    return jsonify([...]), 200
```

### IP Whitelisting with Environment Variables
```python
# Source: https://flask-limiter.readthedocs.io/en/stable/recipes.html
import os
from flask import request

# Load whitelist from environment (comma-separated IPs)
# Example: RATE_LIMIT_WHITELIST="127.0.0.1,10.0.0.0/8,192.168.1.100"
WHITELIST = set(os.getenv("RATE_LIMIT_WHITELIST", "127.0.0.1").split(","))

@limiter.request_filter
def ip_whitelist():
    """Exempt whitelisted IPs from rate limiting."""
    return request.remote_addr in WHITELIST

# Alternative: Whitelist internal services by header
@limiter.request_filter
def internal_service_filter():
    """Exempt requests with valid internal API key."""
    api_key = request.headers.get("X-Internal-API-Key")
    expected_key = os.getenv("INTERNAL_API_KEY")
    return api_key and api_key == expected_key
```

### Custom 429 Error Handler with build_error_response()
```python
# Source: Integration pattern combining Flask-Limiter + existing error handlers
# In error_handlers.py

from flask import request
import structlog

logger = structlog.get_logger(__name__)

def handle_rate_limit_exceeded(e):
    """
    Handle Flask-Limiter RateLimitExceeded exceptions (429).

    Integrates with existing build_error_response() for consistent format.
    Flask-Limiter automatically includes Retry-After header.
    """
    logger.warning(
        "rate_limit_exceeded",
        limit=str(e.description),
        client_ip=request.remote_addr,
        endpoint=request.endpoint
    )

    return build_error_response(
        error='Rate limit exceeded',
        message=f'Too many requests. Limit: {e.description}',
        status_code=429,
        error_code='RATE_LIMIT_EXCEEDED'
    )

def register_error_handlers(app):
    """Register all error handlers including rate limiting."""
    # Existing handlers...
    app.register_error_handler(AirbaisAPIException, handle_airbais_exception)
    app.register_error_handler(ValidationError, handle_validation_error)
    app.register_error_handler(400, handle_bad_request)
    app.register_error_handler(404, handle_not_found)
    app.register_error_handler(500, handle_internal_error)

    # NEW: 429 handler for rate limiting
    app.register_error_handler(429, handle_rate_limit_exceeded)

    app.register_error_handler(Exception, handle_unexpected_exception)
    logger.info("error_handlers_registered", handlers=["429", "400", "404", "500"])
```

### Health Check Endpoints with flask-healthz
```python
# Source: https://github.com/fedora-infra/flask-healthz
from flask import Flask
from flask_healthz import healthz, HealthError

app = Flask(__name__)

# Register health check blueprint
app.register_blueprint(healthz, url_prefix="/health")

# Configure check functions (import paths)
app.config.update({
    "HEALTHZ": {
        "live": "automation.health.liveness.check",
        "ready": "automation.health.readiness.check",
    }
})

# Exempt health checks from rate limiting
@limiter.request_filter
def health_check_filter():
    """Exempt health check endpoints from rate limiting."""
    return request.path.startswith("/health")

# -------- automation/health/liveness.py --------
def check():
    """
    Liveness check: Is the process running?

    CRITICAL: Keep this extremely lightweight. No external calls.
    Kubernetes will RESTART the container if this fails.
    """
    # Process is alive if we reach here
    pass


# -------- automation/health/readiness.py --------
import structlog
from flask_healthz import HealthError

logger = structlog.get_logger(__name__)

def check():
    """
    Readiness check: Can we accept traffic?

    Check dependencies but use SHORT timeouts.
    Kubernetes will REMOVE from load balancer if this fails (no restart).
    """
    # Check rate limit storage connection
    try:
        from api_server import limiter
        # Quick ping to storage (1 second timeout)
        limiter.storage.check()
    except Exception as e:
        logger.warning("readiness_check_failed", component="rate_limit_storage", error=str(e))
        raise HealthError("Rate limit storage unavailable")

    # Add other dependency checks (database, external APIs, etc.)
    # Each should have SHORT timeout (1-2 seconds max)
```

### Testing Rate Limits with Pytest
```python
# Source: Testing pattern based on https://woteq.com/how-to-test-rate-limited-endpoints-in-python-using-pytest/
import pytest
from api_server import app

@pytest.fixture
def client():
    """Create test client with rate limiting enabled."""
    app.config['TESTING'] = True
    # Use in-memory storage for tests
    app.config['RATELIMIT_STORAGE_URI'] = 'memory://'
    with app.test_client() as client:
        yield client

def test_rate_limit_enforced(client):
    """Test that exceeding rate limit returns 429."""
    # Assuming /status/<job_id> has limit of "100 per minute"
    # Make 101 requests to exceed limit
    for i in range(100):
        response = client.get('/status/test-job-id')
        assert response.status_code in (200, 404)  # Normal responses

    # 101st request should be rate limited
    response = client.get('/status/test-job-id')
    assert response.status_code == 429

    # Verify response format matches build_error_response()
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == 'Rate limit exceeded'
    assert 'correlation_id' in data
    assert 'timestamp' in data

def test_rate_limit_headers_present(client):
    """Test that rate limit headers are included in responses."""
    response = client.get('/status/test-job-id')

    # Flask-Limiter should add these headers
    assert 'X-RateLimit-Limit' in response.headers
    assert 'X-RateLimit-Remaining' in response.headers
    assert 'X-RateLimit-Reset' in response.headers

def test_health_checks_not_rate_limited(client):
    """Test that health check endpoints are exempt from rate limits."""
    # Make many requests to health endpoint
    for i in range(200):  # Exceeds default limits
        response = client.get('/health/live')
        assert response.status_code == 200  # Never rate limited
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flask-Limiter < 2.0 with decorator-only config | Flask-Limiter 4.x with storage_uri and Limiter() initialization | v2.0 (2020) | Storage backends now configured via URI, not class imports. Simplified configuration. |
| Manual X-Forwarded-For parsing | ProxyFix middleware with x_for parameter | Werkzeug 0.15+ (2019) | Prevents IP spoofing, validates proxy chains, configurable trust levels |
| Single /health endpoint | Separate /health/live and /health/ready | Kubernetes 1.16+ (2019) | Distinguishes "restart container" from "remove from LB", reduces cascading failures |
| limits.strategies.MovingWindowRateLimiter | strategy="moving-window" string config | Flask-Limiter 3.0 (2023) | String-based config instead of class imports, easier to configure |
| Manual health check routes | flask-healthz blueprint | 2020+ | Standardized K8s conventions, error signaling with HealthError, automatic JSON formatting |

**Deprecated/outdated:**
- **Flask-Limiter < 2.0 import patterns:** Old versions required importing storage classes directly. Current version uses storage_uri strings.
- **Single /health endpoint:** Kubernetes best practices now require separate liveness and readiness endpoints since K8s 1.16.
- **get_ipaddr() helper:** Replaced by get_remote_address from flask_limiter.util which handles ProxyFix correctly.

## Open Questions

Things that couldn't be fully resolved:

1. **Redis connection configuration for production**
   - What we know: Flask-Limiter supports redis:// URIs, can pass storage_options for connection pooling
   - What's unclear: Optimal connection pool settings for this workload, whether to use redis-py or redis-py-cluster
   - Recommendation: Start with simple redis://host:port, add connection pooling via storage_options if needed based on monitoring

2. **Rate limit granularity per tool**
   - What we know: Can use @limiter.limit() decorator per endpoint
   - What's unclear: Should different tools have different limits (intentcrawler vs llmevaluator)?
   - Recommendation: Start with uniform limits, monitor usage patterns, adjust per-tool in future phase if needed

3. **Rate limit exemption for authenticated vs unauthenticated**
   - What we know: Can use custom key_func to rate limit by user ID instead of IP
   - What's unclear: Current API doesn't have authentication - future addition?
   - Recommendation: Use IP-based limiting for now, document pattern for user-based limiting if auth is added

4. **Health check dependency verification depth**
   - What we know: Readiness should check dependencies, liveness should not
   - What's unclear: Which dependencies are critical enough to fail readiness? (Redis? Job storage? Tool directories?)
   - Recommendation: Start with Redis-only check, expand based on observed failure modes

## Sources

### Primary (HIGH confidence)
- [Flask-Limiter 4.1.1 Official Documentation](https://flask-limiter.readthedocs.io/) - Complete configuration reference
- [Flask-Limiter Configuration Guide](https://flask-limiter.readthedocs.io/en/stable/configuration.html) - Storage backends, key functions, options
- [Flask-Limiter Recipes](https://flask-limiter.readthedocs.io/en/stable/recipes.html) - IP whitelisting, custom errors, proxy handling
- [flask-healthz GitHub Repository](https://github.com/fedora-infra/flask-healthz) - Liveness/readiness implementation
- [Kubernetes Liveness/Readiness Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) - Official K8s documentation
- [Flask-Limiter PyPI](https://pypi.org/project/Flask-Limiter/) - Latest version (4.1.1) and installation

### Secondary (MEDIUM confidence)
- [Google Cloud: Readiness vs Liveness Probes](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-setting-up-health-checks-with-readiness-and-liveness-probes) - Best practices guide
- [Flask-Limiter GitHub Issues #41](https://github.com/alisaifee/flask-limiter/issues/41) - IP spoofing security discussion
- [Flask-Limiter GitHub Discussion #373](https://github.com/alisaifee/flask-limiter/discussions/373) - Why memory storage fails in production
- [Woteq: Testing Rate-Limited Endpoints](https://woteq.com/how-to-test-rate-limited-endpoints-in-python-using-pytest/) - Pytest patterns

### Tertiary (LOW confidence)
- [Medium: How to Rate Limit Routes in Flask](https://medium.com/analytics-vidhya/how-to-rate-limit-routes-in-flask-61c6c791961b) - Tutorial with examples
- [Prosperasoft: Rate Limiting in Flask API](https://prosperasoft.com/blog/full-stack/rate-limiting-in-flask-api/) - Integration patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Flask-Limiter is official extension, flask-healthz is standard K8s pattern, Redis is industry standard for rate limiting
- Architecture: HIGH - All patterns verified from official documentation and K8s standards
- Pitfalls: HIGH - Documented in official issues, K8s best practices guides, and security advisories

**Research date:** 2026-01-24
**Valid until:** 30+ days (stable ecosystem, Flask-Limiter 4.1.1 released Dec 2025, no major changes expected)
