"""Test factory for simulator tests - creates reusable components for conversation testing.

This module provides a factory pattern for creating simulator test components
that can be reused across different test scenarios. It reduces repetitive code
and provides consistent test setup patterns.
"""

import os
from typing import Dict, List, Optional, Tuple, Any
from unittest.mock import Mock, patch

import pytest

from simulator_tests.base_test import BaseSimulatorTest


# Test scenario matrices for parameterized testing
CONVERSATION_FLOW_MATRIX = [
    # (tool_name, initial_prompt, continuation_prompt, model)
    ("chat", "Analyze this Python code", "Now focus on the Calculator class", "flash"),
    ("thinkdeep", "Investigate this code structure", "Continue with error handling analysis", "flash"),
    ("analyze", "Analyze code architecture", "Now examine performance implications", "flash"),
    ("codereview", "Review this code for issues", "Focus on security concerns", "flash"),
]

FILE_DEDUPLICATION_MATRIX = [
    # (tool_name, files_initial, files_continuation, should_deduplicate)
    ("chat", ["test.py"], ["test.py"], True),  # Same file should deduplicate
    ("chat", ["test.py"], ["test.py", "config.json"], False),  # Additional file, no dedup
    ("thinkdeep", ["test.py"], ["test.py"], True),
    ("analyze", ["test.py", "config.json"], ["test.py", "config.json"], True),
]

CONTINUATION_VALIDATION_MATRIX = [
    # (initial_tool, continuation_tool, should_preserve_context)
    ("chat", "chat", True),  # Same tool continuation
    ("chat", "thinkdeep", True),  # Cross-tool continuation
    ("thinkdeep", "analyze", True),  # Cross-tool continuation
    ("analyze", "codereview", True),  # Cross-tool continuation
]

MODEL_SELECTION_MATRIX = [
    # (model_name, expected_provider, should_succeed)
    ("flash", "google", True),
    ("flashlite", "google", True),
    ("o3", "openai", True),
    ("pro", "google", True),
    ("unknown-model", None, False),
]


@pytest.fixture
def simulator_factory():
    """Factory fixture for creating simulator test instances."""
    created_instances = []
    
    def _create_simulator(verbose: bool = False, **kwargs) -> BaseSimulatorTest:
        """Create a simulator test instance with optional configuration."""
        instance = BaseSimulatorTest(verbose=verbose)
        
        # Apply any additional configuration
        for key, value in kwargs.items():
            setattr(instance, key, value)
        
        created_instances.append(instance)
        return instance
    
    yield _create_simulator
    
    # Cleanup
    for instance in created_instances:
        if hasattr(instance, 'cleanup_test_files'):
            try:
                instance.cleanup_test_files()
            except Exception:
                pass  # Ignore cleanup errors


@pytest.fixture
def conversation_test_data():
    """Fixture providing common test data for conversation flows."""
    return {
        "python_content": '''"""
Sample Python module for testing MCP conversation continuity
"""

def fibonacci(n):
    """Calculate fibonacci number recursively"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    """Simple calculator class"""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
''',
        "config_content": """{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "testdb"
  },
  "logging": {
    "level": "INFO"
  }
}""",
        "common_prompts": {
            "analyze": "Please use low thinking mode. Analyze this code structure",
            "continue": "Please use low thinking mode. Now focus on the specific implementation",
            "review": "Please use low thinking mode. Review this code for potential issues",
        }
    }


