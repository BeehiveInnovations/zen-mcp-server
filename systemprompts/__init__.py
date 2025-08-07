"""
System prompts for Zen-MCP high-end model tools
Focused on complex, multi-step workflows requiring premium models
"""

from .analyze_prompt import ANALYZE_PROMPT
from .chat_prompt import CHAT_PROMPT
from .consensus_prompt import CONSENSUS_PROMPT
from .debug_prompt import DEBUG_ISSUE_PROMPT
from .planner_prompt import PLANNER_PROMPT
from .secaudit_prompt import SECAUDIT_PROMPT
from .thinkdeep_prompt import THINKDEEP_PROMPT
from .tracer_prompt import TRACER_PROMPT

__all__ = [
    "THINKDEEP_PROMPT",
    "DEBUG_ISSUE_PROMPT",
    "ANALYZE_PROMPT",
    "CHAT_PROMPT",
    "CONSENSUS_PROMPT",
    "PLANNER_PROMPT",
    "SECAUDIT_PROMPT",
    "TRACER_PROMPT",
]
