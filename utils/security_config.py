"""
Security configuration and path validation constants

This module contains security-related constants and configurations
for file access control.
"""

import os
from pathlib import Path

# Dangerous paths that should never be scanned
# These would give overly broad access and pose security risks
DANGEROUS_PATHS = {
    "/",
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/root",
    "/home",
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    # Specific /var subdirectories that are sensitive
    "/var/log",
    "/var/mail",
    "/var/spool",
    "/var/run",
    "/var/db",
    "/var/cache/private",
    # Windows paths
    "C:\\",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\Users",
    "C:\\ProgramData",
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


def is_dangerous_path(path: Path) -> bool:
    """
    Check if a path is in the dangerous paths list or contains traversal attempts.

    Args:
        path: Path to check

    Returns:
        True if the path is dangerous and should not be accessed
    """
    try:
        # Convert to string for pattern checking
        path_str = str(path)

        # Check for path traversal patterns BEFORE resolution
        # This prevents attacks that use symlinks or other techniques
        traversal_patterns = [
            "..",  # Unix/Windows path traversal
            "..%2f",  # URL encoded forward slash
            "..%2F",  # URL encoded forward slash (uppercase)
            "..%5c",  # URL encoded backslash
            "..%5C",  # URL encoded backslash (uppercase)
            "%2e%2e",  # Double URL encoded dots
            "%252e%252e",  # Double URL encoded
            "..;/",  # Path traversal with semicolon
            "..\\x2f",  # Hex encoded slash
            "..\\x5c",  # Hex encoded backslash
        ]

        # Check for any traversal patterns
        for pattern in traversal_patterns:
            if pattern in path_str.lower():
                return True

        # Check for null bytes which can truncate paths
        if "\x00" in path_str or "%00" in path_str:
            return True

        # Now resolve the path (follows symlinks)
        resolved = path.resolve()
        resolved_str = str(resolved)

        # Check if resolved path is root
        if resolved.parent == resolved:
            return True

        # Check against all dangerous paths
        for dangerous in DANGEROUS_PATHS:
            dangerous_normalized = str(Path(dangerous).resolve())
            # Check exact match or if dangerous path is a parent
            if resolved_str == dangerous_normalized or resolved_str.startswith(dangerous_normalized + os.sep):
                return True

        return False

    except Exception:
        # If we can't process the path safely, consider it dangerous
        return True
