"""
Configuration and constants for Gemini MCP Server

This module centralizes all configuration settings for the Gemini MCP Server.
It defines model configurations, token limits, temperature defaults, and other
constants used throughout the application.

Configuration values can be overridden by environment variables where appropriate.
"""

import os

# Version and metadata
# These values are used in server responses and for tracking releases
# IMPORTANT: This is the single source of truth for version and author info
# setup.py imports these values to avoid duplication
__version__ = "3.2.0"  # Semantic versioning: MAJOR.MINOR.PATCH
__updated__ = "2025-06-10"  # Last update date in ISO format
__author__ = "Fahad Gilani"  # Primary maintainer

# Model configuration
# GEMINI_MODEL: The Gemini model used for all AI operations
# This should be a stable, high-performance model suitable for code analysis
GEMINI_MODEL = "gemini-2.5-pro-preview-06-05"

# Token allocation for Gemini Pro (1M total capacity)
# MAX_CONTEXT_TOKENS: Total model capacity
# MAX_CONTENT_TOKENS: Available for prompts, conversation history, and files
# RESPONSE_RESERVE_TOKENS: Reserved for model response generation
MAX_CONTEXT_TOKENS = 1_000_000  # 1M tokens total capacity for Gemini Pro
MAX_CONTENT_TOKENS = 800_000    # 800K tokens for content (prompts + files + history)
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
