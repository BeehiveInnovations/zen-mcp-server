"""
Communication Simulator Tests Package

This package contains individual test modules for the Zen MCP Communication Simulator.
Each test is in its own file for better organization and maintainability.
"""

from .base_test import BaseSimulatorTest
from .test_basic_conversation import BasicConversationTest
from .test_content_validation import ContentValidationTest
from .test_conversation_chain_validation import ConversationChainValidationTest
from .test_cross_tool_comprehensive import CrossToolComprehensiveTest
from .test_cross_tool_continuation import CrossToolContinuationTest
from .test_logs_validation import LogsValidationTest
from .test_model_thinking_config import TestModelThinkingConfig
from .test_o3_model_selection import O3ModelSelectionTest
from .test_per_tool_deduplication import PerToolDeduplicationTest
from .test_redis_validation import RedisValidationTest
from .test_token_allocation_validation import TokenAllocationValidationTest

# Test registry for dynamic loading
TEST_REGISTRY = {
    "basic_conversation": BasicConversationTest,
    "content_validation": ContentValidationTest,
    "per_tool_deduplication": PerToolDeduplicationTest,
    "cross_tool_continuation": CrossToolContinuationTest,
    "cross_tool_comprehensive": CrossToolComprehensiveTest,
    "logs_validation": LogsValidationTest,
    "redis_validation": RedisValidationTest,
    "model_thinking_config": TestModelThinkingConfig,
    "o3_model_selection": O3ModelSelectionTest,
    "token_allocation_validation": TokenAllocationValidationTest,
    "conversation_chain_validation": ConversationChainValidationTest,
}

__all__ = [
    "BaseSimulatorTest",
    "BasicConversationTest",
    "ContentValidationTest",
    "PerToolDeduplicationTest",
    "CrossToolContinuationTest",
    "CrossToolComprehensiveTest",
    "LogsValidationTest",
    "RedisValidationTest",
    "TestModelThinkingConfig",
    "O3ModelSelectionTest",
    "TokenAllocationValidationTest",
    "ConversationChainValidationTest",
    "TEST_REGISTRY",
]
