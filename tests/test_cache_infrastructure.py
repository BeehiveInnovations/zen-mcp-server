"""
Comprehensive tests for the caching infrastructure.

Tests token estimation cache, schema cache, model validation cache,
and the unified cache manager.
"""

import threading
import time
from unittest.mock import patch

import pytest

from tools.shared.schema_cache import SchemaCache, clear_schema_cache
from utils.cache_manager import CacheManager, get_cache_manager
from utils.model_validation_cache import ModelValidationCache
from utils.token_cache import TokenEstimationCache, clear_token_cache, get_token_cache


class TestTokenEstimationCache:
    """Test token estimation cache functionality."""

    def test_cache_initialization(self):
        """Test cache initializes with correct defaults."""
        cache = TokenEstimationCache()
        assert cache.capacity == 1000
        assert cache.default_ttl == 3600
        assert len(cache._cache) == 0

    def test_basic_cache_operations(self):
        """Test basic get/put operations."""
        cache = TokenEstimationCache(capacity=5)

        # Test cache miss
        result = cache.get("test text")
        assert result is None

        # Test cache put and hit
        cache.put("test text", 10)
        result = cache.get("test text")
        assert result == 10

        # Test with different model
        cache.put("test text", 12, "gpt-4")
        result = cache.get("test text", "gpt-4")
        assert result == 12

        # Original should still be there
        result = cache.get("test text")
        assert result == 10

    def test_get_or_compute(self):
        """Test get_or_compute functionality."""
        cache = TokenEstimationCache(capacity=5)

        def compute_func(text):
            return len(text) // 4

        # First call should compute
        result = cache.get_or_compute("hello world", compute_func)
        expected = len("hello world") // 4
        assert result == expected

        # Second call should use cache
        with patch.object(cache, "get", return_value=expected) as mock_get:
            result = cache.get_or_compute("hello world", compute_func)
            assert result == expected
            mock_get.assert_called_once()

    def test_cache_expiration(self):
        """Test TTL-based cache expiration."""
        cache = TokenEstimationCache(capacity=5, default_ttl=1)  # 1 second TTL

        cache.put("test text", 10)

        # Should be available immediately
        result = cache.get("test text")
        assert result == 10

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        result = cache.get("test text")
        assert result is None

    def test_lru_eviction(self):
        """Test LRU eviction when capacity is exceeded."""
        cache = TokenEstimationCache(capacity=3)

        # Fill cache to capacity
        cache.put("text1", 1)
        cache.put("text2", 2)
        cache.put("text3", 3)

        # Access text1 to make it recently used
        cache.get("text1")

        # Add new item, should evict text2 (least recently used)
        cache.put("text4", 4)

        assert cache.get("text1") == 1  # Should still be there
        assert cache.get("text2") is None  # Should be evicted
        assert cache.get("text3") == 3  # Should still be there
        assert cache.get("text4") == 4  # Should be there

    def test_cache_invalidation(self):
        """Test cache invalidation functionality."""
        cache = TokenEstimationCache(capacity=5)

        cache.put("text1", 1, "model1")
        cache.put("text2", 2, "model1")
        cache.put("text3", 3, "model2")

        # Invalidate specific model
        cache.invalidate(model_name="model1")

        assert cache.get("text1", "model1") is None
        assert cache.get("text2", "model1") is None
        assert cache.get("text3", "model2") == 3  # Different model should remain

    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = TokenEstimationCache(capacity=5)

        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 0

        # Add some data and test
        cache.put("text1", 1)
        cache.get("text1")  # Hit
        cache.get("text2")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 50.0

    def test_thread_safety(self):
        """Test thread-safe operations."""
        cache = TokenEstimationCache(capacity=100)
        results = []

        def worker(thread_id):
            for i in range(10):
                text = f"thread_{thread_id}_text_{i}"
                cache.put(text, i)
                result = cache.get(text)
                results.append(result)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All operations should have succeeded
        assert len(results) == 50
        assert all(r is not None for r in results)

    def test_cache_warming(self):
        """Test cache warming functionality."""
        cache = TokenEstimationCache(capacity=10)

        common_texts = {
            "short": "Hello",
            "medium": "Hello world, how are you?",
            "long": "This is a longer text for testing purposes.",
        }

        cache.warm_cache(common_texts, ["gpt-4", "claude"])

        # All texts should be cached for both models
        for text in common_texts.values():
            assert cache.get(text, "gpt-4") is not None
            assert cache.get(text, "claude") is not None


