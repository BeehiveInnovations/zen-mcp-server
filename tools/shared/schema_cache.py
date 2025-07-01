"""
Schema Cache for efficient tool schema generation and validation.

This module provides intelligent caching for tool schema generation to reduce
repeated schema computations and improve tool initialization performance.
"""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SchemaCache:
    """
    LRU cache for tool schema generation with auto-mode support.

    Features:
    - Parameter-based cache key generation
    - Schema validation and consistency checks
    - Bulk cache warming for common tools
    - Cache invalidation on tool updates
    - Thread-safe operations
    - Memory-efficient storage with size limits
    """

    def __init__(self, capacity: int = 500, default_ttl: int = 7200):
        """
        Initialize the schema cache.

        Args:
            capacity: Maximum number of cached schemas (default: 500)
            default_ttl: Default TTL in seconds (default: 7200 = 2 hours)
        """
        self.capacity = capacity
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Dict] = OrderedDict()
        self._lock = threading.RLock()

        # Track tool versions for cache invalidation
        self._tool_versions: Dict[str, str] = {}

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

        logger.debug(f"SchemaCache initialized with capacity={capacity}, ttl={default_ttl}")

    def _generate_cache_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        Generate a deterministic cache key from tool name and parameters.

        Args:
            tool_name: Name of the tool
            parameters: Schema generation parameters

        Returns:
            Hash-based cache key
        """
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(parameters, sort_keys=True, default=str)
        combined = f"{tool_name}:{sorted_params}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    def _is_expired(self, entry: Dict) -> bool:
        """Check if a cache entry has expired."""
        current_time = time.time()
        return current_time > (entry["timestamp"] + entry["ttl"])

    def _evict_lru(self):
        """Evict the least recently used schema from cache."""
        if self._cache:
            evicted_key = next(iter(self._cache))
            evicted_entry = self._cache[evicted_key]
            del self._cache[evicted_key]
            self._evictions += 1
            logger.debug(f"Evicted LRU schema: {evicted_entry.get('tool_name', 'unknown')}")

    def _cleanup_expired(self):
        """Remove expired schema entries from cache."""
        expired_keys = []

        for key, entry in self._cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]
            logger.debug(f"Removed expired schema entry: {key}")

    def _validate_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Validate that a schema is well-formed.

        Args:
            schema: JSON schema to validate

        Returns:
            True if schema is valid, False otherwise
        """
        try:
            # Basic schema validation
            if not isinstance(schema, dict):
                return False

            # Check required fields
            if "type" not in schema or schema["type"] != "object":
                return False

            if "properties" not in schema or not isinstance(schema["properties"], dict):
                return False

            # Check for JSON schema structure
            if "$schema" not in schema:
                return False

            return True

        except Exception as e:
            logger.warning(f"Schema validation failed: {e}")
            return False

    def get(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached schema for tool with given parameters.

        Args:
            tool_name: Name of the tool
            parameters: Schema generation parameters

        Returns:
            Cached schema or None if not found/expired
        """
        cache_key = self._generate_cache_key(tool_name, parameters)

        with self._lock:
            if cache_key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[cache_key]

            # Check if expired
            if self._is_expired(entry):
                del self._cache[cache_key]
                self._misses += 1
                logger.debug(f"Schema cache entry expired for tool: {tool_name}")
                return None

            # Check tool version for invalidation
            tool_version = self._tool_versions.get(tool_name)
            if tool_version and entry.get("tool_version") != tool_version:
                del self._cache[cache_key]
                self._misses += 1
                self._invalidations += 1
                logger.debug(f"Schema cache invalidated due to version mismatch: {tool_name}")
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            self._hits += 1

            schema = entry["schema"]
            logger.debug(f"Schema cache hit for tool: {tool_name}")
            return schema

    def put(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        schema: Dict[str, Any],
        tool_version: str = None,
        ttl: Optional[int] = None,
    ):
        """
        Store schema in cache.

        Args:
            tool_name: Name of the tool
            parameters: Schema generation parameters
            schema: Generated schema to cache
            tool_version: Version of the tool (for invalidation)
            ttl: Time-to-live in seconds
        """
        # Validate schema before caching
        if not self._validate_schema(schema):
            logger.warning(f"Invalid schema not cached for tool: {tool_name}")
            return

        cache_key = self._generate_cache_key(tool_name, parameters)
        ttl = ttl or self.default_ttl

        with self._lock:
            # Cleanup expired entries periodically
            if len(self._cache) % 50 == 0:  # Every 50 operations
                self._cleanup_expired()

            # Ensure capacity
            while len(self._cache) >= self.capacity:
                self._evict_lru()

            # Update tool version if provided
            if tool_version:
                self._tool_versions[tool_name] = tool_version

            # Store new entry
            entry = {
                "schema": schema,
                "tool_name": tool_name,
                "parameters": parameters,
                "tool_version": tool_version,
                "timestamp": time.time(),
                "ttl": ttl,
                "schema_size": len(json.dumps(schema)),
            }

            self._cache[cache_key] = entry
            self._cache.move_to_end(cache_key)

            logger.debug(f"Cached schema for tool: {tool_name}, size: {entry['schema_size']} bytes")

    def get_or_generate(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        generator_func,
        tool_version: str = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get cached schema or generate and cache it.

        Args:
            tool_name: Name of the tool
            parameters: Schema generation parameters
            generator_func: Function to generate schema if not cached
            tool_version: Version of the tool
            ttl: Time-to-live in seconds

        Returns:
            Schema from cache or newly generated
        """
        # Try cache first
        cached_schema = self.get(tool_name, parameters)
        if cached_schema is not None:
            return cached_schema

        # Generate and cache
        schema = generator_func()
        self.put(tool_name, parameters, schema, tool_version, ttl)

        return schema

    def invalidate_tool(self, tool_name: str):
        """
        Invalidate all cached schemas for a specific tool.

        Args:
            tool_name: Name of the tool to invalidate
        """
        with self._lock:
            keys_to_remove = []

            for key, entry in self._cache.items():
                if entry.get("tool_name") == tool_name:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]
                self._invalidations += 1

            # Remove tool version tracking
            if tool_name in self._tool_versions:
                del self._tool_versions[tool_name]

            logger.info(f"Invalidated {len(keys_to_remove)} schema cache entries for tool: {tool_name}")

    def invalidate_all(self):
        """Clear all cached schemas."""
        with self._lock:
            self._cache.clear()
            self._tool_versions.clear()
            logger.info("Cleared all schema cache entries")

    def update_tool_version(self, tool_name: str, version: str):
        """
        Update tool version for cache invalidation.

        Args:
            tool_name: Name of the tool
            version: New version identifier
        """
        with self._lock:
            old_version = self._tool_versions.get(tool_name)
            if old_version != version:
                self._tool_versions[tool_name] = version
                # Invalidate existing cache entries for this tool
                self.invalidate_tool(tool_name)
                logger.info(f"Updated tool version: {tool_name} -> {version}")

    def warm_cache(self, tool_configs: List[Dict[str, Any]]):
        """
        Warm cache with common tool configurations.

        Args:
            tool_configs: List of tool configuration dictionaries
                         Each should contain: tool_name, parameters, generator_func
        """
        warmed_count = 0

        for config in tool_configs:
            tool_name = config.get("tool_name")
            parameters = config.get("parameters", {})
            generator_func = config.get("generator_func")

            if not all([tool_name, generator_func]):
                continue

            # Only warm if not already cached
            if self.get(tool_name, parameters) is None:
                try:
                    schema = generator_func()
                    self.put(tool_name, parameters, schema)
                    warmed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to warm cache for {tool_name}: {e}")

        logger.info(f"Warmed schema cache with {warmed_count} entries")

    def get_tool_schemas(self, tool_name: str) -> List[Dict[str, Any]]:
        """
        Get all cached schemas for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of cached schema entries for the tool
        """
        schemas = []

        with self._lock:
            for entry in self._cache.values():
                if entry.get("tool_name") == tool_name and not self._is_expired(entry):
                    schemas.append(
                        {
                            "parameters": entry["parameters"],
                            "schema": entry["schema"],
                            "tool_version": entry.get("tool_version"),
                            "timestamp": entry["timestamp"],
                        }
                    )

        return schemas

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            # Calculate total schema size
            total_size = sum(entry.get("schema_size", 0) for entry in self._cache.values())

            # Get tool breakdown
            tool_counts = {}
            for entry in self._cache.values():
                tool_name = entry.get("tool_name", "unknown")
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

            return {
                "capacity": self.capacity,
                "current_size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "invalidations": self._invalidations,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "total_schema_size_bytes": total_size,
                "tool_counts": tool_counts,
                "tracked_tool_versions": len(self._tool_versions),
            }

    def cleanup(self):
        """Manual cleanup of expired entries."""
        with self._lock:
            initial_size = len(self._cache)
            self._cleanup_expired()
            cleaned = initial_size - len(self._cache)

            if cleaned > 0:
                logger.info(f"Schema cache cleanup: removed {cleaned} expired entries")


