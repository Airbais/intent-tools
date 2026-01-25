# Phase 3 Research: Structured Logging

## Overview

This research documents the technical approach for implementing structured JSON logging with correlation IDs and audit trails for the Airbais Tools API.

## Current State Analysis

### Existing Logging Implementation

**api_server.py (lines 29-34):**
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

**Issues with current implementation:**
1. Plain text format - not machine-parseable
2. No correlation IDs - cannot trace requests through operations
3. No structured context - fields not extractable
4. No request/response logging middleware
5. Tool executions not logged with job context

**Files using logging:**
- `automation/api_server.py` - main API server
- `automation/error_handlers.py` - error logging with exc_info
- `automation/security/cors_config.py` - CORS configuration logging
- `automation/security/talisman_config.py` - security header logging
- `automation/security/subprocess_validator.py` - validation logging

## Recommended Approach: structlog

### Why structlog?

1. **Native JSON output** - No custom formatters needed
2. **Context variables** - Built-in correlation ID propagation via `contextvars`
3. **Processor pipeline** - Flexible, composable log transformations
4. **Flask integration** - Signal-based request context binding
5. **Standard library compatible** - Works alongside existing `logging` module
6. **Production-ready** - Used by major companies for observability

### Library Version

```
structlog>=24.1.0
```

**Confidence:** HIGH - Well-documented, stable API, active maintenance

## Technical Implementation

### 1. Structlog Configuration Module

Create `automation/logging/structlog_config.py`:

```python
"""
Structlog configuration for Airbais Tools API.

Provides:
- JSON output in production, pretty console in development
- Automatic timestamp and log level injection
- Exception traceback formatting
- Integration with standard library logging
"""
import sys
import logging
import structlog
from structlog.contextvars import merge_contextvars

def configure_structlog(debug: bool = False):
    """
    Configure structlog for the application.

    Args:
        debug: If True, use console renderer; if False, use JSON renderer
    """
    # Shared processors for all environments
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # Inject correlation_id, etc.
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if debug or sys.stderr.isatty():
        # Development: pretty console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output for log aggregators
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )
```

### 2. Correlation ID Middleware

Create `automation/logging/correlation.py`:

```python
"""
Correlation ID middleware for request tracking.

Generates or extracts correlation IDs for each request and binds them
to structlog's context variables for automatic inclusion in all logs.
"""
import uuid
import structlog
from flask import Flask, request, g
from functools import wraps

CORRELATION_HEADER = "X-Correlation-ID"

def bind_correlation_id():
    """
    Generate or extract correlation ID and bind to context.

    Called at the start of each request. The correlation ID:
    1. Is extracted from X-Correlation-ID header if present
    2. Or generated as a new UUID
    3. Is bound to structlog context for all subsequent logs
    4. Is stored in Flask's g object for response header
    """
    # Clear previous request's context
    structlog.contextvars.clear_contextvars()

    # Get or generate correlation ID
    correlation_id = request.headers.get(CORRELATION_HEADER)
    if not correlation_id:
        correlation_id = str(uuid.uuid4())

    # Bind to context for all logs in this request
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        method=request.method,
        path=request.path,
        remote_addr=request.remote_addr,
    )

    # Store for response header
    g.correlation_id = correlation_id

def add_correlation_header(response):
    """Add correlation ID to response headers."""
    if hasattr(g, 'correlation_id'):
        response.headers[CORRELATION_HEADER] = g.correlation_id
    return response

def configure_correlation(app: Flask):
    """
    Configure correlation ID middleware for Flask app.

    Args:
        app: Flask application instance
    """
    app.before_request(bind_correlation_id)
    app.after_request(add_correlation_header)
```

### 3. Request/Response Logging Middleware

Create `automation/logging/request_logger.py`:

```python
"""
Request/response logging middleware.

Logs API requests and responses with timing information.
Excludes sensitive data (auth tokens, passwords, etc.).
"""
import time
import structlog
from flask import Flask, request, g

logger = structlog.get_logger(__name__)

# Fields to redact from request logs
SENSITIVE_FIELDS = {'password', 'token', 'api_key', 'secret', 'authorization'}

def redact_sensitive(data: dict) -> dict:
    """Redact sensitive fields from request data."""
    if not isinstance(data, dict):
        return data
    return {
        k: '[REDACTED]' if k.lower() in SENSITIVE_FIELDS else v
        for k, v in data.items()
    }

def log_request():
    """Log incoming request details."""
    g.request_start_time = time.time()

    # Log request (body logged only for non-sensitive endpoints)
    logger.info(
        "api_request_started",
        endpoint=request.endpoint,
        content_type=request.content_type,
        content_length=request.content_length,
    )

def log_response(response):
    """Log response details with timing."""
    duration_ms = (time.time() - g.request_start_time) * 1000

    logger.info(
        "api_request_completed",
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
        content_length=response.content_length,
    )

    return response

def configure_request_logging(app: Flask):
    """Configure request/response logging middleware."""
    app.before_request(log_request)
    app.after_request(log_response)
```

### 4. Tool Execution Logging

