"""Tests for subprocess command validation."""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security.subprocess_validator import (
    validate_script,
    validate_tool_directory,
    validate_path_within_project,
    build_safe_command,
    ALLOWED_SCRIPTS,
    get_project_root,
)


class TestScriptWhitelist:
    """Test script whitelist validation."""

    def test_allowed_script_passes(self):
        """Whitelisted scripts should pass validation."""
        assert validate_script('intentcrawler.py') is True
        assert validate_script('graspevaluator.py') is True

    def test_unknown_script_rejected(self):
        """Non-whitelisted scripts should be rejected."""
        assert validate_script('malicious.py') is False
        assert validate_script('../../etc/passwd') is False

    def test_empty_script_rejected(self):
        """Empty script name should be rejected."""
        assert validate_script('') is False


class TestPathValidation:
    """Test path canonicalization and traversal prevention."""

    def test_valid_path_within_project(self):
        """Valid paths within project should pass."""
        project_root = get_project_root()
        # Path that exists within project
        valid_path = str(project_root / 'automation')
        result = validate_path_within_project(valid_path, project_root)
        assert result is not None

    def test_path_traversal_blocked(self):
        """Path traversal attempts should be blocked."""
        project_root = get_project_root()
        # Attempt to escape project directory
        traversal_path = str(project_root / '..' / '..' / 'etc' / 'passwd')
        result = validate_path_within_project(traversal_path, project_root)
        assert result is None

    def test_absolute_path_outside_project_blocked(self):
        """Absolute paths outside project should be blocked."""
        project_root = get_project_root()
        result = validate_path_within_project('/etc/passwd', project_root)
        assert result is None


class TestToolDirectoryValidation:
    """Test tool directory validation."""

    def test_valid_tool_directory(self):
        """Valid tool directories should pass."""
        project_root = get_project_root()
        # Assuming intentcrawler exists
        tool_dir = str(project_root / 'intentcrawler')
        if os.path.isdir(tool_dir):
            result = validate_tool_directory(tool_dir)
            assert result is not None

    def test_directory_outside_project_blocked(self):
        """Directories outside project should be blocked."""
        result = validate_tool_directory('/tmp')
        assert result is None


class TestBuildSafeCommand:
    """Test safe command building."""

    def test_build_command_with_valid_inputs(self):
        """Valid inputs should produce a command list."""
        project_root = get_project_root()
        tool_dir = str(project_root / 'intentcrawler')

        if os.path.isdir(tool_dir):
            cmd = build_safe_command(
                script='intentcrawler.py',
                params={'url': 'https://example.com'},
                tool_dir=tool_dir,
                tool_config={'optional_params': []},
                param_style='positional'
            )
            assert cmd is not None
            assert cmd[0] == 'python3'
            assert cmd[1] == 'intentcrawler.py'
            assert 'https://example.com' in cmd

    def test_build_command_rejects_invalid_script(self):
        """Invalid script should return None."""
        project_root = get_project_root()
        tool_dir = str(project_root / 'intentcrawler')

        if os.path.isdir(tool_dir):
            cmd = build_safe_command(
                script='malicious.py',
                params={'url': 'https://example.com'},
                tool_dir=tool_dir,
                tool_config={},
                param_style='positional'
            )
            assert cmd is None

    def test_build_command_rejects_invalid_directory(self):
        """Invalid tool directory should return None."""
        cmd = build_safe_command(
            script='intentcrawler.py',
            params={'url': 'https://example.com'},
            tool_dir='/tmp/evil',
            tool_config={},
            param_style='positional'
        )
        assert cmd is None

    def test_command_is_list_not_string(self):
        """Command should be list for shell=False execution."""
        project_root = get_project_root()
        tool_dir = str(project_root / 'intentcrawler')

        if os.path.isdir(tool_dir):
            cmd = build_safe_command(
                script='intentcrawler.py',
                params={'url': 'https://example.com'},
                tool_dir=tool_dir,
                tool_config={'optional_params': []},
                param_style='positional'
            )
            assert isinstance(cmd, list)
            assert all(isinstance(arg, str) for arg in cmd)