class TestSchemaCache:
    """Test schema cache functionality."""

    def test_cache_initialization(self):
        """Test schema cache initializes correctly."""
        cache = SchemaCache()
        assert cache.capacity == 500
        assert cache.default_ttl == 7200
        assert len(cache._cache) == 0

    def test_schema_caching(self):
        """Test schema generation and caching."""
        cache = SchemaCache(capacity=5)

        def mock_generator():
            return {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"test": {"type": "string"}},
                "additionalProperties": False,
            }

        # First call should generate
        schema = cache.get_or_generate("test_tool", {"auto_mode": False}, mock_generator)

        assert schema["type"] == "object"
        assert "test" in schema["properties"]

        # Second call should use cache
        with patch.object(cache, "get", return_value=schema) as mock_get:
            cached_schema = cache.get_or_generate("test_tool", {"auto_mode": False}, mock_generator)
            assert cached_schema == schema
            mock_get.assert_called_once()

    def test_tool_version_invalidation(self):
        """Test cache invalidation based on tool version."""
        cache = SchemaCache(capacity=5)

        def mock_generator():
            return {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }

        # Cache schema with version 1.0
        cache.put("test_tool", {}, mock_generator(), "1.0")

        # Should get cached version
        result = cache.get("test_tool", {})
        assert result is not None

        # Update tool version
        cache.update_tool_version("test_tool", "2.0")

        # Should not get cached version (invalidated)
        result = cache.get("test_tool", {})
        assert result is None

    def test_schema_validation(self):
        """Test schema validation before caching."""
        cache = SchemaCache(capacity=5)

        # Valid schema
        valid_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

        cache.put("test_tool", {}, valid_schema)
        result = cache.get("test_tool", {})
        assert result is not None

        # Invalid schema (missing required fields)
        invalid_schema = {"invalid": "schema"}

        cache.put("test_tool2", {}, invalid_schema)
        result = cache.get("test_tool2", {})
        assert result is None  # Should not be cached

    def test_cache_statistics(self):
        """Test schema cache statistics."""
        cache = SchemaCache(capacity=5)

        def mock_generator():
            return {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Generate and cache schema
        cache.get_or_generate("tool1", {}, mock_generator)
        cache.get("tool1", {})  # Hit
        cache.get("tool2", {})  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestModelValidationCache:
    """Test model validation cache functionality."""

    def test_cache_initialization(self):
        """Test model validation cache initializes correctly."""
        cache = ModelValidationCache()
        assert cache.capacity == 1000
        assert cache.default_ttl == 1800

    def test_model_availability_caching(self):
        """Test model availability result caching."""
        cache = ModelValidationCache(capacity=5)

        # Cache successful validation
        cache.cache_model_availability("gpt-4", "chat", True, "openai", None)

        result = cache.get_model_availability("gpt-4", "chat")
        assert result is not None
        assert result["is_available"] is True
        assert result["provider_name"] == "openai"

        # Cache failed validation
        cache.cache_model_availability("unknown-model", "chat", False, None, "Model not found")

        result = cache.get_model_availability("unknown-model", "chat")
        assert result is not None
        assert result["is_available"] is False
        assert result["error_message"] == "Model not found"

    def test_provider_capability_caching(self):
        """Test provider capability caching."""
        cache = ModelValidationCache(capacity=5)

        # Cache capability
        cache.cache_provider_capability("openai", "vision", True, {"max_images": 10})

        result = cache.get_provider_capability("openai", "vision")
        assert result is not None
        assert result["is_supported"] is True
        assert result["metadata"]["max_images"] == 10

    def test_model_resolution_caching(self):
        """Test model resolution caching."""
        cache = ModelValidationCache(capacity=5)

        # Cache resolution
        cache.cache_model_resolution("chat", "fast", "gpt-3.5-turbo", auto_mode=True)

        result = cache.get_model_resolution("chat", "fast", auto_mode=True)
        assert result == "gpt-3.5-turbo"

    def test_cache_invalidation(self):
        """Test cache invalidation for models and providers."""
        cache = ModelValidationCache(capacity=10)

        # Add some data
        cache.cache_model_availability("gpt-4", "chat", True, "openai")
        cache.cache_provider_capability("openai", "vision", True)
        cache.cache_model_resolution("chat", "fast", "gpt-4")

        # Invalidate model
        cache.invalidate_model("gpt-4")

        # Model-related caches should be cleared
        assert cache.get_model_availability("gpt-4", "chat") is None
        assert cache.get_model_resolution("chat", "fast") is None

        # Provider capability should remain
        assert cache.get_provider_capability("openai", "vision") is not None

    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        cache = ModelValidationCache(capacity=5, default_ttl=1)

        # Add data that will expire
        cache.cache_model_availability("gpt-4", "chat", True, "openai")

        # Wait for expiration
        time.sleep(1.1)

        # Cleanup should remove expired entries
        cache.cleanup_all()

        result = cache.get_model_availability("gpt-4", "chat")
        assert result is None


class TestCacheManager:
    """Test unified cache manager functionality."""

    def test_cache_manager_initialization(self):
        """Test cache manager initializes correctly."""
        manager = CacheManager(max_total_memory_mb=50)
        assert manager.max_total_memory_bytes == 50 * 1024 * 1024

    def test_global_statistics(self):
        """Test global cache statistics collection."""
        manager = CacheManager()

        # Get stats from all caches
        stats = manager.get_global_stats()

        assert "overall_hit_rate_percent" in stats
        assert "total_memory_usage_bytes" in stats
        assert "cache_breakdown" in stats
        assert "token_cache" in stats["cache_breakdown"]
        assert "schema_cache" in stats["cache_breakdown"]
        assert "model_validation_cache" in stats["cache_breakdown"]

    def test_memory_usage_tracking(self):
        """Test memory usage tracking and warnings."""
        manager = CacheManager(max_total_memory_mb=1)  # Very small limit

        memory_check = manager.check_memory_usage()

        assert "total_memory_bytes" in memory_check
        assert "utilization_percent" in memory_check
        assert "warnings" in memory_check
        assert "is_healthy" in memory_check

    def test_cache_maintenance(self):
        """Test cache maintenance operations."""
        manager = CacheManager()

        # Should not raise exceptions
        manager.cleanup_all_caches()
        manager.perform_maintenance()

    def test_health_status(self):
        """Test cache system health monitoring."""
        manager = CacheManager()

        health = manager.get_health_status()

        assert "overall_healthy" in health
        assert "indicators" in health
        assert "warnings" in health
        assert "stats_summary" in health

    def test_detailed_report(self):
        """Test detailed performance report generation."""
        manager = CacheManager()

        report = manager.get_detailed_report()

        assert isinstance(report, str)
        assert "CACHE SYSTEM PERFORMANCE REPORT" in report
        assert "OVERALL PERFORMANCE" in report
        assert "CACHE BREAKDOWN" in report
        assert "HEALTH STATUS" in report

    @pytest.mark.asyncio
    async def test_cache_warming(self):
        """Test cache warming functionality."""
        manager = CacheManager()

        # Should not raise exceptions
        manager.warm_all_caches()

    def test_model_cache_invalidation(self):
        """Test model-specific cache invalidation."""
        manager = CacheManager()

        # Should not raise exceptions
        manager.invalidate_model_caches("gpt-4")


class TestCacheIntegration:
    """Test integration between different cache components."""

    def test_token_cache_integration(self):
        """Test token cache integration with utilities."""
        # Clear any existing cache
        clear_token_cache()

        # Import here to test integration
        from utils.token_utils import estimate_tokens

        # First call should populate cache
        result1 = estimate_tokens("Hello world", "gpt-4")

        # Second call should use cache
        result2 = estimate_tokens("Hello world", "gpt-4")

        assert result1 == result2

        # Verify cache statistics
        from utils.token_cache import get_token_cache_stats

        stats = get_token_cache_stats()
        assert stats["total_requests"] >= 2

    def test_schema_cache_integration(self):
        """Test schema cache integration with builders."""
        # Clear any existing cache
        clear_schema_cache()

        # Import here to test integration
        from tools.shared.schema_builders import SchemaBuilder

        # Build schema with caching
        schema1 = SchemaBuilder.build_schema(
            tool_name="test_tool", tool_specific_fields={"test": {"type": "string"}}, auto_mode=False
        )

        schema2 = SchemaBuilder.build_schema(
            tool_name="test_tool", tool_specific_fields={"test": {"type": "string"}}, auto_mode=False
        )

        assert schema1 == schema2

        # Verify cache was used
        from tools.shared.schema_cache import get_schema_cache_stats

        stats = get_schema_cache_stats()
        assert stats["total_requests"] >= 1

    def test_global_cache_manager_singleton(self):
        """Test that cache manager is properly singleton."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2

    def test_cache_performance_under_load(self):
        """Test cache performance under concurrent load."""
        manager = get_cache_manager()
        token_cache = get_token_cache()

        # Simulate concurrent access
        def worker():
            for i in range(100):
                text = f"test text {i}"
                token_cache.put(text, len(text))
                result = token_cache.get(text)
                assert result == len(text)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Check final statistics
        stats = manager.get_global_stats()
        assert stats["total_requests"] > 0
        assert stats["overall_hit_rate_percent"] >= 0


if __name__ == "__main__":
    pytest.main([__file__])
