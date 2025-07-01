"""
Test suite for the ToolFactory lazy loading system.

This module tests the lazy tool loading functionality to ensure:
- Tools are loaded on-demand (not at startup)
- Tool caching works correctly
- Thread safety is maintained
- Error handling and recovery work as expected
- Performance characteristics meet requirements
- Backward compatibility is preserved
"""

import importlib
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from tools.factory import ToolFactory, ToolRegistry, get_tool_factory, reset_tool_factory
from tools.shared.base_tool import BaseTool


class TestToolRegistry:
    """Test the ToolRegistry class."""

    def test_get_available_tool_names(self):
        """Test that registry returns expected tool names."""
        tool_names = ToolRegistry.get_available_tool_names()

        # Should include all the standard tools
        expected_tools = [
            "analyze",
            "cache_monitor",
            "challenge",
            "chat",
            "codereview",
            "consensus",
            "debug",
            "docgen",
            "listmodels",
            "planner",
            "precommit",
            "refactor",
            "secaudit",
            "testgen",
            "thinkdeep",
            "tracer",
            "version",
        ]

        for tool in expected_tools:
            assert tool in tool_names, f"Tool '{tool}' not found in registry"

        # Should be a reasonable number of tools
        assert len(tool_names) >= 15, f"Expected at least 15 tools, got {len(tool_names)}"

    def test_get_tool_module_info(self):
        """Test getting module info for specific tools."""
        # Test valid tool
        module_path, class_name = ToolRegistry.get_tool_module_info("chat")
        assert module_path == "tools.chat"
        assert class_name == "ChatTool"

        # Test another valid tool
        module_path, class_name = ToolRegistry.get_tool_module_info("version")
        assert module_path == "tools.version"
        assert class_name == "VersionTool"

        # Test invalid tool
        result = ToolRegistry.get_tool_module_info("nonexistent")
        assert result is None

    def test_is_tool_available(self):
        """Test tool availability check."""
        assert ToolRegistry.is_tool_available("chat") is True
        assert ToolRegistry.is_tool_available("version") is True
        assert ToolRegistry.is_tool_available("nonexistent") is False


