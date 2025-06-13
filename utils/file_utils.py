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

from .token_utils import DEFAULT_CONTEXT_WINDOW, estimate_tokens

logger = logging.getLogger(__name__)

# Get workspace root for Docker path translation
# IMPORTANT: WORKSPACE_ROOT should contain the HOST path (e.g., /Users/john/project)
# that gets mounted to /workspace in the Docker container. This enables proper
# path translation between host absolute paths and container workspace paths.
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
    "/workspace",  # Container path - WORKSPACE_ROOT should be host path
    "C:\\",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Users",
}

# Validate WORKSPACE_ROOT for security if it's set
if WORKSPACE_ROOT:
    # Resolve to canonical path for comparison
    resolved_workspace = Path(WORKSPACE_ROOT).resolve()

    # Special check for /workspace - common configuration mistake
    if str(resolved_workspace) == "/workspace":
        raise RuntimeError(
            f"Configuration Error: WORKSPACE_ROOT should be set to the HOST path, not the container path. "
            f"Found: WORKSPACE_ROOT={WORKSPACE_ROOT} "
            f"Expected: WORKSPACE_ROOT should be set to your host directory path (e.g., $HOME) "
            f"that contains all files Claude might reference. "
            f"This path gets mounted to /workspace inside the Docker container."
        )

    # Check against other dangerous paths
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

# Security boundary
# In Docker: use /workspace (container directory)
# In tests/direct mode: use WORKSPACE_ROOT (host directory)
if CONTAINER_WORKSPACE.exists():
    # Running in Docker container
    SECURITY_ROOT = CONTAINER_WORKSPACE
elif WORKSPACE_ROOT:
    # Running in tests or direct mode with WORKSPACE_ROOT set
    SECURITY_ROOT = Path(WORKSPACE_ROOT).resolve()
else:
    # Fallback for backward compatibility (should not happen in normal usage)
    SECURITY_ROOT = Path.home()


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
    # Additional build and temp directories
    "out",
    ".next",
    ".nuxt",
    ".cache",
    ".temp",
    ".tmp",
    "bower_components",
    "vendor",
    ".sass-cache",
    ".gradle",
    ".m2",
    "coverage",
    # OS-specific directories
    ".DS_Store",
    "Thumbs.db",
    # Python specific
    "*.egg-info",
    ".eggs",
    "wheels",
    ".Python",
    # IDE and editor directories
    ".sublime",
    ".atom",
    ".brackets",
    "*.swp",
    "*.swo",
    "*~",
    # Documentation build
    "_build",
    "site",
    # Mobile development
    ".expo",
    ".flutter",
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


def is_mcp_directory(path: Path) -> bool:
    """
    Check if a directory is the MCP server's own directory.

    This prevents the MCP from including its own code when scanning projects
    where the MCP has been cloned as a subdirectory.

    Args:
        path: Directory path to check

    Returns:
        True if this appears to be the MCP directory
    """
    if not path.is_dir():
        return False

    # Check for multiple signature files to be sure
    matches = 0
    for sig_file in MCP_SIGNATURE_FILES:
        if (path / sig_file).exists():
            matches += 1
            if matches >= 3:  # Require at least 3 matches to be certain
                logger.info(f"Detected MCP directory at {path}, will exclude from scanning")
                return True
    return False


def get_user_home_directory() -> Optional[Path]:
    """
    Get the user's home directory based on environment variables.

    In Docker, USER_HOME should be set to the mounted home path.
    Outside Docker, we use Path.home() or environment variables.

    Returns:
        User's home directory path or None if not determinable
    """
    # Check for explicit USER_HOME env var (set in docker-compose.yml)
    user_home = os.environ.get("USER_HOME")
    if user_home:
        return Path(user_home).resolve()

    # In container, check if we're running in Docker
    if CONTAINER_WORKSPACE.exists():
        # We're in Docker but USER_HOME not set - use WORKSPACE_ROOT as fallback
        if WORKSPACE_ROOT:
            return Path(WORKSPACE_ROOT).resolve()

    # Outside Docker, use system home
    return Path.home()


