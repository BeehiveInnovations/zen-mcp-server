"""
Tool implementations for Zen MCP Server - Premium High-End Models Only
Focused on complex, multi-step workflows requiring premium models
"""

from .analyze import AnalyzeTool
from .challenge import ChallengeTool
from .chat import ChatTool
from .consensus import ConsensusTool
from .debug import DebugIssueTool
from .listmodels import ListModelsTool
from .planner import PlannerTool
from .secaudit import SecauditTool
from .thinkdeep import ThinkDeepTool
from .tracer import TracerTool
from .version import VersionTool

# Archived tools (handled by Claude subagents):
# - CodeReviewTool -> use code-review-specialist subagent
# - PrecommitTool -> use multiple specialized subagents
# - RefactorTool -> use complexity-guard subagent
# - TestGenTool -> use universal-test-engineer subagent
# - DocgenTool -> use documentation subagents

__all__ = [
    "ThinkDeepTool",
    "DebugIssueTool",
    "AnalyzeTool",
    "ChatTool",
    "ConsensusTool",
    "ListModelsTool",
    "PlannerTool",
    "ChallengeTool",
    "SecauditTool",
    "TracerTool",
    "VersionTool",
]
