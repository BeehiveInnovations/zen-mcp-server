"""
Test fixtures and utilities for Phase 3 integration testing.

This module provides reusable fixtures, utilities, and helper classes
for testing Phase 3 optimization components in isolation and integration.

Fixtures provided:
- Large test files for streaming validation
- Mock providers with circuit breaker support
- Performance measurement utilities
- Memory monitoring helpers
- Concurrent testing utilities
"""

import asyncio
import gc
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

# Provider integration
from providers.async_base import AsyncModelProvider, CircuitBreakerMixin

# Phase 3 component imports
from tools.factory import get_tool_factory, reset_tool_factory
from utils.circuit_breaker import CircuitBreaker
from utils.streaming_file_reader import StreamingFileReader


class Phase3TestUtilities:
    """Utility class providing common testing operations for Phase 3 components."""

    @staticmethod
    def create_test_file(path: Path, content: str, size_kb: Optional[int] = None) -> Path:
        """Create a test file with specified content or target size."""
        if size_kb:
            # Create file of approximately the specified size
            line = "Test content line for file size generation\n"
            lines_needed = (size_kb * 1024) // len(line)
            content = line * lines_needed

        path.write_text(content)
        return path

    @staticmethod
    def get_memory_usage() -> Optional[int]:
        """Get current memory usage in bytes."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return None

    @staticmethod
    def force_garbage_collection():
        """Force garbage collection and give time for cleanup."""
        gc.collect()
        time.sleep(0.01)  # Allow cleanup

    @staticmethod
    async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
        """Wait for a condition to be true with timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            await asyncio.sleep(interval)
        return False

    @staticmethod
    def create_concurrent_tasks(task_func, num_tasks: int, *args, **kwargs) -> List:
        """Create a list of concurrent async tasks."""
        return [asyncio.create_task(task_func(*args, **kwargs)) for _ in range(num_tasks)]


