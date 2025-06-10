"""
File reading utilities with directory support and token management

This module provides secure file access functionality for the MCP server.
It implements critical security measures to prevent unauthorized file access
and manages token limits to ensure efficient API usage.

Key Features:
- Path validation and sandboxing to prevent directory traversal attacks
- Support for both individual files and recursive directory reading
- Token counting and management to stay within API limits
- Automatic file type detection and filtering
- Comprehensive error handling with informative messages

Security Model:
- All file access is restricted to PROJECT_ROOT and its subdirectories
- Absolute paths are required to prevent ambiguity
- Symbolic links are resolved to ensure they stay within bounds
"""

import logging
import os
from pathlib import Path
from typing import Optional

from .token_utils import MAX_CONTEXT_TOKENS, estimate_tokens

logger = logging.getLogger(__name__)

# Get workspace root for Docker path translation
# When running in Docker with a mounted workspace, WORKSPACE_ROOT contains
# the host path that corresponds to /workspace in the container
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT")
CONTAINER_WORKSPACE = Path("/workspace")

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
    "C:\\",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Users",
}

# Validate WORKSPACE_ROOT for security if it's set
if WORKSPACE_ROOT:
    # Resolve to canonical path for comparison
    resolved_workspace = Path(WORKSPACE_ROOT).resolve()

    # Check against dangerous paths
    if str(resolved_workspace) in DANGEROUS_WORKSPACE_PATHS:
        raise RuntimeError(
            f"Security Error: WORKSPACE_ROOT '{WORKSPACE_ROOT}' is set to a dangerous system directory. "
            f"This would give access to critical system files. "
            f"Please set WORKSPACE_ROOT to a specific project directory."
        )

    # Additional check: prevent filesystem root
    if resolved_workspace.parent == resolved_workspace:
        raise RuntimeError(
            f"Security Error: WORKSPACE_ROOT '{WORKSPACE_ROOT}' cannot be the filesystem root. "
            f"This would give access to the entire filesystem. "
            f"Please set WORKSPACE_ROOT to a specific project directory."
        )

# Get project root from environment or use current directory
# This defines the sandbox directory where file access is allowed
#
# Simplified Security model:
# 1. If MCP_PROJECT_ROOT is explicitly set, use it as sandbox (override)
# 2. If WORKSPACE_ROOT is set (Docker mode), auto-use /workspace as sandbox
# 3. Otherwise, use home directory (direct usage)
env_root = os.environ.get("MCP_PROJECT_ROOT")
if env_root:
    # If explicitly set, use it as sandbox (allows custom override)
    PROJECT_ROOT = Path(env_root).resolve()
elif WORKSPACE_ROOT and CONTAINER_WORKSPACE.exists():
    # Running in Docker with workspace mounted - auto-use /workspace
    PROJECT_ROOT = CONTAINER_WORKSPACE
else:
    # Running directly on host - default to home directory for normal usage
    # This allows access to any file under the user's home directory
    PROJECT_ROOT = Path.home()

# Additional security check for explicit PROJECT_ROOT
if env_root and PROJECT_ROOT.parent == PROJECT_ROOT:
    raise RuntimeError(
        "Security Error: MCP_PROJECT_ROOT cannot be the filesystem root. "
        "This would give access to the entire filesystem. "
        "Please set MCP_PROJECT_ROOT to a specific directory."
    )


# Directories to exclude from recursive file search
# These typically contain generated code, dependencies, or build artifacts
EXCLUDED_DIRS = {
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".env",
    ".git",
    ".svn",
    ".hg",
    "build",
    "dist",
    "target",
    ".idea",
    ".vscode",
    "__pypackages__",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "htmlcov",
    ".coverage",
}

# Common code file extensions that are automatically included when processing directories
# This set can be extended to support additional file types
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".r",
    ".m",
    ".mm",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".bat",
    ".cmd",
    ".yml",
    ".yaml",
    ".json",
    ".xml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".txt",
    ".md",
    ".rst",
    ".tex",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
}


