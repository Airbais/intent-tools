"""
CORS configuration with explicit origin whitelist.

SECURITY: Never use wildcard (*) origins in production.
Configure allowed origins via:
1. CORS_ALLOWED_ORIGINS environment variable (comma-separated)
2. tools_config.yaml cors_origins list
3. Default: localhost only (development safe default)
"""
import os
import logging
from flask_cors import CORS
from typing import List

logger = logging.getLogger(__name__)

# Default origins for development only
DEFAULT_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8050',  # Dash default port
    'http://127.0.0.1:3000',
    'http://127.0.0.1:8050',
]


def get_cors_origins(config: dict = None) -> List[str]:
    """
    Get allowed CORS origins from environment or config.

    Priority:
    1. CORS_ALLOWED_ORIGINS env var (comma-separated)
    2. config['server']['cors_origins'] from tools_config.yaml
    3. DEFAULT_ORIGINS (localhost only)

    Returns:
        List of allowed origin URLs
    """
    # Check environment variable first (highest priority)
    env_origins = os.getenv('CORS_ALLOWED_ORIGINS', '').strip()
    if env_origins:
        origins = [o.strip() for o in env_origins.split(',') if o.strip()]
        logger.info(f"CORS origins from environment: {origins}")
        return origins

    # Check config file
    if config and 'server' in config and 'cors_origins' in config['server']:
        origins = config['server']['cors_origins']
        if origins and isinstance(origins, list):
            logger.info(f"CORS origins from config: {origins}")
            return origins

    # Fall back to defaults (development only)
    logger.warning("Using default CORS origins (localhost only). "
                   "Set CORS_ALLOWED_ORIGINS env var for production.")
    return DEFAULT_ORIGINS


def configure_cors(app, config: dict = None):
    """
    Configure CORS with explicit origin whitelist.

    SECURITY NOTES:
    - Never uses wildcard (*) origins
    - Requires explicit whitelist
    - Credentials require specific origins (not *)

    Args:
        app: Flask application
        config: Optional config dict with server.cors_origins
    """
    origins = get_cors_origins(config)

    # Validate no wildcards
    if '*' in origins:
        logger.error("SECURITY: Wildcard (*) origin detected and removed from CORS config")
        origins = [o for o in origins if o != '*']
        if not origins:
            origins = DEFAULT_ORIGINS

    cors_config = {
        r"/*": {
            "origins": origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Request-ID"],
            "expose_headers": ["X-Request-ID"],
            "supports_credentials": True,
            "max_age": 3600  # Cache preflight for 1 hour
        }
    }

    CORS(app, resources=cors_config)
    logger.info(f"CORS configured with {len(origins)} allowed origin(s)")
