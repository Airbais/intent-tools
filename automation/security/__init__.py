"""Security configuration modules for Airbais API."""
from .cors_config import configure_cors, get_cors_origins

__all__ = ['configure_cors', 'get_cors_origins']
