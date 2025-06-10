"""
System prompts for Gemini tools
"""

from .tool_prompts import (
    ANALYZE_PROMPT,
    CHAT_PROMPT,
    CODEREVIEW_PROMPT,
    DEBUG_ISSUE_PROMPT,
    THINK_DEEPER_PROMPT,
)

__all__ = [
    "THINK_DEEPER_PROMPT",
    "CODEREVIEW_PROMPT",
    "DEBUG_ISSUE_PROMPT",
    "ANALYZE_PROMPT",
    "CHAT_PROMPT",
]
