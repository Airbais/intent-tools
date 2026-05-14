"""
Custom exception hierarchy for Airbais API.

Provides semantic exception types that carry error codes and HTTP status codes
for consistent error handling across the automation API.
"""


class AirbaisAPIException(Exception):
    """
    Base exception for all Airbais API errors.

    All custom exceptions inherit from this class and include:
    - error_code: Machine-readable error identifier
    - status_code: HTTP status code for API responses
    - message: Human-readable error description
    """

    def __init__(self, message: str, error_code: str, status_code: int = 500):
        """
        Initialize the exception.

        Args:
            message: Human-readable error description
            error_code: Machine-readable error identifier (e.g., 'TOOL_NOT_FOUND')
            status_code: HTTP status code (default: 500)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

    def __str__(self) -> str:
        """Return the error message."""
        return self.message


class ToolNotFoundError(AirbaisAPIException):
    """
    Raised when a requested tool is not found in the configuration.

    HTTP Status: 404
    Error Code: TOOL_NOT_FOUND
    """

    def __init__(self, tool_name: str):
        """
        Initialize the exception.

        Args:
            tool_name: Name of the tool that was not found
        """
        self.tool_name = tool_name
        super().__init__(
            message=f"Tool '{tool_name}' not found",
            error_code="TOOL_NOT_FOUND",
            status_code=404
        )


class ToolExecutionError(AirbaisAPIException):
    """
    Raised when a tool execution fails.

    HTTP Status: 500
    Error Code: TOOL_EXECUTION_FAILED
    """

    def __init__(self, tool_name: str, details: str):
        """
        Initialize the exception.

        Args:
            tool_name: Name of the tool that failed
            details: Detailed error information
        """
        self.tool_name = tool_name
        self.details = details
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {details}",
            error_code="TOOL_EXECUTION_FAILED",
            status_code=500
        )


class JobNotFoundError(AirbaisAPIException):
    """
    Raised when a requested job ID is not found.

    HTTP Status: 404
    Error Code: JOB_NOT_FOUND
    """

    def __init__(self, job_id: str):
        """
        Initialize the exception.

        Args:
            job_id: ID of the job that was not found
        """
        self.job_id = job_id
        super().__init__(
            message=f"Job '{job_id}' not found",
            error_code="JOB_NOT_FOUND",
            status_code=404
        )


class ConfigurationError(AirbaisAPIException):
    """
    Raised when there is a configuration error.

    HTTP Status: 500
    Error Code: CONFIG_ERROR
    """

    def __init__(self, details: str):
        """
        Initialize the exception.

        Args:
            details: Detailed configuration error information
        """
        self.details = details
        super().__init__(
            message=f"Configuration error: {details}",
            error_code="CONFIG_ERROR",
            status_code=500
        )


class InvalidParameterError(AirbaisAPIException):
    """
    Raised when an invalid parameter is provided.

    HTTP Status: 400
    Error Code: INVALID_PARAMETER
    """

    def __init__(self, param_name: str, reason: str):
        """
        Initialize the exception.

        Args:
            param_name: Name of the invalid parameter
            reason: Reason why the parameter is invalid
        """
        self.param_name = param_name
        self.reason = reason
        super().__init__(
            message=f"Invalid parameter '{param_name}': {reason}",
            error_code="INVALID_PARAMETER",
            status_code=400
        )
