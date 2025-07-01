"""
Performance benchmarks and stress tests for Phase 3 optimization components.

This module provides comprehensive performance testing for the three Phase 3 components:
1. Streaming File Processing - Memory efficiency and throughput testing
2. Lazy Tool Loading - Startup time and caching performance
3. Circuit Breaker System - Overhead and recovery performance

Performance test categories:
1. Baseline performance measurements
2. Memory efficiency validation
3. Throughput and latency benchmarks
4. Scalability stress tests
5. Resource utilization optimization
6. Comparative analysis vs pre-Phase 3 approaches

The tests validate that Phase 3 optimizations provide measurable improvements:
- Reduced memory usage for large file processing
- Faster server startup times
- Better resource utilization under load
- Improved fault tolerance
"""

import asyncio
import gc
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock

import pytest

# Utilities for performance measurement
from providers.async_base import AsyncModelProvider, CircuitBreakerMixin

# Phase 3 component imports
from tools.factory import get_tool_factory, reset_tool_factory
from utils.circuit_breaker import CircuitBreaker
from utils.streaming_file_reader import StreamingFileReader


class PerformanceMetrics:
    """Utility class for collecting and analyzing performance metrics."""

    def __init__(self):
        self.measurements: Dict[str, List[float]] = {}
        self.memory_samples: List[int] = []

    def record_time(self, operation: str, duration: float):
        """Record timing measurement for an operation."""
        if operation not in self.measurements:
            self.measurements[operation] = []
        self.measurements[operation].append(duration)

    def record_memory(self):
        """Record current memory usage."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            self.memory_samples.append(process.memory_info().rss)
        except ImportError:
            pass

    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistical summary for an operation."""
        if operation not in self.measurements:
            return {}

        times = self.measurements[operation]
        return {
            "count": len(times),
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "p50": sorted(times)[len(times) // 2],
            "p95": sorted(times)[int(len(times) * 0.95)],
            "p99": sorted(times)[int(len(times) * 0.99)],
        }

    def get_memory_stats(self) -> Dict[str, float]:
        """Get memory usage statistics."""
        if not self.memory_samples:
            return {}

        return {
            "count": len(self.memory_samples),
            "mean_mb": sum(self.memory_samples) / len(self.memory_samples) / 1024 / 1024,
            "min_mb": min(self.memory_samples) / 1024 / 1024,
            "max_mb": max(self.memory_samples) / 1024 / 1024,
            "growth_mb": (max(self.memory_samples) - min(self.memory_samples)) / 1024 / 1024,
        }


@pytest.mark.performance
class TestStreamingPerformance:
    """Performance tests for streaming file processing."""

    @pytest.fixture
    def performance_files(self):
        """Create files of various sizes for performance testing."""
        temp_dir = tempfile.mkdtemp()
        files = {}

        # Small file (10KB)
        small_file = Path(temp_dir) / "small_10kb.txt"
        small_content = "Small file content line\n" * 400  # ~10KB
        small_file.write_text(small_content)
        files["10kb"] = str(small_file)

        # Medium file (1MB)
        medium_file = Path(temp_dir) / "medium_1mb.txt"
        medium_content = "Medium file content with more text per line for realistic testing\n" * 25000  # ~1MB
        medium_file.write_text(medium_content)
        files["1mb"] = str(medium_file)

        # Large file (10MB)
        large_file = Path(temp_dir) / "large_10mb.txt"
        with open(large_file, "w") as f:
            for i in range(250000):  # 250K lines = ~10MB
                f.write(
                    f"Large file line {i:06d} with substantial content for memory testing and performance validation\n"
                )
        files["10mb"] = str(large_file)

        # Very large file (50MB)
        very_large_file = Path(temp_dir) / "very_large_50mb.txt"
        with open(very_large_file, "w") as f:
            for i in range(1250000):  # 1.25M lines = ~50MB
                f.write(f"VeryLarge {i:07d}: Performance testing content with consistent line length for benchmark\n")
        files["50mb"] = str(very_large_file)

        yield files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_streaming_vs_traditional_memory_usage(self, performance_files):
        """Compare memory usage between streaming and traditional file reading."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        metrics = PerformanceMetrics()

        # Test traditional approach simulation (read entire file)
        gc.collect()
        initial_memory = process.memory_info().rss
        metrics.record_memory()

        # Simulate traditional file reading for large file
        start_time = time.time()
        with open(performance_files["10mb"]) as f:
            traditional_content = f.read()
        traditional_time = time.time() - start_time
        traditional_memory = process.memory_info().rss

        metrics.record_time("traditional_read", traditional_time)
        metrics.record_memory()

        # Clear memory
        del traditional_content
        gc.collect()
        await asyncio.sleep(0.1)  # Allow garbage collection

        # Test streaming approach
        streaming_reader = StreamingFileReader(chunk_size=8192)

        start_time = time.time()
        streaming_content = await streaming_reader.read_file_chunked(performance_files["10mb"])
        streaming_time = time.time() - start_time
        streaming_memory = process.memory_info().rss

        metrics.record_time("streaming_read", streaming_time)
        metrics.record_memory()

        # Memory usage comparison
        traditional_growth = traditional_memory - initial_memory
        streaming_growth = streaming_memory - initial_memory

        # Streaming should use significantly less peak memory
        memory_improvement = (traditional_growth - streaming_growth) / traditional_growth
        assert memory_improvement > 0.1, f"Streaming should use at least 10% less memory, got {memory_improvement:.2%}"

        # Both should read the same content
        assert len(streaming_content) > 0
        assert abs(len(streaming_content) - len(traditional_content)) < 1000  # Allow small differences

        # Performance metrics
        print("\nMemory Performance Comparison (10MB file):")
        print(f"Traditional memory growth: {traditional_growth / 1024 / 1024:.1f} MB")
        print(f"Streaming memory growth: {streaming_growth / 1024 / 1024:.1f} MB")
        print(f"Memory improvement: {memory_improvement:.1%}")
        print(f"Traditional time: {traditional_time:.3f}s")
        print(f"Streaming time: {streaming_time:.3f}s")

    @pytest.mark.asyncio
    async def test_streaming_throughput_scaling(self, performance_files):
        """Test streaming throughput across different file sizes."""
        streaming_reader = StreamingFileReader(chunk_size=8192)
        metrics = PerformanceMetrics()

        file_sizes = ["10kb", "1mb", "10mb"]
        throughput_results = {}

        for size in file_sizes:
            file_path = performance_files[size]
            file_size_bytes = os.path.getsize(file_path)

            # Warm up
            await streaming_reader.read_file_chunked(file_path, max_chars=1000)

            # Measure multiple runs
            times = []
            for _ in range(3):
                start_time = time.time()
                content = await streaming_reader.read_file_chunked(file_path)
                end_time = time.time()

                duration = end_time - start_time
                times.append(duration)
                metrics.record_time(f"stream_{size}", duration)

            avg_time = sum(times) / len(times)
            throughput_mbps = (file_size_bytes / 1024 / 1024) / avg_time
            throughput_results[size] = {
                "avg_time": avg_time,
                "throughput_mbps": throughput_mbps,
                "file_size_mb": file_size_bytes / 1024 / 1024,
            }

        # Verify throughput scales reasonably
        # Smaller files should have higher throughput per MB due to overhead
        assert throughput_results["10kb"]["throughput_mbps"] > 5.0  # At least 5 MB/s for small files
        assert throughput_results["1mb"]["throughput_mbps"] > 10.0  # At least 10 MB/s for medium files
        assert throughput_results["10mb"]["throughput_mbps"] > 20.0  # At least 20 MB/s for large files

        print("\nThroughput Scaling Results:")
        for size, result in throughput_results.items():
            print(
                f"{size}: {result['throughput_mbps']:.1f} MB/s ({result['avg_time']:.3f}s for {result['file_size_mb']:.1f}MB)"
            )

    @pytest.mark.asyncio
    async def test_concurrent_streaming_performance(self, performance_files):
        """Test performance of concurrent streaming operations."""
        streaming_reader = StreamingFileReader(chunk_size=8192, max_concurrent=5)
        metrics = PerformanceMetrics()

        # Test concurrent vs sequential performance
        file_list = [performance_files["1mb"], performance_files["1mb"], performance_files["1mb"]]

        # Sequential processing
        start_time = time.time()
        sequential_results = []
        for file_path in file_list:
            content = await streaming_reader.read_file_chunked(file_path)
            sequential_results.append(len(content))
        sequential_time = time.time() - start_time

        metrics.record_time("sequential_processing", sequential_time)

        # Concurrent processing
        start_time = time.time()
        concurrent_tasks = [streaming_reader.read_file_chunked(file_path) for file_path in file_list]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_time = time.time() - start_time

        metrics.record_time("concurrent_processing", concurrent_time)

        # Concurrent should be faster
        speedup = sequential_time / concurrent_time
        assert speedup > 1.5, f"Concurrent processing should be at least 1.5x faster, got {speedup:.2f}x"

        # Results should be equivalent
        assert len(concurrent_results) == len(sequential_results)
        for i, (seq_len, conc_len) in enumerate(zip(sequential_results, [len(r) for r in concurrent_results])):
            assert abs(seq_len - conc_len) < 100, f"Result {i} length mismatch: {seq_len} vs {conc_len}"

        print("\nConcurrent Processing Performance:")
        print(f"Sequential time: {sequential_time:.3f}s")
        print(f"Concurrent time: {concurrent_time:.3f}s")
        print(f"Speedup: {speedup:.2f}x")

    @pytest.mark.asyncio
    async def test_streaming_memory_stability(self, performance_files):
        """Test memory stability during repeated streaming operations."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        streaming_reader = StreamingFileReader(chunk_size=8192)
        metrics = PerformanceMetrics()

        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss
        metrics.record_memory()

        # Process large file multiple times
        for i in range(10):
            content = await streaming_reader.read_file_chunked(performance_files["10mb"])
            assert len(content) > 0

            # Force garbage collection
            del content
            gc.collect()

            # Record memory after each iteration
            current_memory = process.memory_info().rss
            metrics.record_memory()

            # Memory shouldn't grow significantly
            memory_growth = current_memory - baseline_memory
            assert (
                memory_growth < 100 * 1024 * 1024
            ), f"Memory growth {memory_growth / 1024 / 1024:.1f}MB exceeds 100MB limit"

        memory_stats = metrics.get_memory_stats()
        print("\nMemory Stability Test (10 iterations, 10MB file):")
        print(f"Memory growth: {memory_stats['growth_mb']:.1f} MB")
        print(f"Average memory: {memory_stats['mean_mb']:.1f} MB")


@pytest.mark.performance
class TestLazyLoadingPerformance:
    """Performance tests for lazy tool loading."""

    def test_startup_time_comparison(self):
        """Compare startup times with and without lazy loading."""
        metrics = PerformanceMetrics()

        # Test lazy loading startup (just factory creation)
        start_time = time.time()
        reset_tool_factory()
        lazy_factory = get_tool_factory()
        lazy_startup_time = time.time() - start_time

        metrics.record_time("lazy_startup", lazy_startup_time)

        # Verify no tools are loaded
        assert len(lazy_factory.get_loaded_tools()) == 0

        # Simulate eager loading (preload all tools)
        start_time = time.time()
        preload_results = lazy_factory.preload_tools()
        eager_load_time = time.time() - start_time

        metrics.record_time("eager_loading", eager_load_time)

        # Lazy startup should be significantly faster
        speedup = eager_load_time / lazy_startup_time
        assert speedup > 10, f"Lazy startup should be 10x+ faster, got {speedup:.1f}x"

        # Most tools should load successfully
        successful_loads = sum(1 for success in preload_results.values() if success)
        total_tools = len(preload_results)
        success_rate = successful_loads / total_tools
        assert success_rate > 0.8, f"Expected 80%+ tool load success, got {success_rate:.1%}"

        print("\nStartup Performance Comparison:")
        print(f"Lazy startup: {lazy_startup_time * 1000:.1f}ms")
        print(f"Eager loading: {eager_load_time * 1000:.1f}ms")
        print(f"Speedup: {speedup:.1f}x")
        print(f"Tools loaded: {successful_loads}/{total_tools} ({success_rate:.1%})")

    def test_tool_loading_cache_performance(self):
        """Test performance characteristics of tool caching."""
        reset_tool_factory()
        factory = get_tool_factory()
        metrics = PerformanceMetrics()

        # Test first load (cold cache)
        start_time = time.time()
        first_tool = factory.get_tool("version")
        first_load_time = time.time() - start_time

        assert first_tool is not None
        metrics.record_time("first_load", first_load_time)

        # Test subsequent loads (warm cache)
        cache_times = []
        for _ in range(100):  # Many cache hits
            start_time = time.time()
            cached_tool = factory.get_tool("version")
            cache_time = time.time() - start_time
            cache_times.append(cache_time)

            assert cached_tool is first_tool  # Same instance

        avg_cache_time = sum(cache_times) / len(cache_times)
        metrics.record_time("cache_access", avg_cache_time)

        # Cache access should be much faster than first load
        cache_speedup = first_load_time / avg_cache_time
        assert cache_speedup > 100, f"Cache should be 100x+ faster, got {cache_speedup:.1f}x"

        # Verify cache metrics
        factory_metrics = factory.get_metrics()
        assert factory_metrics["cache_hits"] == 100
        assert factory_metrics["cache_efficiency"] > 0.99  # 99%+ cache hit rate

        print("\nCache Performance:")
        print(f"First load: {first_load_time * 1000:.3f}ms")
        print(f"Average cache access: {avg_cache_time * 1000:.6f}ms")
        print(f"Cache speedup: {cache_speedup:.1f}x")

    def test_concurrent_tool_loading_performance(self):
        """Test performance of concurrent tool loading."""
        import threading

        reset_tool_factory()
        factory = get_tool_factory()
        metrics = PerformanceMetrics()

        # Test concurrent loading of the same tool
        results = []
        errors = []
        times = []

        def load_same_tool():
            start_time = time.time()
            try:
                tool = factory.get_tool("chat")
                end_time = time.time()
                results.append(tool)
                times.append(end_time - start_time)
            except Exception as e:
                errors.append(e)

        # Start multiple threads loading the same tool
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=load_same_tool)
            threads.append(thread)

        start_time = time.time()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
        total_time = time.time() - start_time

        # All should succeed with no errors
        assert len(errors) == 0, f"Concurrent loading had errors: {errors}"
        assert len(results) == 20

        # All should be the same instance (cached)
        first_tool = results[0]
        assert all(tool is first_tool for tool in results)

        # Should be reasonably fast
        assert total_time < 5.0, f"Concurrent loading took {total_time:.3f}s, expected < 5s"

        # Most accesses should be cache hits
        factory_metrics = factory.get_metrics()
        assert factory_metrics["cache_hits"] >= 19  # First load + 19 cache hits

        avg_time = sum(times) / len(times)
        metrics.record_time("concurrent_loading", avg_time)

        print("\nConcurrent Tool Loading (20 threads, same tool):")
        print(f"Total time: {total_time:.3f}s")
        print(f"Average per-thread time: {avg_time * 1000:.3f}ms")
        print(f"Cache hits: {factory_metrics['cache_hits']}")

    def test_tool_loading_memory_efficiency(self):
        """Test memory efficiency of lazy tool loading."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        reset_tool_factory()
        factory = get_tool_factory()

        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss

        # Load tools incrementally and measure memory
        available_tools = factory.get_available_tools()[:10]  # First 10 tools
        memory_per_tool = []

        for i, tool_name in enumerate(available_tools):
            gc.collect()
            before_memory = process.memory_info().rss

            tool = factory.get_tool(tool_name)
            assert tool is not None

            gc.collect()
            after_memory = process.memory_info().rss

            tool_memory = after_memory - before_memory
            memory_per_tool.append(tool_memory)

            print(f"Tool {i+1} ({tool_name}): {tool_memory / 1024:.1f} KB")

        # Memory usage should be reasonable per tool
        avg_memory_per_tool = sum(memory_per_tool) / len(memory_per_tool)
        max_memory_per_tool = max(memory_per_tool)

        # Each tool should use less than 10MB on average
        assert (
            avg_memory_per_tool < 10 * 1024 * 1024
        ), f"Average memory per tool {avg_memory_per_tool / 1024 / 1024:.1f}MB exceeds 10MB"

        # No single tool should use more than 50MB
        assert (
            max_memory_per_tool < 50 * 1024 * 1024
        ), f"Max memory per tool {max_memory_per_tool / 1024 / 1024:.1f}MB exceeds 50MB"

        total_memory_growth = process.memory_info().rss - baseline_memory

        print("\nTool Loading Memory Efficiency:")
        print(f"Average memory per tool: {avg_memory_per_tool / 1024:.1f} KB")
        print(f"Max memory per tool: {max_memory_per_tool / 1024:.1f} KB")
        print(f"Total memory growth: {total_memory_growth / 1024 / 1024:.1f} MB")


@pytest.mark.performance
class TestCircuitBreakerPerformance:
    """Performance tests for circuit breaker system."""

    @pytest.fixture
    def performance_circuit_breaker(self):
        """Create circuit breaker optimized for performance testing."""
        return CircuitBreaker(
            service_name="performance_test",
            failure_threshold=10,
            recovery_timeout=0.1,  # Fast recovery for testing
            half_open_max_calls=5,
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_overhead(self, performance_circuit_breaker):
        """Measure overhead introduced by circuit breaker protection."""
        metrics = PerformanceMetrics()

        # Mock function with minimal processing time
        call_count = 0

        async def fast_function():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)  # 1ms simulated work
            return f"result_{call_count}"

        # Measure direct function calls (baseline)
        direct_times = []
        for _ in range(1000):
            start_time = time.time()
            result = await fast_function()
            end_time = time.time()
            direct_times.append(end_time - start_time)
            assert result.startswith("result_")

        avg_direct_time = sum(direct_times) / len(direct_times)
        metrics.record_time("direct_call", avg_direct_time)

        # Reset call count
        call_count = 0

        # Measure circuit breaker protected calls
        protected_times = []
        for _ in range(1000):
            start_time = time.time()
            result = await performance_circuit_breaker.call(fast_function)
            end_time = time.time()
            protected_times.append(end_time - start_time)
            assert result.startswith("result_")

        avg_protected_time = sum(protected_times) / len(protected_times)
        metrics.record_time("protected_call", avg_protected_time)

        # Calculate overhead
        overhead = avg_protected_time - avg_direct_time
        overhead_percentage = (overhead / avg_direct_time) * 100

        # Overhead should be minimal (< 50% for fast functions)
        assert overhead_percentage < 50, f"Circuit breaker overhead {overhead_percentage:.1f}% exceeds 50%"

        # Circuit breaker should remain closed (healthy)
        assert performance_circuit_breaker.is_closed()

        cb_metrics = performance_circuit_breaker.get_metrics()
        assert cb_metrics.success_count == 1000
        assert cb_metrics.failure_count == 0

        print("\nCircuit Breaker Overhead Analysis:")
        print(f"Direct call average: {avg_direct_time * 1000:.3f}ms")
        print(f"Protected call average: {avg_protected_time * 1000:.3f}ms")
        print(f"Overhead: {overhead * 1000:.3f}ms ({overhead_percentage:.1f}%)")

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_performance(self, performance_circuit_breaker):
        """Test performance during failure scenarios."""
        metrics = PerformanceMetrics()
        failure_count = 0

        async def failing_function():
            nonlocal failure_count
            failure_count += 1
            await asyncio.sleep(0.001)
            raise Exception(f"Simulated failure #{failure_count}")

        # Measure time to open circuit breaker
        start_time = time.time()

        for i in range(performance_circuit_breaker.failure_threshold):
            try:
                await performance_circuit_breaker.call(failing_function)
            except Exception:
                pass  # Expected failures

        time_to_open = time.time() - start_time
        metrics.record_time("time_to_open", time_to_open)

        # Circuit breaker should now be open
        assert performance_circuit_breaker.is_open()

        # Measure fast-fail performance
        fast_fail_times = []
        for _ in range(100):
            start_time = time.time()
            try:
                await performance_circuit_breaker.call(failing_function)
                assert False, "Should have fast-failed"
            except Exception:
                end_time = time.time()
                fast_fail_times.append(end_time - start_time)

        avg_fast_fail_time = sum(fast_fail_times) / len(fast_fail_times)
        metrics.record_time("fast_fail", avg_fast_fail_time)

        # Fast-fail should be very fast (< 1ms)
        assert avg_fast_fail_time < 0.001, f"Fast-fail took {avg_fast_fail_time * 1000:.3f}ms, expected < 1ms"

        print("\nCircuit Breaker Failure Performance:")
        print(f"Time to open: {time_to_open * 1000:.1f}ms")
        print(f"Fast-fail average: {avg_fast_fail_time * 1000:.3f}ms")

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_performance(self, performance_circuit_breaker):
        """Test performance of circuit breaker recovery process."""
        metrics = PerformanceMetrics()

        # Open circuit breaker first
        async def failing_function():
            raise Exception("Failure to open circuit")

        for _ in range(performance_circuit_breaker.failure_threshold):
            try:
                await performance_circuit_breaker.call(failing_function)
            except Exception:
                pass

        assert performance_circuit_breaker.is_open()

        # Wait for recovery timeout
        await asyncio.sleep(performance_circuit_breaker.recovery_timeout + 0.05)

        # Test recovery with successful function
        recovery_call_count = 0

        async def recovering_function():
            nonlocal recovery_call_count
            recovery_call_count += 1
            await asyncio.sleep(0.001)
            return f"recovery_{recovery_call_count}"

        # Measure recovery performance
        start_time = time.time()
        result = await performance_circuit_breaker.call(recovering_function)
        recovery_time = time.time() - start_time

        metrics.record_time("recovery_call", recovery_time)

        # Should successfully recover
        assert result == "recovery_1"
        assert performance_circuit_breaker.is_closed()  # Should transition to closed

        # Subsequent calls should be fast (normal operation)
        subsequent_times = []
        for _ in range(10):
            start_time = time.time()
            result = await performance_circuit_breaker.call(recovering_function)
            end_time = time.time()
            subsequent_times.append(end_time - start_time)

        avg_subsequent_time = sum(subsequent_times) / len(subsequent_times)
        metrics.record_time("post_recovery", avg_subsequent_time)

        # Post-recovery performance should be similar to normal operation
        assert avg_subsequent_time < 0.01, f"Post-recovery calls slow: {avg_subsequent_time * 1000:.3f}ms"

        print("\nCircuit Breaker Recovery Performance:")
        print(f"Recovery call: {recovery_time * 1000:.3f}ms")
        print(f"Post-recovery average: {avg_subsequent_time * 1000:.3f}ms")

    @pytest.mark.asyncio
    async def test_concurrent_circuit_breaker_performance(self):
        """Test circuit breaker performance under concurrent load."""
        cb = CircuitBreaker(
            service_name="concurrent_test",
            failure_threshold=50,  # Higher threshold for concurrent testing
            recovery_timeout=0.1,
        )

        metrics = PerformanceMetrics()
        success_count = 0
        failure_count = 0

        async def concurrent_function(request_id: int):
            nonlocal success_count, failure_count

            await asyncio.sleep(0.001)  # Simulate work

            # Simulate 90% success rate
            if request_id % 10 == 0:  # 10% failure rate
                failure_count += 1
                raise Exception(f"Simulated failure for request {request_id}")
            else:
                success_count += 1
                return f"success_{request_id}"

        # Generate concurrent requests
        num_requests = 1000
        concurrent_tasks = [cb.call(concurrent_function, i) for i in range(num_requests)]

        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Analyze results
        successes = [r for r in results if isinstance(r, str) and r.startswith("success_")]
        failures = [r for r in results if isinstance(r, Exception)]

        success_rate = len(successes) / num_requests
        avg_time_per_request = total_time / num_requests

        metrics.record_time("concurrent_requests", avg_time_per_request)

        # Should handle most requests successfully
        assert success_rate > 0.8, f"Success rate {success_rate:.1%} below 80%"

        # Should complete in reasonable time
        assert total_time < 10.0, f"Total time {total_time:.3f}s exceeds 10s"

        # Circuit breaker should still be functional
        cb_metrics = cb.get_metrics()
        assert cb_metrics.total_requests == num_requests

        print("\nConcurrent Circuit Breaker Performance:")
        print(f"Total requests: {num_requests}")
        print(f"Success rate: {success_rate:.1%}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Average per request: {avg_time_per_request * 1000:.3f}ms")
        print(f"Throughput: {num_requests / total_time:.1f} requests/second")


@pytest.mark.performance
class TestIntegratedPerformance:
    """Performance tests for all Phase 3 components working together."""

    @pytest.fixture
    def integration_files(self):
        """Create files for integrated performance testing."""
        temp_dir = tempfile.mkdtemp()
        files = []

        # Create multiple files of varying sizes
        for i, size_kb in enumerate([10, 100, 500, 1000]):  # 10KB to 1MB
            file_path = Path(temp_dir) / f"integration_file_{i}_{size_kb}kb.txt"
            content = f"Integration test file {i} content\n" * (size_kb * 25)  # Approximate size
            file_path.write_text(content)
            files.append(str(file_path))

        yield files

        import shutil

        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_end_to_end_performance(self, integration_files):
        """Test end-to-end performance with all Phase 3 components."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
        except ImportError:
            initial_memory = None

        metrics = PerformanceMetrics()

        # Phase 1: System initialization (lazy loading)
        start_time = time.time()
        reset_tool_factory()
        factory = get_tool_factory()
        streaming_reader = StreamingFileReader(chunk_size=8192, max_concurrent=3)

        class MockProvider(AsyncModelProvider, CircuitBreakerMixin):
            def __init__(self):
                self.base_url = "test://integrated-performance"
                super().__init__(api_key="test")

            async def generate_content_async(self, prompt, model_name, **kwargs):
                await asyncio.sleep(0.001)  # Simulate API latency
                return MagicMock(content=f"Response to: {prompt[:50]}...", model_name=model_name)

        provider = MockProvider()
        init_time = time.time() - start_time
        metrics.record_time("system_init", init_time)

        # Phase 2: Tool loading and file processing
        start_time = time.time()

        # Load tools on demand
        tools = []
        for tool_name in ["chat", "analyze", "version"]:
            tool = factory.get_tool(tool_name)
            tools.append(tool)

        # Process files with streaming
        file_content = await streaming_reader.read_files_chunked(
            file_paths=integration_files, max_tokens=200000, include_line_numbers=True
        )

        processing_time = time.time() - start_time
        metrics.record_time("processing_phase", processing_time)

        # Phase 3: Simulated workload with circuit breaker protection
        start_time = time.time()

        workload_tasks = []
        for i in range(50):  # 50 simulated requests
            task = provider.generate_content_with_circuit_breaker(
                prompt=f"Process request {i} with context: {file_content[:100]}", model_name="test-model"
            )
            workload_tasks.append(task)

        responses = await asyncio.gather(*workload_tasks)
        workload_time = time.time() - start_time
        metrics.record_time("workload_phase", workload_time)

        # Validation and metrics
        assert len(tools) == 3
        assert all(tool is not None for tool in tools)
        assert len(file_content) > 0
        assert len(responses) == 50
        assert all(hasattr(r, "content") for r in responses)

        # Performance requirements
        assert init_time < 0.1, f"System init {init_time:.3f}s exceeds 0.1s"
        assert processing_time < 5.0, f"Processing {processing_time:.3f}s exceeds 5s"
        assert workload_time < 10.0, f"Workload {workload_time:.3f}s exceeds 10s"

        total_time = init_time + processing_time + workload_time

        # Memory efficiency check
        if initial_memory:
            final_memory = process.memory_info().rss
            memory_growth = (final_memory - initial_memory) / 1024 / 1024
            assert memory_growth < 200, f"Memory growth {memory_growth:.1f}MB exceeds 200MB"

        # Component efficiency checks
        factory_metrics = factory.get_metrics()
        assert factory_metrics["cache_efficiency"] > 0.5  # At least 50% cache hits

        cb_metrics = provider.get_circuit_breaker_status()
        assert cb_metrics["is_healthy"] is True

        # Streaming efficiency
        streaming_stats = streaming_reader.get_memory_stats()
        assert streaming_stats["chunk_size"] == 8192

        print("\nEnd-to-End Performance Results:")
        print(f"System initialization: {init_time * 1000:.1f}ms")
        print(f"Processing phase: {processing_time:.3f}s")
        print(f"Workload phase: {workload_time:.3f}s")
        print(f"Total time: {total_time:.3f}s")
        if initial_memory:
            print(f"Memory growth: {memory_growth:.1f}MB")
        print(f"Cache efficiency: {factory_metrics['cache_efficiency']:.1%}")

    @pytest.mark.asyncio
    async def test_scalability_characteristics(self, integration_files):
        """Test how Phase 3 components scale with increased load."""
        reset_tool_factory()
        metrics = PerformanceMetrics()

        # Test different load levels
        load_levels = [1, 5, 10, 20]  # Number of concurrent operations
        scalability_results = {}

        for load_level in load_levels:
            factory = get_tool_factory()
            streaming_reader = StreamingFileReader(max_concurrent=load_level)

            # Concurrent operations at this load level
            start_time = time.time()

            # Tool loading tasks
            tool_tasks = [asyncio.create_task(asyncio.to_thread(factory.get_tool, "chat")) for _ in range(load_level)]

            # File processing tasks
            file_tasks = [
                streaming_reader.read_file_chunked(integration_files[i % len(integration_files)])
                for i in range(load_level)
            ]

            # Execute all tasks concurrently
            all_tasks = tool_tasks + file_tasks
            results = await asyncio.gather(*all_tasks, return_exceptions=True)

            execution_time = time.time() - start_time

            # Analyze results
            tool_results = results[:load_level]
            file_results = results[load_level:]

            successful_tools = sum(1 for r in tool_results if hasattr(r, "name"))
            successful_files = sum(1 for r in file_results if isinstance(r, str) and len(r) > 0)

            scalability_results[load_level] = {
                "execution_time": execution_time,
                "successful_tools": successful_tools,
                "successful_files": successful_files,
                "throughput": (successful_tools + successful_files) / execution_time,
            }

            metrics.record_time(f"load_level_{load_level}", execution_time)

        # Analyze scalability
        for load_level, result in scalability_results.items():
            success_rate = (result["successful_tools"] + result["successful_files"]) / (load_level * 2)
            assert success_rate > 0.8, f"Load level {load_level} success rate {success_rate:.1%} below 80%"

        # Higher loads should maintain reasonable performance
        baseline_throughput = scalability_results[1]["throughput"]
        for load_level in [5, 10, 20]:
            current_throughput = scalability_results[load_level]["throughput"]
            efficiency = current_throughput / (baseline_throughput * load_level)
            assert efficiency > 0.3, f"Load level {load_level} efficiency {efficiency:.1%} below 30%"

        print("\nScalability Results:")
        for load_level, result in scalability_results.items():
            print(
                f"Load {load_level}: {result['execution_time']:.3f}s, "
                f"throughput: {result['throughput']:.1f} ops/sec"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