class MockCircuitBreakerProvider(AsyncModelProvider, CircuitBreakerMixin):
    """Mock provider with circuit breaker for testing."""

    def __init__(self, failure_rate: float = 0.0, latency_ms: float = 1.0, **circuit_breaker_kwargs):
        """
        Initialize mock provider with configurable behavior.

        Args:
            failure_rate: Probability of failure (0.0 to 1.0)
            latency_ms: Simulated latency in milliseconds
            **circuit_breaker_kwargs: Circuit breaker configuration
        """
        self.base_url = "test://mock-provider"
        self.failure_rate = failure_rate
        self.latency_ms = latency_ms
        self.call_count = 0
        self.failure_count = 0
        self._forced_failure = False

        # Default circuit breaker settings for testing
        cb_defaults = {"cb_failure_threshold": 3, "cb_recovery_timeout": 0.1, "cb_half_open_max_calls": 2}
        cb_defaults.update(circuit_breaker_kwargs)

        super().__init__(api_key="test-key", **cb_defaults)

    async def generate_content_async(self, prompt, model_name, **kwargs):
        """Generate mock content with configurable failure behavior."""
        self.call_count += 1

        # Simulate latency
        await asyncio.sleep(self.latency_ms / 1000.0)

        # Check for forced failure or random failure
        should_fail = self._forced_failure or (
            self.failure_rate > 0 and (self.call_count % int(1.0 / self.failure_rate)) == 0
        )

        if should_fail:
            self.failure_count += 1
            raise Exception(f"Mock provider failure #{self.failure_count}")

        return MagicMock(
            content=f"Mock response to: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
            usage={"input_tokens": len(prompt) // 4, "output_tokens": 50},
            model_name=model_name,
        )

    def force_failures(self, enabled: bool = True):
        """Force all subsequent calls to fail."""
        self._forced_failure = enabled

    def _is_error_retryable(self, error):
        """Mock error classification - all failures count as circuit breaker failures."""
        return True

    def get_stats(self) -> Dict:
        """Get provider statistics."""
        return {
            "call_count": self.call_count,
            "failure_count": self.failure_count,
            "failure_rate": self.failure_count / max(1, self.call_count),
            "circuit_breaker_open": self.is_circuit_breaker_open(),
        }


class MemoryMonitor:
    """Monitor memory usage during test execution."""

    def __init__(self):
        self.samples = []
        self.baseline = None

    def start_monitoring(self):
        """Start memory monitoring with baseline."""
        Phase3TestUtilities.force_garbage_collection()
        self.baseline = Phase3TestUtilities.get_memory_usage()
        if self.baseline:
            self.samples = [self.baseline]

    def sample(self):
        """Take a memory sample."""
        memory = Phase3TestUtilities.get_memory_usage()
        if memory:
            self.samples.append(memory)

    def get_stats(self) -> Dict:
        """Get memory usage statistics."""
        if not self.samples or not self.baseline:
            return {}

        current = self.samples[-1]
        peak = max(self.samples)

        return {
            "baseline_mb": self.baseline / 1024 / 1024,
            "current_mb": current / 1024 / 1024,
            "peak_mb": peak / 1024 / 1024,
            "growth_mb": (current - self.baseline) / 1024 / 1024,
            "peak_growth_mb": (peak - self.baseline) / 1024 / 1024,
            "samples_count": len(self.samples),
        }


class ConcurrentTestRunner:
    """Helper for running concurrent tests with coordination."""

    def __init__(self, num_workers: int = 5):
        self.num_workers = num_workers
        self.results = []
        self.errors = []
        self.start_event = asyncio.Event()
        self.completion_times = []

    async def run_concurrent_operation(self, operation_func, *args, **kwargs):
        """Run an operation with timing and error handling."""
        # Wait for start signal
        await self.start_event.wait()

        start_time = time.time()
        try:
            result = await operation_func(*args, **kwargs)
            end_time = time.time()

            self.results.append(result)
            self.completion_times.append(end_time - start_time)

        except Exception as e:
            self.errors.append(e)

    async def execute_concurrent_test(self, operation_func, *args, **kwargs):
        """Execute concurrent test with all workers."""
        # Create tasks
        tasks = [
            asyncio.create_task(self.run_concurrent_operation(operation_func, *args, **kwargs))
            for _ in range(self.num_workers)
        ]

        # Start all tasks simultaneously
        self.start_event.set()

        # Wait for completion
        await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "successful_operations": len(self.results),
            "failed_operations": len(self.errors),
            "average_time": sum(self.completion_times) / len(self.completion_times) if self.completion_times else 0,
            "min_time": min(self.completion_times) if self.completion_times else 0,
            "max_time": max(self.completion_times) if self.completion_times else 0,
            "results": self.results,
            "errors": self.errors,
        }


# Pytest fixtures


@pytest.fixture
def phase3_test_files():
    """Create a set of test files for Phase 3 component testing."""
    temp_dir = tempfile.mkdtemp()
    files = {}

    # Small Python file (5KB)
    small_file = Path(temp_dir) / "small_module.py"
    small_content = (
        '''"""Small test module for Phase 3 testing."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SmallTestClass:
    """A small test class."""
    
    def __init__(self, name: str):
        self.name = name
    
    async def process(self, data: str) -> str:
        """Process data asynchronously."""
        await asyncio.sleep(0.001)
        return f"Processed: {data}"
    
    def validate(self, input_data: str) -> bool:
        """Validate input data."""
        return len(input_data) > 0

def utility_function(value: int) -> int:
    """Utility function for testing."""
    return value * 2

'''
        * 50
    )  # Repeat to make ~5KB

    Phase3TestUtilities.create_test_file(small_file, small_content)
    files["small"] = str(small_file)

    # Medium data file (100KB)
    medium_file = Path(temp_dir) / "medium_data.json"
    Phase3TestUtilities.create_test_file(medium_file, "", 100)
    files["medium"] = str(medium_file)

    # Large log file (1MB)
    large_file = Path(temp_dir) / "large_log.txt"
    Phase3TestUtilities.create_test_file(large_file, "", 1024)
    files["large"] = str(large_file)

    # Very large file (5MB)
    very_large_file = Path(temp_dir) / "very_large_data.txt"
    Phase3TestUtilities.create_test_file(very_large_file, "", 5120)
    files["very_large"] = str(very_large_file)

    yield files

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_circuit_breaker_provider():
    """Create a mock provider with circuit breaker for testing."""
    return MockCircuitBreakerProvider(
        failure_rate=0.0, latency_ms=1.0, cb_failure_threshold=3, cb_recovery_timeout=0.1  # No failures by default
    )