class TestToolFactory:
    """Test the ToolFactory class."""

    def setup_method(self):
        """Set up fresh factory for each test."""
        self.factory = ToolFactory()

    def test_initialization(self):
        """Test factory initializes correctly."""
        assert len(self.factory._tool_cache) == 0
        assert len(self.factory._load_errors) == 0
        assert self.factory._load_metrics["tools_loaded"] == 0
        assert self.factory._load_metrics["cache_hits"] == 0

    def test_get_available_tools(self):
        """Test getting available tools without loading them."""
        available = self.factory.get_available_tools()

        # Should return tools from registry
        assert "chat" in available
        assert "version" in available

        # Should not have loaded any tools yet
        assert len(self.factory._tool_cache) == 0
        assert self.factory._load_metrics["tools_loaded"] == 0

    def test_lazy_loading_basic(self):
        """Test basic lazy loading functionality."""
        # Initially no tools loaded
        assert not self.factory.is_tool_loaded("version")
        assert len(self.factory.get_loaded_tools()) == 0

        # Load a tool
        tool = self.factory.get_tool("version")

        # Should be loaded now
        assert tool is not None
        assert isinstance(tool, BaseTool)
        assert tool.name == "version"
        assert self.factory.is_tool_loaded("version")
        assert "version" in self.factory.get_loaded_tools()
        assert self.factory._load_metrics["tools_loaded"] == 1

    def test_caching_behavior(self):
        """Test that tools are cached after first load."""
        # Load tool first time
        tool1 = self.factory.get_tool("version")
        assert self.factory._load_metrics["tools_loaded"] == 1
        assert self.factory._load_metrics["cache_hits"] == 0

        # Load same tool again
        tool2 = self.factory.get_tool("version")

        # Should be same instance (cached)
        assert tool1 is tool2
        assert self.factory._load_metrics["tools_loaded"] == 1  # No new load
        assert self.factory._load_metrics["cache_hits"] == 1  # Cache hit

    def test_multiple_tools(self):
        """Test loading multiple different tools."""
        # Load multiple tools
        tools = {}
        for tool_name in ["version", "listmodels", "chat"]:
            tools[tool_name] = self.factory.get_tool(tool_name)
            assert tools[tool_name] is not None
            assert tools[tool_name].name == tool_name

        # All should be cached
        assert len(self.factory.get_loaded_tools()) == 3
        assert self.factory._load_metrics["tools_loaded"] == 3

        # Loading again should hit cache
        version_tool = self.factory.get_tool("version")
        assert version_tool is tools["version"]
        assert self.factory._load_metrics["cache_hits"] >= 1

    def test_invalid_tool_handling(self):
        """Test handling of invalid tool names."""
        tool = self.factory.get_tool("nonexistent_tool")
        assert tool is None

        # Should not be in cache or errors
        assert not self.factory.is_tool_loaded("nonexistent_tool")
        assert "nonexistent_tool" not in self.factory._load_errors

    def test_preload_tools(self):
        """Test preloading functionality."""
        # Preload specific tools
        results = self.factory.preload_tools(["version", "listmodels"])

        assert results["version"] is True
        assert results["listmodels"] is True
        assert len(self.factory.get_loaded_tools()) == 2
        assert self.factory._load_metrics["tools_loaded"] == 2

    def test_preload_all_tools(self):
        """Test preloading all tools."""
        # This is a more expensive test but important for validating the full system
        results = self.factory.preload_tools()

        # Should have attempted to load all available tools
        available_tools = ToolRegistry.get_available_tool_names()
        assert len(results) == len(available_tools)

        # Most tools should load successfully
        successful_loads = sum(1 for success in results.values() if success)
        assert successful_loads >= len(available_tools) * 0.8  # Allow for some failures

    def test_cleanup_tool(self):
        """Test individual tool cleanup."""
        # Load a tool
        tool = self.factory.get_tool("version")
        assert tool is not None
        assert self.factory.is_tool_loaded("version")

        # Cleanup the tool
        result = self.factory.cleanup_tool("version")
        assert result is True
        assert not self.factory.is_tool_loaded("version")
        assert len(self.factory.get_loaded_tools()) == 0

        # Cleanup non-existent tool
        result = self.factory.cleanup_tool("never_loaded")
        assert result is False

    def test_cleanup_all_tools(self):
        """Test cleaning up all tools."""
        # Load several tools
        tools = ["version", "listmodels", "chat"]
        for tool_name in tools:
            self.factory.get_tool(tool_name)

        assert len(self.factory.get_loaded_tools()) == 3

        # Cleanup all
        count = self.factory.cleanup_all_tools()
        assert count == 3
        assert len(self.factory.get_loaded_tools()) == 0
        assert len(self.factory._load_errors) == 0

    def test_metrics(self):
        """Test metrics collection."""
        # Initial metrics
        metrics = self.factory.get_metrics()
        assert metrics["tools_loaded"] == 0
        assert metrics["cache_hits"] == 0
        assert metrics["cached_tools"] == 0
        assert metrics["available_tools"] > 0

        # Load some tools
        self.factory.get_tool("version")
        self.factory.get_tool("version")  # Cache hit
        self.factory.get_tool("listmodels")

        metrics = self.factory.get_metrics()
        assert metrics["tools_loaded"] == 2
        assert metrics["cache_hits"] == 1
        assert metrics["cached_tools"] == 2
        assert metrics["cache_efficiency"] > 0

    def test_dict_like_interface(self):
        """Test dictionary-like interface methods."""
        # Test __len__
        assert len(self.factory) > 0

        # Test __contains__
        assert "version" in self.factory
        assert "nonexistent" not in self.factory

        # Test __iter__
        tool_names = list(self.factory)
        assert "version" in tool_names
        assert len(tool_names) > 0

        # Test keys()
        keys = self.factory.keys()
        assert "version" in keys

        # Test values() - this triggers loading
        values = list(self.factory.values())
        assert len(values) > 0
        assert all(isinstance(tool, BaseTool) for tool in values)

        # Test items() - this triggers loading
        items = list(self.factory.items())
        assert len(items) > 0
        assert all(isinstance(name, str) and isinstance(tool, BaseTool) for name, tool in items)


