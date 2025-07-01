"""
Unified Cache Manager for centralized cache management and monitoring.

This module provides a centralized interface for managing all caching systems
in the Zen MCP Server, including token estimation, schema generation, and
model validation caches.
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from tools.shared.schema_cache import get_schema_cache
from utils.model_validation_cache import get_model_validation_cache
from utils.token_cache import get_token_cache

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Unified cache management interface for all caching systems.

    Features:
    - Global cache statistics and monitoring
    - Memory usage tracking and limits
    - Cache cleanup and maintenance tasks
    - Performance metrics collection
    - Centralized cache warming
    - Health monitoring and alerting
    """

    def __init__(self, max_total_memory_mb: int = 100):
        """
        Initialize the cache manager.

        Args:
            max_total_memory_mb: Maximum total memory usage across all caches (default: 100MB)
        """
        self.max_total_memory_bytes = max_total_memory_mb * 1024 * 1024
        self._lock = threading.RLock()

        # Cache instances
        self._token_cache = get_token_cache()
        self._schema_cache = get_schema_cache()
        self._model_validation_cache = get_model_validation_cache()

        # Monitoring
        self._last_cleanup_time = time.time()
        self._cleanup_interval = 300  # 5 minutes
        self._performance_history: List[Dict[str, Any]] = []
        self._max_history_entries = 100

        logger.info(f"CacheManager initialized with max memory: {max_total_memory_mb}MB")

    def get_global_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics from all caches.

        Returns:
            Dictionary with global cache statistics
        """
        with self._lock:
            token_stats = self._token_cache.get_stats()
            schema_stats = self._schema_cache.get_stats()
            model_stats = self._model_validation_cache.get_stats()

            # Calculate totals
            total_hits = token_stats["hits"] + schema_stats["hits"] + model_stats["hits"]
            total_misses = token_stats["misses"] + schema_stats["misses"] + model_stats["misses"]
            total_requests = total_hits + total_misses
            overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

            # Estimate total memory usage
            total_memory = (
                token_stats.get("memory_usage_estimate", 0)
                + schema_stats.get("total_schema_size_bytes", 0)
                + self._estimate_model_cache_memory()
            )

            return {
                "timestamp": time.time(),
                "overall_hit_rate_percent": round(overall_hit_rate, 2),
                "total_hits": total_hits,
                "total_misses": total_misses,
                "total_requests": total_requests,
                "total_memory_usage_bytes": total_memory,
                "total_memory_usage_mb": round(total_memory / (1024 * 1024), 2),
                "memory_limit_mb": self.max_total_memory_bytes // (1024 * 1024),
                "memory_utilization_percent": round((total_memory / self.max_total_memory_bytes) * 100, 2),
                "cache_breakdown": {
                    "token_cache": token_stats,
                    "schema_cache": schema_stats,
                    "model_validation_cache": model_stats,
                },
            }

    def _estimate_model_cache_memory(self) -> int:
        """
        Estimate memory usage of model validation cache.

        Returns:
            Estimated memory usage in bytes
        """
        model_stats = self._model_validation_cache.get_stats()
        # Rough estimate: ~200 bytes per entry on average
        return model_stats["total_entries"] * 200

    def cleanup_all_caches(self):
        """Perform cleanup on all caches."""
        with self._lock:
            logger.info("Starting global cache cleanup...")

            cleanup_start = time.time()

            # Cleanup individual caches
            self._token_cache.cleanup()
            self._schema_cache.cleanup()
            self._model_validation_cache.cleanup_all()

            cleanup_duration = time.time() - cleanup_start
            self._last_cleanup_time = time.time()

            logger.info(f"Global cache cleanup completed in {cleanup_duration:.2f} seconds")

    def invalidate_all_caches(self):
        """Clear all caches completely."""
        with self._lock:
            logger.warning("Invalidating all caches...")

            self._token_cache.invalidate()
            self._schema_cache.invalidate_all()
            # Model validation cache doesn't have a clear all method, so we'll skip it

            logger.warning("All caches invalidated")

    def warm_all_caches(self):
        """Warm all caches with common data."""
        logger.info("Starting cache warming process...")

        # Warm token cache with common text patterns
        common_texts = {
            "short_prompt": "Please analyze this code and provide feedback.",
            "medium_prompt": "I need help understanding this implementation. Can you review the code and explain how it works, including any potential issues or improvements?",
            "long_prompt": "I'm working on a complex system that involves multiple components. " * 10,
            "system_prompt": "You are an AI assistant specialized in code analysis and development. " * 5,
        }

        common_models = ["gpt-4", "claude-3-5-sonnet-20241022", "gpt-3.5-turbo", "gemini-pro"]

        try:
            self._token_cache.warm_cache(common_texts, common_models)
        except Exception as e:
            logger.warning(f"Token cache warming failed: {e}")

        # Note: Schema and model validation cache warming would need actual generator functions
        # and would be more complex to implement without circular imports

        logger.info("Cache warming process completed")

    def check_memory_usage(self) -> Dict[str, Any]:
        """
        Check current memory usage against limits.

        Returns:
            Dictionary with memory usage information and warnings
        """
        stats = self.get_global_stats()
        total_memory = stats["total_memory_usage_bytes"]
        utilization = stats["memory_utilization_percent"]

        warnings = []
        if utilization > 90:
            warnings.append("CRITICAL: Cache memory usage above 90%")
        elif utilization > 75:
            warnings.append("WARNING: Cache memory usage above 75%")

        recommendations = []
        if utilization > 80:
            recommendations.append("Consider reducing cache capacity or running cleanup")
        if stats["overall_hit_rate_percent"] < 30:
            recommendations.append("Low cache hit rate - review caching strategy")

        return {
            "total_memory_bytes": total_memory,
            "total_memory_mb": round(total_memory / (1024 * 1024), 2),
            "utilization_percent": utilization,
            "warnings": warnings,
            "recommendations": recommendations,
            "is_healthy": utilization < 90 and len(warnings) == 0,
        }

    def should_cleanup(self) -> bool:
        """
        Check if automatic cleanup should be performed.

        Returns:
            True if cleanup is recommended
        """
        current_time = time.time()
        time_since_cleanup = current_time - self._last_cleanup_time

        # Cleanup if interval has passed or memory usage is high
        memory_check = self.check_memory_usage()

        return time_since_cleanup > self._cleanup_interval or memory_check["utilization_percent"] > 75

    def perform_maintenance(self):
        """Perform routine maintenance on all caches."""
        logger.debug("Performing cache maintenance...")

        # Record performance snapshot
        self._record_performance_snapshot()

        # Cleanup if needed
        if self.should_cleanup():
            self.cleanup_all_caches()

        # Check memory usage and log warnings
        memory_check = self.check_memory_usage()
        for warning in memory_check["warnings"]:
            logger.warning(warning)

        logger.debug("Cache maintenance completed")

    def _record_performance_snapshot(self):
        """Record a performance snapshot for trend analysis."""
        with self._lock:
            snapshot = {"timestamp": time.time(), **self.get_global_stats()}

            self._performance_history.append(snapshot)

            # Limit history size
            if len(self._performance_history) > self._max_history_entries:
                self._performance_history.pop(0)

    def get_performance_trends(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get performance trends over specified time period.

        Args:
            hours: Number of hours to analyze (default: 1)

        Returns:
            Dictionary with trend analysis
        """
        cutoff_time = time.time() - (hours * 3600)
        recent_snapshots = [s for s in self._performance_history if s["timestamp"] > cutoff_time]

        if len(recent_snapshots) < 2:
            return {"error": "Insufficient data for trend analysis"}

        # Calculate trends
        first = recent_snapshots[0]
        last = recent_snapshots[-1]

        hit_rate_trend = last["overall_hit_rate_percent"] - first["overall_hit_rate_percent"]
        memory_trend = last["total_memory_usage_mb"] - first["total_memory_usage_mb"]
        request_trend = last["total_requests"] - first["total_requests"]

        return {
            "time_period_hours": hours,
            "snapshots_analyzed": len(recent_snapshots),
            "hit_rate_trend_percent": round(hit_rate_trend, 2),
            "memory_usage_trend_mb": round(memory_trend, 2),
            "request_count_increase": request_trend,
            "current_hit_rate": last["overall_hit_rate_percent"],
            "current_memory_mb": last["total_memory_usage_mb"],
        }

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of caching system.

        Returns:
            Dictionary with health information
        """
        stats = self.get_global_stats()
        memory_check = self.check_memory_usage()

        # Health indicators
        indicators = {
            "memory_healthy": memory_check["utilization_percent"] < 80,
            "hit_rate_healthy": stats["overall_hit_rate_percent"] > 40,
            "total_requests_reasonable": stats["total_requests"] < 100000,  # Prevent runaway caching
        }

        overall_healthy = all(indicators.values())

        return {
            "overall_healthy": overall_healthy,
            "indicators": indicators,
            "warnings": memory_check["warnings"],
            "recommendations": memory_check["recommendations"],
            "stats_summary": {
                "hit_rate_percent": stats["overall_hit_rate_percent"],
                "memory_usage_mb": stats["total_memory_usage_mb"],
                "total_requests": stats["total_requests"],
            },
        }

    def invalidate_model_caches(self, model_name: str):
        """
        Invalidate caches for a specific model across all cache types.

        Args:
            model_name: Name of the model to invalidate
        """
        logger.info(f"Invalidating caches for model: {model_name}")

        # Invalidate token cache for this model
        self._token_cache.invalidate(model_name=model_name)

        # Invalidate model validation cache
        self._model_validation_cache.invalidate_model(model_name)

        # Schema cache doesn't directly depend on models, so we skip it

        logger.info(f"Cache invalidation completed for model: {model_name}")

    def get_detailed_report(self) -> str:
        """
        Generate a detailed cache performance report.

        Returns:
            Formatted string report
        """
        stats = self.get_global_stats()
        health = self.get_health_status()

        report_lines = [
            "=== CACHE SYSTEM PERFORMANCE REPORT ===",
            f"Timestamp: {time.ctime(stats['timestamp'])}",
            "",
            "=== OVERALL PERFORMANCE ===",
            f"Hit Rate: {stats['overall_hit_rate_percent']:.1f}%",
            f"Total Requests: {stats['total_requests']:,}",
            f"Memory Usage: {stats['total_memory_usage_mb']:.1f}MB / {stats['memory_limit_mb']:.0f}MB",
            f"Memory Utilization: {stats['memory_utilization_percent']:.1f}%",
            "",
            "=== CACHE BREAKDOWN ===",
            f"Token Cache: {stats['cache_breakdown']['token_cache']['hit_rate_percent']:.1f}% hit rate, "
            f"{stats['cache_breakdown']['token_cache']['current_size']} entries",
            f"Schema Cache: {stats['cache_breakdown']['schema_cache']['hit_rate_percent']:.1f}% hit rate, "
            f"{stats['cache_breakdown']['schema_cache']['current_size']} entries",
            f"Model Validation Cache: {stats['cache_breakdown']['model_validation_cache']['hit_rate_percent']:.1f}% hit rate, "
            f"{stats['cache_breakdown']['model_validation_cache']['total_entries']} entries",
            "",
            "=== HEALTH STATUS ===",
            f"Overall Health: {'HEALTHY' if health['overall_healthy'] else 'UNHEALTHY'}",
        ]

        if health["warnings"]:
            report_lines.extend(["", "=== WARNINGS ===", *health["warnings"]])

        if health["recommendations"]:
            report_lines.extend(["", "=== RECOMMENDATIONS ===", *health["recommendations"]])

        return "\n".join(report_lines)


# Global cache manager instance
_cache_manager_instance: Optional[CacheManager] = None
_manager_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance.

    Returns:
        CacheManager instance (singleton)
    """
    global _cache_manager_instance

    if _cache_manager_instance is None:
        with _manager_lock:
            if _cache_manager_instance is None:
                _cache_manager_instance = CacheManager()
                logger.info("Global cache manager initialized")

    return _cache_manager_instance


def get_global_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics."""
    manager = get_cache_manager()
    return manager.get_global_stats()


def perform_global_cache_maintenance():
    """Perform maintenance on all caches."""
    manager = get_cache_manager()
    manager.perform_maintenance()


def get_cache_health_status() -> Dict[str, Any]:
    """Get overall cache system health status."""
    manager = get_cache_manager()
    return manager.get_health_status()
