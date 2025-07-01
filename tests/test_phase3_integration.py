"""
Comprehensive integration tests for Phase 3 optimization components.

This module tests the integration of all three Phase 3 optimization components:
1. Streaming File Processing (utils/streaming_file_reader.py)
2. Lazy Tool Loading (tools/factory.py)
3. Circuit Breaker System (utils/circuit_breaker.py)

The tests validate that these components work together seamlessly to provide:
- Memory-efficient large file processing
- On-demand tool loading with caching
- Graceful failure handling and recovery
- End-to-end MCP protocol compatibility
- Performance improvements under load

Integration test scenarios:
1. Large file processing with multiple lazy-loaded tools under circuit breaker protection
2. Memory stress testing with streaming + lazy loading
3. Provider failure scenarios with circuit breaker recovery
4. Concurrent tool execution with streaming file operations
5. Complete MCP workflow testing with all Phase 3 features
"""

import asyncio
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Provider integration
from providers.async_base import AsyncModelProvider, CircuitBreakerMixin

# Phase 3 component imports
from tools.factory import ToolFactory, get_tool_factory, reset_tool_factory

# MCP and tool system imports
from tools.shared.base_tool import BaseTool
from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from utils.streaming_file_reader import StreamingFileReader


class TestPhase3Integration:
    """Core integration tests for Phase 3 components working together."""

    @pytest.fixture
    def large_test_files(self):
        """Create large test files for streaming + lazy loading tests."""
        temp_dir = tempfile.mkdtemp()
        files = {}

        # Small code file (50KB) - typical source file
        small_file = Path(temp_dir) / "small_module.py"
        small_content = (
            """# Small Python module for testing
import asyncio
import logging
from typing import Optional, Dict, Any

class SmallTestClass:
    '''A test class for small file processing.'''
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(__name__)
    
    async def process_data(self, data: Dict[str, Any]) -> Optional[str]:
        '''Process data asynchronously.'''
        await asyncio.sleep(0.001)  # Simulate async work
        return f"Processed {data} for {self.name}"
    
    def validate_input(self, input_data: Any) -> bool:
        '''Validate input data.'''
        return input_data is not None and len(str(input_data)) > 0

"""
            * 200
        )  # Repeat to make ~50KB
        small_file.write_text(small_content)
        files["small"] = str(small_file)

        # Medium file (500KB) - typical large source file
        medium_file = Path(temp_dir) / "medium_module.py"
        medium_content = (
            """# Medium Python module for testing Phase 3 integration
import asyncio
import json
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

@dataclass
class MediumTestDataClass:
    '''A dataclass for medium file testing.'''
    name: str
    value: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        '''Convert to dictionary representation.'''
        return {
            'name': self.name,
            'value': self.value,
            'metadata': self.metadata.copy(),
            'tags': self.tags.copy()
        }

class MediumTestInterface(ABC):
    '''Abstract interface for medium file testing.'''
    
    @abstractmethod
    async def process_batch(self, items: List[Any]) -> List[Any]:
        '''Process a batch of items asynchronously.'''
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        '''Get processing metrics.'''
        pass

class MediumTestProcessor(MediumTestInterface):
    '''Concrete implementation for medium file processing.'''
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.processed_count = 0
        self.error_count = 0
        self._lock = threading.Lock()
    
    async def process_batch(self, items: List[Any]) -> List[Any]:
        '''Process a batch of items with error handling.'''
        results = []
        for item in items:
            try:
                # Simulate processing time
                await asyncio.sleep(0.001)
                processed_item = await self._process_single_item(item)
                results.append(processed_item)
                
                with self._lock:
                    self.processed_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing item {item}: {e}")
                with self._lock:
                    self.error_count += 1
                results.append(None)
        
        return results
    
    async def _process_single_item(self, item: Any) -> Any:
        '''Process a single item.'''
        if isinstance(item, dict):
            return {k: v * 2 if isinstance(v, (int, float)) else v 
                   for k, v in item.items()}
        elif isinstance(item, (int, float)):
            return item * 2
        else:
            return str(item).upper()
    
    def get_metrics(self) -> Dict[str, Any]:
        '''Get current processing metrics.'''
        with self._lock:
            return {
                'processed_count': self.processed_count,
                'error_count': self.error_count,
                'batch_size': self.batch_size
            }

class MediumTestCache:
    '''Cache implementation for medium file testing.'''
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        '''Get value from cache.'''
        with self._lock:
            if key in self._cache:
                self._access_times[key] = time.time()
                return self._cache[key]
            return None
    
    def put(self, key: str, value: Any) -> None:
        '''Put value in cache with LRU eviction.'''
        with self._lock:
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = value
            self._access_times[key] = time.time()
    
    def _evict_lru(self) -> None:
        '''Evict least recently used item.'''
        if not self._access_times:
            return
        
        lru_key = min(self._access_times.keys(), 
                     key=lambda k: self._access_times[k])
        del self._cache[lru_key]
        del self._access_times[lru_key]
    
    def clear(self) -> None:
        '''Clear the cache.'''
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
    
    def size(self) -> int:
        '''Get current cache size.'''
        with self._lock:
            return len(self._cache)

"""
            * 50
        )  # Repeat to make ~500KB
        medium_file.write_text(medium_content)
        files["medium"] = str(medium_file)

        # Large file (2MB) - test streaming capabilities
        large_file = Path(temp_dir) / "large_data.json"
        large_content = """[
    {
        "id": "test_data_entry_%d",
        "timestamp": "2024-01-01T%02d:%02d:%02d.000Z",
        "data": {
            "value": %d,
            "processed": false,
            "metadata": {
                "source": "test_generator",
                "version": "1.0.0",
                "tags": ["test", "phase3", "integration"],
                "config": {
                    "batch_size": 100,
                    "timeout": 30,
                    "retry_count": 3
                }
            }
        },
        "details": "This is test data entry number %d generated for Phase 3 integration testing. It contains various data types and nested structures to test streaming file processing capabilities."
    }%s"""

        with open(large_file, "w") as f:
            f.write("[\n")
            for i in range(10000):  # 10K entries = ~2MB
                entry = large_content % (i, i % 24, i % 60, i % 60, i * 42, i, "," if i < 9999 else "")
                f.write(entry)
            f.write("\n]")

        files["large"] = str(large_file)

        # Very large file (5MB) - stress test streaming
        very_large_file = Path(temp_dir) / "very_large_log.txt"
        with open(very_large_file, "w") as f:
            for i in range(50000):  # 50K log entries = ~5MB
                log_entry = f"2024-01-01T{i%24:02d}:{i%60:02d}:{i%60:02d}.{i%1000:03d}Z [INFO] Phase3IntegrationTest: Processing entry {i:06d} with data_size={i*13} bytes, memory_usage={i*7.3:.2f}MB, cpu_usage={i%100}%, status=processing, thread_id=worker_{i%10}, batch_id={i//100:04d}\n"
                f.write(log_entry)

        files["very_large"] = str(very_large_file)

        yield files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    @pytest.fixture
    def circuit_breaker_provider(self):
        """Create a mock provider with circuit breaker for testing."""

        class MockCircuitBreakerProvider:
            def __init__(self, **kwargs):
                self.base_url = kwargs.get("base_url", "test://mock-provider")
                self._should_fail = False
                self._failure_count = 0

                # Create circuit breaker manually
                self._circuit_breaker = CircuitBreaker(
                    service_name="MockProvider:test://mock-provider",
                    failure_threshold=kwargs.get("cb_failure_threshold", 3),
                    recovery_timeout=kwargs.get("cb_recovery_timeout", 0.1),
                    half_open_max_calls=kwargs.get("cb_half_open_max_calls", 2),
                    error_classifier=self._is_error_retryable,
                )

            async def generate_content_async(self, prompt, model_name, **kwargs):
                if self._should_fail:
                    self._failure_count += 1
                    raise Exception(f"Mock provider failure #{self._failure_count}")

                from unittest.mock import Mock

                return Mock(
                    content=f"Generated response for: {prompt[:50]}...",
                    usage={"input_tokens": 100, "output_tokens": 50},
                    model_name=model_name,
                )

            async def generate_content_with_circuit_breaker(self, prompt, model_name, **kwargs):
                """Generate content with circuit breaker protection."""
                try:
                    return await self._circuit_breaker.call(
                        self.generate_content_async, prompt=prompt, model_name=model_name, **kwargs
                    )
                except CircuitBreakerOpenException as e:
                    raise RuntimeError(
                        f"Service temporarily unavailable. Circuit breaker is protecting "
                        f"against failures (failed {e.failure_count} times)."
                    )

            def _is_error_retryable(self, error):
                # All mock failures should count as circuit breaker failures
                return True

            def is_circuit_breaker_open(self):
                return self._circuit_breaker.is_open()

            def get_circuit_breaker_status(self):
                return self._circuit_breaker.get_health_status()

            async def reset_circuit_breaker(self):
                await self._circuit_breaker.reset()

        return MockCircuitBreakerProvider(
            cb_failure_threshold=3, cb_recovery_timeout=0.1, cb_half_open_max_calls=2  # Fast recovery for tests
        )

    @pytest.mark.asyncio
    async def test_streaming_with_lazy_tools_integration(self, large_test_files):
        """Test streaming file processing with lazy-loaded tools."""
        # Reset tool factory for clean test
        reset_tool_factory()

        # Get fresh factory
        factory = get_tool_factory()

        # Verify no tools are loaded initially
        assert len(factory.get_loaded_tools()) == 0

        # Create streaming reader
        streaming_reader = StreamingFileReader(
            chunk_size=8192, max_file_size=10 * 1024 * 1024, max_concurrent=3  # 10MB limit
        )

        # Test that we can process large files without loading tools
        file_paths = [large_test_files["medium"], large_test_files["large"]]

        # Process files with streaming
        content = await streaming_reader.read_files_chunked(
            file_paths=file_paths,
            max_tokens=500000,  # Very generous token budget for test files
            include_line_numbers=True,
        )

        # Verify content was processed
        assert len(content) > 0
        assert "--- BEGIN FILE:" in content
        assert "MediumTestProcessor" in content or "test_data_entry" in content

        # Now lazy-load a tool and verify it works with processed content
        chat_tool = factory.get_tool("chat")
        assert chat_tool is not None
        assert factory.is_tool_loaded("chat")
        assert len(factory.get_loaded_tools()) == 1

        # Tool should be able to process the streamed content
        assert hasattr(chat_tool, "name")
        assert chat_tool.name == "chat"

        # Verify streaming reader memory efficiency
        memory_stats = streaming_reader.get_memory_stats()
        assert memory_stats["chunk_size"] == 8192
        assert memory_stats["memory_rss_mb"] > 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_streaming_and_lazy_loading(self, large_test_files, circuit_breaker_provider):
        """Test circuit breaker protection during streaming + lazy loading operations."""
        # Reset tool factory
        reset_tool_factory()
        factory = get_tool_factory()

        # Verify circuit breaker is initially closed
        assert circuit_breaker_provider.is_circuit_breaker_open() is False

        # Create streaming reader
        streaming_reader = StreamingFileReader(chunk_size=4096, max_concurrent=2)

        # Test successful operation with all components
        file_paths = [large_test_files["small"], large_test_files["medium"]]

        # Stream files successfully
        content = await streaming_reader.read_files_chunked(file_paths=file_paths, max_tokens=50000)
        assert len(content) > 0

        # Lazy load tool successfully
        version_tool = factory.get_tool("version")
        assert version_tool is not None

        # Provider should work successfully
        response = await circuit_breaker_provider.generate_content_with_circuit_breaker(
            prompt="Test prompt", model_name="test-model"
        )
        assert response.content.startswith("Generated response")

        # Now simulate provider failures
        circuit_breaker_provider._should_fail = True

        # Trigger circuit breaker opening
        for _ in range(3):  # failure_threshold = 3
            with pytest.raises(Exception, match="Mock provider failure"):
                await circuit_breaker_provider.generate_content_with_circuit_breaker(
                    prompt="Failing prompt", model_name="test-model"
                )

        # Circuit breaker should now be open
        assert circuit_breaker_provider.is_circuit_breaker_open() is True

        # Verify that streaming and lazy loading still work independently
        more_content = await streaming_reader.read_file_chunked(large_test_files["small"])
        assert len(more_content) > 0

        listmodels_tool = factory.get_tool("listmodels")
        assert listmodels_tool is not None
        assert len(factory.get_loaded_tools()) == 2  # version + listmodels

        # Provider should fast-fail
        with pytest.raises(RuntimeError, match="Service temporarily unavailable"):
            await circuit_breaker_provider.generate_content_with_circuit_breaker(
                prompt="Should fast-fail", model_name="test-model"
            )

    @pytest.mark.asyncio
    async def test_concurrent_operations_all_components(self, large_test_files, circuit_breaker_provider):
        """Test concurrent operations involving all Phase 3 components."""
        reset_tool_factory()
        factory = get_tool_factory()

        streaming_reader = StreamingFileReader(chunk_size=8192, max_concurrent=5)

        # Define concurrent operations
        async def stream_files_operation():
            return await streaming_reader.read_files_chunked(
                file_paths=[large_test_files["medium"], large_test_files["large"]],
                max_tokens=500000,  # Very generous budget
            )

        async def lazy_load_tools_operation():
            tools = []
            for tool_name in ["chat", "version", "listmodels", "analyze"]:
                tool = factory.get_tool(tool_name)
                if tool:
                    tools.append(tool)
            return tools

        async def circuit_breaker_operation():
            responses = []
            for i in range(5):
                response = await circuit_breaker_provider.generate_content_with_circuit_breaker(
                    prompt=f"Concurrent request {i}", model_name="test-model"
                )
                responses.append(response)
                await asyncio.sleep(0.01)  # Small delay between requests
            return responses

        # Execute all operations concurrently
        start_time = time.time()

        results = await asyncio.gather(
            stream_files_operation(), lazy_load_tools_operation(), circuit_breaker_operation(), return_exceptions=True
        )

        end_time = time.time()

        # Verify all operations completed successfully
        streaming_content, loaded_tools, provider_responses = results

        # Check streaming results
        assert isinstance(streaming_content, str)
        assert len(streaming_content) > 0
        assert "--- BEGIN FILE:" in streaming_content

        # Check lazy loading results
        assert isinstance(loaded_tools, list)
        assert len(loaded_tools) >= 3  # Should load at least 3 tools
        assert all(isinstance(tool, BaseTool) for tool in loaded_tools)

        # Check circuit breaker results
        assert isinstance(provider_responses, list)
        assert len(provider_responses) == 5
        assert all(hasattr(resp, "content") for resp in provider_responses)

        # Verify performance - concurrent operations should be faster than sequential
        assert end_time - start_time < 10.0  # Should complete within 10 seconds

        # Verify tool factory state
        assert len(factory.get_loaded_tools()) >= 3
        metrics = factory.get_metrics()
        assert metrics["cached_tools"] >= 3

        # Verify circuit breaker health
        assert circuit_breaker_provider.is_circuit_breaker_open() is False

    @pytest.mark.asyncio
    async def test_memory_stress_with_all_components(self, large_test_files):
        """Test memory efficiency under stress with all Phase 3 components."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        reset_tool_factory()
        factory = get_tool_factory()

        # Create multiple streaming readers for stress testing
        readers = [StreamingFileReader(chunk_size=4096, max_concurrent=2) for _ in range(3)]

        # Large file processing tasks
        streaming_tasks = []
        for i, reader in enumerate(readers):
            task = reader.read_files_chunked(
                file_paths=[large_test_files["large"], large_test_files["very_large"]],
                max_tokens=200000,  # Large token budget
                include_line_numbers=True,
            )
            streaming_tasks.append(task)

        # Tool loading tasks
        tool_loading_tasks = []
        all_tools = factory.get_available_tools()
        for tool_name in all_tools[:10]:  # Load first 10 tools
            task = asyncio.create_task(asyncio.to_thread(factory.get_tool, tool_name))
            tool_loading_tasks.append(task)

        # Execute stress test
        all_tasks = streaming_tasks + tool_loading_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Check memory usage after stress test
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Verify results
        streaming_results = results[: len(streaming_tasks)]
        tool_results = results[len(streaming_tasks) :]

        # All streaming operations should succeed
        for result in streaming_results:
            assert isinstance(result, str)
            assert len(result) > 0

        # Tool loading should succeed
        successful_tools = [r for r in tool_results if isinstance(r, BaseTool)]
        assert len(successful_tools) >= 5  # At least half should load successfully

        # Memory growth should be reasonable (< 200MB for stress test)
        memory_growth_mb = memory_growth / 1024 / 1024
        assert memory_growth_mb < 200, f"Memory growth {memory_growth_mb:.1f}MB exceeds 200MB limit"

        # Verify streaming readers maintained efficiency
        for reader in readers:
            stats = reader.get_memory_stats()
            assert stats["chunk_size"] == 4096
            assert stats["semaphore_available"] >= 0

    @pytest.mark.asyncio
    async def test_failure_recovery_integration(self, large_test_files, circuit_breaker_provider):
        """Test failure recovery across all Phase 3 components."""
        reset_tool_factory()
        factory = get_tool_factory()

        streaming_reader = StreamingFileReader(chunk_size=8192)

        # Step 1: Establish normal operation
        content = await streaming_reader.read_file_chunked(large_test_files["medium"])
        tool = factory.get_tool("chat")
        response = await circuit_breaker_provider.generate_content_with_circuit_breaker(
            prompt="Initial test", model_name="test-model"
        )

        assert len(content) > 0
        assert tool is not None
        assert response.content.startswith("Generated response")

        # Step 2: Introduce failures
        circuit_breaker_provider._should_fail = True

        # Open circuit breaker
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker_provider.generate_content_with_circuit_breaker(
                    prompt="Failing", model_name="test-model"
                )

        assert circuit_breaker_provider.is_circuit_breaker_open()

        # Simulate tool loading failure
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Simulated import failure")
            failed_tool = factory.get_tool("debug")
            assert failed_tool is None  # Should handle failure gracefully

        # Step 3: Verify other components still work during failures
        # Streaming should still work
        more_content = await streaming_reader.read_file_chunked(large_test_files["small"])
        assert len(more_content) > 0

        # Previously loaded tools should still be available
        cached_tool = factory.get_tool("chat")  # Should hit cache
        assert cached_tool is tool  # Same instance from cache

        # Step 4: Recovery
        # Wait for circuit breaker recovery timeout
        await asyncio.sleep(0.2)  # recovery_timeout = 0.1s, add buffer

        # Fix provider
        circuit_breaker_provider._should_fail = False

        # Circuit breaker should allow recovery
        recovery_response = await circuit_breaker_provider.generate_content_with_circuit_breaker(
            prompt="Recovery test", model_name="test-model"
        )
        assert recovery_response.content.startswith("Generated response")
        assert not circuit_breaker_provider.is_circuit_breaker_open()

        # New tools should load successfully again
        new_tool = factory.get_tool("version")
        assert new_tool is not None

        # All components should work together after recovery
        final_content = await streaming_reader.read_files_chunked(
            file_paths=[large_test_files["small"], large_test_files["medium"]], max_tokens=50000
        )
        assert len(final_content) > 0
        assert factory.is_tool_loaded("chat")
        assert factory.is_tool_loaded("version")

    @pytest.mark.asyncio
    async def test_end_to_end_mcp_workflow(self, large_test_files):
        """Test end-to-end MCP workflow using all Phase 3 components."""
        reset_tool_factory()
        factory = get_tool_factory()

        # Simulate MCP tool call workflow that would use all components

        # 1. Tool discovery (lazy loading)
        available_tools = factory.get_available_tools()
        assert len(available_tools) > 0
        assert "chat" in available_tools
        assert "analyze" in available_tools

        # No tools loaded yet
        assert len(factory.get_loaded_tools()) == 0

        # 2. Tool instantiation on demand (lazy loading)
        analyze_tool = factory.get_tool("analyze")
        assert analyze_tool is not None
        assert factory.is_tool_loaded("analyze")
        assert len(factory.get_loaded_tools()) == 1

        # 3. File processing for tool input (streaming)
        streaming_reader = StreamingFileReader(chunk_size=8192)

        # Simulate analyze tool reading project files
        project_files = [large_test_files["small"], large_test_files["medium"], large_test_files["large"]]

        # Process files with streaming for memory efficiency
        file_content = await streaming_reader.read_files_chunked(
            file_paths=project_files, max_tokens=150000, include_line_numbers=True
        )

        assert len(file_content) > 0
        assert file_content.count("--- BEGIN FILE:") >= 1
        assert "→" in file_content or "│" in file_content  # Line numbers

        # 4. Load additional tools as needed (lazy loading)
        chat_tool = factory.get_tool("chat")
        version_tool = factory.get_tool("version")

        assert chat_tool is not None
        assert version_tool is not None
        assert len(factory.get_loaded_tools()) == 3

        # 5. Verify tool caching efficiency
        cached_analyze = factory.get_tool("analyze")
        assert cached_analyze is analyze_tool  # Same instance

        metrics = factory.get_metrics()
        assert metrics["cache_hits"] >= 1
        assert metrics["cache_efficiency"] > 0

        # 6. Concurrent tool usage (realistic MCP scenario)
        async def use_tool_concurrently(tool_name, file_path):
            tool = factory.get_tool(tool_name)
            content = await streaming_reader.read_file_chunked(file_path, max_chars=50000)
            return {"tool": tool.name, "content_length": len(content)}

        concurrent_tasks = [
            use_tool_concurrently("chat", large_test_files["small"]),
            use_tool_concurrently("analyze", large_test_files["medium"]),
            use_tool_concurrently("version", large_test_files["large"]),
        ]

        concurrent_results = await asyncio.gather(*concurrent_tasks)

        # All tasks should complete successfully
        assert len(concurrent_results) == 3
        for result in concurrent_results:
            assert "tool" in result
            assert "content_length" in result
            assert result["content_length"] > 0

        # 7. Memory efficiency verification
        memory_stats = streaming_reader.get_memory_stats()
        assert memory_stats["memory_rss_mb"] > 0

        # Streaming should have processed large files without excessive memory
        assert memory_stats["chunk_size"] == 8192

        # 8. Cleanup verification
        factory.cleanup_all_tools()
        assert len(factory.get_loaded_tools()) == 0

        await streaming_reader.aclose() if hasattr(streaming_reader, "aclose") else None

    @pytest.mark.asyncio
    async def test_phase3_performance_characteristics(self, large_test_files):
        """Test performance characteristics of Phase 3 components integration."""
        reset_tool_factory()

        # Measure startup time (should be fast due to lazy loading)
        startup_start = time.time()
        factory = get_tool_factory()
        streaming_reader = StreamingFileReader()
        startup_time = time.time() - startup_start

        # Startup should be very fast (< 100ms)
        assert startup_time < 0.1, f"Startup took {startup_time:.3f}s, expected < 0.1s"

        # No tools should be loaded at startup
        assert len(factory.get_loaded_tools()) == 0

        # Measure first tool load time
        first_load_start = time.time()
        first_tool = factory.get_tool("version")
        first_load_time = time.time() - first_load_start

        assert first_tool is not None
        assert first_load_time < 1.0  # Should load within 1 second

        # Measure cached access time
        cache_access_start = time.time()
        cached_tool = factory.get_tool("version")
        cache_access_time = time.time() - cache_access_start

        assert cached_tool is first_tool  # Same instance
        assert cache_access_time < 0.01  # Cache access should be very fast

        # Measure streaming performance
        stream_start = time.time()
        content = await streaming_reader.read_files_chunked(
            file_paths=[large_test_files["large"]], max_tokens=100000  # 2MB file
        )
        stream_time = time.time() - stream_start

        assert len(content) > 0
        assert stream_time < 5.0  # Should process 2MB file within 5 seconds

        # Verify performance ratios
        assert cache_access_time < first_load_time * 0.1  # Cache should be 10x+ faster

        # Memory efficiency check
        memory_stats = streaming_reader.get_memory_stats()
        assert memory_stats["chunk_size"] == 8192  # Reasonable chunk size
        assert memory_stats["memory_rss_mb"] < 100  # Should not use excessive memory


class TestPhase3EdgeCases:
    """Test edge cases and error conditions for Phase 3 integration."""

    @pytest.fixture
    def problematic_files(self):
        """Create files that might cause issues for testing edge cases."""
        temp_dir = tempfile.mkdtemp()
        files = {}

        # Empty file
        empty_file = Path(temp_dir) / "empty.txt"
        empty_file.write_text("")
        files["empty"] = str(empty_file)

        # Binary file
        binary_file = Path(temp_dir) / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\xff\xfe\xfd" * 1000)
        files["binary"] = str(binary_file)

        # Very long lines
        long_lines_file = Path(temp_dir) / "long_lines.txt"
        long_line = "x" * 10000  # 10KB line
        long_lines_file.write_text("\n".join([long_line] * 100))
        files["long_lines"] = str(long_lines_file)

        yield files

        import shutil

        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_streaming_with_problematic_files(self, problematic_files):
        """Test streaming handles problematic files gracefully."""
        reset_tool_factory()
        factory = get_tool_factory()
        streaming_reader = StreamingFileReader(chunk_size=4096)

        # Test empty file
        empty_content = await streaming_reader.read_file_chunked(problematic_files["empty"])
        assert isinstance(empty_content, str)
        assert len(empty_content) == 0 or empty_content.strip() == ""

        # Test binary file (should handle with errors='replace')
        binary_content = await streaming_reader.read_file_chunked(problematic_files["binary"])
        assert isinstance(binary_content, str)  # Should still return string

        # Test long lines
        long_lines_content = await streaming_reader.read_file_chunked(problematic_files["long_lines"], max_chars=50000)
        assert isinstance(long_lines_content, str)
        assert len(long_lines_content) <= 50000

        # Tool loading should still work
        tool = factory.get_tool("version")
        assert tool is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_edge_cases(self):
        """Test circuit breaker edge cases with Phase 3 components."""

        class EdgeCaseProvider(AsyncModelProvider, CircuitBreakerMixin):
            def __init__(self):
                self.base_url = "test://edge-case"
                super().__init__(api_key="test", cb_failure_threshold=2, cb_recovery_timeout=0.1)
                self.call_count = 0

            async def generate_content_async(self, prompt, model_name, **kwargs):
                self.call_count += 1
                if self.call_count <= 2:
                    raise Exception(f"Edge case failure {self.call_count}")
                return MagicMock(content="Success after failures", model_name=model_name)

        provider = EdgeCaseProvider()
        reset_tool_factory()
        factory = get_tool_factory()

        # Circuit breaker should open after 2 failures
        for i in range(2):
            with pytest.raises(Exception, match="Edge case failure"):
                await provider.generate_content_with_circuit_breaker(prompt="test", model_name="test")

        assert provider.is_circuit_breaker_open()

        # Tools should still load during circuit breaker open state
        tool = factory.get_tool("chat")
        assert tool is not None

        # Wait for recovery
        await asyncio.sleep(0.2)

        # Should recover successfully
        response = await provider.generate_content_with_circuit_breaker(prompt="recovery", model_name="test")
        assert response.content == "Success after failures"
        assert not provider.is_circuit_breaker_open()

    @pytest.mark.asyncio
    async def test_tool_loading_failures_with_streaming(self):
        """Test that streaming continues to work when tool loading fails."""
        reset_tool_factory()
        factory = get_tool_factory()
        streaming_reader = StreamingFileReader()

        # Create a test file
        temp_file = Path(tempfile.mkdtemp()) / "test.txt"
        temp_file.write_text("Test content for streaming during tool failures")

        try:
            # Simulate tool loading failure
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = ImportError("Simulated import failure")

                # Tool loading should fail gracefully
                failed_tool = factory.get_tool("nonexistent")
                assert failed_tool is None

                # Streaming should still work
                content = await streaming_reader.read_file_chunked(str(temp_file))
                assert len(content) > 0
                assert "Test content for streaming" in content

            # After removing the mock, tools should load normally
            working_tool = factory.get_tool("version")
            assert working_tool is not None

        finally:
            import shutil

            shutil.rmtree(temp_file.parent)

    @pytest.mark.asyncio
    async def test_resource_cleanup_integration(self):
        """Test proper resource cleanup across all Phase 3 components."""
        reset_tool_factory()
        factory = get_tool_factory()

        # Create multiple components
        streaming_reader = StreamingFileReader(max_concurrent=3)

        class CleanupTestProvider(AsyncModelProvider, CircuitBreakerMixin):
            def __init__(self):
                self.base_url = "test://cleanup"
                super().__init__(api_key="test")
                self.cleanup_called = False

            async def generate_content_async(self, prompt, model_name, **kwargs):
                return MagicMock(content="test", model_name=model_name)

            async def aclose(self):
                await super().aclose()
                self.cleanup_called = True

        provider = CleanupTestProvider()

        # Load some tools
        tools = [factory.get_tool(name) for name in ["version", "chat", "listmodels"]]
        assert all(tool is not None for tool in tools)
        assert len(factory.get_loaded_tools()) == 3

        # Test cleanup
        factory.cleanup_all_tools()
        assert len(factory.get_loaded_tools()) == 0

        await provider.aclose()
        assert provider.cleanup_called

        # Verify components can be recreated after cleanup
        new_factory = ToolFactory()
        new_tool = new_factory.get_tool("version")
        assert new_tool is not None

    @pytest.mark.asyncio
    async def test_concurrent_failure_scenarios(self):
        """Test concurrent operations during various failure scenarios."""
        reset_tool_factory()
        factory = get_tool_factory()

        class ConcurrentFailureProvider(AsyncModelProvider, CircuitBreakerMixin):
            def __init__(self):
                self.base_url = "test://concurrent-fail"
                super().__init__(api_key="test", cb_failure_threshold=3)
                self.request_count = 0
                self._lock = asyncio.Lock()

            async def generate_content_async(self, prompt, model_name, **kwargs):
                async with self._lock:
                    self.request_count += 1
                    if self.request_count % 3 == 0:  # Every 3rd request fails
                        raise Exception(f"Intermittent failure #{self.request_count}")
                return MagicMock(content=f"Success #{self.request_count}", model_name=model_name)

        provider = ConcurrentFailureProvider()

        # Test concurrent requests with intermittent failures
        async def make_request(i):
            try:
                return await provider.generate_content_with_circuit_breaker(prompt=f"request {i}", model_name="test")
            except Exception as e:
                return e

        # Make 10 concurrent requests
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some should succeed, some should fail
        successes = [r for r in results if hasattr(r, "content")]
        failures = [r for r in results if isinstance(r, Exception)]

        assert len(successes) > 0  # Some should succeed
        assert len(failures) > 0  # Some should fail

        # Tools should still load during concurrent provider issues
        concurrent_tool_tasks = [
            asyncio.create_task(asyncio.to_thread(factory.get_tool, name)) for name in ["chat", "version", "analyze"]
        ]

        tool_results = await asyncio.gather(*concurrent_tool_tasks, return_exceptions=True)
        successful_tools = [t for t in tool_results if isinstance(t, BaseTool)]
        assert len(successful_tools) >= 2  # Most tools should load successfully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