Update `run_tool_async` to log with job context:

```python
def run_tool_async(job_id, tool_name, params):
    """Run tool in background thread with structured logging."""
    # Bind job context for all logs in this execution
    structlog.contextvars.bind_contextvars(
        job_id=job_id,
        tool_name=tool_name,
    )

    logger = structlog.get_logger(__name__)

    try:
        logger.info("tool_execution_started", params=redact_sensitive(params))
        update_job(job_id, {'status': 'running'})

        # ... existing execution logic ...

        logger.info(
            "tool_execution_completed",
            results_dir=results_dir,
            duration_seconds=duration,
        )

    except Exception as e:
        logger.error(
            "tool_execution_failed",
            error=str(e),
            exc_info=True,
        )
```

### 5. Propagating Correlation IDs to Subprocesses

For tool executions via subprocess, pass correlation ID as environment variable:

```python
# In run_tool_async
env = os.environ.copy()
env['CORRELATION_ID'] = structlog.contextvars.get_contextvars().get('correlation_id', '')

process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=tool_dir,
    env=env  # Pass correlation ID
)
```

Tools can read this from environment and include in their logs.

## Output Format

### JSON Log Structure (Production)

```json
{
  "timestamp": "2026-01-23T12:34:56.789Z",
  "level": "info",
  "logger": "automation.api_server",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/intentcrawler/analyze",
  "event": "api_request_completed",
  "status_code": 202,
  "duration_ms": 45.23
}
```

### Console Log Structure (Development)

```
2026-01-23 12:34:56 [info     ] api_request_completed  correlation_id=550e8400-e29b-41d4-a716-446655440000 duration_ms=45.23 method=POST path=/intentcrawler/analyze status_code=202
```

## Integration Points

### API Server Integration Order

```python
app = Flask(__name__)

# 1. Configure structlog FIRST (before any logging)
configure_structlog(debug=app.debug)

# 2. Error handlers (use structlog for logging)
register_error_handlers(app)

# 3. Correlation ID middleware (for all requests)
configure_correlation(app)

# 4. Request/response logging (after correlation ID bound)
configure_request_logging(app)

# 5. Security middleware (CORS, Talisman)
configure_cors(app, config)
configure_talisman(app)
```

### Updating Existing Loggers

All existing `logger = logging.getLogger(__name__)` calls should be replaced with:
```python
logger = structlog.get_logger(__name__)
```

Log calls change from:
```python
logger.info(f"Created job {job_id} for tool {tool_name}")
```

To:
```python
logger.info("job_created", job_id=job_id, tool_name=tool_name)
```

## Plan Breakdown

### Plan 03-01: Configure structlog and create logging module
- Add structlog to requirements.txt
- Create `automation/logging/__init__.py`
- Create `automation/logging/structlog_config.py`
- Configure for development/production modes
- Tests: Verify JSON/console output modes

### Plan 03-02: Implement correlation ID middleware
- Create `automation/logging/correlation.py`
- Integrate with Flask before/after request hooks
- Add X-Correlation-ID header handling
- Tests: Verify correlation ID propagation

### Plan 03-03: Add request/response logging middleware
- Create `automation/logging/request_logger.py`
- Log request method, path, status, duration
- Redact sensitive fields
- Tests: Verify request/response logging

### Plan 03-04: Update tool execution logging
- Update `run_tool_async` with structured logging
- Add job_id context binding
- Pass correlation ID to subprocesses via environment
- Tests: Verify job execution logs

### Plan 03-05: Migrate existing loggers to structlog
- Update api_server.py logger calls
- Update error_handlers.py to use structlog
- Update security modules to use structlog
- Tests: Verify all log output is structured

## Dependencies

**New packages:**
- `structlog>=24.1.0`

**Existing packages (compatible):**
- `flask==3.0.0` - signal system for request hooks
- No conflicts with existing dependencies

## ELK/CloudWatch Compatibility

The JSON output format is directly compatible with:
- **Elasticsearch/Logstash** - Filebeat can ingest JSON logs directly
- **AWS CloudWatch** - Structured JSON recognized automatically
- **Datadog** - JSON logs parsed without custom rules
- **Grafana Loki** - JSON fields extractable for queries

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| structlog configuration | HIGH | Well-documented, stable API |
| Flask integration | HIGH | Official documentation pattern |
| Correlation ID propagation | HIGH | Built-in contextvars support |
| Subprocess correlation | MEDIUM | Environment variable approach is standard but requires tool cooperation |
| Request/response logging | HIGH | Standard middleware pattern |

## Sources

- [Better Stack: Guide to Python Logging with Structlog](https://betterstack.com/community/guides/logging/structlog/)
- [Structlog Frameworks Documentation](https://www.structlog.org/en/stable/frameworks.html)
- [Structlog Logging Best Practices](https://www.structlog.org/en/stable/logging-best-practices.html)
- [Dash0: Leveling Up Python Logs with Structlog](https://www.dash0.com/guides/python-logging-with-structlog)
- [Uptrace: Structured Logging Best Practices](https://uptrace.dev/glossary/structured-logging)
