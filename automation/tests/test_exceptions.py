"""
Tests for custom exception hierarchy.

Verifies that all custom exceptions:
- Have correct error_code attributes
- Have correct status_code attributes
- Inherit from AirbaisAPIException
- Include relevant context in message formatting
- String representation works correctly
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exceptions import (
    AirbaisAPIException,
    ToolNotFoundError,
    ToolExecutionError,
    JobNotFoundError,
    ConfigurationError,
    InvalidParameterError
)


class TestBaseException:
    """Test the base AirbaisAPIException class."""

    def test_base_exception_has_required_attributes(self):
        """Base exception should have error_code, status_code, and message attributes."""
        exc = AirbaisAPIException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=500
        )
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.status_code == 500

    def test_base_exception_default_status_code(self):
        """Base exception should default to 500 status code."""
        exc = AirbaisAPIException(
            message="Test error",
            error_code="TEST_ERROR"
        )
        assert exc.status_code == 500

    def test_base_exception_str_representation(self):
        """Base exception __str__ should return the message."""
        exc = AirbaisAPIException(
            message="Test error message",
            error_code="TEST_ERROR"
        )
        assert str(exc) == "Test error message"

    def test_base_exception_inherits_from_exception(self):
        """Base exception should inherit from Exception."""
        exc = AirbaisAPIException(
            message="Test",
            error_code="TEST"
        )
        assert isinstance(exc, Exception)


class TestToolNotFoundError:
    """Test ToolNotFoundError exception."""

    def test_has_correct_error_code(self):
        """ToolNotFoundError should have error_code 'TOOL_NOT_FOUND'."""
        exc = ToolNotFoundError(tool_name="test_tool")
        assert exc.error_code == "TOOL_NOT_FOUND"

    def test_has_correct_status_code(self):
        """ToolNotFoundError should have status_code 404."""
        exc = ToolNotFoundError(tool_name="test_tool")
        assert exc.status_code == 404

    def test_inherits_from_base_exception(self):
        """ToolNotFoundError should inherit from AirbaisAPIException."""
        exc = ToolNotFoundError(tool_name="test_tool")
        assert isinstance(exc, AirbaisAPIException)

    def test_message_includes_tool_name(self):
        """ToolNotFoundError message should include the tool name."""
        exc = ToolNotFoundError(tool_name="my_tool")
        assert "my_tool" in exc.message
        assert "not found" in exc.message.lower()

    def test_stores_tool_name_attribute(self):
        """ToolNotFoundError should store tool_name as attribute."""
        exc = ToolNotFoundError(tool_name="my_tool")
        assert exc.tool_name == "my_tool"

    def test_str_representation(self):
        """ToolNotFoundError string representation should be readable."""
        exc = ToolNotFoundError(tool_name="my_tool")
        assert str(exc) == "Tool 'my_tool' not found"


class TestToolExecutionError:
    """Test ToolExecutionError exception."""

    def test_has_correct_error_code(self):
        """ToolExecutionError should have error_code 'TOOL_EXECUTION_FAILED'."""
        exc = ToolExecutionError(tool_name="test_tool", details="Test failure")
        assert exc.error_code == "TOOL_EXECUTION_FAILED"

    def test_has_correct_status_code(self):
        """ToolExecutionError should have status_code 500."""
        exc = ToolExecutionError(tool_name="test_tool", details="Test failure")
        assert exc.status_code == 500

    def test_inherits_from_base_exception(self):
        """ToolExecutionError should inherit from AirbaisAPIException."""
        exc = ToolExecutionError(tool_name="test_tool", details="Test failure")
        assert isinstance(exc, AirbaisAPIException)

    def test_message_includes_tool_name_and_details(self):
        """ToolExecutionError message should include tool name and details."""
        exc = ToolExecutionError(tool_name="my_tool", details="Connection timeout")
        assert "my_tool" in exc.message
        assert "Connection timeout" in exc.message
        assert "execution failed" in exc.message.lower()

    def test_stores_tool_name_and_details_attributes(self):
        """ToolExecutionError should store tool_name and details as attributes."""
        exc = ToolExecutionError(tool_name="my_tool", details="Test details")
        assert exc.tool_name == "my_tool"
        assert exc.details == "Test details"

    def test_str_representation(self):
        """ToolExecutionError string representation should be readable."""
        exc = ToolExecutionError(tool_name="my_tool", details="Test error")
        assert str(exc) == "Tool 'my_tool' execution failed: Test error"


class TestJobNotFoundError:
    """Test JobNotFoundError exception."""

    def test_has_correct_error_code(self):
        """JobNotFoundError should have error_code 'JOB_NOT_FOUND'."""
        exc = JobNotFoundError(job_id="test-job-id")
        assert exc.error_code == "JOB_NOT_FOUND"

    def test_has_correct_status_code(self):
        """JobNotFoundError should have status_code 404."""
        exc = JobNotFoundError(job_id="test-job-id")
        assert exc.status_code == 404

    def test_inherits_from_base_exception(self):
        """JobNotFoundError should inherit from AirbaisAPIException."""
        exc = JobNotFoundError(job_id="test-job-id")
        assert isinstance(exc, AirbaisAPIException)

    def test_message_includes_job_id(self):
        """JobNotFoundError message should include the job ID."""
        exc = JobNotFoundError(job_id="job-123")
        assert "job-123" in exc.message
        assert "not found" in exc.message.lower()

    def test_stores_job_id_attribute(self):
        """JobNotFoundError should store job_id as attribute."""
        exc = JobNotFoundError(job_id="job-123")
        assert exc.job_id == "job-123"

    def test_str_representation(self):
        """JobNotFoundError string representation should be readable."""
        exc = JobNotFoundError(job_id="job-123")
        assert str(exc) == "Job 'job-123' not found"


class TestConfigurationError:
    """Test ConfigurationError exception."""

    def test_has_correct_error_code(self):
        """ConfigurationError should have error_code 'CONFIG_ERROR'."""
        exc = ConfigurationError(details="Invalid config")
        assert exc.error_code == "CONFIG_ERROR"

    def test_has_correct_status_code(self):
        """ConfigurationError should have status_code 500."""
        exc = ConfigurationError(details="Invalid config")
        assert exc.status_code == 500

    def test_inherits_from_base_exception(self):
        """ConfigurationError should inherit from AirbaisAPIException."""
        exc = ConfigurationError(details="Invalid config")
        assert isinstance(exc, AirbaisAPIException)

    def test_message_includes_details(self):
        """ConfigurationError message should include the details."""
        exc = ConfigurationError(details="Missing required field")
        assert "Missing required field" in exc.message
        assert "configuration error" in exc.message.lower()

    def test_stores_details_attribute(self):
        """ConfigurationError should store details as attribute."""
        exc = ConfigurationError(details="Test details")
        assert exc.details == "Test details"

    def test_str_representation(self):
        """ConfigurationError string representation should be readable."""
        exc = ConfigurationError(details="Test config error")
        assert str(exc) == "Configuration error: Test config error"


class TestInvalidParameterError:
    """Test InvalidParameterError exception."""

    def test_has_correct_error_code(self):
        """InvalidParameterError should have error_code 'INVALID_PARAMETER'."""
        exc = InvalidParameterError(param_name="test_param", reason="Invalid value")
        assert exc.error_code == "INVALID_PARAMETER"

    def test_has_correct_status_code(self):
        """InvalidParameterError should have status_code 400."""
        exc = InvalidParameterError(param_name="test_param", reason="Invalid value")
        assert exc.status_code == 400

    def test_inherits_from_base_exception(self):
        """InvalidParameterError should inherit from AirbaisAPIException."""
        exc = InvalidParameterError(param_name="test_param", reason="Invalid value")
        assert isinstance(exc, AirbaisAPIException)

    def test_message_includes_param_name_and_reason(self):
        """InvalidParameterError message should include param name and reason."""
        exc = InvalidParameterError(param_name="max_depth", reason="Must be positive")
        assert "max_depth" in exc.message
        assert "Must be positive" in exc.message
        assert "invalid parameter" in exc.message.lower()

    def test_stores_param_name_and_reason_attributes(self):
        """InvalidParameterError should store param_name and reason as attributes."""
        exc = InvalidParameterError(param_name="test_param", reason="Test reason")
        assert exc.param_name == "test_param"
        assert exc.reason == "Test reason"

    def test_str_representation(self):
        """InvalidParameterError string representation should be readable."""
        exc = InvalidParameterError(param_name="test_param", reason="Test reason")
        assert str(exc) == "Invalid parameter 'test_param': Test reason"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
