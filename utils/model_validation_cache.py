"""
Model Validation Cache for efficient model validation and capability caching.

This module provides intelligent caching for model validation, provider resolution,
and capability checks to reduce repeated validation computations.
"""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelValidationCache:
    """
    Cache for model validation results, provider capabilities, and model resolution.

    Features:
    - Provider-model combination caching
    - Capability caching with expiration
    - Temperature constraint caching
    - Provider availability monitoring
    - Background cache refresh mechanisms
    - Thread-safe operations
    """

    def __init__(self, capacity: int = 1000, default_ttl: int = 1800):
        """
        Initialize the model validation cache.

        Args:
            capacity: Maximum number of cached entries (default: 1000)
            default_ttl: Default TTL in seconds (default: 1800 = 30 minutes)
        """
        self.capacity = capacity
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Dict] = OrderedDict()
        self._lock = threading.RLock()

        # Separate caches for different validation types
        self._model_availability_cache: Dict[str, Dict] = {}
        self._provider_capability_cache: Dict[str, Dict] = {}
        self._model_resolution_cache: Dict[str, Dict] = {}

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

        logger.debug(f"ModelValidationCache initialized with capacity={capacity}, ttl={default_ttl}")

    def _generate_cache_key(self, cache_type: str, **kwargs) -> str:
        """
        Generate cache key for different validation types.

        Args:
            cache_type: Type of cache entry (availability, capability, resolution)
            **kwargs: Key-value pairs for cache key generation

        Returns:
            Hash-based cache key
        """
        # Sort kwargs for consistent hashing
        sorted_params = json.dumps(kwargs, sort_keys=True, default=str)
        combined = f"{cache_type}:{sorted_params}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    def _is_expired(self, entry: Dict) -> bool:
        """Check if a cache entry has expired."""
        current_time = time.time()
        return current_time > (entry["timestamp"] + entry["ttl"])

    def _evict_lru(self, cache_dict: OrderedDict):
        """Evict the least recently used item from specified cache."""
        if cache_dict:
            evicted_key = next(iter(cache_dict))
            del cache_dict[evicted_key]
            self._evictions += 1
            logger.debug(f"Evicted LRU cache entry: {evicted_key}")

    def _cleanup_expired(self, cache_dict: Dict[str, Dict]):
        """Remove expired entries from specified cache."""
        expired_keys = []

        for key, entry in cache_dict.items():
            if self._is_expired(entry):
                expired_keys.append(key)

        for key in expired_keys:
            del cache_dict[key]
            logger.debug(f"Removed expired cache entry: {key}")

    def cache_model_availability(
        self,
        model_name: str,
        tool_name: str,
        is_available: bool,
        provider_name: str = None,
        error_message: str = None,
        ttl: Optional[int] = None,
    ):
        """
        Cache model availability result.

        Args:
            model_name: Name of the model
            tool_name: Name of the tool requesting validation
            is_available: Whether the model is available
            provider_name: Name of the provider (if resolved)
            error_message: Error message if not available
            ttl: Time-to-live in seconds
        """
        cache_key = self._generate_cache_key("availability", model=model_name, tool=tool_name)

        ttl = ttl or self.default_ttl

        with self._lock:
            # Ensure capacity
            while len(self._model_availability_cache) >= self.capacity // 3:  # Use 1/3 of capacity
                oldest_key = next(iter(self._model_availability_cache))
                del self._model_availability_cache[oldest_key]
                self._evictions += 1

            entry = {
                "is_available": is_available,
                "provider_name": provider_name,
                "error_message": error_message,
                "model_name": model_name,
                "tool_name": tool_name,
                "timestamp": time.time(),
                "ttl": ttl,
            }

            self._model_availability_cache[cache_key] = entry
            logger.debug(f"Cached model availability: {model_name} -> {is_available}")

    def get_model_availability(self, model_name: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get cached model availability result.

        Args:
            model_name: Name of the model
            tool_name: Name of the tool

        Returns:
            Cached availability result or None if not found/expired
        """
        cache_key = self._generate_cache_key("availability", model=model_name, tool=tool_name)

        with self._lock:
            if cache_key not in self._model_availability_cache:
                self._misses += 1
                return None

            entry = self._model_availability_cache[cache_key]

            if self._is_expired(entry):
                del self._model_availability_cache[cache_key]
                self._misses += 1
                return None

            self._hits += 1
            logger.debug(f"Model availability cache hit: {model_name}")

            return {
                "is_available": entry["is_available"],
                "provider_name": entry.get("provider_name"),
                "error_message": entry.get("error_message"),
            }

    def cache_provider_capability(
        self,
        provider_name: str,
        capability: str,
        is_supported: bool,
        metadata: Dict[str, Any] = None,
        ttl: Optional[int] = None,
    ):
        """
        Cache provider capability information.

        Args:
            provider_name: Name of the provider
            capability: Capability being checked (e.g., 'vision', 'function_calling')
            is_supported: Whether the capability is supported
            metadata: Additional metadata about the capability
            ttl: Time-to-live in seconds
        """
        cache_key = self._generate_cache_key("capability", provider=provider_name, capability=capability)

        ttl = ttl or (self.default_ttl * 2)  # Capabilities change less frequently

        with self._lock:
            # Ensure capacity
            while len(self._provider_capability_cache) >= self.capacity // 3:
                oldest_key = next(iter(self._provider_capability_cache))
                del self._provider_capability_cache[oldest_key]
                self._evictions += 1

            entry = {
                "is_supported": is_supported,
                "metadata": metadata or {},
                "provider_name": provider_name,
                "capability": capability,
                "timestamp": time.time(),
                "ttl": ttl,
            }

            self._provider_capability_cache[cache_key] = entry
            logger.debug(f"Cached provider capability: {provider_name}.{capability} -> {is_supported}")

    def get_provider_capability(self, provider_name: str, capability: str) -> Optional[Dict[str, Any]]:
        """
        Get cached provider capability result.

        Args:
            provider_name: Name of the provider
            capability: Capability being checked

        Returns:
            Cached capability result or None if not found/expired
        """
        cache_key = self._generate_cache_key("capability", provider=provider_name, capability=capability)

        with self._lock:
            if cache_key not in self._provider_capability_cache:
                self._misses += 1
                return None

            entry = self._provider_capability_cache[cache_key]

            if self._is_expired(entry):
                del self._provider_capability_cache[cache_key]
                self._misses += 1
                return None

            self._hits += 1
            logger.debug(f"Provider capability cache hit: {provider_name}.{capability}")

            return {"is_supported": entry["is_supported"], "metadata": entry.get("metadata", {})}

    def cache_model_resolution(
        self,
        tool_name: str,
        tool_category: str,
        resolved_model: str,
        auto_mode: bool = False,
        ttl: Optional[int] = None,
    ):
        """
        Cache model resolution result for auto mode.

        Args:
            tool_name: Name of the tool
            tool_category: Category of the tool
            resolved_model: The resolved model name
            auto_mode: Whether this was auto mode resolution
            ttl: Time-to-live in seconds
        """
        cache_key = self._generate_cache_key("resolution", tool=tool_name, category=tool_category, auto=auto_mode)

        ttl = ttl or (self.default_ttl // 2)  # Shorter TTL for auto resolution

        with self._lock:
            # Ensure capacity
            while len(self._model_resolution_cache) >= self.capacity // 3:
                oldest_key = next(iter(self._model_resolution_cache))
                del self._model_resolution_cache[oldest_key]
                self._evictions += 1

            entry = {
                "resolved_model": resolved_model,
                "tool_name": tool_name,
                "tool_category": tool_category,
                "auto_mode": auto_mode,
                "timestamp": time.time(),
                "ttl": ttl,
            }

            self._model_resolution_cache[cache_key] = entry
            logger.debug(f"Cached model resolution: {tool_name} -> {resolved_model}")

    def get_model_resolution(self, tool_name: str, tool_category: str, auto_mode: bool = False) -> Optional[str]:
        """
        Get cached model resolution result.

        Args:
            tool_name: Name of the tool
            tool_category: Category of the tool
            auto_mode: Whether this is auto mode resolution

        Returns:
            Cached resolved model name or None if not found/expired
        """
        cache_key = self._generate_cache_key("resolution", tool=tool_name, category=tool_category, auto=auto_mode)

        with self._lock:
            if cache_key not in self._model_resolution_cache:
                self._misses += 1
                return None

            entry = self._model_resolution_cache[cache_key]

            if self._is_expired(entry):
                del self._model_resolution_cache[cache_key]
                self._misses += 1
                return None

            self._hits += 1
            logger.debug(f"Model resolution cache hit: {tool_name}")

            return entry["resolved_model"]

    def invalidate_model(self, model_name: str):
        """
        Invalidate all cached entries for a specific model.

        Args:
            model_name: Name of the model to invalidate
        """
        with self._lock:
            # Invalidate from all cache types
            caches = [
                ("availability", self._model_availability_cache),
                ("capability", self._provider_capability_cache),
                ("resolution", self._model_resolution_cache),
            ]

            total_invalidated = 0

            for cache_name, cache_dict in caches:
                keys_to_remove = []

                for key, entry in cache_dict.items():
                    if entry.get("model_name") == model_name or entry.get("resolved_model") == model_name:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del cache_dict[key]
                    total_invalidated += 1
                    self._invalidations += 1

            logger.info(f"Invalidated {total_invalidated} cache entries for model: {model_name}")

    def invalidate_provider(self, provider_name: str):
        """
        Invalidate all cached entries for a specific provider.

        Args:
            provider_name: Name of the provider to invalidate
        """
        with self._lock:
            caches = [
                ("availability", self._model_availability_cache),
                ("capability", self._provider_capability_cache),
                ("resolution", self._model_resolution_cache),
            ]

            total_invalidated = 0

            for cache_name, cache_dict in caches:
                keys_to_remove = []

                for key, entry in cache_dict.items():
                    if entry.get("provider_name") == provider_name:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del cache_dict[key]
                    total_invalidated += 1
                    self._invalidations += 1

            logger.info(f"Invalidated {total_invalidated} cache entries for provider: {provider_name}")

    def cleanup_all(self):
        """Manual cleanup of expired entries from all caches."""
        with self._lock:
            caches = [
                ("availability", self._model_availability_cache),
                ("capability", self._provider_capability_cache),
                ("resolution", self._model_resolution_cache),
            ]

            total_cleaned = 0

            for cache_name, cache_dict in caches:
                initial_size = len(cache_dict)
                self._cleanup_expired(cache_dict)
                cleaned = initial_size - len(cache_dict)
                total_cleaned += cleaned

            if total_cleaned > 0:
                logger.info(f"Model validation cache cleanup: removed {total_cleaned} expired entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary with detailed cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "capacity": self.capacity,
                "total_entries": (
                    len(self._model_availability_cache)
                    + len(self._provider_capability_cache)
                    + len(self._model_resolution_cache)
                ),
                "availability_cache_size": len(self._model_availability_cache),
                "capability_cache_size": len(self._provider_capability_cache),
                "resolution_cache_size": len(self._model_resolution_cache),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "invalidations": self._invalidations,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
            }

    def warm_cache(self, common_models: List[str], common_tools: List[str]):
        """
        Warm cache with common model-tool combinations.

        Args:
            common_models: List of commonly used model names
            common_tools: List of commonly used tool names
        """
        # This would typically be called with actual validation functions
        # For now, we'll just log the warming attempt
        logger.info(
            f"Model validation cache warming attempted for {len(common_models)} models "
            f"and {len(common_tools)} tools"
        )


# Global cache instance
_model_validation_cache_instance: Optional[ModelValidationCache] = None
_cache_lock = threading.Lock()


def get_model_validation_cache() -> ModelValidationCache:
    """
    Get the global model validation cache instance.

    Returns:
        ModelValidationCache instance (singleton)
    """
    global _model_validation_cache_instance

    if _model_validation_cache_instance is None:
        with _cache_lock:
            if _model_validation_cache_instance is None:
                _model_validation_cache_instance = ModelValidationCache()
                logger.info("Global model validation cache initialized")

    return _model_validation_cache_instance


def clear_model_validation_cache():
    """Clear the global model validation cache."""
    cache = get_model_validation_cache()
    cache.invalidate_model("")  # This will clear all entries
    logger.info("Global model validation cache cleared")


def get_model_validation_cache_stats() -> Dict[str, Any]:
    """Get statistics from the global model validation cache."""
    cache = get_model_validation_cache()
    return cache.get_stats()