def translate_path_for_environment(path_str: str) -> str:
    """
    Translate paths between host and container environments as needed.

    This is the unified path translation function that should be used by all
    tools and utilities throughout the codebase. It handles:
    1. Docker host-to-container path translation
    2. Direct mode (no translation needed)
    3. Security validation and error handling

    Args:
        path_str: Original path string from the client

    Returns:
        Translated path appropriate for the current environment
    """
    if not WORKSPACE_ROOT or not WORKSPACE_ROOT.strip() or not CONTAINER_WORKSPACE.exists():
        # Not in the configured Docker environment, no translation needed
        return path_str

    # Check if the path is already a container path (starts with /workspace)
    if path_str.startswith(str(CONTAINER_WORKSPACE) + "/") or path_str == str(CONTAINER_WORKSPACE):
        # Path is already translated to container format, return as-is
        return path_str

    try:
        # Use os.path.realpath for security - it resolves symlinks completely
        # This prevents symlink attacks that could escape the workspace
        real_workspace_root = Path(os.path.realpath(WORKSPACE_ROOT))
        # For the host path, we can't use realpath if it doesn't exist in the container
        # So we'll use Path().resolve(strict=False) instead
        real_host_path = Path(path_str).resolve(strict=False)

        # Security check: ensure the path is within the mounted workspace
        # This prevents path traversal attacks (e.g., ../../../etc/passwd)
        relative_path = real_host_path.relative_to(real_workspace_root)

        # Construct the container path
        container_path = CONTAINER_WORKSPACE / relative_path

        # Log the translation for debugging (but not sensitive paths)
        if str(container_path) != path_str:
            logger.info(f"Translated host path to container: {path_str} -> {container_path}")

        return str(container_path)

    except ValueError:
        # Path is not within the host's WORKSPACE_ROOT
        # In Docker, we cannot access files outside the mounted volume
        logger.warning(
            f"Path '{path_str}' is outside the mounted workspace '{WORKSPACE_ROOT}'. "
            f"Docker containers can only access files within the mounted directory."
        )
        # Return a clear error path that will fail gracefully
        return f"/inaccessible/outside/mounted/volume{path_str}"
    except Exception as e:
        # Log unexpected errors but don't expose internal details to clients
        logger.warning(f"Path translation failed for '{path_str}': {type(e).__name__}")
        # Return a clear error path that will fail gracefully
        return f"/inaccessible/translation/error{path_str}"


def resolve_and_validate_path(path_str: str) -> Path:
    """
    Resolves, translates, and validates a path against security policies.

    This is the primary security function that ensures all file access
    is properly sandboxed. It enforces three critical policies:
    1. Translate host paths to container paths if applicable (Docker environment)
    2. All paths must be absolute (no ambiguity)
    3. All paths must resolve to within PROJECT_ROOT (sandboxing)

    Args:
        path_str: Path string (must be absolute)

    Returns:
        Resolved Path object that is guaranteed to be within PROJECT_ROOT

    Raises:
        ValueError: If path is not absolute or otherwise invalid
        PermissionError: If path is outside allowed directory
    """
    # Step 1: Translate Docker paths first (if applicable)
    # This must happen before any other validation
    translated_path_str = translate_path_for_environment(path_str)

    # Step 2: Create a Path object from the (potentially translated) path
    user_path = Path(translated_path_str)

    # Step 3: Security Policy - Require absolute paths
    # Relative paths could be interpreted differently depending on working directory
    if not user_path.is_absolute():
        raise ValueError(f"Relative paths are not supported. Please provide an absolute path.\nReceived: {path_str}")

    # Step 4: Resolve the absolute path (follows symlinks, removes .. and .)
    # This is critical for security as it reveals the true destination of symlinks
    resolved_path = user_path.resolve()

    # Step 5: Security Policy - Ensure the resolved path is within PROJECT_ROOT
    # This prevents directory traversal attacks (e.g., /project/../../../etc/passwd)
    try:
        resolved_path.relative_to(PROJECT_ROOT)
    except ValueError:
        # Provide detailed error for debugging while avoiding information disclosure
        logger.warning(
            f"Access denied - path outside project root. "
            f"Requested: {path_str}, Resolved: {resolved_path}, Root: {PROJECT_ROOT}"
        )
        raise PermissionError(
            f"Path outside project root: {path_str}\nProject root: {PROJECT_ROOT}\nResolved path: {resolved_path}"
        )

    return resolved_path


