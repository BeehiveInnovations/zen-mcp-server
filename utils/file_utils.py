"""
File reading utilities with directory support and token management
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple, Set

from .token_utils import estimate_tokens, MAX_CONTEXT_TOKENS


# Common code file extensions
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


def expand_paths(paths: List[str], extensions: Optional[Set[str]] = None) -> List[str]:
    """
    Expand paths to individual files, handling both files and directories.

    Args:
        paths: List of file or directory paths
        extensions: Optional set of file extensions to include

    Returns:
        List of individual file paths
    """
    if extensions is None:
        extensions = CODE_EXTENSIONS

    expanded_files = []
    seen = set()

    for path in paths:
        path_obj = Path(path)

        if not path_obj.exists():
            continue

        if path_obj.is_file():
            # Add file directly
            if str(path_obj) not in seen:
                expanded_files.append(str(path_obj))
                seen.add(str(path_obj))

        elif path_obj.is_dir():
            # Walk directory recursively
            for root, dirs, files in os.walk(path_obj):
                # Skip hidden directories and __pycache__
                dirs[:] = [
                    d for d in dirs if not d.startswith(".") and d != "__pycache__"
                ]

                for file in files:
                    # Skip hidden files
                    if file.startswith("."):
                        continue

                    file_path = Path(root) / file

                    # Check extension
                    if not extensions or file_path.suffix.lower() in extensions:
                        full_path = str(file_path)
                        if full_path not in seen:
                            expanded_files.append(full_path)
                            seen.add(full_path)

    # Sort for consistent ordering
    expanded_files.sort()
    return expanded_files


def read_file_content(file_path: str, max_size: int = 1_000_000) -> Tuple[str, int]:
    """
    Read a single file and format it for Gemini.

    Args:
        file_path: Path to file
        max_size: Maximum file size to read

    Returns:
        (formatted_content, estimated_tokens)
    """
    path = Path(file_path)

    try:
        # Check if path exists and is a file
        if not path.exists():
            content = f"\n--- FILE NOT FOUND: {file_path} ---\nError: File does not exist\n--- END FILE ---\n"
            return content, estimate_tokens(content)

        if not path.is_file():
            content = f"\n--- NOT A FILE: {file_path} ---\nError: Path is not a file\n--- END FILE ---\n"
            return content, estimate_tokens(content)

        # Check file size
        file_size = path.stat().st_size
        if file_size > max_size:
            content = f"\n--- FILE TOO LARGE: {file_path} ---\nFile size: {file_size:,} bytes (max: {max_size:,})\n--- END FILE ---\n"
            return content, estimate_tokens(content)

        # Read the file
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            file_content = f.read()

        # Format with clear delimiters for Gemini
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

    Args:
        file_paths: List of file or directory paths
        code: Optional direct code to include
        max_tokens: Maximum tokens to use (defaults to MAX_CONTEXT_TOKENS)
        reserve_tokens: Tokens to reserve for prompt and response

    Returns:
        (full_content, brief_summary)
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

    # First, handle direct code if provided
    if code:
        formatted_code = (
            f"\n--- BEGIN DIRECT CODE ---\n{code}\n--- END DIRECT CODE ---\n"
        )
        code_tokens = estimate_tokens(formatted_code)

        if code_tokens <= available_tokens:
            content_parts.append(formatted_code)
            total_tokens += code_tokens
            available_tokens -= code_tokens
            code_preview = code[:50] + "..." if len(code) > 50 else code
            summary_parts.append(f"Direct code: {code_preview}")
        else:
            summary_parts.append("Direct code skipped (too large)")

    # Expand all paths to get individual files
    if file_paths:
        # Track which paths are directories
        for path in file_paths:
            if Path(path).is_dir():
                dirs_processed.append(path)

        # Expand to get all files
        all_files = expand_paths(file_paths)

        if not all_files and file_paths:
            # No files found but paths were provided
            content_parts.append(
                f"\n--- NO FILES FOUND ---\nProvided paths: {', '.join(file_paths)}\n--- END ---\n"
            )
        else:
            # Read files up to token limit
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
                    files_skipped.append(file_path)

    # Build summary
    if dirs_processed:
        summary_parts.append(f"Processed {len(dirs_processed)} dir(s)")
    if files_read:
        summary_parts.append(f"Read {len(files_read)} file(s)")
    if files_skipped:
        summary_parts.append(f"Skipped {len(files_skipped)} file(s) (token limit)")
    if total_tokens > 0:
        summary_parts.append(f"~{total_tokens:,} tokens used")

    # Add skipped files note if any were skipped
    if files_skipped:
        skip_note = "\n\n--- SKIPPED FILES (TOKEN LIMIT) ---\n"
        skip_note += f"Total skipped: {len(files_skipped)}\n"
        # Show first 10 skipped files
        for i, file_path in enumerate(files_skipped[:10]):
            skip_note += f"  - {file_path}\n"
        if len(files_skipped) > 10:
            skip_note += f"  ... and {len(files_skipped) - 10} more\n"
        skip_note += "--- END SKIPPED FILES ---\n"
        content_parts.append(skip_note)

    full_content = "\n\n".join(content_parts) if content_parts else ""
    summary = " | ".join(summary_parts) if summary_parts else "No input provided"

    return full_content, summary
