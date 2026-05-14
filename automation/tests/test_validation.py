"""
Unit tests for Pydantic request validation models.

Tests ensure that malformed input is properly rejected before
reaching the processing layer.
"""

import pytest
from pydantic import ValidationError
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from validation.request_models import AnalyzeRequest, JobIdPath


class TestAnalyzeRequestValidation:
    """Test suite for AnalyzeRequest model validation."""

    def test_analyze_request_valid_url(self):
        """Test that valid URLs are accepted."""
        request = AnalyzeRequest(url="https://example.com")
        assert request.url == "https://example.com"

        request = AnalyzeRequest(url="http://example.com")
        assert request.url == "http://example.com"

    def test_analyze_request_invalid_url(self):
        """Test that URLs without http/https prefix are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeRequest(url="not-a-url")

        errors = exc_info.value.errors()
        assert any('URL must start with http:// or https://' in str(e['ctx'].get('error', '')) for e in errors)

    def test_analyze_request_relative_url(self):
        """Test that relative URLs are rejected."""
        with pytest.raises(ValidationError):
            AnalyzeRequest(url="/relative/path")

    def test_analyze_request_file_url(self):
        """Test that file:// URLs are rejected."""
        with pytest.raises(ValidationError):
            AnalyzeRequest(url="file:///etc/passwd")

    def test_analyze_request_missing_url(self):
        """Test that request validates when URL is optional."""
        # URL is optional (some tools use config file instead)
        request = AnalyzeRequest()
        assert request.url is None

    def test_analyze_request_invalid_log_level(self):
        """Test that invalid log levels are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeRequest(url="https://example.com", log_level="INVALID")

        errors = exc_info.value.errors()
        assert any('log_level' in str(e['loc']) for e in errors)

    def test_analyze_request_valid_log_levels(self):
        """Test that valid log levels are accepted."""
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            request = AnalyzeRequest(url="https://example.com", log_level=level)
            assert request.log_level == level

    @pytest.mark.parametrize("max_pages,should_pass", [
        (1, True),      # Minimum valid
        (500, True),    # Mid-range valid
        (1000, True),   # Maximum valid
        (0, False),     # Below minimum
        (2000, False),  # Above maximum
        (-1, False),    # Negative
    ])
    def test_analyze_request_max_pages_bounds(self, max_pages, should_pass):
        """Test max_pages constraint validation (1-1000)."""
        if should_pass:
            request = AnalyzeRequest(url="https://example.com", max_pages=max_pages)
            assert request.max_pages == max_pages
        else:
            with pytest.raises(ValidationError):
                AnalyzeRequest(url="https://example.com", max_pages=max_pages)

    @pytest.mark.parametrize("crawl_depth,should_pass", [
        (1, True),      # Minimum valid
        (5, True),      # Mid-range valid
        (10, True),     # Maximum valid
        (0, False),     # Below minimum
        (11, False),    # Above maximum
    ])
    def test_analyze_request_crawl_depth_bounds(self, crawl_depth, should_pass):
        """Test crawl_depth constraint validation (1-10)."""
        if should_pass:
            request = AnalyzeRequest(url="https://example.com", crawl_depth=crawl_depth)
            assert request.crawl_depth == crawl_depth
        else:
            with pytest.raises(ValidationError):
                AnalyzeRequest(url="https://example.com", crawl_depth=crawl_depth)

    @pytest.mark.parametrize("delay,should_pass", [
        (0, True),      # Minimum valid
        (30, True),     # Mid-range valid
        (60, True),     # Maximum valid
        (-1, False),    # Below minimum
        (61, False),    # Above maximum
    ])
    def test_analyze_request_delay_bounds(self, delay, should_pass):
        """Test delay constraint validation (0-60)."""
        if should_pass:
            request = AnalyzeRequest(url="https://example.com", delay=delay)
            assert request.delay == delay
        else:
            with pytest.raises(ValidationError):
                AnalyzeRequest(url="https://example.com", delay=delay)

    @pytest.mark.parametrize("timeout,should_pass", [
        (1, True),      # Minimum valid
        (1800, True),   # Mid-range valid
        (3600, True),   # Maximum valid
        (0, False),     # Below minimum
        (3601, False),  # Above maximum
    ])
    def test_analyze_request_timeout_bounds(self, timeout, should_pass):
        """Test timeout constraint validation (1-3600)."""
        if should_pass:
            request = AnalyzeRequest(url="https://example.com", timeout=timeout)
            assert request.timeout == timeout
        else:
            with pytest.raises(ValidationError):
                AnalyzeRequest(url="https://example.com", timeout=timeout)

    def test_analyze_request_unknown_fields_rejected(self):
        """Test that unknown fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeRequest(url="https://example.com", unknown_field="value")

        errors = exc_info.value.errors()
        assert any('extra_forbidden' in e['type'] for e in errors)

    def test_analyze_request_name_max_length(self):
        """Test that name field respects max_length constraint."""
        # Valid: within 200 characters
        request = AnalyzeRequest(url="https://example.com", name="Valid Name")
        assert request.name == "Valid Name"

        # Invalid: exceeds 200 characters
        with pytest.raises(ValidationError):
            AnalyzeRequest(url="https://example.com", name="x" * 201)

    def test_analyze_request_boolean_fields(self):
        """Test boolean field validation."""
        request = AnalyzeRequest(
            url="https://example.com",
            no_cache=True,
            clear_cache=False,
            dry_run=True,
            dashboard=False,
            verbose=True
        )
        assert request.no_cache is True
        assert request.clear_cache is False
        assert request.dry_run is True
        assert request.dashboard is False
        assert request.verbose is True

    def test_analyze_request_model_dump_excludes_none(self):
        """Test that model_dump(exclude_none=True) removes None values."""
        request = AnalyzeRequest(
            url="https://example.com",
            max_pages=100
            # Other fields are None
        )
        dumped = request.model_dump(exclude_none=True)
        assert dumped == {'url': 'https://example.com', 'max_pages': 100, 'no_cache': False, 'clear_cache': False, 'dry_run': False, 'dashboard': False, 'verbose': False}


class TestJobIdPathValidation:
    """Test suite for JobIdPath model validation."""

    def test_job_id_valid_uuid(self):
        """Test that valid UUIDs are accepted."""
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "123e4567-e89b-12d3-a456-426614174000"
        ]
        for uuid in valid_uuids:
            job_id = JobIdPath(job_id=uuid)
            assert job_id.job_id == uuid

    def test_job_id_invalid_format(self):
        """Test that non-UUID formats are rejected."""
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "550e8400-e29b-41d4-a716",  # Incomplete UUID
            "550e8400e29b41d4a716446655440000",  # Missing hyphens
            "550E8400-E29B-41D4-A716-446655440000",  # Uppercase (pattern is lowercase)
            "../../../etc/passwd",  # Path traversal attempt
            "job_123",  # Non-UUID string
        ]
        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                JobIdPath(job_id=invalid_id)

            errors = exc_info.value.errors()
            assert any('string_pattern_mismatch' in e['type'] for e in errors)

    def test_job_id_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(ValidationError):
            JobIdPath(job_id="")

    def test_job_id_with_whitespace(self):
        """Test that UUIDs with whitespace are rejected."""
        with pytest.raises(ValidationError):
            JobIdPath(job_id=" 550e8400-e29b-41d4-a716-446655440000 ")

    def test_job_id_unknown_fields_rejected(self):
        """Test that unknown fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError):
            JobIdPath(job_id="550e8400-e29b-41d4-a716-446655440000", extra_field="value")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
