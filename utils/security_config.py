"""
Security configuration and path validation constants

This module contains security-related constants and configurations
for file access control and workspace management.
"""

import os
from pathlib import Path

# Dangerous paths that should never be used as WORKSPACE_ROOT
# These would give overly broad access and pose security risks
DANGEROUS_WORKSPACE_PATHS = {
    "/",
    "/etc",
    "/usr",
    "/bin",
    "/var",
    "/root",
    "/home",
    "/workspace",  # Container path - WORKSPACE_ROOT should be host path
    "C:\\",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Users",
}

# Directories to exclude from recursive file search
# These typically contain generated code, dependencies, or build artifacts
EXCLUDED_DIRS = {
    # Python
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "*.egg-info",
    ".eggs",
    "wheels",
    ".Python",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "htmlcov",
    ".coverage",
    "coverage",
    # Node.js / JavaScript
    "node_modules",
    ".next",
    ".nuxt",
    "bower_components",
    ".sass-cache",
    # Version Control
    ".git",
    ".svn",
    ".hg",
    # Build Output
    "build",
    "dist",
    "target",
    "out",
    # IDEs
    ".idea",
    ".vscode",
    ".sublime",
    ".atom",
    ".brackets",
    # Temporary / Cache
    ".cache",
    ".temp",
    ".tmp",
    "*.swp",
    "*.swo",
    "*~",
    # OS-specific
    ".DS_Store",
    "Thumbs.db",
    # Java / JVM
    ".gradle",
    ".m2",
    # Documentation build
    "_build",
    "site",
    # Mobile development
    ".expo",
    ".flutter",
    # Package managers
    "vendor",
}

# MCP signature files - presence of these indicates the MCP's own directory
# Used to prevent the MCP from scanning its own codebase
MCP_SIGNATURE_FILES = {
    "zen_server.py",
    "server.py",
    "tools/precommit.py",
    "utils/file_utils.py",
    "prompts/tool_prompts.py",
}

# Workspace configuration
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT")
CONTAINER_WORKSPACE = Path("/workspace")


def validate_workspace_security(workspace_root: str) -> None:
    """
    Validate that WORKSPACE_ROOT is set to a safe directory.

    Args:
        workspace_root: The workspace root path to validate

    Raises:
        RuntimeError: If the workspace root is unsafe
    """
    if not workspace_root:
        return

    # Resolve to canonical path for comparison
    resolved_workspace = Path(workspace_root).resolve()

    # Special check for /workspace - common configuration mistake
    if str(resolved_workspace) == "/workspace":
        raise RuntimeError(
            f"Configuration Error: WORKSPACE_ROOT should be set to the HOST path, not the container path. "
            f"Found: WORKSPACE_ROOT={workspace_root} "
            f"Expected: WORKSPACE_ROOT should be set to your host directory path (e.g., $HOME) "
            f"that contains all files Claude might reference. "
            f"This path gets mounted to /workspace inside the Docker container."
        )

    # Check against other dangerous paths
    if str(resolved_workspace) in DANGEROUS_WORKSPACE_PATHS:
        raise RuntimeError(
            f"Security Error: WORKSPACE_ROOT '{workspace_root}' is set to a dangerous system directory. "
            f"This would give access to critical system files. "
            f"Please set WORKSPACE_ROOT to a specific project directory."
        )

    # Additional check: prevent filesystem root
    if resolved_workspace.parent == resolved_workspace:
        raise RuntimeError(
            f"Security Error: WORKSPACE_ROOT '{workspace_root}' cannot be the filesystem root. "
            f"This would give access to the entire filesystem. "
            f"Please set WORKSPACE_ROOT to a specific project directory."
        )


def get_security_root() -> Path:
    """
    Determine the security boundary for file access.

    Returns:
        Path object representing the security root directory
    """
    # In Docker: use /workspace (container directory)
    # In tests/direct mode: use WORKSPACE_ROOT (host directory)
    if CONTAINER_WORKSPACE.exists():
        # Running in Docker container
        return CONTAINER_WORKSPACE
    elif WORKSPACE_ROOT:
        # Running in tests or direct mode with WORKSPACE_ROOT set
        return Path(WORKSPACE_ROOT).resolve()
    else:
        # Fallback for backward compatibility (should not happen in normal usage)
        return Path.home()


# Validate security on import if WORKSPACE_ROOT is set
if WORKSPACE_ROOT:
    validate_workspace_security(WORKSPACE_ROOT)

# Export the computed security root
SECURITY_ROOT = get_security_root()
