"""
Performance testing module for Phase 3 optimization components.

This module provides utilities and fixtures for performance testing
of the three Phase 3 optimization components:
- Streaming File Processing
- Lazy Tool Loading
- Circuit Breaker System
"""

from .test_phase3_performance import PerformanceMetrics

__all__ = ["PerformanceMetrics"]
