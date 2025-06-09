"""
Configuration and constants for Gemini MCP Server
"""

# Version and metadata
__version__ = "2.8.0"
__updated__ = "2025-06-09"
__author__ = "Fahad Gilani"

# Model configuration
DEFAULT_MODEL = "gemini-2.5-pro-preview-06-05"
THINKING_MODEL = (
    "gemini-2.0-flash-thinking-exp"  # Enhanced reasoning model for think_deeper
)
MAX_CONTEXT_TOKENS = 1_000_000  # 1M tokens for Gemini Pro

# Temperature defaults for different tool types
TEMPERATURE_ANALYTICAL = 0.2  # For code review, debugging
TEMPERATURE_BALANCED = 0.5  # For general chat
TEMPERATURE_CREATIVE = 0.7  # For architecture, deep thinking

# Tool trigger phrases for natural language matching
TOOL_TRIGGERS = {
    "think_deeper": [
        "think deeper",
        "ultrathink",
        "extend my analysis",
        "reason through",
        "explore alternatives",
        "challenge my thinking",
        "deep think",
        "extended thinking",
        "validate my approach",
        "find edge cases",
    ],
    "review_code": [
        "review",
        "check for issues",
        "find bugs",
        "security check",
        "code quality",
        "audit",
        "code review",
        "check this code",
        "review for",
        "find vulnerabilities",
    ],
    "debug_issue": [
        "debug",
        "error",
        "failing",
        "root cause",
        "trace",
        "why doesn't",
        "not working",
        "diagnose",
        "troubleshoot",
        "investigate this error",
    ],
    "analyze": [
        "analyze",
        "examine",
        "look at",
        "check",
        "inspect",
        "understand",
        "analyze file",
        "analyze these files",
    ],
}