def translate_file_paths(file_paths: Optional[list[str]]) -> Optional[list[str]]:
    """
    Translate a list of file paths for the current environment.

    This function should be used by all tools to consistently handle path translation
    for file lists. It applies the unified path translation to each path in the list.

    Args:
        file_paths: List of file paths to translate, or None

    Returns:
        List of translated paths, or None if input was None
    """
    if not file_paths:
        return file_paths

    return [translate_path_for_environment(path) for path in file_paths]


def expand_paths(paths: list[str], extensions: Optional[set[str]] = None) -> list[str]:
    """
    Expand paths to individual files, handling both files and directories.

    This function recursively walks directories to find all matching files.
    It automatically filters out hidden files and common non-code directories
    like __pycache__ to avoid including generated or system files.

    Args:
        paths: List of file or directory paths (must be absolute)
        extensions: Optional set of file extensions to include (defaults to CODE_EXTENSIONS)

    Returns:
        List of individual file paths, sorted for consistent ordering
    """
    if extensions is None:
        extensions = CODE_EXTENSIONS

    expanded_files = []
    seen = set()

    for path in paths:
        try:
            # Validate each path for security before processing
            path_obj = resolve_and_validate_path(path)
        except (ValueError, PermissionError):
            # Skip invalid paths silently to allow partial success
            continue

        if not path_obj.exists():
            continue

        if path_obj.is_file():
            # Add file directly
            if str(path_obj) not in seen:
                expanded_files.append(str(path_obj))
                seen.add(str(path_obj))

        elif path_obj.is_dir():
            # Walk directory recursively to find all files
            for root, dirs, files in os.walk(path_obj):
                # Filter directories in-place to skip hidden and excluded directories
                # This prevents descending into .git, .venv, __pycache__, node_modules, etc.
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in EXCLUDED_DIRS]

                for file in files:
                    # Skip hidden files (e.g., .DS_Store, .gitignore)
                    if file.startswith("."):
                        continue

                    file_path = Path(root) / file

                    # Filter by extension if specified
                    if not extensions or file_path.suffix.lower() in extensions:
                        full_path = str(file_path)
                        # Use set to prevent duplicates
                        if full_path not in seen:
                            expanded_files.append(full_path)
                            seen.add(full_path)

    # Sort for consistent ordering across different runs
    # This makes output predictable and easier to debug
    expanded_files.sort()
    return expanded_files


def read_file_content(file_path: str, max_size: int = 1_000_000) -> tuple[str, int]:
    """
    Read a single file and format it for inclusion in AI prompts.

    This function handles various error conditions gracefully and always
    returns formatted content, even for errors. This ensures the AI model
    gets context about what files were attempted but couldn't be read.

    Args:
        file_path: Path to file (must be absolute)
        max_size: Maximum file size to read (default 1MB to prevent memory issues)

    Returns:
        Tuple of (formatted_content, estimated_tokens)
        Content is wrapped with clear delimiters for AI parsing
    """
    try:
        # Validate path security before any file operations
        path = resolve_and_validate_path(file_path)
    except (ValueError, PermissionError) as e:
        # Return error in a format that provides context to the AI
        error_msg = str(e)
        # Add Docker-specific help if we're in Docker and path is inaccessible
        if WORKSPACE_ROOT and CONTAINER_WORKSPACE.exists():
            # We're in Docker
            error_msg = (
                f"File is outside the Docker mounted directory. "
                f"When running in Docker, only files within the mounted workspace are accessible. "
                f"Current mounted directory: {WORKSPACE_ROOT}. "
                f"To access files in a different directory, please run Claude from that directory."
            )
        content = f"\n--- ERROR ACCESSING FILE: {file_path} ---\nError: {error_msg}\n--- END FILE ---\n"
        return content, estimate_tokens(content)

    try:
        # Validate file existence and type
        if not path.exists():
            content = f"\n--- FILE NOT FOUND: {file_path} ---\nError: File does not exist\n--- END FILE ---\n"
            return content, estimate_tokens(content)

        if not path.is_file():
            content = f"\n--- NOT A FILE: {file_path} ---\nError: Path is not a file\n--- END FILE ---\n"
            return content, estimate_tokens(content)

        # Check file size to prevent memory exhaustion
        file_size = path.stat().st_size
        if file_size > max_size:
            content = f"\n--- FILE TOO LARGE: {file_path} ---\nFile size: {file_size:,} bytes (max: {max_size:,})\n--- END FILE ---\n"
            return content, estimate_tokens(content)

        # Read the file with UTF-8 encoding, replacing invalid characters
        # This ensures we can handle files with mixed encodings
        with open(path, encoding="utf-8", errors="replace") as f:
            file_content = f.read()

        # Format with clear delimiters that help the AI understand file boundaries
        # Using consistent markers makes it easier for the model to parse
        formatted = f"\n--- BEGIN FILE: {file_path} ---\n{file_content}\n--- END FILE: {file_path} ---\n"
        return formatted, estimate_tokens(formatted)

    except Exception as e:
        content = f"\n--- ERROR READING FILE: {file_path} ---\nError: {str(e)}\n--- END FILE ---\n"
        return content, estimate_tokens(content)


