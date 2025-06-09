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

import os
from pathlib import Path
from typing import List, Optional, Tuple, Set

from .token_utils import estimate_tokens, MAX_CONTEXT_TOKENS

# Get project root from environment or use current directory
# This defines the sandbox directory where file access is allowed
# Security: All file operations are restricted to this directory and its children
default_root = os.environ.get("MCP_PROJECT_ROOT", os.getcwd())

# If current directory is "/" (can happen when launched from Claude Desktop),
# use the user's home directory as a safe default
if default_root == "/" or os.getcwd() == "/":
    default_root = os.path.expanduser("~")

PROJECT_ROOT = Path(default_root).resolve()

# Critical Security Check: Prevent running with overly permissive root
# Setting PROJECT_ROOT to "/" would allow access to the entire filesystem,
# which is a severe security vulnerability
if str(PROJECT_ROOT) == "/":
    raise RuntimeError(
        "Security Error: PROJECT_ROOT cannot be '/'. "
        "This would give access to the entire filesystem. "
        "Please set MCP_PROJECT_ROOT environment variable to a specific directory."
    )


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


def resolve_and_validate_path(path_str: str) -> Path:
    """
    Validates that a path is absolute and resolves it.

    This is the primary security function that ensures all file access
    is properly sandboxed. It enforces two critical security policies:
    1. All paths must be absolute (no ambiguity)
    2. All paths must resolve to within PROJECT_ROOT (sandboxing)

    Args:
        path_str: Path string (must be absolute)

    Returns:
        Resolved Path object that is guaranteed to be within PROJECT_ROOT

    Raises:
        ValueError: If path is not absolute
        PermissionError: If path is outside allowed directory
    """
    # Create a Path object from the user-provided path
    user_path = Path(path_str)

    # Security Policy 1: Require absolute paths to prevent ambiguity
    # Relative paths could be interpreted differently depending on working directory
    if not user_path.is_absolute():
        raise ValueError(
            f"Relative paths are not supported. Please provide an absolute path.\n"
            f"Received: {path_str}"
        )

    # Resolve the absolute path (follows symlinks, removes .. and .)
    resolved_path = user_path.resolve()

    # Security Policy 2: Ensure the resolved path is within PROJECT_ROOT
    # This prevents directory traversal attacks (e.g., /project/../../../etc/passwd)
    try:
        resolved_path.relative_to(PROJECT_ROOT)
    except ValueError:
        raise PermissionError(
            f"Path outside project root: {path_str}\n"
            f"Project root: {PROJECT_ROOT}\n"
            f"Resolved path: {resolved_path}"
        )

    return resolved_path


def expand_paths(paths: List[str], extensions: Optional[Set[str]] = None) -> List[str]:
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
                # Filter directories in-place to skip hidden and cache directories
                # This prevents descending into .git, .venv, __pycache__, etc.
                dirs[:] = [
                    d for d in dirs if not d.startswith(".") and d != "__pycache__"
                ]

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


def read_file_content(file_path: str, max_size: int = 1_000_000) -> Tuple[str, int]:
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
        content = f"\n--- ERROR ACCESSING FILE: {file_path} ---\nError: {str(e)}\n--- END FILE ---\n"
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
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            file_content = f.read()

        # Format with clear delimiters that help the AI understand file boundaries
        # Using consistent markers makes it easier for the model to parse
        formatted = f"\n--- BEGIN FILE: {file_path} ---\n{file_content}\n--- END FILE: {file_path} ---\n"
        return formatted, estimate_tokens(formatted)

    except Exception as e:
        content = f"\n--- ERROR READING FILE: {file_path} ---\nError: {str(e)}\n--- END FILE ---\n"
        return content, estimate_tokens(content)


def read_files(
    file_paths: List[str],
    code: Optional[str] = None,
    max_tokens: Optional[int] = None,
    reserve_tokens: int = 50_000,
) -> Tuple[str, str]:
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
        Tuple of (full_content, brief_summary)
        - full_content: All file contents formatted for AI consumption
        - brief_summary: Human-readable summary of what was processed
    """
    if max_tokens is None:
        max_tokens = MAX_CONTEXT_TOKENS

    content_parts = []
    summary_parts = []
    total_tokens = 0
    available_tokens = max_tokens - reserve_tokens

    files_read = []
    files_skipped = []
    dirs_processed = []

    # Priority 1: Handle direct code if provided
    # Direct code is prioritized because it's explicitly provided by the user
    if code:
        formatted_code = (
            f"\n--- BEGIN DIRECT CODE ---\n{code}\n--- END DIRECT CODE ---\n"
        )
        code_tokens = estimate_tokens(formatted_code)

        if code_tokens <= available_tokens:
            content_parts.append(formatted_code)
            total_tokens += code_tokens
            available_tokens -= code_tokens
            # Create a preview for the summary
            code_preview = code[:50] + "..." if len(code) > 50 else code
            summary_parts.append(f"Direct code: {code_preview}")
        else:
            summary_parts.append("Direct code skipped (too large)")

    # Priority 2: Process file paths
    if file_paths:
        # Track which paths are directories for summary
        for path in file_paths:
            try:
                if Path(path).is_dir():
                    dirs_processed.append(path)
            except Exception:
                pass  # Ignore invalid paths

        # Expand directories to get all individual files
        all_files = expand_paths(file_paths)

        if not all_files and file_paths:
            # No files found but paths were provided
            content_parts.append(
                f"\n--- NO FILES FOUND ---\nProvided paths: {', '.join(file_paths)}\n--- END ---\n"
            )
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
                    files_read.append(file_path)
                else:
                    # File too large for remaining budget
                    files_skipped.append(file_path)

    # Build human-readable summary of what was processed
    if dirs_processed:
        summary_parts.append(f"Processed {len(dirs_processed)} dir(s)")
    if files_read:
        summary_parts.append(f"Read {len(files_read)} file(s)")
    if files_skipped:
        summary_parts.append(f"Skipped {len(files_skipped)} file(s) (token limit)")
    if total_tokens > 0:
        summary_parts.append(f"~{total_tokens:,} tokens used")

    # Add informative note about skipped files to help users understand
    # what was omitted and why
    if files_skipped:
        skip_note = "\n\n--- SKIPPED FILES (TOKEN LIMIT) ---\n"
        skip_note += f"Total skipped: {len(files_skipped)}\n"
        # Show first 10 skipped files as examples
        for i, file_path in enumerate(files_skipped[:10]):
            skip_note += f"  - {file_path}\n"
        if len(files_skipped) > 10:
            skip_note += f"  ... and {len(files_skipped) - 10} more\n"
        skip_note += "--- END SKIPPED FILES ---\n"
        content_parts.append(skip_note)

    full_content = "\n\n".join(content_parts) if content_parts else ""
    summary = " | ".join(summary_parts) if summary_parts else "No input provided"

    return full_content, summary
