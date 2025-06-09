"""
Configuration and constants for Gemini MCP Server
"""

# Version and metadata
__version__ = "2.8.0"
__updated__ = "2025-09-09"
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
    "chat": [
        "chat with gemini",
        "ask gemini",
        "brainstorm",
        "discuss",
        "get gemini's opinion",
        "talk to gemini",
        "gemini's thoughts",
        "collaborate with gemini",
        "second opinion",
        "what does gemini think",
        "bounce ideas",
        "thinking partner",
        "explain",
        "help me understand",
        "clarify",
    ],
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
        "gemini think deeper",
        "deeper analysis",
        "extend thinking",
        "critical thinking",
        "comprehensive analysis",
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
        "review my code",
        "code problems",
        "code issues",
        "find security issues",
        "performance review",
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
        "stack trace",
        "exception",
        "crashed",
        "broken",
        "fix this error",
        "debug this",
        "what's wrong",
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
        "what does this do",
        "how does this work",
        "explain this code",
        "architecture analysis",
        "code structure",
        "dependencies",
        "analyze directory",
    ],
    "review_pending_changes": [
        "review pending changes",
        "check my changes",
        "validate changes",
        "pre-commit review",
        "before commit",
        "about to commit",
        "ready to commit",
        "review my git changes",
        "check git changes",
        "validate my changes",
        "review staged changes",
        "review unstaged changes",
        "pre-commit",
        "before I commit",
        "should I commit",
        "commit ready",
        "review diff",
        "check diff",
        "validate implementation",
        "review my work",
    ],
}
