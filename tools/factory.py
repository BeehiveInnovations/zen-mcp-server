"""
Tool Factory - Lazy loading system for Zen MCP Server tools

This module implements a factory pattern that enables lazy loading of tools,
reducing server startup memory usage and initialization time by only loading
tools when they are actually needed.

Key Features:
- Lazy import and instantiation of tools
- Tool registry mapping tool names to module paths
- Caching of loaded tools to maintain performance
- Support for tool cleanup and resource management
- Backward compatibility with existing tool system
- Dynamic tool discovery for MCP protocol

The factory pattern allows the server to start quickly with minimal memory
footprint, then load tools on-demand as they are requested by MCP clients.
"""

import importlib
import logging
import threading
from typing import Any, Dict, Optional

from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry that maps tool names to their module paths and class names.

    This registry defines which tools are available and how to dynamically
    import them. It serves as the single source of truth for tool discovery
    and loading.
    """

    # Tool registry mapping tool names to (module_path, class_name)
    _TOOL_REGISTRY: Dict[str, tuple[str, str]] = {
        "analyze": ("tools.analyze", "AnalyzeTool"),
        "cache_monitor": ("tools.cache_monitor", "CacheMonitorTool"),
        "challenge": ("tools.challenge", "ChallengeTool"),
        "chat": ("tools.chat", "ChatTool"),
        "codereview": ("tools.codereview", "CodeReviewTool"),
        "consensus": ("tools.consensus", "ConsensusTool"),
        "debug": ("tools.debug", "DebugIssueTool"),
        "docgen": ("tools.docgen", "DocgenTool"),
        "listmodels": ("tools.listmodels", "ListModelsTool"),
        "planner": ("tools.planner", "PlannerTool"),
        "precommit": ("tools.precommit", "PrecommitTool"),
        "refactor": ("tools.refactor", "RefactorTool"),
        "secaudit": ("tools.secaudit", "SecauditTool"),
        "testgen": ("tools.testgen", "TestGenTool"),
        "thinkdeep": ("tools.thinkdeep", "ThinkDeepTool"),
        "tracer": ("tools.tracer", "TracerTool"),
        "version": ("tools.version", "VersionTool"),
    }

    @classmethod
    def get_available_tool_names(cls) -> list[str]:
        """Get list of all available tool names."""
        return list(cls._TOOL_REGISTRY.keys())

    @classmethod
    def get_tool_module_info(cls, tool_name: str) -> Optional[tuple[str, str]]:
        """Get module path and class name for a tool."""
        return cls._TOOL_REGISTRY.get(tool_name)

    @classmethod
    def is_tool_available(cls, tool_name: str) -> bool:
        """Check if a tool is available in the registry."""
        return tool_name in cls._TOOL_REGISTRY


class ToolFactory:
    """
    Factory class that implements lazy loading of MCP tools.

    This factory provides the same interface as the previous TOOLS dictionary
    but loads tools on-demand to reduce startup memory usage and initialization time.

    Features:
    - Thread-safe tool loading and caching
    - Lazy import and instantiation
    - Tool cleanup and resource management
    - Error handling and fallback mechanisms
    - Metrics tracking for performance monitoring

    Usage:
        factory = ToolFactory()
        tool = factory.get_tool("chat")  # Loads tool if not cached
        tool = factory.get_tool("chat")  # Returns cached instance
    """

    def __init__(self):
        """Initialize the tool factory with empty cache."""
        self._tool_cache: Dict[str, BaseTool] = {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._load_errors: Dict[str, Exception] = {}
        self._load_metrics = {"tools_loaded": 0, "cache_hits": 0, "load_errors": 0, "startup_time": 0.0}
        logger.debug("ToolFactory initialized with empty cache")

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool instance, loading it lazily if not already cached.

        This method is thread-safe and handles concurrent access to the same tool.
        If a tool fails to load, the error is cached to avoid repeated attempts.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            BaseTool instance if successful, None if tool doesn't exist or failed to load

        Raises:
            Exception: Critical errors that should propagate to caller
        """
        if not ToolRegistry.is_tool_available(tool_name):
            logger.warning(f"Tool '{tool_name}' not found in registry")
            return None

        # Check cache first (fast path)
        if tool_name in self._tool_cache:
            self._load_metrics["cache_hits"] += 1
            logger.debug(f"Tool '{tool_name}' returned from cache")
            return self._tool_cache[tool_name]

        # Check if previous load attempt failed
        if tool_name in self._load_errors:
            logger.debug(f"Tool '{tool_name}' previously failed to load: {self._load_errors[tool_name]}")
            return None

        # Load tool with thread safety
        with self._lock:
            # Double-check pattern: tool might have been loaded by another thread
            if tool_name in self._tool_cache:
                self._load_metrics["cache_hits"] += 1
                logger.debug(f"Tool '{tool_name}' loaded by another thread, returning cached instance")
                return self._tool_cache[tool_name]

            # Actually load the tool
            try:
                logger.debug(f"Loading tool '{tool_name}' on-demand")
                tool_instance = self._load_tool(tool_name)
                if tool_instance:
                    self._tool_cache[tool_name] = tool_instance
                    self._load_metrics["tools_loaded"] += 1
                    logger.info(f"Tool '{tool_name}' loaded and cached successfully")
                    return tool_instance
                else:
                    logger.warning(f"Tool '{tool_name}' returned None from _load_tool")
                    return None
            except Exception as e:
                # Cache the error to avoid repeated load attempts
                self._load_errors[tool_name] = e
                self._load_metrics["load_errors"] += 1
                logger.error(f"Failed to load tool '{tool_name}': {type(e).__name__}: {e}")
                # For critical system tools, we might want to propagate the error
                if tool_name in ["version", "listmodels"]:
                    raise
                return None

    def _load_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Internal method to dynamically import and instantiate a tool.

        Args:
            tool_name: Name of the tool to load

        Returns:
            Instantiated tool or None if loading fails

        Raises:
            ImportError: If module or class cannot be imported
            Exception: If tool instantiation fails
        """
        module_info = ToolRegistry.get_tool_module_info(tool_name)
        if not module_info:
            logger.error(f"No module info found for tool '{tool_name}'")
            return None

        module_path, class_name = module_info

        try:
            # Import the module dynamically
            logger.debug(f"Importing module '{module_path}' for tool '{tool_name}'")
            module = importlib.import_module(module_path)

            # Get the tool class
            tool_class = getattr(module, class_name)
            logger.debug(f"Found class '{class_name}' in module '{module_path}'")

            # Instantiate the tool
            tool_instance = tool_class()
            logger.debug(f"Instantiated tool '{tool_name}' of type {type(tool_instance).__name__}")

            # Validate tool interface
            if not isinstance(tool_instance, BaseTool):
                raise TypeError(f"Tool '{tool_name}' does not inherit from BaseTool")

            # Validate tool name matches expected
            if hasattr(tool_instance, "name") and tool_instance.name != tool_name:
                logger.warning(f"Tool name mismatch: expected '{tool_name}', got '{tool_instance.name}'")

            return tool_instance

        except ImportError as e:
            logger.error(f"Failed to import module '{module_path}' for tool '{tool_name}': {e}")
            raise
        except AttributeError as e:
            logger.error(f"Class '{class_name}' not found in module '{module_path}' for tool '{tool_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to instantiate tool '{tool_name}': {type(e).__name__}: {e}")
            raise

    def get_available_tools(self) -> list[str]:
        """
        Get list of all available tool names.

        This method returns tool names from the registry without loading them,
        allowing for tool discovery without triggering lazy loading.

        Returns:
            List of available tool names
        """
        return ToolRegistry.get_available_tool_names()

    def get_loaded_tools(self) -> list[str]:
        """
        Get list of currently loaded (cached) tool names.

        Returns:
            List of tool names that are currently in cache
        """
        return list(self._tool_cache.keys())

    def is_tool_loaded(self, tool_name: str) -> bool:
        """
        Check if a specific tool is currently loaded in cache.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool is loaded, False otherwise
        """
        return tool_name in self._tool_cache

    def preload_tools(self, tool_names: Optional[list[str]] = None) -> Dict[str, bool]:
        """
        Pre-load specific tools or all tools to warm the cache.

        This method can be used to pre-load essential tools during server
        initialization or to warm the cache for better runtime performance.

        Args:
            tool_names: List of tool names to preload, or None to preload all

        Returns:
            Dictionary mapping tool names to success status
        """
        if tool_names is None:
            tool_names = self.get_available_tools()

        results = {}
        logger.info(f"Pre-loading {len(tool_names)} tools: {', '.join(tool_names)}")

        for tool_name in tool_names:
            try:
                tool = self.get_tool(tool_name)
                results[tool_name] = tool is not None
                if tool:
                    logger.debug(f"Pre-loaded tool '{tool_name}' successfully")
                else:
                    logger.warning(f"Failed to pre-load tool '{tool_name}'")
            except Exception as e:
                results[tool_name] = False
                logger.error(f"Error pre-loading tool '{tool_name}': {e}")

        successful = sum(1 for success in results.values() if success)
        logger.info(f"Pre-loading complete: {successful}/{len(tool_names)} tools loaded successfully")

        return results

    def cleanup_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from cache and perform cleanup if needed.

        Args:
            tool_name: Name of the tool to cleanup

        Returns:
            True if tool was cleaned up, False if not found
        """
        with self._lock:
            if tool_name in self._tool_cache:
                tool = self._tool_cache[tool_name]

                # Call cleanup method if tool supports it
                if hasattr(tool, "cleanup"):
                    try:
                        tool.cleanup()
                        logger.debug(f"Called cleanup() on tool '{tool_name}'")
                    except Exception as e:
                        logger.warning(f"Tool '{tool_name}' cleanup failed: {e}")

                # Remove from cache
                del self._tool_cache[tool_name]
                logger.debug(f"Tool '{tool_name}' removed from cache")
                return True

            return False

    def cleanup_all_tools(self) -> int:
        """
        Cleanup all loaded tools and clear the cache.

        Returns:
            Number of tools that were cleaned up
        """
        with self._lock:
            tool_names = list(self._tool_cache.keys())
            cleaned_count = 0

            for tool_name in tool_names:
                if self.cleanup_tool(tool_name):
                    cleaned_count += 1

            # Clear error cache as well
            self._load_errors.clear()

            logger.info(f"Cleaned up {cleaned_count} tools")
            return cleaned_count

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get factory performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        return {
            **self._load_metrics,
            "cached_tools": len(self._tool_cache),
            "available_tools": len(ToolRegistry.get_available_tool_names()),
            "failed_tools": len(self._load_errors),
            "cache_efficiency": (
                self._load_metrics["cache_hits"]
                / max(1, self._load_metrics["cache_hits"] + self._load_metrics["tools_loaded"])
            ),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        self._load_metrics = {"tools_loaded": 0, "cache_hits": 0, "load_errors": 0, "startup_time": 0.0}
        logger.debug("Factory metrics reset")

    def __len__(self) -> int:
        """Return number of available tools."""
        return len(ToolRegistry.get_available_tool_names())

    def __contains__(self, tool_name: str) -> bool:
        """Check if tool name is available in registry."""
        return ToolRegistry.is_tool_available(tool_name)

    def __iter__(self):
        """Iterate over available tool names."""
        return iter(ToolRegistry.get_available_tool_names())

    def keys(self):
        """Get available tool names (dict-like interface)."""
        return ToolRegistry.get_available_tool_names()

    def values(self):
        """Get all tool instances, loading them lazily (dict-like interface)."""
        for tool_name in self.get_available_tools():
            tool = self.get_tool(tool_name)
            if tool:
                yield tool

    def items(self):
        """Get (name, tool) pairs, loading tools lazily (dict-like interface)."""
        for tool_name in self.get_available_tools():
            tool = self.get_tool(tool_name)
            if tool:
                yield (tool_name, tool)


# Global factory instance - initialized once and reused
_global_factory: Optional[ToolFactory] = None
_factory_lock = threading.Lock()


def get_tool_factory() -> ToolFactory:
    """
    Get the global tool factory instance.

    This function ensures thread-safe initialization of the global factory
    and provides a single point of access for the lazy loading system.

    Returns:
        Global ToolFactory instance
    """
    global _global_factory

    if _global_factory is None:
        with _factory_lock:
            # Double-check pattern
            if _global_factory is None:
                _global_factory = ToolFactory()
                logger.info("Global ToolFactory instance created")

    return _global_factory


def reset_tool_factory() -> None:
    """
    Reset the global tool factory (primarily for testing).

    This function cleans up the current factory and forces creation
    of a new one on next access.
    """
    global _global_factory

    with _factory_lock:
        if _global_factory:
            _global_factory.cleanup_all_tools()
            _global_factory = None
            logger.info("Global ToolFactory instance reset")
