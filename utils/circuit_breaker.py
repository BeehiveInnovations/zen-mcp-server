"""
Circuit Breaker Implementation for Provider Failure Handling.

This module implements the Circuit Breaker pattern to provide graceful degradation
and automatic recovery for provider failures. The circuit breaker prevents
overwhelming failing services and provides fast-fail behavior during outages.

Key Features:
- Async support with proper locking mechanisms
- Three states: CLOSED (normal), OPEN (fast-fail), HALF_OPEN (testing recovery)
- Configurable failure thresholds and recovery timeouts
- Comprehensive metrics and observability
- Resource protection to prevent overwhelming failing services
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerState(Enum):
    """Circuit breaker states following the standard circuit breaker pattern."""

    CLOSED = "closed"  # Normal operation, failures counted
    OPEN = "open"  # Fast-fail mode, all requests rejected
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring and observability."""

    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    total_requests: int = 0
    rejected_requests: int = 0
    state_transitions: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for logging/monitoring."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "total_requests": self.total_requests,
            "rejected_requests": self.rejected_requests,
            "state_transitions": self.state_transitions.copy(),
            "failure_rate": self.failure_count / max(1, self.total_requests),
            "time_since_last_failure": time.time() - self.last_failure_time if self.last_failure_time > 0 else 0,
        }


class CircuitBreakerOpenException(Exception):
    """
    Exception raised when circuit breaker is open and rejects requests.

    This exception indicates that the circuit breaker is in OPEN state
    and is fast-failing requests to protect the failing service.
    """

    def __init__(self, service_name: str, failure_count: int, last_failure_time: float):
        """
        Initialize the circuit breaker open exception.

        Args:
            service_name: Name of the service that is circuit broken
            failure_count: Number of consecutive failures
            last_failure_time: Timestamp of the last failure
        """
        super().__init__(
            f"Circuit breaker OPEN for service '{service_name}' "
            f"(failures: {failure_count}, last failure: {last_failure_time})"
        )
        self.service_name = service_name
        self.failure_count = failure_count
        self.last_failure_time = last_failure_time


