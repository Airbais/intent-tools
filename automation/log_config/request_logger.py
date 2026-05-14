"""
Request/response logging middleware.

Logs API requests and responses with timing information.
Automatically redacts sensitive data (passwords, tokens, etc.).
"""
import time
import structlog
from flask import Flask, request, g

logger = structlog.get_logger(__name__)

SENSITIVE_FIELDS = {
    'password', 'passwd', 'pwd',
    'token', 'access_token', 'refresh_token',
    'api_key', 'apikey', 'api-key',
    'secret', 'secret_key',
    'authorization', 'auth',
    'credential', 'credentials',
    'private_key', 'privatekey',
}


def redact_sensitive(data: dict) -> dict:
    """Redact sensitive fields from a dictionary."""
    if not isinstance(data, dict):
        return data
    return {
        k: '[REDACTED]' if k.lower() in SENSITIVE_FIELDS else (
            redact_sensitive(v) if isinstance(v, dict) else v
        )
        for k, v in data.items()
    }


def log_request_start():
    """Log incoming request details."""
    g.request_start_time = time.time()
    logger.info(
        "api_request_started",
        method=request.method,
        path=request.path,
        endpoint=request.endpoint,
        content_type=request.content_type,
        content_length=request.content_length,
        query_params=redact_sensitive(dict(request.args)) if request.args else None,
    )


def log_request_end(response):
    """Log response details with timing."""
    duration_ms = 0
    if hasattr(g, 'request_start_time'):
        duration_ms = (time.time() - g.request_start_time) * 1000
    logger.info(
        "api_request_completed",
        method=request.method,
        path=request.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
        content_length=response.content_length,
    )
    return response


def configure_request_logging(app: Flask):
    """Configure request/response logging middleware."""
    app.before_request(log_request_start)
    app.after_request(log_request_end)
