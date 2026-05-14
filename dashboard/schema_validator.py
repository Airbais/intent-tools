"""
Schema validator for dashboard-data.json files.

Validates tool outputs against the dashboard data schema to ensure
consistent structure and required fields.
"""

import json
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError
except ImportError:
    raise ImportError(
        "jsonschema library is required. Install with: pip install jsonschema>=4.20.0"
    )


logger = logging.getLogger(__name__)


class DashboardDataValidator:
    """Validator for dashboard-data.json files using JSON Schema."""

    def __init__(self, schema_path: Path = None):
        """
        Initialize validator with JSON Schema.

        Args:
            schema_path: Path to the JSON Schema file. If None, uses default location.
        """
        if schema_path is None:
            # Default to schema file in the same package
            schema_path = Path(__file__).parent / "schemas" / "dashboard-data.schema.json"

        self.schema_path = Path(schema_path)

        if not self.schema_path.exists():
            raise FileNotFoundError(
                f"Schema file not found at {self.schema_path}. "
                f"Please ensure the schema file exists."
            )

        with open(self.schema_path, 'r') as f:
            self.schema = json.load(f)

        self.validator = Draft202012Validator(self.schema)
        logger.debug(f"Loaded schema from {self.schema_path}")

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate dashboard data against the schema.

        Args:
            data: Dictionary containing dashboard data to validate

        Returns:
            Tuple of (is_valid, list_of_error_messages)
            Error messages include json_path and description.
        """
        errors = []

        # Collect all validation errors
        for error in self.validator.iter_errors(data):
            # Build json_path from the error's path
            json_path = "root"
            if error.path:
                json_path += "." + ".".join(str(p) for p in error.path)

            error_msg = f"{json_path}: {error.message}"
            errors.append(error_msg)
            logger.debug(f"Validation error: {error_msg}")

        is_valid = len(errors) == 0

        if is_valid:
            logger.debug("Validation successful")
        else:
            logger.warning(f"Validation failed with {len(errors)} error(s)")

        return is_valid, errors

    def validate_file(self, filepath: Path) -> Tuple[bool, List[str]]:
        """
        Validate a dashboard-data.json file.

        Args:
            filepath: Path to the JSON file to validate

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        filepath = Path(filepath)

        if not filepath.exists():
            return False, [f"File not found: {filepath}"]

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON in {filepath}: {str(e)}"]
        except Exception as e:
            return False, [f"Error reading {filepath}: {str(e)}"]

        return self.validate(data)


def validate_dashboard_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate dashboard data.

    Args:
        data: Dictionary containing dashboard data to validate

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    validator = DashboardDataValidator()
    return validator.validate(data)