def is_home_directory_root(path: Path) -> bool:
    """
    Check if the given path is the user's home directory root.

    This prevents scanning the entire home directory which could include
    sensitive data and non-project files.

    Args:
        path: Directory path to check

    Returns:
        True if this is the home directory root
    """
    user_home = get_user_home_directory()
    if not user_home:
        return False

    try:
        resolved_path = path.resolve()
        resolved_home = user_home.resolve()

        # Check if this is exactly the home directory
        if resolved_path == resolved_home:
            logger.warning(
                f"Attempted to scan user home directory root: {path}. " f"Please specify a subdirectory instead."
            )
            return True

        # Also check common home directory patterns
        path_str = str(resolved_path).lower()
        home_patterns = [
            "/users/",  # macOS
            "/home/",  # Linux
            "c:\\users\\",  # Windows
            "c:/users/",  # Windows with forward slashes
        ]

        for pattern in home_patterns:
            if pattern in path_str:
                # Extract the user directory path
                # e.g., /Users/fahad or /home/username
                parts = path_str.split(pattern)
                if len(parts) > 1:
                    # Get the part after the pattern
                    after_pattern = parts[1]
                    # Check if we're at the user's root (no subdirectories)
                    if "/" not in after_pattern and "\\" not in after_pattern:
                        logger.warning(
                            f"Attempted to scan user home directory root: {path}. "
                            f"Please specify a subdirectory instead."
                        )
                        return True

    except Exception as e:
        logger.debug(f"Error checking if path is home directory: {e}")

    return False


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
    1. Docker host-to-container path translation (host paths -> /workspace/...)
    2. Direct mode (no translation needed)
    3. Security validation and error handling

    Docker Path Translation Logic:
    - Input: /Users/john/project/src/file.py (host path from Claude)
    - WORKSPACE_ROOT: /Users/john/project (host path in env var)
    - Output: /workspace/src/file.py (container path for file operations)

    Args:
        path_str: Original path string from the client (absolute host path)

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
        resolved_path.relative_to(SECURITY_ROOT)
    except ValueError:
        # Provide detailed error for debugging while avoiding information disclosure
        logger.warning(
            f"Access denied - path outside workspace. "
            f"Requested: {path_str}, Resolved: {resolved_path}, Workspace: {SECURITY_ROOT}"
        )
        raise PermissionError(
            f"Path outside workspace: {path_str}\nWorkspace: {SECURITY_ROOT}\nResolved path: {resolved_path}"
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

        # Safety checks for directory scanning
        if path_obj.is_dir():
            resolved_workspace = SECURITY_ROOT.resolve()
            resolved_path = path_obj.resolve()

            # Check 1: Prevent reading entire workspace root
            if resolved_path == resolved_workspace:
                logger.warning(
                    f"Ignoring request to read entire workspace directory: {path}. "
                    f"Please specify individual files or subdirectories instead."
                )
                continue

            # Check 2: Prevent scanning user's home directory root
            if is_home_directory_root(path_obj):
                logger.warning(
                    f"Skipping home directory root: {path}. " f"Please specify a project subdirectory instead."
                )
                continue

            # Check 3: Skip if this is the MCP's own directory
            if is_mcp_directory(path_obj):
                logger.info(
                    f"Skipping MCP server directory: {path}. " f"The MCP server code is excluded from project scans."
                )
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
                original_dirs = dirs[:]
                dirs[:] = []
                for d in original_dirs:
                    # Skip hidden directories
                    if d.startswith("."):
                        continue
                    # Skip excluded directories
                    if d in EXCLUDED_DIRS:
                        continue
                    # Skip MCP directories found during traversal
                    dir_path = Path(root) / d
                    if is_mcp_directory(dir_path):
                        logger.debug(f"Skipping MCP directory during traversal: {dir_path}")
                        continue
                    dirs.append(d)

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
    logger.debug(f"[FILES] read_file_content called for: {file_path}")
    try:
        # Validate path security before any file operations
        path = resolve_and_validate_path(file_path)
        logger.debug(f"[FILES] Path validated and resolved: {path}")
    except (ValueError, PermissionError) as e:
        # Return error in a format that provides context to the AI
        logger.debug(f"[FILES] Path validation failed for {file_path}: {type(e).__name__}: {e}")
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
        tokens = estimate_tokens(content)
        logger.debug(f"[FILES] Returning error content for {file_path}: {tokens} tokens")
        return content, tokens

    try:
        # Validate file existence and type
        if not path.exists():
            logger.debug(f"[FILES] File does not exist: {file_path}")
            content = f"\n--- FILE NOT FOUND: {file_path} ---\nError: File does not exist\n--- END FILE ---\n"
            return content, estimate_tokens(content)

        if not path.is_file():
            logger.debug(f"[FILES] Path is not a file: {file_path}")
            content = f"\n--- NOT A FILE: {file_path} ---\nError: Path is not a file\n--- END FILE ---\n"
            return content, estimate_tokens(content)

        # Check file size to prevent memory exhaustion
        file_size = path.stat().st_size
        logger.debug(f"[FILES] File size for {file_path}: {file_size:,} bytes")
        if file_size > max_size:
            logger.debug(f"[FILES] File too large: {file_path} ({file_size:,} > {max_size:,} bytes)")
            content = f"\n--- FILE TOO LARGE: {file_path} ---\nFile size: {file_size:,} bytes (max: {max_size:,})\n--- END FILE ---\n"
            return content, estimate_tokens(content)

        # Read the file with UTF-8 encoding, replacing invalid characters
        # This ensures we can handle files with mixed encodings
        logger.debug(f"[FILES] Reading file content for {file_path}")
        with open(path, encoding="utf-8", errors="replace") as f:
            file_content = f.read()

        logger.debug(f"[FILES] Successfully read {len(file_content)} characters from {file_path}")

        # Format with clear delimiters that help the AI understand file boundaries
        # Using consistent markers makes it easier for the model to parse
        # NOTE: These markers ("--- BEGIN FILE: ... ---") are distinct from git diff markers
        # ("--- BEGIN DIFF: ... ---") to allow AI to distinguish between complete file content
        # vs. partial diff content when files appear in both sections
        formatted = f"\n--- BEGIN FILE: {file_path} ---\n{file_content}\n--- END FILE: {file_path} ---\n"
        tokens = estimate_tokens(formatted)
        logger.debug(f"[FILES] Formatted content for {file_path}: {len(formatted)} chars, {tokens} tokens")
        return formatted, tokens

    except Exception as e:
        logger.debug(f"[FILES] Exception reading file {file_path}: {type(e).__name__}: {e}")
        content = f"\n--- ERROR READING FILE: {file_path} ---\nError: {str(e)}\n--- END FILE ---\n"
        tokens = estimate_tokens(content)
        logger.debug(f"[FILES] Returning error content for {file_path}: {tokens} tokens")
        return content, tokens


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
        max_tokens: Maximum tokens to use (defaults to DEFAULT_CONTEXT_WINDOW)
        reserve_tokens: Tokens to reserve for prompt and response (default 50K)

    Returns:
        str: All file contents formatted for AI consumption
    """
    if max_tokens is None:
        max_tokens = DEFAULT_CONTEXT_WINDOW

    logger.debug(f"[FILES] read_files called with {len(file_paths)} paths")
    logger.debug(
        f"[FILES] Token budget: max={max_tokens:,}, reserve={reserve_tokens:,}, available={max_tokens - reserve_tokens:,}"
    )

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
        logger.debug(f"[FILES] Expanding {len(file_paths)} file paths")
        all_files = expand_paths(file_paths)
        logger.debug(f"[FILES] After expansion: {len(all_files)} individual files")

        if not all_files and file_paths:
            # No files found but paths were provided
            logger.debug("[FILES] No files found from provided paths")
            content_parts.append(f"\n--- NO FILES FOUND ---\nProvided paths: {', '.join(file_paths)}\n--- END ---\n")
        else:
            # Read files sequentially until token limit is reached
            logger.debug(f"[FILES] Reading {len(all_files)} files with token budget {available_tokens:,}")
            for i, file_path in enumerate(all_files):
                if total_tokens >= available_tokens:
                    logger.debug(f"[FILES] Token budget exhausted, skipping remaining {len(all_files) - i} files")
                    files_skipped.extend(all_files[i:])
                    break

                file_content, file_tokens = read_file_content(file_path)
                logger.debug(f"[FILES] File {file_path}: {file_tokens:,} tokens")

                # Check if adding this file would exceed limit
                if total_tokens + file_tokens <= available_tokens:
                    content_parts.append(file_content)
                    total_tokens += file_tokens
                    logger.debug(f"[FILES] Added file {file_path}, total tokens: {total_tokens:,}")
                else:
                    # File too large for remaining budget
                    logger.debug(
                        f"[FILES] File {file_path} too large for remaining budget ({file_tokens:,} tokens, {available_tokens - total_tokens:,} remaining)"
                    )
                    files_skipped.append(file_path)

    # Add informative note about skipped files to help users understand
    # what was omitted and why
    if files_skipped:
        logger.debug(f"[FILES] {len(files_skipped)} files skipped due to token limits")
        skip_note = "\n\n--- SKIPPED FILES (TOKEN LIMIT) ---\n"
        skip_note += f"Total skipped: {len(files_skipped)}\n"
        # Show first 10 skipped files as examples
        for _i, file_path in enumerate(files_skipped[:10]):
            skip_note += f"  - {file_path}\n"
        if len(files_skipped) > 10:
            skip_note += f"  ... and {len(files_skipped) - 10} more\n"
        skip_note += "--- END SKIPPED FILES ---\n"
        content_parts.append(skip_note)

    result = "\n\n".join(content_parts) if content_parts else ""
    logger.debug(f"[FILES] read_files complete: {len(result)} chars, {total_tokens:,} tokens used")
    return result