class SimulatorTestFactory:
    """Factory class for creating simulator test components."""
    
    @staticmethod
    def create_conversation_test(
        simulator: BaseSimulatorTest,
        tool_name: str = "chat",
        model: str = "flash",
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a conversation test configuration."""
        return {
            "tool_name": tool_name,
            "model": model,
            "files": files or [],
            "initial_params": {
                "prompt": f"Please use low thinking mode. Test prompt for {tool_name}",
                "model": model,
                "files": files or [],
            },
            "continuation_params": {
                "prompt": f"Please use low thinking mode. Continue conversation for {tool_name}",
                "model": model,
            }
        }
    
    @staticmethod
    def create_file_setup(
        simulator: BaseSimulatorTest,
        additional_files: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Create test files and return their paths."""
        simulator.setup_test_files()
        files = simulator.test_files.copy()
        
        if additional_files:
            for filename, content in additional_files.items():
                file_path = simulator.create_additional_test_file(filename, content)
                files[filename] = file_path
        
        return files
    
    @staticmethod
    def validate_continuation_flow(
        response1: Optional[str],
        continuation_id: Optional[str],
        response2: Optional[str]
    ) -> bool:
        """Validate that a continuation flow is working correctly."""
        if not response1 or not continuation_id or not response2:
            return False
        
        # Basic validation - responses should be non-empty strings
        return (
            isinstance(response1, str) and len(response1.strip()) > 0 and
            isinstance(continuation_id, str) and len(continuation_id.strip()) > 0 and
            isinstance(response2, str) and len(response2.strip()) > 0
        )


class TestSimulatorFactory:
    """Test suite for the simulator factory patterns."""
    
    @pytest.mark.parametrize("tool_name,initial_prompt,continuation_prompt,model", CONVERSATION_FLOW_MATRIX)
    def test_conversation_flow_factory(
        self, 
        simulator_factory, 
        conversation_test_data, 
        tool_name, 
        initial_prompt, 
        continuation_prompt, 
        model
    ):
        """Test conversation flow creation with factory pattern."""
        simulator = simulator_factory(verbose=False)
        files = SimulatorTestFactory.create_file_setup(simulator)
        
        # Create conversation test configuration
        conv_test = SimulatorTestFactory.create_conversation_test(
            simulator, tool_name, model, [files["python"]]
        )
        
        assert conv_test["tool_name"] == tool_name
        assert conv_test["model"] == model
        assert len(conv_test["files"]) == 1
        assert conv_test["initial_params"]["model"] == model
    
    @pytest.mark.parametrize("tool_name,files_initial,files_continuation,should_deduplicate", FILE_DEDUPLICATION_MATRIX)
    def test_file_deduplication_factory(
        self, 
        simulator_factory, 
        tool_name, 
        files_initial, 
        files_continuation, 
        should_deduplicate
    ):
        """Test file deduplication scenarios with factory pattern."""
        simulator = simulator_factory(verbose=False)
        files = SimulatorTestFactory.create_file_setup(simulator)
        
        # Map file keys to actual paths
        initial_paths = [files.get(f, f) for f in files_initial]
        continuation_paths = [files.get(f, f) for f in files_continuation]
        
        # Validate file setup
        assert len(initial_paths) == len(files_initial)
        assert len(continuation_paths) == len(files_continuation)
        
        # Test deduplication logic
        unique_files = set(initial_paths + continuation_paths)
        has_duplicates = len(unique_files) < len(initial_paths + continuation_paths)
        
        if should_deduplicate:
            assert has_duplicates  # Should have duplicates to deduplicate
        else:
            assert not has_duplicates or len(continuation_paths) > len(initial_paths)
    
    @pytest.mark.parametrize("initial_tool,continuation_tool,should_preserve_context", CONTINUATION_VALIDATION_MATRIX)
    def test_continuation_validation_factory(
        self, 
        simulator_factory, 
        initial_tool, 
        continuation_tool, 
        should_preserve_context
    ):
        """Test continuation validation with factory pattern."""
        simulator = simulator_factory(verbose=False)
        
        # Mock successful responses
        response1 = "Initial response content"
        continuation_id = "test-123"
        response2 = "Continuation response content"
        
        # Validate continuation flow
        is_valid = SimulatorTestFactory.validate_continuation_flow(
            response1, continuation_id, response2
        )
        
        assert is_valid == should_preserve_context
        if should_preserve_context:
            assert continuation_id is not None
            assert len(continuation_id) > 0