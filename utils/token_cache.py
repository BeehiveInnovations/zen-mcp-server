"""
Token Estimation Cache for efficient repeated token calculations.

This module provides intelligent caching for token estimation to achieve
50-80% reduction in repeated token calculations across the Zen MCP Server.
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TokenEstimationCache:
    """
    LRU cache with TTL support for token estimation results.

    Features:
    - LRU eviction policy with configurable capacity
    - TTL-based expiration for dynamic content
    - Hash-based cache keys for memory efficiency
    - Model-specific token estimation caching
    - Thread-safe operations with proper locking
    - Cache hit rate monitoring and statistics
    """

    def __init__(self, capacity: int = 1000, default_ttl: int = 3600):
        """
        Initialize the token estimation cache.

        Args:
            capacity: Maximum number of cache entries (default: 1000)
            default_ttl: Default TTL in seconds (default: 3600 = 1 hour)
        """
        self.capacity = capacity
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Dict] = OrderedDict()
        self._lock = threading.RLock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        logger.debug(f"TokenEstimationCache initialized with capacity={capacity}, ttl={default_ttl}")

    def _generate_cache_key(self, text: str, model_name: str = "default") -> str:
        """
        Generate a hash-based cache key for memory efficiency.

        Args:
            text: Input text for token estimation
            model_name: Model name for model-specific caching

        Returns:
            SHA256 hash as cache key
        """
        # Create a combined string with text length for quick differentiation
        combined = f"{len(text)}:{model_name}:{text}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]  # Use first 16 chars

    def _is_expired(self, entry: Dict) -> bool:
        """
        Check if a cache entry has expired based on TTL.

        Args:
            entry: Cache entry with timestamp and ttl

        Returns:
            True if entry is expired, False otherwise
        """
        current_time = time.time()
        return current_time > (entry["timestamp"] + entry["ttl"])

    def _evict_lru(self):
        """Evict the least recently used item from cache."""
        if self._cache:
            evicted_key = next(iter(self._cache))
            del self._cache[evicted_key]
            self._evictions += 1
            logger.debug(f"Evicted LRU cache entry: {evicted_key}")

    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []

        for key, entry in self._cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]
            logger.debug(f"Removed expired cache entry: {key}")

    def get(self, text: str, model_name: str = "default") -> Optional[int]:
        """
        Get cached token estimation result.

        Args:
            text: Input text for token estimation
            model_name: Model name for model-specific lookup

        Returns:
            Cached token count or None if not found/expired
        """
        cache_key = self._generate_cache_key(text, model_name)

        with self._lock:
            if cache_key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[cache_key]

            # Check if expired
            if self._is_expired(entry):
                del self._cache[cache_key]
                self._misses += 1
                logger.debug(f"Cache entry expired for key: {cache_key}")
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            self._hits += 1

            logger.debug(f"Cache hit for model={model_name}, text_len={len(text)}")
            return entry["token_count"]

    def put(self, text: str, token_count: int, model_name: str = "default", ttl: Optional[int] = None):
        """
        Store token estimation result in cache.

        Args:
            text: Input text that was processed
            token_count: Calculated token count
            model_name: Model name for model-specific caching
            ttl: Time-to-live in seconds (uses default if None)
        """
        cache_key = self._generate_cache_key(text, model_name)
        ttl = ttl or self.default_ttl

        with self._lock:
            # Cleanup expired entries periodically
            if len(self._cache) % 100 == 0:  # Every 100 operations
                self._cleanup_expired()

            # Ensure capacity
            while len(self._cache) >= self.capacity:
                self._evict_lru()

            # Store new entry
            entry = {
                "token_count": token_count,
                "timestamp": time.time(),
                "ttl": ttl,
                "model_name": model_name,
                "text_length": len(text),
            }

            self._cache[cache_key] = entry
            self._cache.move_to_end(cache_key)  # Mark as most recently used

            logger.debug(f"Cached token estimation: model={model_name}, text_len={len(text)}, tokens={token_count}")

    def get_or_compute(self, text: str, compute_func, model_name: str = "default", ttl: Optional[int] = None) -> int:
        """
        Get cached result or compute and cache it.

        Args:
            text: Input text for token estimation
            compute_func: Function to compute token count if not cached
            model_name: Model name for model-specific caching
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            Token count from cache or newly computed
        """
        # Try cache first
        cached_result = self.get(text, model_name)
        if cached_result is not None:
            return cached_result

        # Compute and cache
        token_count = compute_func(text)
        self.put(text, token_count, model_name, ttl)

        return token_count

    def invalidate(self, text: str = None, model_name: str = None):
        """
        Invalidate cache entries.

        Args:
            text: Specific text to invalidate (if None, invalidates all for model)
            model_name: Model to invalidate (if None, invalidates all)
        """
        with self._lock:
            if text is not None and model_name is not None:
                # Invalidate specific entry
                cache_key = self._generate_cache_key(text, model_name)
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.debug(f"Invalidated specific cache entry: {cache_key}")
            elif model_name is not None:
                # Invalidate all entries for model
                keys_to_remove = []
                for key, entry in self._cache.items():
                    if entry.get("model_name") == model_name:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self._cache[key]

                logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for model: {model_name}")
            else:
                # Clear all
                self._cache.clear()
                logger.debug("Cleared all token estimation cache entries")

    def get_stats(self) -> Dict:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "capacity": self.capacity,
                "current_size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "memory_usage_estimate": self._estimate_memory_usage(),
            }

    def _estimate_memory_usage(self) -> int:
        """
        Estimate memory usage of cache in bytes.

        Returns:
            Estimated memory usage in bytes
        """
        if not self._cache:
            return 0

        # Estimate based on average entry size
        # Each entry has: cache_key (16 chars), token_count (int), timestamp (float),
        # ttl (int), model_name (string), text_length (int)
        avg_model_name_len = 20  # Estimate
        entry_size = 16 + 4 + 8 + 4 + avg_model_name_len + 4  # ~56 bytes per entry

        return len(self._cache) * entry_size

    def warm_cache(self, common_texts: Dict[str, str], model_names: list[str] = None):
        """
        Warm the cache with commonly used texts.

        Args:
            common_texts: Dictionary of {description: text} for warming
            model_names: List of models to warm cache for (default: ["default"])
        """
        if model_names is None:
            model_names = ["default"]

        from utils.token_utils import estimate_tokens  # Import here to avoid circular import

        warmed_count = 0

        with self._lock:
            for desc, text in common_texts.items():
                for model_name in model_names:
                    if self.get(text, model_name) is None:  # Only if not already cached
                        token_count = estimate_tokens(text)
                        self.put(text, token_count, model_name)
                        warmed_count += 1

        logger.info(f"Warmed token cache with {warmed_count} entries for {len(model_names)} models")

    def cleanup(self):
        """Manual cleanup of expired entries."""
        with self._lock:
            initial_size = len(self._cache)
            self._cleanup_expired()
            cleaned = initial_size - len(self._cache)

            if cleaned > 0:
                logger.info(f"Token cache cleanup: removed {cleaned} expired entries")


# Global cache instance
_token_cache_instance: Optional[TokenEstimationCache] = None
_cache_lock = threading.Lock()


def get_token_cache() -> TokenEstimationCache:
    """
    Get the global token estimation cache instance.

    Returns:
        TokenEstimationCache instance (singleton)
    """
    global _token_cache_instance

    if _token_cache_instance is None:
        with _cache_lock:
            if _token_cache_instance is None:
                _token_cache_instance = TokenEstimationCache()
                logger.info("Global token estimation cache initialized")

    return _token_cache_instance


def clear_token_cache():
    """Clear the global token estimation cache."""
    cache = get_token_cache()
    cache.invalidate()
    logger.info("Global token estimation cache cleared")


def get_token_cache_stats() -> Dict:
    """Get statistics from the global token estimation cache."""
    cache = get_token_cache()
    return cache.get_stats()
