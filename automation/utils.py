"""
Utility functions for Airbais automation API.

Provides timezone-aware datetime utilities to replace naive datetime.now() calls.
"""

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """
    Get current UTC time as ISO 8601 / RFC 3339 string.

    Returns:
        Current UTC time in ISO 8601 format with timezone offset.
        Example: "2026-01-24T12:34:56.789123+00:00"
    """
    return datetime.now(timezone.utc).isoformat()


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime object.

    Returns:
        Current UTC time as datetime object with timezone.utc
    """
    return datetime.now(timezone.utc)
