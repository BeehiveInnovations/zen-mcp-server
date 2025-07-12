"""Retry utilities using tenacity and pybreaker for enterprise-grade reliability."""

import logging
from typing import Any, Callable, Optional

import pybreaker
from google.api_core import exceptions as google_exceptions
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error should be retried.

    Args:
        error: The exception to check

    Returns:
        True if error is retryable
    """
    # Common retryable exception types
    retryable_types = (
        ConnectionError,
        TimeoutError,
        OSError,  # Includes network errors
    )

    if isinstance(error, retryable_types):
        return True

    # Network and timeout errors by message content
    error_str = str(error).lower()
    retryable_keywords = ["timeout", "timed out", "connection", "temporary", "unavailable", "network"]
    if any(keyword in error_str for keyword in retryable_keywords):
        return True

    # HTTP status codes that are retryable
    if hasattr(error, "status_code"):
        return error.status_code in {429, 500, 502, 503, 504}

    # Google API specific errors
    try:
        google_retryable_types = (
            google_exceptions.ServiceUnavailable,
            google_exceptions.DeadlineExceeded,
            google_exceptions.ResourceExhausted,
            google_exceptions.InternalServerError,
            google_exceptions.BadGateway,
            google_exceptions.GatewayTimeout,
        )

        if isinstance(error, google_retryable_types):
            # Check for quota exhaustion (not retryable)
            if isinstance(error, google_exceptions.ResourceExhausted):
                error_details = str(error)
                if "quota" in error_details.lower() and "failure" in error_details.lower():
                    return False
            return True

    except ImportError:
        pass

    return False


def create_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    name: Optional[str] = None,
) -> pybreaker.CircuitBreaker:
    """Create a configured circuit breaker.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time in seconds before attempting recovery
        name: Optional name for the circuit breaker

    Returns:
        Configured CircuitBreaker instance
    """
    # Create basic circuit breaker without listeners to avoid compatibility issues
    return pybreaker.CircuitBreaker(
        fail_max=failure_threshold,
        reset_timeout=recovery_timeout,
        name=name or "default",
    )


def with_retries(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
):
    """Decorator for adding retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays

    Returns:
        Decorator function
    """
    if jitter:
        from tenacity import wait_random_exponential

        wait_strategy = wait_random_exponential(
            multiplier=initial_delay,
            max=max_delay,
        )
    else:
        wait_strategy = wait_exponential(
            multiplier=initial_delay,
            max=max_delay,
            exp_base=exponential_base,
        )

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception(is_retryable_error),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def with_circuit_breaker(circuit_breaker: pybreaker.CircuitBreaker):
    """Decorator for adding circuit breaker protection.

    Args:
        circuit_breaker: Configured CircuitBreaker instance

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator


def with_retries_and_circuit_breaker(
    circuit_breaker: pybreaker.CircuitBreaker,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
):
    """Combined decorator for retry logic with circuit breaker protection.

    Args:
        circuit_breaker: Configured CircuitBreaker instance
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays

    Returns:
        Decorator function that applies both retry and circuit breaker
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Apply circuit breaker first, then retries on top
        @with_retries(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
        )
        def retry_wrapper(*args, **kwargs):
            # Use circuit breaker call method for each retry attempt
            return circuit_breaker.call(func, *args, **kwargs)

        return retry_wrapper

    return decorator
