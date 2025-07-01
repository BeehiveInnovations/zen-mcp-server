"""
Streaming file reader for memory-efficient file processing.

This module provides memory-efficient file processing for files >100MB by implementing
chunked reading with configurable chunk sizes, character limits, and async operations.

Key Features:
- Memory-efficient chunked reading (default 8KB chunks)
- Support for files >100MB without memory issues
- Consistent memory usage regardless of file size
- Async operations using aiofiles
- Configurable chunk size and file size limits
- Character limits for content truncation
- Proper error handling and resource cleanup

Implementation follows Priority 8 specifications from PLAN.md for Phase 3 optimization.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from typing import Optional, Tuple

import aiofiles

from .file_utils import _add_line_numbers, _normalize_line_endings, resolve_and_validate_path, should_add_line_numbers
from .token_utils import estimate_tokens

logger = logging.getLogger(__name__)


class StreamingFileReader:
    """
    Memory-efficient file processing for large files using chunked reading.

    This class provides streaming file reading capabilities that maintain consistent
    memory usage regardless of file size, making it suitable for processing files
    larger than 100MB without memory issues.

    Features:
    - Configurable chunk size (default 8KB)
    - Max file size protection (default 100MB)
    - Character limits for content truncation
    - Async operations with aiofiles
    - Memory monitoring and validation
    - Proper error handling and resource cleanup
    """

    def __init__(
        self,
        chunk_size: int = 8192,  # 8KB default as specified in PLAN.md
        max_file_size: int = 100 * 1024 * 1024,  # 100MB default as specified
        max_concurrent: int = 5,  # Limit concurrent operations
    ):
        """
        Initialize StreamingFileReader with memory-efficient settings.

        Args:
            chunk_size: Size of each chunk to read (default 8KB)
            max_file_size: Maximum file size to process (default 100MB)
            max_concurrent: Maximum concurrent read operations (default 5)
        """
        self.chunk_size = chunk_size
        self.max_file_size = max_file_size
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

        logger.debug(
            f"StreamingFileReader initialized: chunk_size={chunk_size}, "
            f"max_file_size={max_file_size}, max_concurrent={max_concurrent}"
        )

    async def read_file_chunked(
        self, file_path: str, max_chars: Optional[int] = None, include_line_numbers: Optional[bool] = None
    ) -> str:
        """
        Read file in chunks with size limits and memory management.

        This method implements memory-efficient file reading that maintains
        consistent memory usage regardless of file size by reading in small
        chunks and processing incrementally.

        Args:
            file_path: Path to the file to read (must be absolute)
            max_chars: Maximum characters to read (None for file size limit)
            include_line_numbers: Whether to add line numbers to content

        Returns:
            File content as string, truncated if necessary

        Raises:
            ValueError: If path is invalid
            PermissionError: If path is restricted
            OSError: If file cannot be read
        """
        logger.debug(f"[STREAMING] read_file_chunked called for: {file_path}")

        async with self._semaphore:
            # Validate path security first
            try:
                path = resolve_and_validate_path(file_path)
                logger.debug(f"[STREAMING] Path validated: {path}")
            except (ValueError, PermissionError) as e:
                logger.warning(f"[STREAMING] Path validation failed for {file_path}: {e}")
                raise

            # Check file existence and type
            if not path.exists():
                raise FileNotFoundError(f"File does not exist: {file_path}")

            if not path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")

            # Check file size before reading
            file_size = path.stat().st_size
            logger.debug(f"[STREAMING] File size: {file_size:,} bytes")

            if file_size > self.max_file_size:
                raise ValueError(
                    f"File too large: {file_size:,} bytes > {self.max_file_size:,} bytes. "
                    f"Use a larger max_file_size or process file in smaller sections."
                )

            # Determine character limit
            char_limit = max_chars or self.max_file_size

            # Read file content in chunks
            content_chunks = []
            total_chars_read = 0

            try:
                async with aiofiles.open(path, encoding="utf-8", errors="replace") as f:
                    while total_chars_read < char_limit:
                        # Calculate remaining chunk size
                        remaining_chars = char_limit - total_chars_read
                        current_chunk_size = min(self.chunk_size, remaining_chars)

                        chunk = await f.read(current_chunk_size)
                        if not chunk:
                            break  # End of file

                        content_chunks.append(chunk)
                        total_chars_read += len(chunk)

                        logger.debug(f"[STREAMING] Read chunk: {len(chunk)} chars, total: {total_chars_read}")

                        # Memory safety check
                        if total_chars_read >= char_limit:
                            logger.debug(f"[STREAMING] Reached character limit: {char_limit}")
                            break

                # Combine chunks into final content
                file_content = "".join(content_chunks)

                # Normalize line endings for consistency
                file_content = _normalize_line_endings(file_content)

                # Add line numbers if requested
                add_line_numbers = should_add_line_numbers(file_path, include_line_numbers)
                if add_line_numbers:
                    file_content = _add_line_numbers(file_content)
                    logger.debug(f"[STREAMING] Added line numbers to {file_path}")

                logger.debug(
                    f"[STREAMING] Successfully read {file_path}: {len(file_content)} chars, "
                    f"chunks: {len(content_chunks)}, memory efficient: True"
                )

                return file_content

            except UnicodeDecodeError as e:
                logger.warning(f"[STREAMING] Unicode decode error for {file_path}: {e}")
                raise ValueError(f"File contains invalid UTF-8 encoding: {file_path}")
            except OSError as e:
                logger.error(f"[STREAMING] I/O error reading {file_path}: {e}")
                raise

    async def read_file_chunked_with_format(
        self, file_path: str, max_chars: Optional[int] = None, include_line_numbers: Optional[bool] = None
    ) -> Tuple[str, int]:
        """
        Read file in chunks and format with delimiters for AI consumption.

        This method combines chunked reading with the standard file formatting
        used throughout the codebase, ensuring compatibility with existing tools.

        Args:
            file_path: Path to the file to read (must be absolute)
            max_chars: Maximum characters to read (None for file size limit)
            include_line_numbers: Whether to add line numbers to content

        Returns:
            Tuple of (formatted_content, estimated_tokens)
        """
        logger.debug(f"[STREAMING] read_file_chunked_with_format called for: {file_path}")

        try:
            # Read file content using chunked reading
            file_content = await self.read_file_chunked(
                file_path, max_chars=max_chars, include_line_numbers=include_line_numbers
            )

            # Format with standard delimiters
            formatted_content = f"\n--- BEGIN FILE: {file_path} ---\n{file_content}\n--- END FILE: {file_path} ---\n"

            # Estimate tokens
            tokens = estimate_tokens(formatted_content)

            logger.debug(f"[STREAMING] Formatted {file_path}: {len(formatted_content)} chars, {tokens} tokens")

            return formatted_content, tokens

        except Exception as e:
            # Return error in consistent format
            logger.debug(f"[STREAMING] Error reading {file_path}: {type(e).__name__}: {e}")
            error_content = f"\n--- ERROR READING FILE: {file_path} ---\nError: {str(e)}\n--- END FILE ---\n"
            error_tokens = estimate_tokens(error_content)
            return error_content, error_tokens

    async def read_files_chunked(
        self,
        file_paths: list[str],
        max_total_chars: Optional[int] = None,
        include_line_numbers: bool = False,
        max_tokens: Optional[int] = None,
        reserve_tokens: int = 50_000,
    ) -> str:
        """
        Read multiple files using chunked reading with token budget management.

        This method processes multiple files using memory-efficient chunked reading
        while respecting token budgets and maintaining consistent memory usage.

        Args:
            file_paths: List of file paths to read
            max_total_chars: Maximum total characters across all files
            include_line_numbers: Whether to add line numbers to files
            max_tokens: Maximum tokens to use (for budget management)
            reserve_tokens: Tokens to reserve for prompt and response

        Returns:
            Combined formatted content from all files
        """
        logger.debug(f"[STREAMING] read_files_chunked called with {len(file_paths)} files")

        content_parts = []
        total_tokens = 0
        total_chars = 0
        files_skipped = []

        # Calculate available budget
        if max_tokens and max_tokens > reserve_tokens:
            available_tokens = max_tokens - reserve_tokens
        else:
            available_tokens = float("inf")  # No token limit

        if max_total_chars and max_total_chars > 0:
            available_chars = max_total_chars
        else:
            available_chars = float("inf")  # No character limit

        logger.debug(f"[STREAMING] Budget: available_tokens={available_tokens}, " f"available_chars={available_chars}")

        # Process files sequentially to manage budget
        for file_path in file_paths:
            # Check if we've exceeded budget
            if total_tokens >= available_tokens or total_chars >= available_chars:
                logger.debug("[STREAMING] Budget exhausted, skipping remaining files")
                files_skipped.extend(file_paths[file_paths.index(file_path) :])
                break

            try:
                # Calculate remaining character budget for this file
                if available_chars != float("inf"):
                    remaining_chars = min(available_chars - total_chars, self.max_file_size)
                else:
                    remaining_chars = self.max_file_size

                # Read file with chunked reading
                formatted_content, file_tokens = await self.read_file_chunked_with_format(
                    file_path, max_chars=remaining_chars, include_line_numbers=include_line_numbers
                )

                # Check if adding this file would exceed budget
                if total_tokens + file_tokens <= available_tokens:
                    content_parts.append(formatted_content)
                    total_tokens += file_tokens
                    total_chars += len(formatted_content)
                    logger.debug(
                        f"[STREAMING] Added {file_path}: {file_tokens} tokens, "
                        f"total: {total_tokens}/{available_tokens}"
                    )
                else:
                    logger.debug(f"[STREAMING] File {file_path} would exceed token budget, skipping")
                    files_skipped.append(file_path)

            except Exception as e:
                logger.warning(f"[STREAMING] Error processing {file_path}: {e}")
                files_skipped.append(file_path)

        # Add note about skipped files
        if files_skipped:
            skip_note = (
                f"\n--- STREAMING READER NOTE ---\n"
                f"Files skipped due to budget/size constraints: {len(files_skipped)}\n"
                f"Memory-efficient processing used chunked reading with {self.chunk_size} byte chunks\n"
                f"First few skipped: {', '.join(files_skipped[:3])}"
                f"{f' and {len(files_skipped) - 3} more...' if len(files_skipped) > 3 else ''}\n"
                f"--- END NOTE ---\n"
            )
            content_parts.append(skip_note)

        final_content = "".join(content_parts)
        logger.debug(
            f"[STREAMING] read_files_chunked completed: {len(final_content)} chars, "
            f"{total_tokens} tokens, {len(files_skipped)} files skipped"
        )

        return final_content

    async def read_file_stream(self, file_path: str, max_chars: Optional[int] = None) -> AsyncGenerator[str, None]:
        """
        Stream file content chunk by chunk for real-time processing.

        This method provides a streaming interface for processing large files
        without loading them entirely into memory, useful for real-time analysis
        or processing pipelines.

        Args:
            file_path: Path to the file to stream
            max_chars: Maximum characters to stream (None for file size limit)

        Yields:
            File content chunks as strings

        Raises:
            ValueError: If path is invalid
            PermissionError: If path is restricted
            OSError: If file cannot be read
        """
        logger.debug(f"[STREAMING] read_file_stream started for: {file_path}")

        async with self._semaphore:
            # Validate path
            path = resolve_and_validate_path(file_path)

            # Check file
            if not path.exists() or not path.is_file():
                raise FileNotFoundError(f"File not found or not a file: {file_path}")

            # Check size
            file_size = path.stat().st_size
            if file_size > self.max_file_size:
                raise ValueError(f"File too large for streaming: {file_size} bytes")

            char_limit = max_chars or self.max_file_size
            chars_streamed = 0

            try:
                async with aiofiles.open(path, encoding="utf-8", errors="replace") as f:
                    while chars_streamed < char_limit:
                        remaining = char_limit - chars_streamed
                        chunk_size = min(self.chunk_size, remaining)

                        chunk = await f.read(chunk_size)
                        if not chunk:
                            break

                        chars_streamed += len(chunk)
                        yield chunk

                        logger.debug(f"[STREAMING] Streamed chunk: {len(chunk)} chars")

            except Exception as e:
                logger.error(f"[STREAMING] Error streaming {file_path}: {e}")
                raise

        logger.debug(f"[STREAMING] Stream completed for {file_path}: {chars_streamed} chars")

    def get_memory_stats(self) -> dict:
        """
        Get memory usage statistics for the streaming reader.

        Returns:
            Dictionary with memory usage information
        """
        import psutil

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        return {
            "chunk_size": self.chunk_size,
            "max_file_size": self.max_file_size,
            "max_concurrent": self.max_concurrent,
            "memory_rss_mb": memory_info.rss / 1024 / 1024,
            "memory_vms_mb": memory_info.vms / 1024 / 1024,
            "semaphore_available": self._semaphore._value,
        }


# Convenience functions for integration with existing code


async def read_large_file_streaming(
    file_path: str,
    chunk_size: int = 8192,
    max_file_size: int = 100 * 1024 * 1024,
    max_chars: Optional[int] = None,
    include_line_numbers: Optional[bool] = None,
) -> Tuple[str, int]:
    """
    Convenience function for streaming large file reading.

    This function provides a simple interface for reading large files using
    the StreamingFileReader with sensible defaults.

    Args:
        file_path: Path to the file to read
        chunk_size: Size of chunks to read (default 8KB)
        max_file_size: Maximum file size to allow (default 100MB)
        max_chars: Maximum characters to read (None for file size limit)
        include_line_numbers: Whether to add line numbers

    Returns:
        Tuple of (formatted_content, estimated_tokens)
    """
    reader = StreamingFileReader(chunk_size=chunk_size, max_file_size=max_file_size)

    return await reader.read_file_chunked_with_format(
        file_path=file_path, max_chars=max_chars, include_line_numbers=include_line_numbers
    )


async def read_multiple_files_streaming(
    file_paths: list[str],
    chunk_size: int = 8192,
    max_file_size: int = 100 * 1024 * 1024,
    max_total_chars: Optional[int] = None,
    include_line_numbers: bool = False,
    max_tokens: Optional[int] = None,
    reserve_tokens: int = 50_000,
) -> str:
    """
    Convenience function for streaming multiple file reading.

    Args:
        file_paths: List of file paths to read
        chunk_size: Size of chunks to read (default 8KB)
        max_file_size: Maximum individual file size (default 100MB)
        max_total_chars: Maximum total characters across all files
        include_line_numbers: Whether to add line numbers
        max_tokens: Maximum tokens for budget management
        reserve_tokens: Tokens to reserve for prompt/response

    Returns:
        Combined formatted content from all files
    """
    reader = StreamingFileReader(chunk_size=chunk_size, max_file_size=max_file_size)

    return await reader.read_files_chunked(
        file_paths=file_paths,
        max_total_chars=max_total_chars,
        include_line_numbers=include_line_numbers,
        max_tokens=max_tokens,
        reserve_tokens=reserve_tokens,
    )
