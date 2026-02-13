"""
Validation Utilities

Security helpers for input sanitization, path validation, etc.
"""

import os
from pathlib import Path


def validate_path(requested_path: str, allowed_directories: list[str]) -> Path:
    """
    Validate a file path against allowed directories.
    Prevents path traversal attacks.

    Args:
        requested_path: The path the user/LLM wants to access
        allowed_directories: List of directories that are allowed

    Returns:
        Resolved, validated Path

    Raises:
        ValueError: If path is outside allowed directories
    """
    resolved = Path(requested_path).resolve()

    for allowed_dir in allowed_directories:
        allowed = Path(allowed_dir).resolve()
        try:
            resolved.relative_to(allowed)
            return resolved
        except ValueError:
            continue

    raise ValueError(
        f"Access denied: '{requested_path}' is outside allowed directories"
    )


def require_env_vars(var_names: list[str]) -> dict[str, str]:
    """
    Validate that required environment variables are set.

    Args:
        var_names: List of required env var names

    Returns:
        Dict of var_name -> value

    Raises:
        EnvironmentError: If any variables are missing
    """
    values = {}
    missing = []

    for name in var_names:
        value = os.environ.get(name)
        if value:
            values[name] = value
        else:
            missing.append(name)

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return values
