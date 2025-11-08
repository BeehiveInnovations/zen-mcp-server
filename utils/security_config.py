"""
Security configuration and path validation constants

This module contains security-related constants and configurations
for file access control.
"""

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
    # Note: /home itself is removed to allow user directories
    # Only root home directories should be blocked
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

        # Platform-independent check for Windows paths
        # Check the raw path string for Windows patterns
        path_str_normalized = path_str.replace("\\", "/").lower()
        windows_dangerous = [
            "c:/windows",
            "c:/program files",
            "c:/programdata",
            "c:/users",
            "d:/windows",  # Also check D: drive
            "e:/windows",  # And E: drive
            "/windows",  # Unix-style Windows path
            "/program files",
            "/users",
        ]
        for win_path in windows_dangerous:
            if path_str_normalized.startswith(win_path):
                return True

        # Now resolve the path (follows symlinks)
        resolved = path.resolve()

        # Check if resolved path is root
        if resolved.parent == resolved:
            return True

        # Check for specific safe paths that should always be allowed
        safe_prefixes = [
            "/tmp",
            "/var/tmp",
            "/home",  # Allow user home directories
            "/private/tmp",  # macOS temp directory
            "/private/var/tmp",  # macOS var/tmp
            "/System/Volumes/Data/home",  # macOS home
        ]

        for safe_prefix in safe_prefixes:
            try:
                safe_path = Path(safe_prefix).resolve()
                resolved.relative_to(safe_path)
                # This is under a safe directory, allow it
                return False
            except ValueError:
                # Not under this safe directory, continue checking
                pass

        # Use the recommended approach from #293: relative_to() method
        for dangerous in DANGEROUS_PATHS:
            try:
                # Skip root directory check if path is in safe locations
                if dangerous == "/":
                    # For root, only block if it's actually the root
                    if resolved == Path("/").resolve():
                        return True
                    # Skip the relative_to check for root
                    continue

                # Try to create a relative path from the dangerous directory
                danger_path = Path(dangerous).resolve()
                resolved.relative_to(danger_path)
                # If successful, the path is under a dangerous directory
                return True
            except ValueError:
                # Path is not relative to this dangerous directory
                continue
            except Exception:
                # Handle any other errors safely
                continue

        return False

    except Exception:
        # If we can't process the path safely, consider it dangerous
        return True
