"""
Correlation ID middleware for request tracking.

Generates or extracts correlation IDs for each request and binds them
to structlog's context variables for automatic inclusion in all logs.

Usage:
    from log_config.correlation import configure_correlation
    configure_correlation(app)

All subsequent logs within a request will include the correlation_id.
"""
import uuid
import structlog
from flask import Flask, request, g

# Standard header name for correlation ID
CORRELATION_HEADER = "X-Correlation-ID"


def bind_correlation_id():
    """
    Generate or extract correlation ID and bind to structlog context.
    """
    structlog.contextvars.clear_contextvars()
    correlation_id = request.headers.get(CORRELATION_HEADER)
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        http_method=request.method,
        http_path=request.path,
        remote_addr=request.remote_addr,
    )
    g.correlation_id = correlation_id


def add_correlation_header(response):
    """Add correlation ID to response headers."""
    if hasattr(g, 'correlation_id'):
        response.headers[CORRELATION_HEADER] = g.correlation_id
    return response


def configure_correlation(app: Flask):
    """Configure correlation ID middleware for Flask application."""
    app.before_request(bind_correlation_id)
    app.after_request(add_correlation_header)


def get_correlation_id() -> str:
    """Get the current request's correlation ID."""
    return getattr(g, 'correlation_id', '')
