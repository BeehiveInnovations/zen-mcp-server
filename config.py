"""
Configuration and constants for Gemini MCP Server

This module centralizes all configuration settings for the Gemini MCP Server.
It defines model configurations, token limits, temperature defaults, and other
constants used throughout the application.

Configuration values can be overridden by environment variables where appropriate.
"""

# Version and metadata
# These values are used in server responses and for tracking releases
__version__ = "2.9.0"  # Semantic versioning: MAJOR.MINOR.PATCH
__updated__ = "2025-06-09"  # Last update date in ISO format
__author__ = "Fahad Gilani"  # Primary maintainer

# Model configuration
# GEMINI_MODEL: The Gemini model used for all AI operations
# This should be a stable, high-performance model suitable for code analysis
GEMINI_MODEL = "gemini-2.5-pro-preview-06-05"

# MAX_CONTEXT_TOKENS: Maximum number of tokens that can be included in a single request
# This limit includes both the prompt and expected response
# Gemini Pro models support up to 1M tokens, but practical usage should reserve
# space for the model's response (typically 50K-100K tokens reserved)
MAX_CONTEXT_TOKENS = 1_000_000  # 1M tokens for Gemini Pro

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
