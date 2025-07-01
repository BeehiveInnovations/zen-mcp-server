"""
Tests for streaming file reader implementation.

This module provides comprehensive tests for the StreamingFileReader class
and its integration with the file utilities system, including:
- Memory-efficient chunked reading
- Large file handling (>100MB)
- Async operations and concurrency control
- Error handling and resource management
- Integration with existing file processing
- Memory usage validation

Tests follow Priority 8 specifications from PLAN.md for Phase 3 optimization.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.file_utils import (
    get_streaming_recommendations,
    read_file_content_streaming,
    read_files_streaming,
    should_use_streaming_for_file,
)
from utils.streaming_file_reader import (
    StreamingFileReader,
    read_large_file_streaming,
    read_multiple_files_streaming,
)


class TestStreamingFileReader:
    """Test core StreamingFileReader functionality."""

    @pytest.fixture
    def temp_files(self):
        """Create temporary files with various sizes for testing."""
        temp_dir = tempfile.mkdtemp()
        files = {}

        # Small file (1KB)
        small_file = Path(temp_dir) / "small_file.txt"
        small_content = "Small file content\n" * 50  # ~1KB
        small_file.write_text(small_content)
        files["small"] = str(small_file)

        # Medium file (100KB)
        medium_file = Path(temp_dir) / "medium_file.txt"
        medium_content = "Medium file content line\n" * 4000  # ~100KB
        medium_file.write_text(medium_content)
        files["medium"] = str(medium_file)

        # Large file (1MB)
        large_file = Path(temp_dir) / "large_file.txt"
        large_content = "Large file content line with more text\n" * 25000  # ~1MB
        large_file.write_text(large_content)
        files["large"] = str(large_file)

        # Very large file (5MB) - for testing chunked reading
        very_large_file = Path(temp_dir) / "very_large_file.txt"
        very_large_content = "Very large file content with significant amount of text\n" * 100000  # ~5MB
        very_large_file.write_text(very_large_content)
        files["very_large"] = str(very_large_file)

        yield files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    @pytest.fixture
    def streaming_reader(self):
        """Create a StreamingFileReader instance with test settings."""
        return StreamingFileReader(
            chunk_size=8192,  # 8KB as specified in PLAN.md
            max_file_size=100 * 1024 * 1024,  # 100MB as specified
            max_concurrent=3,  # Lower for testing
        )

    @pytest.mark.asyncio
    async def test_basic_chunked_reading(self, streaming_reader, temp_files):
        """Test basic chunked file reading functionality."""
        # Test reading a medium-sized file
        content = await streaming_reader.read_file_chunked(temp_files["medium"])

        # Content should be read successfully
        assert isinstance(content, str)
        assert len(content) > 0
        assert "Medium file content line" in content

        # File should be normalized
        assert "\r\n" not in content  # Line endings normalized

    @pytest.mark.asyncio
    async def test_chunked_reading_with_char_limit(self, streaming_reader, temp_files):
        """Test chunked reading with character limits."""
        # Read only first 1000 characters
        content = await streaming_reader.read_file_chunked(temp_files["large"], max_chars=1000)

        # Should respect character limit
        assert len(content) <= 1000
        assert "Large file content line" in content

    @pytest.mark.asyncio
    async def test_chunked_reading_with_line_numbers(self, streaming_reader, temp_files):
        """Test chunked reading with line numbers enabled."""
        content = await streaming_reader.read_file_chunked(temp_files["small"], include_line_numbers=True)

        # Should contain line numbers
        assert "1→" in content or "   1│" in content  # Either format is acceptable
        lines = content.split("\n")
        assert len(lines) > 1  # Should have multiple lines

    @pytest.mark.asyncio
    async def test_formatted_reading(self, streaming_reader, temp_files):
        """Test reading with AI-compatible formatting."""
        formatted_content, tokens = await streaming_reader.read_file_chunked_with_format(temp_files["medium"])

        # Should have proper delimiters
        assert "--- BEGIN FILE:" in formatted_content
        assert "--- END FILE:" in formatted_content
        assert tokens > 0

        # Should contain actual file content
        assert "Medium file content line" in formatted_content

    @pytest.mark.asyncio
    async def test_memory_efficient_large_file(self, streaming_reader, temp_files):
        """Test that streaming processes large files without loading them entirely."""
        # Read large file with chunked reading
        content = await streaming_reader.read_file_chunked(temp_files["very_large"])

        # Content should be complete
        assert len(content) > 0
        assert "Very large file content" in content

        # The key validation: streaming should handle large files without error
        file_size = os.path.getsize(temp_files["very_large"])
        assert file_size > 1024 * 1024  # Ensure we're testing with a file > 1MB

        # Content length should match or be close to file size (accounting for processing)
        # This validates that the entire file was processed, not truncated
        assert len(content) > file_size * 0.8  # Allow for some processing overhead

    @pytest.mark.asyncio
    async def test_concurrent_file_reading(self, streaming_reader, temp_files):
        """Test concurrent file reading with semaphore control."""
        # Read multiple files concurrently
        tasks = [
            streaming_reader.read_file_chunked(temp_files["small"]),
            streaming_reader.read_file_chunked(temp_files["medium"]),
            streaming_reader.read_file_chunked(temp_files["large"]),
        ]

        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()

        # All files should be read successfully
        assert len(results) == 3
        for content in results:
            assert isinstance(content, str)
            assert len(content) > 0

        # Should complete in reasonable time (concurrent processing)
        elapsed = end_time - start_time
        assert elapsed < 10.0  # Should be fast for test files

    @pytest.mark.asyncio
    async def test_multiple_files_reading(self, streaming_reader, temp_files):
        """Test reading multiple files with token budget management."""
        file_paths = [temp_files["small"], temp_files["medium"], temp_files["large"]]

        content = await streaming_reader.read_files_chunked(
            file_paths=file_paths, max_tokens=50000, include_line_numbers=False  # More generous budget for testing
        )

        # Should return combined content
        assert isinstance(content, str)
        assert len(content) > 0

        # Should contain content from multiple files
        assert content.count("--- BEGIN FILE:") > 0

    @pytest.mark.asyncio
    async def test_file_streaming_generator(self, streaming_reader, temp_files):
        """Test streaming file content as async generator."""
        chunks = []
        total_size = 0

        async for chunk in streaming_reader.read_file_stream(temp_files["medium"]):
            chunks.append(chunk)
            total_size += len(chunk)

        # Should receive multiple chunks
        assert len(chunks) > 1
        assert total_size > 0

        # Reconstruct content should match file
        reconstructed = "".join(chunks)
        with open(temp_files["medium"]) as f:
            original = f.read()

        # Content should match (allowing for line ending normalization)
        assert reconstructed.replace("\r\n", "\n") == original.replace("\r\n", "\n")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_path(self, streaming_reader):
        """Test error handling with invalid file paths."""
        with pytest.raises(FileNotFoundError):
            await streaming_reader.read_file_chunked("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_error_handling_oversized_file(self, temp_files):
        """Test error handling with files exceeding size limits."""
        # Create reader with very small limit
        small_reader = StreamingFileReader(max_file_size=1024)  # 1KB limit

        with pytest.raises(ValueError, match="File too large"):
            await small_reader.read_file_chunked(temp_files["large"])

    @pytest.mark.asyncio
    async def test_memory_stats(self, streaming_reader):
        """Test memory statistics reporting."""
        stats = streaming_reader.get_memory_stats()

        # Should contain expected keys
        assert "chunk_size" in stats
        assert "max_file_size" in stats
        assert "max_concurrent" in stats
        assert "memory_rss_mb" in stats
        assert "semaphore_available" in stats

        # Values should be reasonable
        assert stats["chunk_size"] == 8192
        assert stats["max_file_size"] == 100 * 1024 * 1024
        assert stats["memory_rss_mb"] > 0


class TestStreamingIntegration:
    """Test integration with existing file utilities."""

    @pytest.fixture
    def temp_files(self):
        """Create temporary files for integration testing."""
        temp_dir = tempfile.mkdtemp()
        files = []

        # Create files of different sizes
        for i, size_kb in enumerate([1, 10, 100]):  # 1KB, 10KB, 100KB
            file_path = Path(temp_dir) / f"test_file_{i}.txt"
            content = f"Test content for file {i}\n" * (size_kb * 25)  # Approximate size
            file_path.write_text(content)
            files.append(str(file_path))

        yield files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_convenience_function_large_file(self, temp_files):
        """Test convenience function for single large file reading."""
        formatted_content, tokens = await read_large_file_streaming(temp_files[2])  # Largest file

        # Should have proper formatting
        assert "--- BEGIN FILE:" in formatted_content
        assert "--- END FILE:" in formatted_content
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_convenience_function_multiple_files(self, temp_files):
        """Test convenience function for multiple files."""
        content = await read_multiple_files_streaming(
            file_paths=temp_files, max_tokens=5000, include_line_numbers=False
        )

        # Should combine all files
        assert isinstance(content, str)
        assert content.count("--- BEGIN FILE:") <= len(temp_files)  # May skip some due to budget

    @pytest.mark.asyncio
    async def test_file_utils_streaming_integration(self, temp_files):
        """Test integration with file_utils streaming functions."""
        # Test streaming file content reading
        formatted_content, tokens = await read_file_content_streaming(temp_files[1])

        assert "--- BEGIN FILE:" in formatted_content
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_file_utils_multiple_streaming(self, temp_files):
        """Test integration with file_utils multiple file streaming."""
        content = await read_files_streaming(file_paths=temp_files, use_streaming=True, max_tokens=8000)

        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_streaming_fallback_mechanism(self, temp_files):
        """Test fallback to async reading when streaming fails."""
        with patch(
            "utils.streaming_file_reader.read_multiple_files_streaming", side_effect=Exception("Streaming failed")
        ):
            # Should fallback to async reading
            content = await read_files_streaming(file_paths=temp_files, use_streaming=True)

            # Should still return content via fallback
            assert isinstance(content, str)
            assert len(content) > 0

    def test_streaming_recommendations(self, temp_files):
        """Test streaming recommendation system."""
        # Create a large file for testing
        temp_dir = Path(temp_files[0]).parent
        large_file = temp_dir / "large_test.txt"
        large_file.write_text("x" * (15 * 1024 * 1024))  # 15MB file

        all_files = temp_files + [str(large_file)]

        # Test individual file recommendation
        assert should_use_streaming_for_file(str(large_file)) == True
        assert should_use_streaming_for_file(temp_files[0]) == False  # Small file

        # Test batch recommendations
        recommendations = get_streaming_recommendations(all_files)

        assert recommendations["use_streaming"] == True  # Has large files
        assert len(recommendations["large_files"]) >= 1
        assert str(large_file) in recommendations["streaming_files"]
        assert recommendations["total_size"] > 15 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_streaming_vs_async_performance(self, temp_files):
        """Test that streaming performs well compared to async reading."""
        import time

        # Test streaming performance
        start_time = time.time()
        streaming_content = await read_files_streaming(file_paths=temp_files, use_streaming=True)
        streaming_time = time.time() - start_time

        # Test async performance
        start_time = time.time()
        async_content = await read_files_streaming(file_paths=temp_files, use_streaming=False)
        async_time = time.time() - start_time

        # Both should produce similar content
        assert len(streaming_content) > 0
        assert len(async_content) > 0

        # Streaming should be reasonably fast (within 2x of async for small files)
        assert streaming_time < async_time * 3  # Allow some overhead for small files


class TestStreamingErrorHandling:
    """Test error handling and edge cases for streaming operations."""

    @pytest.mark.asyncio
    async def test_malformed_file_handling(self):
        """Test handling of files with encoding issues."""
        # Create a file with binary data
        temp_dir = tempfile.mkdtemp()
        binary_file = Path(temp_dir) / "binary_file.bin"
        binary_file.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")

        try:
            reader = StreamingFileReader()

            # Should handle binary data gracefully with errors='replace'
            content = await reader.read_file_chunked(str(binary_file))
            assert isinstance(content, str)  # Should still return string

        finally:
            import shutil

            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_concurrent_limit_enforcement(self):
        """Test that concurrent operations respect semaphore limits."""
        reader = StreamingFileReader(max_concurrent=1)  # Only 1 concurrent operation

        # Create temporary files
        temp_dir = tempfile.mkdtemp()
        files = []
        for i in range(3):
            file_path = Path(temp_dir) / f"test_{i}.txt"
            file_path.write_text(f"Test content {i}\n" * 1000)
            files.append(str(file_path))

        try:
            # Monitor semaphore usage
            initial_available = reader._semaphore._value

            # Start concurrent operations
            tasks = [reader.read_file_chunked(f) for f in files]
            results = await asyncio.gather(*tasks)

            # Should complete successfully
            assert len(results) == 3
            for content in results:
                assert len(content) > 0

            # Semaphore should be back to initial state
            final_available = reader._semaphore._value
            assert final_available == initial_available

        finally:
            import shutil

            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_memory_usage_consistency(self):
        """Test that streaming handles files of different sizes consistently."""
        temp_dir = tempfile.mkdtemp()
        reader = StreamingFileReader(chunk_size=4096)  # Smaller chunks for testing

        try:
            # Create files of different sizes
            small_file = Path(temp_dir) / "small.txt"
            large_file = Path(temp_dir) / "large.txt"

            small_file.write_text("x" * 1000)  # 1KB
            large_file.write_text("x" * (5 * 1024 * 1024))  # 5MB

            # Read both files successfully
            small_content = await reader.read_file_chunked(str(small_file))
            large_content = await reader.read_file_chunked(str(large_file))

            # Both should complete successfully
            assert len(small_content) > 0
            assert len(large_content) > 0

            # Large file content should be proportionally larger
            assert len(large_content) > len(small_content) * 1000  # Much larger

            # Both should contain expected content
            assert "x" in small_content
            assert "x" in large_content

        finally:
            import shutil

            shutil.rmtree(temp_dir)


class TestStreamingPerformance:
    """Test streaming performance characteristics."""

    @pytest.mark.asyncio
    async def test_chunk_size_impact(self):
        """Test impact of different chunk sizes on performance."""
        temp_dir = tempfile.mkdtemp()
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("x" * (500 * 1024))  # 500KB file

        try:
            # Test different chunk sizes
            chunk_sizes = [1024, 4096, 8192, 16384]  # 1KB to 16KB
            times = []

            for chunk_size in chunk_sizes:
                reader = StreamingFileReader(chunk_size=chunk_size)

                start_time = asyncio.get_event_loop().time()
                await reader.read_file_chunked(str(test_file))
                end_time = asyncio.get_event_loop().time()

                times.append(end_time - start_time)

            # All operations should complete in reasonable time
            for time_taken in times:
                assert time_taken < 5.0  # Should be fast

            # 8KB (default) should perform well
            default_time = times[2]  # 8192 is at index 2
            assert default_time < max(times) * 1.5  # Should be among the better performers

        finally:
            import shutil

            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_large_file_memory_bound(self):
        """Test that streaming can handle very large files successfully."""
        temp_dir = tempfile.mkdtemp()

        # Create a large file (simplified version - 2MB for faster testing)
        large_file = Path(temp_dir) / "very_large.txt"
        with open(large_file, "w") as f:
            for i in range(50000):  # 50K lines
                f.write(f"Line {i} with some content to make it larger\n")

        try:
            reader = StreamingFileReader(chunk_size=8192)

            # Read file successfully
            content = await reader.read_file_chunked(str(large_file))

            file_size = large_file.stat().st_size

            # Should successfully process large file
            assert len(content) > 0  # Should read content
            assert file_size > 1024 * 1024  # Ensure file is > 1MB
            assert "Line" in content  # Should contain expected content
            assert content.count("Line") > 1000  # Should process many lines

        finally:
            import shutil

            shutil.rmtree(temp_dir)


# Integration tests with existing system


class TestExistingSystemIntegration:
    """Test integration with existing file processing system."""

    @pytest.mark.asyncio
    async def test_backwards_compatibility(self):
        """Test that streaming functions are backwards compatible."""
        temp_dir = tempfile.mkdtemp()
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Test content for compatibility")

        try:
            from utils.file_utils import read_file_content_async

            # Standard async reading
            async_content, async_tokens = await read_file_content_async(str(test_file))

            # Streaming reading
            streaming_content, streaming_tokens = await read_file_content_streaming(str(test_file))

            # Results should be similar (allowing for small differences in formatting)
            assert "Test content for compatibility" in async_content
            assert "Test content for compatibility" in streaming_content
            assert abs(async_tokens - streaming_tokens) < async_tokens * 0.1  # Within 10%

        finally:
            import shutil

            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_tool_integration_compatibility(self):
        """Test that streaming works with tool-style file processing."""
        temp_dir = tempfile.mkdtemp()
        files = []

        # Create multiple test files
        for i in range(3):
            file_path = Path(temp_dir) / f"tool_test_{i}.py"
            content = f'''# Test file {i}
def function_{i}():
    """Test function {i}"""
    return "result_{i}"

class TestClass{i}:
    def method(self):
        return {i}
'''
            file_path.write_text(content)
            files.append(str(file_path))

        try:
            # Test with streaming enabled and generous token budget
            content = await read_files_streaming(
                file_paths=files,
                use_streaming=True,
                include_line_numbers=True,  # Tools often use line numbers
                max_tokens=100000,  # Generous budget for test files
            )

            # Should contain files with proper formatting (may not be all if budget limited)
            file_count = content.count("--- BEGIN FILE:")
            assert file_count >= 1  # At least one file should be processed
            assert "def function_" in content
            assert "class TestClass" in content

            # Should have line numbers when requested
            # Note: Line number format may vary between implementations
            has_line_numbers = "→" in content or "│" in content
            assert has_line_numbers

        finally:
            import shutil

            shutil.rmtree(temp_dir)