def read_files(
    file_paths: list[str],
    code: Optional[str] = None,
    max_tokens: Optional[int] = None,
    reserve_tokens: int = 50_000,
) -> str:
    """
    Read multiple files and optional direct code with smart token management.

    This function implements intelligent token budgeting to maximize the amount
    of relevant content that can be included in an AI prompt while staying
    within token limits. It prioritizes direct code and reads files until
    the token budget is exhausted.

    Args:
        file_paths: List of file or directory paths (absolute paths required)
        code: Optional direct code to include (prioritized over files)
        max_tokens: Maximum tokens to use (defaults to MAX_CONTEXT_TOKENS)
        reserve_tokens: Tokens to reserve for prompt and response (default 50K)

    Returns:
        str: All file contents formatted for AI consumption
    """
    if max_tokens is None:
        max_tokens = MAX_CONTEXT_TOKENS

    content_parts = []
    total_tokens = 0
    available_tokens = max_tokens - reserve_tokens

    files_skipped = []

    # Priority 1: Handle direct code if provided
    # Direct code is prioritized because it's explicitly provided by the user
    if code:
        formatted_code = f"\n--- BEGIN DIRECT CODE ---\n{code}\n--- END DIRECT CODE ---\n"
        code_tokens = estimate_tokens(formatted_code)

        if code_tokens <= available_tokens:
            content_parts.append(formatted_code)
            total_tokens += code_tokens
            available_tokens -= code_tokens

    # Priority 2: Process file paths
    if file_paths:
        # Expand directories to get all individual files
        all_files = expand_paths(file_paths)

        if not all_files and file_paths:
            # No files found but paths were provided
            content_parts.append(f"\n--- NO FILES FOUND ---\nProvided paths: {', '.join(file_paths)}\n--- END ---\n")
        else:
            # Read files sequentially until token limit is reached
            for file_path in all_files:
                if total_tokens >= available_tokens:
                    files_skipped.append(file_path)
                    continue

                file_content, file_tokens = read_file_content(file_path)

                # Check if adding this file would exceed limit
                if total_tokens + file_tokens <= available_tokens:
                    content_parts.append(file_content)
                    total_tokens += file_tokens
                else:
                    # File too large for remaining budget
                    files_skipped.append(file_path)

    # Add informative note about skipped files to help users understand
    # what was omitted and why
    if files_skipped:
        skip_note = "\n\n--- SKIPPED FILES (TOKEN LIMIT) ---\n"
        skip_note += f"Total skipped: {len(files_skipped)}\n"
        # Show first 10 skipped files as examples
        for _i, file_path in enumerate(files_skipped[:10]):
            skip_note += f"  - {file_path}\n"
        if len(files_skipped) > 10:
            skip_note += f"  ... and {len(files_skipped) - 10} more\n"
        skip_note += "--- END SKIPPED FILES ---\n"
        content_parts.append(skip_note)

    return "\n\n".join(content_parts) if content_parts else ""
