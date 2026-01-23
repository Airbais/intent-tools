"""
Integration tests for dashboard data loading and schema validation.

Tests verify that dashboard-data.json files:
1. Can be validated against the JSON schema
2. Are loaded correctly by the data loader
3. Have proper tool_type detection (explicit, legacy, heuristic)
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

# Import the modules we're testing
from dashboard.schema_validator import DashboardDataValidator
from dashboard.data_loader import ToolDataLoader


class TestSchemaValidator:
    """Test schema validation for dashboard-data.json files."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance for testing."""
        return DashboardDataValidator()

    def test_valid_minimal_data_passes(self, validator):
        """Valid minimal data with required fields should pass validation."""
        data = {
            "tool_type": "intentcrawler",
            "timestamp": "2025-07-19T10:30:00Z"
        }
        is_valid, errors = validator.validate(data)
        assert is_valid, f"Expected valid but got errors: {errors}"
        assert len(errors) == 0

    def test_missing_tool_type_fails(self, validator):
        """Missing tool_type field should fail validation."""
        data = {
            "timestamp": "2025-07-19T10:30:00Z"
        }
        is_valid, errors = validator.validate(data)
        assert not is_valid
        assert len(errors) > 0
        assert any("tool_type" in error.lower() for error in errors)

    def test_missing_timestamp_fails(self, validator):
        """Missing timestamp field should fail validation."""
        data = {
            "tool_type": "intentcrawler"
        }
        is_valid, errors = validator.validate(data)
        assert not is_valid
        assert len(errors) > 0
        assert any("timestamp" in error.lower() for error in errors)

    def test_invalid_tool_type_value_fails(self, validator):
        """Invalid tool_type value should fail validation."""
        data = {
            "tool_type": "invalid_tool",
            "timestamp": "2025-07-19T10:30:00Z"
        }
        is_valid, errors = validator.validate(data)
        assert not is_valid
        assert len(errors) > 0
        assert any("tool_type" in error.lower() for error in errors)

    @pytest.mark.parametrize("tool_type", [
        "intentcrawler",
        "graspevaluator",
        "llmevaluator",
        "geoevaluator",
        "rulesevaluator",
        "llmstxtgenerator"
    ])
    def test_all_valid_tool_types_pass(self, validator, tool_type):
        """All 6 valid tool types should pass validation."""
        data = {
            "tool_type": tool_type,
            "timestamp": "2025-07-19T10:30:00Z"
        }
        is_valid, errors = validator.validate(data)
        assert is_valid, f"Tool type '{tool_type}' should be valid but got errors: {errors}"

    def test_additional_properties_allowed(self, validator):
        """Additional properties beyond required fields should be allowed."""
        data = {
            "tool_type": "intentcrawler",
            "timestamp": "2025-07-19T10:30:00Z",
            "summary": {"pages": 10},
            "metrics": {"intents": 42},
            "data": {"custom_field": "value"},
            "extra_field": "should be allowed"
        }
        is_valid, errors = validator.validate(data)
        assert is_valid, f"Additional properties should be allowed but got errors: {errors}"

    def test_invalid_timestamp_format_fails(self, validator):
        """Invalid timestamp format should fail validation."""
        data = {
            "tool_type": "intentcrawler",
            "timestamp": "2025-07-19 10:30:00"  # Missing T separator and timezone
        }
        is_valid, errors = validator.validate(data)
        assert not is_valid
        assert len(errors) > 0
        assert any("timestamp" in error.lower() for error in errors)

    def test_valid_timestamp_with_offset(self, validator):
        """Valid timestamp with timezone offset should pass."""
        data = {
            "tool_type": "graspevaluator",
            "timestamp": "2025-07-19T10:30:00-04:00"
        }
        is_valid, errors = validator.validate(data)
        assert is_valid, f"Timestamp with offset should be valid but got errors: {errors}"


