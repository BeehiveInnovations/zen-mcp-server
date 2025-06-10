"""
System prompts for Gemini tools
"""

from .tool_prompts import (ANALYZE_PROMPT, CHAT_PROMPT, DEBUG_ISSUE_PROMPT,
                           REVIEW_CODE_PROMPT, THINK_DEEPER_PROMPT)

__all__ = [
    "THINK_DEEPER_PROMPT",
    "REVIEW_CODE_PROMPT",
    "DEBUG_ISSUE_PROMPT",
    "ANALYZE_PROMPT",
    "CHAT_PROMPT",
]
