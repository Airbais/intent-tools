"""
Pydantic request validation models for API endpoints.

These models enforce type safety, format validation, and constraint
checking for all incoming API requests, preventing malformed input
from reaching the processing layer.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class AnalyzeRequest(BaseModel):
    """
    Request model for /<tool_name>/analyze POST endpoint.

    Validates all parameters accepted by the tool analysis endpoints,
    ensuring proper types, formats, and constraints before execution.
    """

    model_config = ConfigDict(extra='forbid')

    # Core parameters
    url: Optional[str] = None
    config: Optional[str] = Field(default=None, description="Path to config file")

    # Output parameters
    output: Optional[str] = Field(default=None, description="Output directory")
    output_dir: Optional[str] = Field(default=None, description="Output directory (alias for geoevaluator/llmevaluator)")

    # Logging parameters
    log_level: Optional[str] = Field(
        default=None,
        pattern=r"^(DEBUG|INFO|WARNING|ERROR)$",
        description="Logging level"
    )
    verbose: Optional[bool] = Field(default=False, description="Enable verbose output")

    # Caching parameters
    no_cache: Optional[bool] = Field(default=False, description="Disable caching")
    clear_cache: Optional[bool] = Field(default=False, description="Clear cache before execution")

    # Execution parameters
    dry_run: Optional[bool] = Field(default=False, description="Perform dry run without actual execution")
    dashboard: Optional[bool] = Field(default=False, description="Generate dashboard-compatible output")

    # Crawling parameters
    max_pages: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of pages to crawl"
    )
    crawl_depth: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Maximum depth for recursive crawling"
    )
    delay: Optional[float] = Field(
        default=None,
        ge=0,
        le=60,
        description="Delay between requests in seconds"
    )
    timeout: Optional[int] = Field(
        default=None,
        ge=1,
        le=3600,
        description="Request timeout in seconds"
    )

    # Tool-specific parameters
    rules_file: Optional[str] = Field(default=None, description="Path to rules file (rulesevaluator)")
    content_source: Optional[str] = Field(default=None, description="Content source for evaluation (rulesevaluator)")
    name: Optional[str] = Field(default=None, max_length=200, description="Name for analysis (geoevaluator)")
    formats: Optional[str] = Field(default=None, description="Output formats (geoevaluator)")

    @field_validator('url')
    @classmethod
    def validate_url_format(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate that URL starts with http:// or https://.

        This prevents relative paths, file:// URIs, and other potentially
        unsafe URL schemes from being processed.
        """
        if v is not None and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class JobIdPath(BaseModel):
    """
    Path parameter validation for job_id in /status/<job_id> and /results/<job_id>.

    Ensures job_id follows UUID format to prevent injection attacks
    and invalid lookups.
    """

    model_config = ConfigDict(extra='forbid')

    job_id: str = Field(
        pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
        description="UUID format job identifier"
    )
