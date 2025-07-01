"""
Test fixtures module for Phase 3 optimization components.

This module provides reusable fixtures and utilities for testing
Phase 3 components in isolation and integration scenarios.
"""

from .phase3_fixtures import (
    ConcurrentTestRunner,
    MemoryMonitor,
    MockCircuitBreakerProvider,
    Phase3TestUtilities,
    assert_circuit_breaker_opens,
    assert_circuit_breaker_recovers,
    assert_memory_efficient,
    assert_performance_acceptable,
)

__all__ = [
    "Phase3TestUtilities",
    "MockCircuitBreakerProvider",
    "MemoryMonitor",
    "ConcurrentTestRunner",
    "assert_memory_efficient",
    "assert_performance_acceptable",
    "assert_circuit_breaker_opens",
    "assert_circuit_breaker_recovers",
]