class TestThreadSafety:
    """Test thread safety of the factory."""

    def test_concurrent_loading(self):
        """Test concurrent loading of the same tool."""
        factory = ToolFactory()
        results = []
        errors = []

        def load_tool():
            try:
                tool = factory.get_tool("version")
                results.append(tool)
            except Exception as e:
                errors.append(e)

        # Start multiple threads loading the same tool
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=load_tool)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0

        # All results should be the same instance (cached)
        assert len(results) == 10
        first_tool = results[0]
        assert all(tool is first_tool for tool in results)

        # Should only be loaded once
        assert factory._load_metrics["tools_loaded"] == 1
        assert factory._load_metrics["cache_hits"] == 9

    def test_concurrent_different_tools(self):
        """Test concurrent loading of different tools."""
        factory = ToolFactory()
        results = {}
        errors = []

        tool_names = ["version", "listmodels", "chat", "analyze"]

        def load_tool(tool_name):
            try:
                tool = factory.get_tool(tool_name)
                results[tool_name] = tool
            except Exception as e:
                errors.append((tool_name, e))

        # Start threads loading different tools
        threads = []
        for tool_name in tool_names:
            thread = threading.Thread(target=load_tool, args=(tool_name,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0

        # Should have loaded all tools
        assert len(results) == len(tool_names)
        for tool_name in tool_names:
            assert tool_name in results
            assert results[tool_name] is not None
            assert results[tool_name].name == tool_name


class TestGlobalFactory:
    """Test global factory instance management."""

    def test_get_global_factory(self):
        """Test getting global factory instance."""
        factory1 = get_tool_factory()
        factory2 = get_tool_factory()

        # Should be same instance
        assert factory1 is factory2
        assert isinstance(factory1, ToolFactory)

    def test_reset_global_factory(self):
        """Test resetting global factory."""
        # Get factory and load a tool
        factory1 = get_tool_factory()
        tool = factory1.get_tool("version")
        assert tool is not None
        assert factory1.is_tool_loaded("version")

        # Reset factory
        reset_tool_factory()

        # Get factory again - should be new instance
        factory2 = get_tool_factory()
        assert factory2 is not factory1
        assert not factory2.is_tool_loaded("version")


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_lazy_imports(self):
        """Test that __getattr__ provides lazy imports."""
        # Import the tools module
        import tools

        # Accessing a tool class should work
        ChatTool = tools.ChatTool
        assert ChatTool is not None

        # Should be the actual class
        instance = ChatTool()
        assert isinstance(instance, BaseTool)
        assert instance.name == "chat"

    def test_import_error_handling(self):
        """Test proper error handling for invalid imports."""
        import tools

        # Accessing invalid attribute should raise AttributeError
        with pytest.raises(AttributeError):
            _ = tools.NonexistentTool


class TestErrorHandling:
    """Test error handling and recovery."""

    def test_load_error_caching(self):
        """Test that load errors are cached to avoid repeated attempts."""
        factory = ToolFactory()

        # Mock a failing import
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Mock import error")

            # First attempt should fail and cache error
            tool = factory.get_tool("chat")
            assert tool is None
            assert "chat" in factory._load_errors
            assert factory._load_metrics["load_errors"] == 1

            # Second attempt should use cached error (no additional import)
            tool = factory.get_tool("chat")
            assert tool is None
            assert mock_import.call_count == 1  # Only called once

    def test_partial_failure_recovery(self):
        """Test recovery when some tools fail to load."""
        factory = ToolFactory()

        # Mock some tools to fail
        original_import = importlib.import_module

        def selective_import(name):
            if name == "tools.chat":
                raise ImportError("Mock chat failure")
            return original_import(name)

        with patch("importlib.import_module", side_effect=selective_import):
            # Chat should fail
            chat_tool = factory.get_tool("chat")
            assert chat_tool is None

            # Version should succeed
            version_tool = factory.get_tool("version")
            assert version_tool is not None
            assert version_tool.name == "version"

    def test_malformed_tool_handling(self):
        """Test handling of tools that don't inherit from BaseTool."""
        factory = ToolFactory()

        # Mock a tool that doesn't inherit from BaseTool
        class FakeTool:
            def __init__(self):
                self.name = "fake"

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.FakeTool = FakeTool
            mock_import.return_value = mock_module

            # Patch the registry to include fake tool
            original_registry = ToolRegistry._TOOL_REGISTRY.copy()
            ToolRegistry._TOOL_REGISTRY["fake"] = ("fake.module", "FakeTool")

            try:
                # Should fail with TypeError
                tool = factory.get_tool("fake")
                assert tool is None
                assert "fake" in factory._load_errors
                assert isinstance(factory._load_errors["fake"], TypeError)
            finally:
                # Restore original registry
                ToolRegistry._TOOL_REGISTRY = original_registry


class TestPerformanceCharacteristics:
    """Test performance characteristics of lazy loading."""

    def test_startup_time_improvement(self):
        """Test that factory creation is fast (doesn't load tools)."""
        start_time = time.time()
        factory = ToolFactory()
        creation_time = time.time() - start_time

        # Factory creation should be very fast (< 1ms)
        assert creation_time < 0.001, f"Factory creation took {creation_time:.3f}s, expected < 0.001s"

        # No tools should be loaded
        assert len(factory.get_loaded_tools()) == 0
        assert factory._load_metrics["tools_loaded"] == 0

    def test_first_load_vs_cache_performance(self):
        """Test that caching works correctly and provides performance benefit."""
        factory = ToolFactory()

        # First load should trigger actual loading
        tool1 = factory.get_tool("version")
        assert factory._load_metrics["tools_loaded"] == 1
        assert factory._load_metrics["cache_hits"] == 0

        # Cached access should use cache
        tool2 = factory.get_tool("version")
        assert factory._load_metrics["tools_loaded"] == 1  # No additional load
        assert factory._load_metrics["cache_hits"] == 1  # Cache hit recorded

        # Should be same instance
        assert tool1 is tool2

        # Multiple cache accesses should continue hitting cache
        for _ in range(5):
            tool_n = factory.get_tool("version")
            assert tool_n is tool1

        # Should have multiple cache hits
        assert factory._load_metrics["cache_hits"] >= 5

    def test_memory_usage_pattern(self):
        """Test that lazy loading doesn't immediately consume memory for all tools."""
        try:
            import os

            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process(os.getpid())

        # Baseline memory
        factory = ToolFactory()
        baseline_memory = process.memory_info().rss

        # Just creating factory shouldn't use much memory
        initial_memory = process.memory_info().rss
        initial_growth = initial_memory - baseline_memory

        # Should be minimal growth just for factory creation (< 1MB)
        assert initial_growth < 1024 * 1024, f"Factory creation used {initial_growth / 1024:.1f}KB, expected < 1MB"

        # Load a few tools
        tools_to_load = ["version", "listmodels", "chat"]
        for tool_name in tools_to_load:
            factory.get_tool(tool_name)

        final_memory = process.memory_info().rss
        total_growth = final_memory - baseline_memory

        # Total growth should be reasonable (< 50MB for 3 tools)
        # This is a generous limit to avoid flaky tests while still catching memory leaks
        assert (
            total_growth < 50 * 1024 * 1024
        ), f"Total memory growth ({total_growth / 1024 / 1024:.1f}MB) seems excessive for 3 tools"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
