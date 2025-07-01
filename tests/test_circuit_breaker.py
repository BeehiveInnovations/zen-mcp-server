"""
Comprehensive test suite for circuit breaker functionality.

Tests circuit breaker pattern implementation including:
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Error classification and failure counting
- Recovery timeout behavior
- Async support and thread safety
- Integration with provider classes
- Metrics and observability
"""

import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from providers.async_base import CircuitBreakerMixin
from utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerMetrics,
    CircuitBreakerOpenException,
    CircuitBreakerState,
)


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker for testing."""
        return CircuitBreaker(
            service_name="test_service",
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            half_open_max_calls=2,
        )

    @pytest.fixture
    def mock_async_function(self):
        """Create a mock async function for testing."""
        return AsyncMock()

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization with default values."""
        cb = CircuitBreaker("test_service")

        assert cb.service_name == "test_service"
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60.0
        assert cb.half_open_max_calls == 3
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.is_closed()
        assert not cb.is_open()
        assert not cb.is_half_open()

    def test_circuit_breaker_custom_configuration(self):
        """Test circuit breaker initialization with custom values."""
        cb = CircuitBreaker(
            service_name="custom_service", failure_threshold=10, recovery_timeout=120.0, half_open_max_calls=5
        )

        assert cb.service_name == "custom_service"
        assert cb.failure_threshold == 10
        assert cb.recovery_timeout == 120.0
        assert cb.half_open_max_calls == 5

    @pytest.mark.asyncio
    async def test_successful_request_in_closed_state(self, circuit_breaker, mock_async_function):
        """Test successful request execution in CLOSED state."""
        mock_async_function.return_value = "success"

        result = await circuit_breaker.call(mock_async_function, "arg1", key="value")

        assert result == "success"
        assert circuit_breaker.is_closed()
        assert circuit_breaker.failure_count == 0
        mock_async_function.assert_called_once_with("arg1", key="value")

    @pytest.mark.asyncio
    async def test_failure_counting_in_closed_state(self, circuit_breaker, mock_async_function):
        """Test failure counting in CLOSED state."""
        mock_async_function.side_effect = Exception("Test error")

        # Circuit breaker should remain closed until threshold is reached
        for i in range(circuit_breaker.failure_threshold - 1):
            with pytest.raises(Exception, match="Test error"):
                await circuit_breaker.call(mock_async_function)
            assert circuit_breaker.is_closed()
            assert circuit_breaker.failure_count == i + 1

    @pytest.mark.asyncio
    async def test_transition_to_open_state(self, circuit_breaker, mock_async_function):
        """Test transition from CLOSED to OPEN state when threshold is reached."""
        mock_async_function.side_effect = Exception("Test error")

        # Trigger failures up to threshold
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception, match="Test error"):
                await circuit_breaker.call(mock_async_function)

        # Circuit breaker should now be OPEN
        assert circuit_breaker.is_open()
        assert circuit_breaker.failure_count == circuit_breaker.failure_threshold

    @pytest.mark.asyncio
    async def test_fast_fail_in_open_state(self, circuit_breaker, mock_async_function):
        """Test fast-fail behavior in OPEN state."""
        mock_async_function.side_effect = Exception("Test error")

        # Trigger failures to open circuit breaker
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception, match="Test error"):
                await circuit_breaker.call(mock_async_function)

        assert circuit_breaker.is_open()

        # Reset mock to track calls
        mock_async_function.reset_mock()

        # Next request should fast-fail without calling the function
        with pytest.raises(CircuitBreakerOpenException) as exc_info:
            await circuit_breaker.call(mock_async_function)

        assert "Circuit breaker OPEN" in str(exc_info.value)
        assert exc_info.value.service_name == "test_service"
        mock_async_function.assert_not_called()

    @pytest.mark.asyncio
    async def test_transition_to_half_open_after_timeout(self, circuit_breaker, mock_async_function):
        """Test transition from OPEN to HALF_OPEN after recovery timeout."""
        mock_async_function.side_effect = Exception("Test error")

        # Open the circuit breaker
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception, match=r".*"):
                await circuit_breaker.call(mock_async_function)

        assert circuit_breaker.is_open()

        # Wait for recovery timeout
        await asyncio.sleep(circuit_breaker.recovery_timeout + 0.1)

        # Reset mock for success
        mock_async_function.side_effect = None
        mock_async_function.return_value = "success"

        # Next request should transition to HALF_OPEN and succeed
        result = await circuit_breaker.call(mock_async_function)
        assert result == "success"
        assert circuit_breaker.is_closed()  # Should transition back to CLOSED on success

    @pytest.mark.asyncio
    async def test_half_open_state_behavior(self, circuit_breaker, mock_async_function):
        """Test HALF_OPEN state behavior with limited calls."""
        mock_async_function.side_effect = Exception("Test error")

        # Open the circuit breaker
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception, match=r".*"):
                await circuit_breaker.call(mock_async_function)

        assert circuit_breaker.is_open()

        # Wait for recovery timeout
        await asyncio.sleep(circuit_breaker.recovery_timeout + 0.1)

        # Manually transition to half-open (simulating first call after timeout)
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        circuit_breaker.half_open_calls = 0

        # First call in half-open should be allowed but fail
        with pytest.raises(Exception, match=r".*"):
            await circuit_breaker.call(mock_async_function)

        # Should transition back to OPEN on failure
        assert circuit_breaker.is_open()

    @pytest.mark.asyncio
    async def test_error_classification(self, circuit_breaker):
        """Test error classification for circuit breaker failures."""
        # Test default error classifier

        # Client errors (4xx) should not count as failures
        client_error = Exception("Error code: 400 - Bad Request")
        assert not circuit_breaker.error_classifier(client_error)

        auth_error = Exception("Error code: 401 - Unauthorized")
        assert not circuit_breaker.error_classifier(auth_error)

        # Server errors should count as failures
        server_error = Exception("Error code: 500 - Internal Server Error")
        assert circuit_breaker.error_classifier(server_error)

        timeout_error = Exception("Connection timeout")
        assert circuit_breaker.error_classifier(timeout_error)

    @pytest.mark.asyncio
    async def test_custom_error_classifier(self):
        """Test circuit breaker with custom error classifier."""

        def custom_classifier(error):
            # Only count "critical" errors
            return "critical" in str(error).lower()

        cb = CircuitBreaker(service_name="test", failure_threshold=2, error_classifier=custom_classifier)

        mock_func = AsyncMock()

        # Non-critical error should not count
        mock_func.side_effect = Exception("Minor error")
        with pytest.raises(Exception, match=r".*"):
            await cb.call(mock_func)
        assert cb.failure_count == 0
        assert cb.is_closed()

        # Critical error should count
        mock_func.side_effect = Exception("Critical system failure")
        with pytest.raises(Exception, match=r".*"):
            await cb.call(mock_func)
        assert cb.failure_count == 1
        assert cb.is_closed()

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, circuit_breaker, mock_async_function):
        """Test that success resets failure count in CLOSED state."""
        mock_async_function.side_effect = Exception("Test error")

        # Generate some failures
        for _ in range(2):
            with pytest.raises(Exception, match=r".*"):
                await circuit_breaker.call(mock_async_function)

        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.is_closed()

        # Success should reset failure count
        mock_async_function.side_effect = None
        mock_async_function.return_value = "success"

        result = await circuit_breaker.call(mock_async_function)
        assert result == "success"
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, circuit_breaker, mock_async_function):
        """Test metrics tracking functionality."""
        initial_metrics = circuit_breaker.get_metrics()
        assert isinstance(initial_metrics, CircuitBreakerMetrics)
        assert initial_metrics.state == CircuitBreakerState.CLOSED
        assert initial_metrics.total_requests == 0
        assert initial_metrics.failure_count == 0
        assert initial_metrics.success_count == 0

        # Successful request
        mock_async_function.return_value = "success"
        await circuit_breaker.call(mock_async_function)

        metrics = circuit_breaker.get_metrics()
        assert metrics.total_requests == 1
        assert metrics.success_count == 1
        assert metrics.failure_count == 0

        # Failed request
        mock_async_function.side_effect = Exception("Test error")
        with pytest.raises(Exception, match=r".*"):
            await circuit_breaker.call(mock_async_function)

        metrics = circuit_breaker.get_metrics()
        assert metrics.total_requests == 2
        assert metrics.success_count == 1
        assert metrics.failure_count == 1

    @pytest.mark.asyncio
    async def test_health_status(self, circuit_breaker):
        """Test health status reporting."""
        health = circuit_breaker.get_health_status()

        assert health["service_name"] == "test_service"
        assert health["state"] == "closed"
        assert health["is_healthy"] is True
        assert health["failure_threshold"] == 3
        assert health["current_failures"] == 0
        assert "metrics" in health

        # Open circuit breaker
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception, match=r".*"):
                await circuit_breaker.call(mock_func)

        health = circuit_breaker.get_health_status()
        assert health["state"] == "open"
        assert health["is_healthy"] is False
        assert health["current_failures"] == 3

    @pytest.mark.asyncio
    async def test_manual_reset(self, circuit_breaker, mock_async_function):
        """Test manual circuit breaker reset."""
        mock_async_function.side_effect = Exception("Test error")

        # Open the circuit breaker
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception, match=r".*"):
                await circuit_breaker.call(mock_async_function)

        assert circuit_breaker.is_open()
        assert circuit_breaker.failure_count == circuit_breaker.failure_threshold

        # Manual reset
        await circuit_breaker.reset()

        assert circuit_breaker.is_closed()
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, circuit_breaker):
        """Test circuit breaker behavior with concurrent requests."""
        call_count = 0

        async def counting_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return "success"
            else:
                raise Exception("Failure after 2 successes")

        # Execute concurrent requests
        tasks = [circuit_breaker.call(counting_function) for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results
        successes = [r for r in results if r == "success"]
        failures = [r for r in results if isinstance(r, Exception)]

        assert len(successes) >= 2  # At least 2 should succeed
        assert len(failures) >= 1  # At least 1 should fail
        assert call_count == 5  # All should have been attempted

    def test_metrics_to_dict(self):
        """Test metrics conversion to dictionary."""
        metrics = CircuitBreakerMetrics(
            state=CircuitBreakerState.OPEN, failure_count=5, success_count=10, total_requests=15, rejected_requests=3
        )

        metrics_dict = metrics.to_dict()

        assert metrics_dict["state"] == "open"
        assert metrics_dict["failure_count"] == 5
        assert metrics_dict["success_count"] == 10
        assert metrics_dict["total_requests"] == 15
        assert metrics_dict["rejected_requests"] == 3
        assert "failure_rate" in metrics_dict
        assert "time_since_last_failure" in metrics_dict


class TestCircuitBreakerMixin:
    """Test suite for CircuitBreakerMixin integration."""

    class MockProvider(CircuitBreakerMixin):
        """Mock provider for testing circuit breaker mixin."""

        def __init__(self, **kwargs):
            self.base_url = kwargs.get("base_url", "test://localhost")
            super().__init__(**kwargs)

        async def generate_content_async(self, prompt, model_name, **kwargs):
            """Mock async content generation."""
            if hasattr(self, "_should_fail") and self._should_fail:
                raise Exception("Mock failure")
            return Mock(content="Generated content", usage={}, model_name=model_name)

        def _is_error_retryable(self, error):
            """Mock error classification."""
            # For testing, consider most failures as circuit breaker failures
            return "mock failure" in str(error).lower() or "retryable" in str(error).lower()

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider with circuit breaker mixin."""
        return self.MockProvider()

    def test_circuit_breaker_mixin_initialization(self, mock_provider):
        """Test circuit breaker mixin initialization."""
        assert hasattr(mock_provider, "_circuit_breaker")
        assert isinstance(mock_provider._circuit_breaker, CircuitBreaker)
        assert mock_provider._circuit_breaker.service_name.startswith("MockProvider:")

    def test_circuit_breaker_mixin_environment_configuration(self):
        """Test circuit breaker configuration from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "MOCK_CB_FAILURE_THRESHOLD": "10",
                "MOCK_CB_RECOVERY_TIMEOUT": "120.0",
                "MOCK_CB_HALF_OPEN_MAX_CALLS": "5",
            },
        ):
            provider = self.MockProvider()

            assert provider._circuit_breaker.failure_threshold == 10
            assert provider._circuit_breaker.recovery_timeout == 120.0
            assert provider._circuit_breaker.half_open_max_calls == 5

    @pytest.mark.asyncio
    async def test_circuit_breaker_protected_method(self, mock_provider):
        """Test circuit breaker protected content generation."""
        result = await mock_provider.generate_content_with_circuit_breaker(
            prompt="Test prompt", model_name="test-model"
        )

        assert result.content == "Generated content"
        assert result.model_name == "test-model"

    @pytest.mark.asyncio
    async def test_circuit_breaker_protection_on_failure(self, mock_provider):
        """Test circuit breaker protection when provider fails."""
        mock_provider._should_fail = True

        # Trigger failures to open circuit breaker
        for _ in range(mock_provider._circuit_breaker.failure_threshold):
            with pytest.raises(Exception, match=r".*"):
                await mock_provider.generate_content_with_circuit_breaker(prompt="Test prompt", model_name="test-model")

        # Circuit breaker should now be open
        assert mock_provider.is_circuit_breaker_open()

        # Next request should be rejected with helpful error message
        with pytest.raises(RuntimeError) as exc_info:
            await mock_provider.generate_content_with_circuit_breaker(prompt="Test prompt", model_name="test-model")

        assert "Service temporarily unavailable" in str(exc_info.value)
        assert "Circuit breaker is protecting" in str(exc_info.value)

    def test_circuit_breaker_status_reporting(self, mock_provider):
        """Test circuit breaker status reporting methods."""
        status = mock_provider.get_circuit_breaker_status()

        assert "service_name" in status
        assert "state" in status
        assert "is_healthy" in status
        assert status["is_healthy"] is True

        assert not mock_provider.is_circuit_breaker_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_manual_reset(self, mock_provider):
        """Test manual circuit breaker reset through mixin."""
        mock_provider._should_fail = True

        # Open circuit breaker
        for _ in range(mock_provider._circuit_breaker.failure_threshold):
            with pytest.raises(Exception, match=r".*"):
                await mock_provider.generate_content_with_circuit_breaker(prompt="Test prompt", model_name="test-model")

        assert mock_provider.is_circuit_breaker_open()

        # Manual reset
        await mock_provider.reset_circuit_breaker()

        assert not mock_provider.is_circuit_breaker_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_cleanup(self, mock_provider):
        """Test circuit breaker cleanup during provider closure."""
        # Get initial status
        initial_status = mock_provider.get_circuit_breaker_status()
        assert "service_name" in initial_status  # Circuit breaker is enabled if service_name exists

        # Close provider (cleanup)
        await mock_provider.aclose()

        # Circuit breaker should still be accessible for status
        final_status = mock_provider.get_circuit_breaker_status()
        assert "service_name" in final_status


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker with real provider patterns."""

    @pytest.mark.asyncio
    async def test_error_classification_integration(self):
        """Test error classification integration with provider patterns."""

        def openai_error_classifier(error):
            """Simulate OpenAI-compatible provider error classification."""
            error_str = str(error).lower()

            # Don't count client errors
            if any(code in error_str for code in ["400", "401", "403", "404"]):
                return False

            # Count server errors and infrastructure failures
            return any(indicator in error_str for indicator in ["timeout", "connection", "500", "502", "503", "504"])

        cb = CircuitBreaker(
            service_name="openai_provider", failure_threshold=2, error_classifier=openai_error_classifier
        )

        mock_func = AsyncMock()

        # Client error should not count
        mock_func.side_effect = Exception("Error code: 400 - Bad Request")
        with pytest.raises(Exception, match=r".*"):
            await cb.call(mock_func)
        assert cb.failure_count == 0

        # Server error should count
        mock_func.side_effect = Exception("Error code: 500 - Internal Server Error")
        with pytest.raises(Exception, match=r".*"):
            await cb.call(mock_func)
        assert cb.failure_count == 1

        # Connection error should count
        mock_func.side_effect = Exception("Connection timeout")
        with pytest.raises(Exception, match=r".*"):
            await cb.call(mock_func)
        assert cb.failure_count == 2

        # Circuit breaker should now be open
        assert cb.is_open()

    @pytest.mark.asyncio
    async def test_recovery_workflow(self):
        """Test complete recovery workflow from OPEN to CLOSED."""
        cb = CircuitBreaker(
            service_name="test_recovery",
            failure_threshold=2,
            recovery_timeout=0.1,  # Very short for testing
            half_open_max_calls=1,
        )

        mock_func = AsyncMock()

        # 1. Trigger failures to open circuit
        mock_func.side_effect = Exception("Service failure")
        for _ in range(2):
            with pytest.raises(Exception, match=r".*"):
                await cb.call(mock_func)

        assert cb.is_open()

        # 2. Wait for recovery timeout
        await asyncio.sleep(0.2)

        # 3. Successful request should close circuit
        mock_func.side_effect = None
        mock_func.return_value = "recovered"

        result = await cb.call(mock_func)
        assert result == "recovered"
        assert cb.is_closed()
        assert cb.failure_count == 0

    def test_circuit_breaker_logging(self, caplog):
        """Test circuit breaker logging functionality."""
        with caplog.at_level(logging.INFO):
            cb = CircuitBreaker(service_name="logging_test", failure_threshold=1)

            # Check initialization logging
            assert "Circuit breaker initialized for 'logging_test'" in caplog.text

    @pytest.mark.asyncio
    async def test_state_transition_logging(self, caplog):
        """Test state transition logging."""
        cb = CircuitBreaker(service_name="transition_test", failure_threshold=1, recovery_timeout=0.1)

        mock_func = AsyncMock(side_effect=Exception("Test failure"))

        with caplog.at_level(logging.WARNING):
            # Trigger failure to open circuit
            with pytest.raises(Exception, match=r".*"):
                await cb.call(mock_func)

            # Check failure logging
            assert "Circuit breaker failure #1" in caplog.text

        with caplog.at_level(logging.ERROR):
            # Check circuit opened logging
            assert "Circuit breaker OPENED for 'transition_test'" in caplog.text

        # Wait for recovery and test successful closure
        await asyncio.sleep(0.2)
        mock_func.side_effect = None
        mock_func.return_value = "success"

        with caplog.at_level(logging.INFO):
            await cb.call(mock_func)
            assert "Circuit breaker CLOSED for 'transition_test'" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