@pytest.fixture
def failing_circuit_breaker_provider():
    """Create a mock provider configured to fail for circuit breaker testing."""
    return MockCircuitBreakerProvider(
        failure_rate=1.0, latency_ms=1.0, cb_failure_threshold=2, cb_recovery_timeout=0.1  # Always fail
    )


@pytest.fixture
def streaming_reader():
    """Create a streaming file reader for testing."""
    return StreamingFileReader(chunk_size=8192, max_file_size=100 * 1024 * 1024, max_concurrent=5)  # 100MB


@pytest.fixture
def tool_factory():
    """Create a fresh tool factory for testing."""
    reset_tool_factory()
    return get_tool_factory()


@pytest.fixture
def memory_monitor():
    """Create a memory monitor for testing."""
    monitor = MemoryMonitor()
    monitor.start_monitoring()
    yield monitor


@pytest.fixture
def concurrent_test_runner():
    """Create a concurrent test runner."""
    return ConcurrentTestRunner(num_workers=5)


@pytest.fixture
def performance_circuit_breaker():
    """Create a circuit breaker optimized for performance testing."""
    return CircuitBreaker(
        service_name="performance_test", failure_threshold=5, recovery_timeout=0.1, half_open_max_calls=3
    )


# Pytest markers for test organization


def pytest_configure(config):
    """Configure pytest markers for Phase 3 tests."""
    config.addinivalue_line("markers", "phase3: mark test as Phase 3 component test")
    config.addinivalue_line("markers", "streaming: mark test as streaming file processing test")
    config.addinivalue_line("markers", "lazy_loading: mark test as lazy tool loading test")
    config.addinivalue_line("markers", "circuit_breaker: mark test as circuit breaker test")
    config.addinivalue_line("markers", "integration: mark test as component integration test")
    config.addinivalue_line("markers", "performance: mark test as performance benchmark")
    config.addinivalue_line("markers", "memory: mark test as memory efficiency test")
    config.addinivalue_line("markers", "concurrent: mark test as concurrency test")


# Test utilities that can be imported


def assert_memory_efficient(initial_memory: int, final_memory: int, max_growth_mb: float = 50):
    """Assert that memory usage is within efficient bounds."""
    if initial_memory and final_memory:
        growth_mb = (final_memory - initial_memory) / 1024 / 1024
        assert growth_mb < max_growth_mb, f"Memory growth {growth_mb:.1f}MB exceeds {max_growth_mb}MB limit"


def assert_performance_acceptable(operation_time: float, max_time: float, operation_name: str = "operation"):
    """Assert that operation performance is acceptable."""
    assert operation_time < max_time, f"{operation_name} took {operation_time:.3f}s, expected < {max_time}s"


async def assert_circuit_breaker_opens(circuit_breaker: CircuitBreaker, failing_func, max_attempts: int = 10):
    """Assert that circuit breaker opens after sufficient failures."""
    attempts = 0
    while attempts < max_attempts and not circuit_breaker.is_open():
        try:
            await circuit_breaker.call(failing_func)
        except Exception:
            pass  # Expected failures
        attempts += 1

    assert circuit_breaker.is_open(), f"Circuit breaker did not open after {attempts} attempts"


async def assert_circuit_breaker_recovers(circuit_breaker: CircuitBreaker, success_func, recovery_timeout: float = 1.0):
    """Assert that circuit breaker recovers successfully."""
    # Wait for recovery timeout
    await asyncio.sleep(recovery_timeout)

    # Should allow recovery attempt
    result = await circuit_breaker.call(success_func)
    assert result is not None, "Circuit breaker recovery failed"
    assert circuit_breaker.is_closed(), "Circuit breaker did not close after successful recovery"