# Global cache instance
_schema_cache_instance: Optional[SchemaCache] = None
_cache_lock = threading.Lock()


def get_schema_cache() -> SchemaCache:
    """
    Get the global schema cache instance.

    Returns:
        SchemaCache instance (singleton)
    """
    global _schema_cache_instance

    if _schema_cache_instance is None:
        with _cache_lock:
            if _schema_cache_instance is None:
                _schema_cache_instance = SchemaCache()
                logger.info("Global schema cache initialized")

    return _schema_cache_instance


def clear_schema_cache():
    """Clear the global schema cache."""
    cache = get_schema_cache()
    cache.invalidate_all()
    logger.info("Global schema cache cleared")


def get_schema_cache_stats() -> Dict[str, Any]:
    """Get statistics from the global schema cache."""
    cache = get_schema_cache()
    return cache.get_stats()


def warm_common_schemas():
    """Warm cache with common tool schema configurations."""
    cache = get_schema_cache()

    # Define common configurations that tools typically use
    common_configs = [
        {
            "tool_name": "chat",
            "parameters": {"auto_mode": False, "required_fields": ["prompt"]},
        },
        {
            "tool_name": "chat",
            "parameters": {"auto_mode": True, "required_fields": ["prompt", "model"]},
        },
        # Add more common configurations as needed
    ]

    # Note: This would need actual generator functions to be useful
    # For now, we'll just log the warming attempt
    logger.info(f"Schema cache warming attempted for {len(common_configs)} common configurations")