class CircuitBreaker:
    """
    Async Circuit Breaker implementation for provider failure handling.

    The circuit breaker monitors failures and automatically opens to prevent
    overwhelming failing services. It attempts recovery after a timeout period.

    States:
    - CLOSED: Normal operation, tracks failures
    - OPEN: Fast-fail mode, rejects all requests
    - HALF_OPEN: Testing recovery with limited requests

    Usage:
        circuit_breaker = CircuitBreaker(
            service_name="openai_provider",
            failure_threshold=5,
            recovery_timeout=60.0
        )

        result = await circuit_breaker.call(some_async_function, arg1, arg2)
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        error_classifier: Optional[Callable[[Exception], bool]] = None,
    ):
        """
        Initialize the circuit breaker.

        Args:
            service_name: Name of the service for logging and monitoring
            failure_threshold: Number of failures to trigger OPEN state
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Maximum calls allowed in HALF_OPEN state
            error_classifier: Function to determine if error should count as failure
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.error_classifier = error_classifier or self._default_error_classifier

        # State management
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0
        self.last_failure_time = 0.0

        # Metrics for monitoring
        self.metrics = CircuitBreakerMetrics()

        # Async synchronization
        self._lock = asyncio.Lock()

        logger.info(
            f"Circuit breaker initialized for '{service_name}' "
            f"(threshold: {failure_threshold}, timeout: {recovery_timeout}s)"
        )

    def _default_error_classifier(self, error: Exception) -> bool:
        """
        Default error classifier that treats most exceptions as failures.

        Args:
            error: Exception to classify

        Returns:
            True if error should count as circuit breaker failure
        """
        # Don't count client errors (4xx) as circuit breaker failures
        error_str = str(error).lower()
        if any(code in error_str for code in ["400", "401", "403", "404", "422"]):
            return False

        # Count server errors and infrastructure failures
        return True

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function call through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result from the function call

        Raises:
            CircuitBreakerOpenException: When circuit breaker is OPEN
            Exception: Any exception from the wrapped function
        """
        async with self._lock:
            self.metrics.total_requests += 1

            # Check if request should be allowed
            if not await self._should_allow_request():
                self.metrics.rejected_requests += 1
                raise CircuitBreakerOpenException(self.service_name, self.failure_count, self.last_failure_time)

            # Track half-open calls
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.half_open_calls += 1

        # Execute the function (outside of lock to avoid blocking)
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def _should_allow_request(self) -> bool:
        """
        Determine if a request should be allowed based on circuit breaker state.

        Returns:
            True if request should be allowed, False otherwise
        """
        current_time = time.time()

        if self.state == CircuitBreakerState.CLOSED:
            return True

        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if current_time - self.last_failure_time >= self.recovery_timeout:
                await self._transition_to_half_open()
                return True
            return False

        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Allow limited requests in half-open state
            return self.half_open_calls < self.half_open_max_calls

        return False

    async def _on_success(self) -> None:
        """Handle successful request completion."""
        async with self._lock:
            self.metrics.success_count += 1
            self.metrics.last_success_time = time.time()

            if self.state == CircuitBreakerState.HALF_OPEN:
                # Success in half-open state transitions to closed
                await self._transition_to_closed()
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success in closed state
                self.failure_count = 0

    async def _on_failure(self, error: Exception) -> None:
        """
        Handle failed request.

        Args:
            error: Exception that caused the failure
        """
        # Check if this error should count as a circuit breaker failure
        if not self.error_classifier(error):
            logger.debug(f"Error not classified as circuit breaker failure for '{self.service_name}': {error}")
            return

        async with self._lock:
            self.failure_count += 1
            self.metrics.failure_count += 1
            self.last_failure_time = time.time()
            self.metrics.last_failure_time = self.last_failure_time

            logger.warning(f"Circuit breaker failure #{self.failure_count} for '{self.service_name}': {error}")

            if self.state == CircuitBreakerState.CLOSED:
                # Check if we should transition to open
                if self.failure_count >= self.failure_threshold:
                    await self._transition_to_open()
            elif self.state == CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open state transitions back to open
                await self._transition_to_open()

    async def _transition_to_open(self) -> None:
        """Transition circuit breaker to OPEN state."""
        old_state = self.state
        self.state = CircuitBreakerState.OPEN
        self.half_open_calls = 0

        await self._record_state_transition(old_state, self.state)

        logger.error(
            f"Circuit breaker OPENED for '{self.service_name}' "
            f"after {self.failure_count} failures. "
            f"Will attempt recovery in {self.recovery_timeout}s"
        )

    async def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitBreakerState.HALF_OPEN
        self.half_open_calls = 0

        await self._record_state_transition(old_state, self.state)

        logger.info(
            f"Circuit breaker HALF_OPEN for '{self.service_name}' - "
            f"testing recovery with up to {self.half_open_max_calls} calls"
        )

    async def _transition_to_closed(self) -> None:
        """Transition circuit breaker to CLOSED state."""
        old_state = self.state
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0

        await self._record_state_transition(old_state, self.state)

        logger.info(f"Circuit breaker CLOSED for '{self.service_name}' - normal operation resumed")

    async def _record_state_transition(self, from_state: CircuitBreakerState, to_state: CircuitBreakerState) -> None:
        """
        Record a state transition in metrics.

        Args:
            from_state: Previous state
            to_state: New state
        """
        transition_key = f"{from_state.value}_to_{to_state.value}"
        self.metrics.state_transitions[transition_key] = self.metrics.state_transitions.get(transition_key, 0) + 1
        self.metrics.state = to_state

    def get_metrics(self) -> CircuitBreakerMetrics:
        """
        Get current circuit breaker metrics.

        Returns:
            CircuitBreakerMetrics with current state and statistics
        """
        # Update current state in metrics
        self.metrics.state = self.state
        return self.metrics

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status for monitoring systems.

        Returns:
            Dictionary with health status information
        """
        current_time = time.time()
        metrics = self.get_metrics()

        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "is_healthy": self.state != CircuitBreakerState.OPEN,
            "failure_threshold": self.failure_threshold,
            "current_failures": self.failure_count,
            "recovery_timeout": self.recovery_timeout,
            "time_until_recovery": (
                max(0, self.recovery_timeout - (current_time - self.last_failure_time))
                if self.state == CircuitBreakerState.OPEN
                else 0
            ),
            "metrics": metrics.to_dict(),
        }

    async def reset(self) -> None:
        """
        Manually reset the circuit breaker to CLOSED state.

        This method can be used for manual recovery or testing purposes.
        """
        async with self._lock:
            old_state = self.state
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.half_open_calls = 0

            await self._record_state_transition(old_state, self.state)

            logger.info(f"Circuit breaker manually reset for '{self.service_name}'")

    def is_closed(self) -> bool:
        """Check if circuit breaker is in CLOSED state."""
        return self.state == CircuitBreakerState.CLOSED

    def is_open(self) -> bool:
        """Check if circuit breaker is in OPEN state."""
        return self.state == CircuitBreakerState.OPEN

    def is_half_open(self) -> bool:
        """Check if circuit breaker is in HALF_OPEN state."""
        return self.state == CircuitBreakerState.HALF_OPEN
