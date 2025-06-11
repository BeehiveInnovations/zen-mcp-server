"""
Communication Simulator Tests Package

This package contains individual test modules for the Gemini MCP Communication Simulator.
Each test is in its own file for better organization and maintainability.
"""

from .base_test import BaseSimulatorTest
from .test_basic_conversation import BasicConversationTest
from .test_content_validation import ContentValidationTest
from .test_per_tool_deduplication import PerToolDeduplicationTest
from .test_cross_tool_continuation import CrossToolContinuationTest
from .test_logs_validation import LogsValidationTest
from .test_redis_validation import RedisValidationTest

# Test registry for dynamic loading
TEST_REGISTRY = {
    "basic_conversation": BasicConversationTest,
    "content_validation": ContentValidationTest,
    "per_tool_deduplication": PerToolDeduplicationTest,
    "cross_tool_continuation": CrossToolContinuationTest,
    "logs_validation": LogsValidationTest,
    "redis_validation": RedisValidationTest,
}

__all__ = [
    'BaseSimulatorTest',
    'BasicConversationTest',
    'ContentValidationTest', 
    'PerToolDeduplicationTest',
    'CrossToolContinuationTest',
    'LogsValidationTest',
    'RedisValidationTest',
    'TEST_REGISTRY'
]