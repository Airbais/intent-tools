"""
Tests for structured error responses.

Verifies that build_error_response() and error handlers:
- Include all required fields (error, message, timestamp, correlation_id)
- Include optional fields when provided (error_code, details)
- Return correct HTTP status codes
- Use UTC-aware timestamps in RFC 3339 format
- Have fallback for correlation_id (never None)
"""

import pytest
import json
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_server import app
from error_handlers import build_error_response, handle_airbais_exception
from exceptions import (
    AirbaisAPIException,
    ToolNotFoundError,
    ToolExecutionError,
    JobNotFoundError,
    ConfigurationError,
    InvalidParameterError
)
from utils import utc_now_iso


@pytest.fixture
def app_context():
    """Create Flask app context for testing."""
    with app.app_context():
        yield app


@pytest.fixture
def client():
    """Create test client with Flask test mode enabled."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestBuildErrorResponse:
    """Test the build_error_response() function."""

    def test_includes_required_fields(self, app_context):
        """build_error_response should include error, message, timestamp, correlation_id."""
        response, status_code = build_error_response(
            error="Test Error",
            message="Test message"
        )
        data = json.loads(response.data)

        assert 'error' in data
        assert 'message' in data
        assert 'timestamp' in data
        assert 'correlation_id' in data

    def test_error_field_matches_input(self, app_context):
        """Error field should match the provided error parameter."""
        response, status_code = build_error_response(
            error="NotFoundError",
            message="Resource not found"
        )
        data = json.loads(response.data)
        assert data['error'] == "NotFoundError"

    def test_message_field_matches_input(self, app_context):
        """Message field should match the provided message parameter."""
        response, status_code = build_error_response(
            error="Test Error",
            message="Custom error message"
        )
        data = json.loads(response.data)
        assert data['message'] == "Custom error message"

    def test_default_status_code_is_500(self, app_context):
        """Default status code should be 500."""
        response, status_code = build_error_response(
            error="Test Error",
            message="Test message"
        )
        assert status_code == 500

    def test_custom_status_code(self, app_context):
        """Custom status code should be returned."""
        response, status_code = build_error_response(
            error="Not Found",
            message="Resource not found",
            status_code=404
        )
        assert status_code == 404

    def test_error_code_included_when_provided(self, app_context):
        """Error code should be included when provided."""
        response, status_code = build_error_response(
            error="Test Error",
            message="Test message",
            error_code="TEST_ERROR_CODE"
        )
        data = json.loads(response.data)
        assert 'error_code' in data
        assert data['error_code'] == "TEST_ERROR_CODE"

    def test_error_code_not_included_when_none(self, app_context):
        """Error code should not be included when None."""
        response, status_code = build_error_response(
            error="Test Error",
            message="Test message",
            error_code=None
        )
        data = json.loads(response.data)
        assert 'error_code' not in data

    def test_details_included_when_provided(self, app_context):
        """Details dict should be included when provided."""
        details = {"field": "value", "count": 42}
        response, status_code = build_error_response(
            error="Test Error",
            message="Test message",
            details=details
        )
        data = json.loads(response.data)
        assert 'details' in data
        assert data['details'] == details

    def test_details_not_included_when_none(self, app_context):
        """Details should not be included when None."""
        response, status_code = build_error_response(
            error="Test Error",
            message="Test message",
            details=None
        )
        data = json.loads(response.data)
        assert 'details' not in data

    def test_timestamp_is_utc_aware(self, app_context):
        """Timestamp should be UTC-aware with +00:00 timezone."""
        response, status_code = build_error_response(
            error="Test Error",
            message="Test message"
        )
        data = json.loads(response.data)

        timestamp = data['timestamp']
        # RFC 3339 compliant timestamp should end with +00:00 or Z
        assert timestamp.endswith('+00:00') or timestamp.endswith('Z')

        # Should be parseable as ISO 8601
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert dt.tzinfo is not None

    def test_correlation_id_has_fallback(self, app_context):
        """Correlation ID should never be None (has fallback)."""
        response, status_code = build_error_response(
            error="Test Error",
            message="Test message"
        )
        data = json.loads(response.data)

        assert data['correlation_id'] is not None
        # When no correlation ID in context, should be 'none'
        assert data['correlation_id'] == 'none'


class TestUtcNowIso:
    """Test the utc_now_iso() utility function."""

    def test_returns_rfc_3339_compliant_timestamp(self):
        """utc_now_iso() should return RFC 3339 compliant timestamp."""
        timestamp = utc_now_iso()

        # Should contain timezone offset
        assert '+00:00' in timestamp or timestamp.endswith('Z')

        # Should be parseable as ISO 8601
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert dt.tzinfo is not None

    def test_timestamp_is_utc(self):
        """Timestamp should be in UTC timezone."""
        timestamp = utc_now_iso()
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        # Should be UTC (offset should be 0)
        assert dt.tzinfo == timezone.utc or dt.utcoffset().total_seconds() == 0

    def test_timestamp_includes_microseconds(self):
        """Timestamp should include microseconds for precision."""
        timestamp = utc_now_iso()
        # RFC 3339 with microseconds: 2026-01-24T12:34:56.123456+00:00
        assert '.' in timestamp  # Decimal point for fractional seconds


class TestCustomExceptionHandler:
    """Test the handle_airbais_exception error handler."""

    def test_returns_correct_status_code_for_404_exceptions(self, app_context):
        """404 exceptions should return status code 404."""
        exc = ToolNotFoundError(tool_name="test_tool")
        response, status_code = handle_airbais_exception(exc)

        assert status_code == 404

    def test_returns_correct_status_code_for_500_exceptions(self, app_context):
        """500 exceptions should return status code 500."""
        exc = ToolExecutionError(tool_name="test_tool", details="Failed")
        response, status_code = handle_airbais_exception(exc)

        assert status_code == 500

    def test_returns_correct_status_code_for_400_exceptions(self, app_context):
        """400 exceptions should return status code 400."""
        exc = InvalidParameterError(param_name="test_param", reason="Invalid")
        response, status_code = handle_airbais_exception(exc)

        assert status_code == 400

    def test_includes_error_code_in_response(self, app_context):
        """Response should include error_code from exception."""
        exc = ToolNotFoundError(tool_name="test_tool")
        response, status_code = handle_airbais_exception(exc)

        data = json.loads(response.data)
        assert 'error_code' in data
        assert data['error_code'] == "TOOL_NOT_FOUND"

    def test_includes_message_in_response(self, app_context):
        """Response should include message from exception."""
        exc = ToolExecutionError(tool_name="my_tool", details="Connection failed")
        response, status_code = handle_airbais_exception(exc)

        data = json.loads(response.data)
        assert 'message' in data
        assert "my_tool" in data['message']
        assert "Connection failed" in data['message']

    def test_includes_exception_class_name_as_error(self, app_context):
        """Response error field should be exception class name."""
        exc = ConfigurationError(details="Test error")
        response, status_code = handle_airbais_exception(exc)

        data = json.loads(response.data)
        assert data['error'] == "ConfigurationError"


class TestErrorResponseIntegration:
    """Integration tests for error responses via API endpoints."""

    def test_tool_not_found_returns_404_with_error_code(self, client):
        """Unknown tool should return 404 with TOOL_NOT_FOUND error code."""
        response = client.post(
            '/nonexistent_tool/analyze',
            json={'url': 'https://example.com'},
            content_type='application/json'
        )

        assert response.status_code == 404
        data = json.loads(response.data)

        # Should have standard error response structure
        assert 'error' in data
        assert 'message' in data
        assert 'timestamp' in data
        assert 'correlation_id' in data

        # Should have error code
        assert 'error_code' in data

    def test_error_response_has_utc_timestamp(self, client):
        """Error responses should include UTC timestamp."""
        response = client.get('/nonexistent-endpoint')

        assert response.status_code == 404
        data = json.loads(response.data)

        assert 'timestamp' in data
        timestamp = data['timestamp']

        # Should be RFC 3339 compliant
        assert '+00:00' in timestamp or timestamp.endswith('Z')

    def test_error_response_has_correlation_id(self, client):
        """Error responses should include correlation_id."""
        response = client.get('/nonexistent-endpoint')

        assert response.status_code == 404
        data = json.loads(response.data)

        assert 'correlation_id' in data
        assert data['correlation_id'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
