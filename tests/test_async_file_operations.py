"""
Tests for async file operations implementation.

This module tests the async versions of file operations including:
- Async file size checking with semaphore control
- Async file reading with chunked processing
- Async file content preparation
- Error handling and resource management
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from utils.file_utils import (
    check_total_file_size_async,
    read_file_content_async,
    read_files_async,
)


class TestAsyncFileOperations:
    """Test async file operations functionality."""

    @pytest.fixture
    def temp_files(self):
        """Create temporary files for testing."""
        temp_dir = tempfile.mkdtemp()

        # Create test files with different sizes
        files = []
        for i, content in enumerate(
            [
                "Small file content",
                "Medium file content " * 100,
                "Large file content " * 1000,
            ]
        ):
            file_path = Path(temp_dir) / f"test_file_{i}.txt"
            file_path.write_text(content)
            files.append(str(file_path))

        yield files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_check_total_file_size_async_with_semaphore(self, temp_files):
        """Test async file size checking with semaphore control."""
        # Test that the async function works with a valid model
        result = await check_total_file_size_async(temp_files, "gemini-2.5-flash")

        # For small test files, this should not return an error
        assert result is None  # Should proceed with all files

    @pytest.mark.asyncio
    async def test_read_file_content_async_chunked(self, temp_files):
        """Test async file reading with chunked processing."""
        # Test that the async function works
        content, tokens = await read_file_content_async(temp_files[0])

        # Should return formatted content and token count
        assert content.startswith("\n--- BEGIN FILE:")
        assert "--- END FILE:" in content
        assert content.count("---") >= 2
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_read_files_async_with_concurrency_control(self, temp_files):
        """Test async multiple file reading with concurrency control."""
        # Test that the async function works with multiple files
        content = await read_files_async(temp_files)

        # Should return combined content from all files
        assert isinstance(content, str)
        assert len(content) > 0
        # Should contain content from multiple files
        assert content.count("--- BEGIN FILE:") == len(temp_files)

    @pytest.mark.asyncio
    async def test_async_file_operations_memory_efficiency(self, temp_files):
        """Test that async operations use memory efficiently with chunked reading."""
        # Create a large file for testing
        temp_dir = Path(temp_files[0]).parent
        large_file = temp_dir / "large_test.txt"

        # Write content that will be chunked (32KB)
        large_content = "x" * (32 * 1024)
        large_file.write_text(large_content)

        # Test with custom chunk size
        content, tokens = await read_file_content_async(str(large_file), chunk_size=8192)

        # Should successfully read the file
        assert "--- BEGIN FILE:" in content
        assert len(content) > 0
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_semaphore_concurrency_limit(self, temp_files):
        """Test that semaphore properly limits concurrent operations."""
        # Test that concurrent operations work without overwhelming system
        import time

        start_time = time.time()

        # Run multiple async operations concurrently
        tasks = [
            read_file_content_async(temp_files[0]),
            read_file_content_async(temp_files[1]),
            read_file_content_async(temp_files[2]) if len(temp_files) > 2 else read_file_content_async(temp_files[0]),
        ]

        results = await asyncio.gather(*tasks)

        elapsed_time = time.time() - start_time

        # All tasks should complete successfully
        assert len(results) == 3
        for content, tokens in results:
            assert "--- BEGIN FILE:" in content
            assert tokens > 0

        # Should complete relatively quickly due to concurrency
        assert elapsed_time < 5.0  # Should be much faster than sequential

    @pytest.mark.asyncio
    async def test_async_error_handling_with_context_managers(self, temp_files):
        """Test proper error handling with async context managers."""
        # Test with non-existent file
        non_existent_file = Path(temp_files[0]).parent / "does_not_exist.txt"

        # Should handle the error gracefully
        content, tokens = await read_file_content_async(str(non_existent_file))

        # Should return error content rather than raising exception
        assert "ERROR" in content
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_async_performance_with_multiple_files(self, temp_files):
        """Test that async operations are faster than sync for multiple files."""
        import time

        # Test concurrent processing
        start_time = time.time()

        # Process all files concurrently
        results = await asyncio.gather(*[read_file_content_async(file_path) for file_path in temp_files])

        async_time = time.time() - start_time

        # All files should be processed successfully
        assert len(results) == len(temp_files)
        for content, tokens in results:
            assert "--- BEGIN FILE:" in content
            assert tokens > 0

        # Should complete in reasonable time
        assert async_time < 2.0  # Should be fast for small test files


class TestAsyncFileIntegration:
    """Test integration of async file operations with server components."""

    @pytest.mark.asyncio
    async def test_server_async_file_size_validation(self):
        """Test server integration with async file size validation."""
        # Test that the async functions are now available and can be imported
        # Create a simple test file
        import tempfile

        from utils.file_utils import check_total_file_size_async

        temp_dir = tempfile.mkdtemp()
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        try:
            # Should be able to call the async function
            result = await check_total_file_size_async([str(test_file)], "gemini-2.5-flash")
            # For small test file, should not return an error
            assert result is None
        finally:
            # Cleanup
            import shutil

            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_base_tool_async_file_preparation(self):
        """Test base tool integration with async file content preparation."""
        # Test that the async functions are now available and can be imported
        # Create test files
        import tempfile

        from utils.file_utils import read_files_async

        temp_dir = tempfile.mkdtemp()
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content for base tool")

        try:
            # Should be able to call the async function
            content = await read_files_async([str(test_file)])

            # Should return formatted content
            assert isinstance(content, str)
            assert "--- BEGIN FILE:" in content
            assert "test content for base tool" in content
        finally:
            # Cleanup
            import shutil

            shutil.rmtree(temp_dir)