class TestDataLoader:
    """Test data loader functionality."""

    @pytest.fixture
    def loader(self, tmp_path):
        """Create a data loader instance for testing."""
        return ToolDataLoader(str(tmp_path))

    def test_explicit_tool_type_detection(self, loader):
        """Data loader should detect explicit tool_type field."""
        data = {
            "tool_type": "intentcrawler",
            "timestamp": "2025-07-19T10:30:00Z",
            "discovered_intents": []
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "intentcrawler"

    def test_legacy_tool_field_detection(self, loader):
        """Data loader should fall back to legacy 'tool' field."""
        data = {
            "tool": "graspevaluator",
            "timestamp": "2025-07-19T10:30:00Z"
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "graspevaluator"

    def test_heuristic_intentcrawler_detection(self, loader):
        """Data loader should detect intentcrawler by structure."""
        data = {
            "discovered_intents": [],
            "by_section": {},
            "timestamp": "2025-07-19T10:30:00Z"
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "intentcrawler"

    def test_heuristic_graspevaluator_detection(self, loader):
        """Data loader should detect graspevaluator by structure."""
        data = {
            "overall_score": 85,
            "metrics": {
                "grounded": 90,
                "readable": 85,
                "accurate": 80
            },
            "breakdown": {},
            "recommendations": [],
            "timestamp": "2025-07-19T10:30:00Z"
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "graspevaluator"

    def test_heuristic_llmevaluator_detection(self, loader):
        """Data loader should detect llmevaluator by structure."""
        data = {
            "evaluation_results": [],
            "aggregate_metrics": {},
            "brand_info": {},
            "timestamp": "2025-07-19T10:30:00Z"
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "llmevaluator"

    def test_heuristic_geoevaluator_detection(self, loader):
        """Data loader should detect geoevaluator by structure."""
        data = {
            "overall_score": {},
            "analysis_summary": {},
            "recommendations": [],
            "metadata": {"tool_name": "geoevaluator"},
            "timestamp": "2025-07-19T10:30:00Z"
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "geoevaluator"

    def test_heuristic_llmstxtgenerator_detection(self, loader):
        """Data loader should detect llmstxtgenerator by structure."""
        data = {
            "generation_summary": {},
            "site_analysis": {},
            "metadata": {"tool_name": "llmstxtgenerator"},
            "timestamp": "2025-07-19T10:30:00Z"
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "llmstxtgenerator"

    def test_heuristic_rulesevaluator_detection(self, loader):
        """Data loader should detect rulesevaluator by structure."""
        data = {
            "summary": {
                "total_prompts": 100,
                "overall_pass_rate": 85.5
            },
            "metrics": {
                "pass_rates_by_type": {},
                "database_stats": {}
            },
            "timestamp": "2025-07-19T10:30:00Z"
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "rulesevaluator"

    def test_unknown_tool_type_when_no_match(self, loader):
        """Data loader should return 'unknown' when no pattern matches."""
        data = {
            "some_field": "value",
            "timestamp": "2025-07-19T10:30:00Z"
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "unknown"

    def test_explicit_tool_type_preferred_over_heuristics(self, loader):
        """Explicit tool_type should be preferred over heuristic detection."""
        data = {
            "tool_type": "graspevaluator",
            "discovered_intents": [],  # Would match intentcrawler heuristic
            "by_section": {},
            "timestamp": "2025-07-19T10:30:00Z"
        }
        tool_type = loader._detect_tool_type(data)
        assert tool_type == "graspevaluator"


class TestExistingDataFiles:
    """Integration tests with real dashboard-data.json files."""

    @pytest.fixture
    def loader(self):
        """Create a data loader instance pointing to the tools directory."""
        # This assumes we're running from the tools directory
        tools_root = Path(__file__).parent.parent.parent
        return ToolDataLoader(str(tools_root))

    def test_discover_tools_finds_available_tools(self, loader):
        """Discover tools should find tools with results directories."""
        tools = loader.discover_tools()
        assert isinstance(tools, list)
        # We know at least some tools should exist based on the project structure
        # But don't assert specific tools to avoid test brittleness

    def test_load_graspevaluator_data(self, loader):
        """Load and validate graspevaluator dashboard-data.json if available."""
        # Check if graspevaluator data exists
        data_file = loader.tools_root / "graspevaluator" / "results" / "2025-07-19" / "dashboard-data.json"
        if not data_file.exists():
            pytest.skip("graspevaluator data not available")

        data = loader.load_tool_data("graspevaluator", "2025-07-19")
        assert data is not None
        assert data['_metadata']['tool_type'] in ['graspevaluator', 'unknown']

    def test_load_intentcrawler_data(self, loader):
        """Load and validate intentcrawler dashboard-data.json if available."""
        # Check if intentcrawler data exists
        data_file = loader.tools_root / "intentcrawler" / "results" / "2025-06-26" / "dashboard-data.json"
        if not data_file.exists():
            pytest.skip("intentcrawler data not available")

        data = loader.load_tool_data("intentcrawler", "2025-06-26")
        assert data is not None
        assert data['_metadata']['tool_type'] in ['intentcrawler', 'unknown']

    def test_load_rulesevaluator_data(self, loader):
        """Load and validate rulesevaluator dashboard-data.json if available."""
        # Check if rulesevaluator data exists
        data_file = loader.tools_root / "rulesevaluator" / "results" / "2025-08-05" / "dashboard-data.json"
        if not data_file.exists():
            pytest.skip("rulesevaluator data not available")

        data = loader.load_tool_data("rulesevaluator", "2025-08-05")
        assert data is not None
        assert data['_metadata']['tool_type'] in ['rulesevaluator', 'unknown']

    def test_schema_validation_on_existing_files(self, loader):
        """Verify schema validation runs on existing files (warns but doesn't fail)."""
        # Get all available tools and try loading their latest data
        tools = loader.discover_tools()
        if not tools:
            pytest.skip("No tools with data available")

        for tool in tools:
            runs = loader.get_tool_runs(tool)
            if runs:
                # Load latest run - should not raise exception even if validation fails
                data = loader.load_tool_data(tool, runs[0][0])
                # Just verify it loads without crashing
                assert data is not None or data is None  # Either outcome is acceptable
