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

from log_config.correlation import get_correlation_id
from utils import utc_now_iso
from exceptions import AirbaisAPIException

logger = structlog.get_logger(__name__)


def build_error_response(
    error: str,
    message: str,
    status_code: int = 500,
    error_code: str = None,
    details: dict = None
) -> tuple:
    """
    Build a structured error response with correlation_id and timestamp.

    Args:
        error: Error type string (e.g., 'Not Found', 'ValidationError')
        message: Human-readable error message
        status_code: HTTP status code (default: 500)
        error_code: Machine-readable error code (optional)
        details: Additional error details (optional)

    Returns:
        Tuple of (jsonify response, status_code)
    """
    response = {
        'error': error,
        'message': message,
        'timestamp': utc_now_iso(),
        'correlation_id': get_correlation_id() or 'none',
    }

    if error_code is not None:
        response['error_code'] = error_code

    if details is not None:
        response['details'] = details

    return jsonify(response), status_code


def handle_airbais_exception(e: AirbaisAPIException):
    """
    Handle custom Airbais API exceptions.

    Logs the exception with full context and returns a structured error
    response using the exception's error_code and status_code.

    Args:
        e: AirbaisAPIException or subclass

    Returns:
        Tuple of (jsonify response, status_code)
    """
    logger.error(
        "airbais_api_error",
        error_code=e.error_code,
        status_code=e.status_code,
        error=str(e),
        exc_info=True
    )
    return build_error_response(
        error=type(e).__name__,
        message=e.message,
        status_code=e.status_code,
        error_code=e.error_code
    )


def handle_validation_error(e: ValidationError):
    """
    Handle Pydantic validation errors (400).

    Pydantic v2 errors contain field names and validation messages but no
    internal file paths, making them safe to expose to clients.
    """
    logger.warning("validation_error", errors=e.errors())
    return build_error_response(
        error='Invalid request parameters',
        message='Request validation failed',
        status_code=400,
        error_code='VALIDATION_ERROR',
        details=e.errors()
    )


def handle_bad_request(e):
    """
    Handle generic 400 Bad Request errors.

    Returns structured error with safe description if available.
    """
    message = 'Invalid request'
    if hasattr(e, 'description') and e.description:
        message = str(e.description)
    logger.warning("bad_request", message=message)
    return build_error_response(
        error='Bad request',
        message=message,
        status_code=400,
        error_code='BAD_REQUEST'
    )


def handle_not_found(e):
    """
    Handle 404 Not Found errors.

    No logging needed - 404s are expected behavior (e.g., unknown endpoints).
    """
    return build_error_response(
        error='Not found',
        message='The requested resource does not exist',
        status_code=404,
        error_code='NOT_FOUND'
    )


def handle_internal_error(e):
    """
    Handle 500 Internal Server Error.

    CRITICAL: Full exception details (including traceback) are logged via
    exc_info=True, but the client receives only a generic error message.
    This prevents leaking sensitive information like file paths, database
    queries, configuration values, etc.
    """
    logger.error("internal_server_error", error=str(e), exc_info=True)
    return build_error_response(
        error='Internal server error',
        message='An unexpected error occurred. Please try again later.',
        status_code=500,
        error_code='INTERNAL_ERROR'
    )


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
    return build_error_response(
        error='Internal server error',
        message='An unexpected error occurred',
        status_code=500,
        error_code='UNEXPECTED_ERROR'
    )


def register_error_handlers(app):
    """
    Register all error handlers with the Flask application.

    Handler order matters: specific handlers (ValidationError, AirbaisAPIException)
    are checked before generic ones (Exception). Flask processes them in registration order.

    Args:
        app: Flask application instance
    """
    app.register_error_handler(AirbaisAPIException, handle_airbais_exception)
    app.register_error_handler(ValidationError, handle_validation_error)
    app.register_error_handler(400, handle_bad_request)
    app.register_error_handler(404, handle_not_found)
    app.register_error_handler(500, handle_internal_error)
    app.register_error_handler(Exception, handle_unexpected_exception)
    logger.info("error_handlers_registered")
