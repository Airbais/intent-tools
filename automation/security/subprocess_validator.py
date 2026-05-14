"""
Subprocess command validation with whitelist and path canonicalization.

SECURITY:
- Only whitelisted scripts can be executed
- Tool directories must be within project root
- Path parameters are canonicalized to prevent traversal
- Never uses shell=True
"""
import structlog
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = structlog.get_logger(__name__)

# Whitelist of allowed tool scripts - derived from tools_config.yaml
ALLOWED_SCRIPTS = {
    'intentcrawler.py',
    'graspevaluator.py',
    'llmevaluator.py',
    'geoevaluator.py',
    'rulesevaluator.py',
}

# Allowed parameter flags (excluding positional)
ALLOWED_FLAGS = {
    '--url', '--config', '--output', '--output-dir', '--log-level',
    '--no-cache', '--clear-cache', '--dry-run', '--dashboard',
    '--max-pages', '--crawl-depth', '--delay', '--timeout',
    '--verbose', '--rules-file', '--content-source', '--name', '--formats',
}


def get_project_root() -> Path:
    """Get the project root directory (parent of automation/)."""
    return Path(__file__).parent.parent.parent.resolve()


def validate_path_within_project(path: str, base_dir: Path = None) -> Optional[Path]:
    """
    Validate that a file path is within the project directory after symlink resolution.

    SECURITY: Uses resolve() to follow symlinks and canonicalize path,
    then checks if result is within allowed directory.

    Args:
        path: Path string to validate
        base_dir: Base directory path must be within (default: project root)

    Returns:
        Resolved Path if valid, None if invalid (path traversal attempt)
    """
    if base_dir is None:
        base_dir = get_project_root()
    else:
        base_dir = Path(base_dir).resolve()

    try:
        # resolve(strict=False) follows symlinks but doesn't require path to exist
        resolved_path = Path(path).resolve(strict=False)

        # Check if resolved path is within allowed directory
        resolved_path.relative_to(base_dir)
        return resolved_path
    except ValueError:
        # Path is outside base_dir
        logger.warning("path_traversal_detected", path=str(path), project_root=str(base_dir))
        return None
    except OSError as e:
        logger.warning("invalid_path", path=str(path), error=str(e))
        return None


def validate_script(script: str) -> bool:
    """
    Check if script is in the whitelist.

    Args:
        script: Script filename to validate

    Returns:
        True if script is allowed, False otherwise
    """
    if script not in ALLOWED_SCRIPTS:
        logger.warning("script_not_allowed", script=script, allowed=list(ALLOWED_SCRIPTS))
        return False
    return True


def validate_tool_directory(tool_dir: str) -> Optional[Path]:
    """
    Validate tool directory is within project root.

    Args:
        tool_dir: Tool directory path

    Returns:
        Resolved Path if valid, None otherwise
    """
    project_root = get_project_root()
    validated = validate_path_within_project(tool_dir, project_root)

    if validated is None:
        logger.warning("tool_directory_outside_project", tool_dir=str(tool_dir), project_root=str(project_root))
        return None

    if not validated.is_dir():
        logger.warning("tool_directory_not_found", tool_dir=str(tool_dir))
        return None

    return validated


def build_safe_command(
    script: str,
    params: Dict[str, Any],
    tool_dir: str,
    tool_config: dict,
    param_style: str = 'flags'
) -> Optional[List[str]]:
    """
    Build a validated subprocess command.

    SECURITY:
    - Validates script against whitelist
    - Validates tool_dir within project
    - Validates path parameters
    - Returns list (not string) for shell=False execution

    Args:
        script: Script filename (e.g., 'intentcrawler.py')
        params: Parameter dictionary from request
        tool_dir: Tool directory path
        tool_config: Tool configuration from tools_config.yaml
        param_style: 'flags', 'positional', or 'config_file'

    Returns:
        Command list if valid, None if validation fails
    """
    # 1. Validate script
    if not validate_script(script):
        return None

    # 2. Validate tool directory
    validated_dir = validate_tool_directory(tool_dir)
    if validated_dir is None:
        return None

    # 3. Start building command
    cmd = ['python3', script]

    # 4. Handle parameters based on style (matching existing api_server.py logic)
    if param_style == 'positional':
        # URL is positional argument
        if 'url' in params:
            url = str(params['url'])
            # URL doesn't need path validation - it's a web URL
            cmd.append(url)

        # Optional params with -- prefix
        for param in tool_config.get('optional_params', []):
            if param in params:
                flag = f'--{param.replace("_", "-")}'
                if flag not in ALLOWED_FLAGS:
                    logger.warning("unknown_flag_rejected", flag=flag, allowed=list(ALLOWED_FLAGS))
                    continue
                cmd.extend([flag, str(params[param])])

    elif param_style == 'config_file':
        # Config file is positional
        if 'config' in params:
            config_path = str(params['config'])
            # Validate config path is within project
            validated_config = validate_path_within_project(config_path, validated_dir)
            if validated_config is None:
                logger.warning("config_path_invalid", config_path=config_path)
                return None
            cmd.append(str(validated_config))

        # Optional params
        for param in tool_config.get('optional_params', []):
            if param in params:
                # Boolean flags
                if param in ['no_cache', 'clear_cache', 'dry_run', 'dashboard']:
                    if params[param]:
                        cmd.append(f'--{param.replace("_", "-")}')
                else:
                    flag = f'--{param.replace("_", "-")}'
                    if flag not in ALLOWED_FLAGS:
                        logger.warning("unknown_flag_rejected", flag=flag, allowed=list(ALLOWED_FLAGS))
                        continue
                    cmd.extend([flag, str(params[param])])

    else:  # flags style
        # Required params
        for param in tool_config.get('required_params', []):
            if param in params:
                flag = f'--{param.replace("_", "-")}'
                if flag not in ALLOWED_FLAGS:
                    logger.warning("unknown_flag_rejected", flag=flag, allowed=list(ALLOWED_FLAGS))
                    continue
                cmd.extend([flag, str(params[param])])

        # Optional params
        for param in tool_config.get('optional_params', []):
            if param in params:
                # Handle output-dir alias for geoevaluator
                if param == 'output' and 'geoevaluator' in str(tool_dir):
                    cmd.extend(['--output-dir', str(params[param])])
                else:
                    flag = f'--{param.replace("_", "-")}'
                    if flag not in ALLOWED_FLAGS:
                        logger.warning("unknown_flag_rejected", flag=flag, allowed=list(ALLOWED_FLAGS))
                        continue
                    cmd.extend([flag, str(params[param])])

    logger.info("command_built", script=script, arg_count=len(cmd)-1)
    return cmd
