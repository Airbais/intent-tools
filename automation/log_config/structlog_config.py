"""
Structlog configuration for Airbais Tools API.

Provides:
- JSON output in production (for ELK/CloudWatch ingestion)
- Pretty console output in development
- Automatic timestamp and log level injection
- Exception traceback formatting
- Integration with standard library logging
"""
import sys
import logging
import structlog


def configure_structlog(debug: bool = False):
    """
    Configure structlog for the application.

    Must be called BEFORE any logging occurs, typically at application startup.

    Args:
        debug: If True or stderr is a tty, use console renderer.
               If False and stderr is not a tty, use JSON renderer.

    Environment detection:
    - Development (terminal): Pretty, colored console output
    - Production (container/service): JSON for log aggregators
    """
    # Shared processors for all environments
    shared_processors = [
        # Inject bound context variables (correlation_id, job_id, etc.)
        structlog.contextvars.merge_contextvars,
        # Add log level as 'level' field
        structlog.stdlib.add_log_level,
        # Add logger name as 'logger' field
        structlog.stdlib.add_logger_name,
        # Add ISO timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Format positional args
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Render stack info if present
        structlog.processors.StackInfoRenderer(),
        # Decode bytes to string
        structlog.processors.UnicodeDecoder(),
    ]

    # Environment-specific output format
    if debug or sys.stderr.isatty():
        # Development: pretty console output with colors
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output for log aggregators
        processors = shared_processors + [
            # Format exception tracebacks as structured data
            structlog.processors.dict_tracebacks,
            # Render final output as JSON
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to output through structlog
    # This ensures any code using logging.getLogger() also gets structured output
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stderr)],
        force=True,  # Override any existing config
    )


def get_logger(name: str = None):
    """
    Get a structlog logger instance.

    Use this instead of logging.getLogger() for structured logging.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Bound structlog logger
    """
    return structlog.get_logger(name)
