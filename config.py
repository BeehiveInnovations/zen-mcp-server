"""
Configuration and constants for Zen MCP Server

This module centralizes all configuration settings for the Zen MCP Server.
It defines model configurations, token limits, temperature defaults, and other
constants used throughout the application.

Configuration values can be overridden by environment variables where appropriate.
"""

import os

# Version and metadata
# These values are used in server responses and for tracking releases
# IMPORTANT: This is the single source of truth for version and author info
__version__ = "4.1.0"  # Semantic versioning: MAJOR.MINOR.PATCH
__updated__ = "2025-06-12"  # Last update date in ISO format
__author__ = "Fahad Gilani"  # Primary maintainer

# Model configuration
# DEFAULT_MODEL: The default model used for all AI operations
# This should be a stable, high-performance model suitable for code analysis
# Can be overridden by setting DEFAULT_MODEL environment variable
# Special value "auto" means Claude should pick the best model for each task
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "auto")

# Validate DEFAULT_MODEL and set to "auto" if invalid
# Only include actually supported models from providers
VALID_MODELS = [
    "auto",
    "flash",
    "pro",
    "o3",
    "o3-mini",
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.5-pro-preview-06-05",
]
if DEFAULT_MODEL not in VALID_MODELS:
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(
        f"Invalid DEFAULT_MODEL '{DEFAULT_MODEL}'. Setting to 'auto'. Valid options: {', '.join(VALID_MODELS)}"
    )
    DEFAULT_MODEL = "auto"

# Auto mode detection - when DEFAULT_MODEL is "auto", Claude picks the model
IS_AUTO_MODE = DEFAULT_MODEL.lower() == "auto"

# Model capabilities descriptions for auto mode
# These help Claude choose the best model for each task
MODEL_CAPABILITIES_DESC = {
    "flash": "Ultra-fast (1M context) - Quick analysis, simple queries, rapid iterations",
    "pro": "Deep reasoning + thinking mode (1M context) - Complex problems, architecture, deep analysis",
    "o3": "Strong reasoning (200K context) - Logical problems, code generation, systematic analysis",
    "o3-mini": "Fast O3 variant (200K context) - Balanced performance/speed, moderate complexity",
    # Full model names also supported
    "gemini-2.5-flash-preview-05-20": "Ultra-fast (1M context) - Quick analysis, simple queries, rapid iterations",
    "gemini-2.5-pro-preview-06-05": (
        "Deep reasoning + thinking mode (1M context) - Complex problems, architecture, deep analysis"
    ),
}

# Note: When only OpenRouter is configured, these model aliases automatically map to equivalent models:
# - "flash" → "google/gemini-flash-1.5-8b"
# - "pro" → "google/gemini-pro-1.5"
# - "o3" → "openai/gpt-4o"
# - "o3-mini" → "openai/gpt-4o-mini"

# Token allocation for Gemini Pro (1M total capacity)
# MAX_CONTEXT_TOKENS: Total model capacity
# MAX_CONTENT_TOKENS: Available for prompts, conversation history, and files
# RESPONSE_RESERVE_TOKENS: Reserved for model response generation
MAX_CONTEXT_TOKENS = 1_000_000  # 1M tokens total capacity for Gemini Pro
MAX_CONTENT_TOKENS = 800_000  # 800K tokens for content (prompts + files + history)
RESPONSE_RESERVE_TOKENS = 200_000  # 200K tokens reserved for response generation

# Temperature defaults for different tool types
# Temperature controls the randomness/creativity of model responses
# Lower values (0.0-0.3) produce more deterministic, focused responses
# Higher values (0.7-1.0) produce more creative, varied responses

# TEMPERATURE_ANALYTICAL: Used for tasks requiring precision and consistency
# Ideal for code review, debugging, and error analysis where accuracy is critical
TEMPERATURE_ANALYTICAL = 0.2  # For code review, debugging

# TEMPERATURE_BALANCED: Middle ground for general conversations
# Provides a good balance between consistency and helpful variety
TEMPERATURE_BALANCED = 0.5  # For general chat

# TEMPERATURE_CREATIVE: Higher temperature for exploratory tasks
# Used when brainstorming, exploring alternatives, or architectural discussions
TEMPERATURE_CREATIVE = 0.7  # For architecture, deep thinking

# Thinking Mode Defaults
# DEFAULT_THINKING_MODE_THINKDEEP: Default thinking depth for extended reasoning tool
# Higher modes use more computational budget but provide deeper analysis
DEFAULT_THINKING_MODE_THINKDEEP = os.getenv("DEFAULT_THINKING_MODE_THINKDEEP", "high")

# MCP Protocol Limits
# MCP_PROMPT_SIZE_LIMIT: Maximum character size for prompts sent directly through MCP
# The MCP protocol has a combined request+response limit of ~25K tokens.
# To ensure we have enough space for responses, we limit direct prompt input
# to 50K characters (roughly ~10-12K tokens). Larger prompts must be sent
# as files to bypass MCP's token constraints.
MCP_PROMPT_SIZE_LIMIT = 50_000  # 50K characters

# Threading configuration
# Simple Redis-based conversation threading for stateless MCP environment
# Set REDIS_URL environment variable to connect to your Redis instance
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
