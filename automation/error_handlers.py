"""
Error handlers for the Airbais Tools API server.

This module provides sanitized error responses that hide internal implementation
details (stack traces, file paths, SQL queries, etc.) from API clients while
preserving full debugging information in server logs.

Security objectives:
- 500 errors return generic messages without exposing system internals
- 400 errors provide structured validation feedback without leaking paths
- All exceptions are logged with full traceback (exc_info=True) before sanitizing response
"""

import structlog
from flask import jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

logger = structlog.get_logger(__name__)


def handle_validation_error(e: ValidationError):
    """
    Handle Pydantic validation errors (400).

    Pydantic v2 errors contain field names and validation messages but no
    internal file paths, making them safe to expose to clients.
    """
    logger.warning("validation_error", errors=e.errors())
    return jsonify({
        'error': 'Invalid request parameters',
        'details': e.errors()
    }), 400


def handle_bad_request(e):
    """
    Handle generic 400 Bad Request errors.

    Returns structured error with safe description if available.
    """
    message = 'Invalid request'
    if hasattr(e, 'description') and e.description:
        message = str(e.description)
    logger.warning("bad_request", message=message)
    return jsonify({
        'error': 'Bad request',
        'message': message
    }), 400


def handle_not_found(e):
    """
    Handle 404 Not Found errors.

    No logging needed - 404s are expected behavior (e.g., unknown endpoints).
    """
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource does not exist'
    }), 404


def handle_internal_error(e):
    """
    Handle 500 Internal Server Error.

    CRITICAL: Full exception details (including traceback) are logged via
    exc_info=True, but the client receives only a generic error message.
    This prevents leaking sensitive information like file paths, database
    queries, configuration values, etc.
    """
    logger.error("internal_server_error", error=str(e), exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again later.'
    }), 500


def handle_unexpected_exception(e):
    """
    Handle any unhandled exceptions (catch-all).

    Logs at CRITICAL level since unhandled exceptions indicate bugs or
    unexpected conditions. Full traceback logged via exc_info=True.
    """
    logger.critical(
        "unhandled_exception",
        error_type=type(e).__name__,
        error=str(e),
        exc_info=True,
    )
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


def register_error_handlers(app):
    """
    Register all error handlers with the Flask application.

    Handler order matters: specific handlers (ValidationError) are checked
    before generic ones (Exception). Flask processes them in registration order.

    Args:
        app: Flask application instance
    """
    app.register_error_handler(ValidationError, handle_validation_error)
    app.register_error_handler(400, handle_bad_request)
    app.register_error_handler(404, handle_not_found)
    app.register_error_handler(500, handle_internal_error)
    app.register_error_handler(Exception, handle_unexpected_exception)
    logger.info("error_handlers_registered")
