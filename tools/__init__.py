"""
Tool implementations for Zen MCP Server

This module provides access to tools through both direct imports (for backward compatibility)
and lazy loading via the ToolFactory (for reduced startup memory usage).

For new code, prefer using the factory pattern:
    from tools.factory import get_tool_factory
    factory = get_tool_factory()
    tool = factory.get_tool("chat")

Direct imports are maintained for backward compatibility but will load modules immediately:
    from tools import ChatTool  # Loads module immediately
"""

# Lazy factory interface - preferred for new code
from .factory import get_tool_factory, reset_tool_factory


# Direct imports for backward compatibility - these load modules immediately
# Import on-demand to preserve lazy loading benefits when not used
def _lazy_import_all():
    """Import all tools for backward compatibility when needed."""
    global AnalyzeTool, CacheMonitorTool, ChallengeTool, ChatTool
    global CodeReviewTool, ConsensusTool, DebugIssueTool, DocgenTool
    global ListModelsTool, PlannerTool, PrecommitTool, RefactorTool
    global SecauditTool, TestGenTool, ThinkDeepTool, TracerTool, VersionTool

    from .analyze import AnalyzeTool
    from .cache_monitor import CacheMonitorTool
    from .challenge import ChallengeTool
    from .chat import ChatTool
    from .codereview import CodeReviewTool
    from .consensus import ConsensusTool
    from .debug import DebugIssueTool
    from .docgen import DocgenTool
    from .listmodels import ListModelsTool
    from .planner import PlannerTool
    from .precommit import PrecommitTool
    from .refactor import RefactorTool
    from .secaudit import SecauditTool
    from .testgen import TestGenTool
    from .thinkdeep import ThinkDeepTool
    from .tracer import TracerTool
    from .version import VersionTool


# Lazy module-level attribute access for backward compatibility
def __getattr__(name):
    """Provide lazy access to tool classes when accessed directly."""
    tool_classes = [
        "AnalyzeTool",
        "CacheMonitorTool",
        "ChallengeTool",
        "ChatTool",
        "CodeReviewTool",
        "ConsensusTool",
        "DebugIssueTool",
        "DocgenTool",
        "ListModelsTool",
        "PlannerTool",
        "PrecommitTool",
        "RefactorTool",
        "SecauditTool",
        "TestGenTool",
        "ThinkDeepTool",
        "TracerTool",
        "VersionTool",
    ]

    if name in tool_classes:
        # Import all tools and return the requested one
        _lazy_import_all()
        return globals()[name]

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # Factory interface (preferred)
    "get_tool_factory",
    "reset_tool_factory",
    # Tool classes (backward compatibility)
    "ThinkDeepTool",
    "CodeReviewTool",
    "DebugIssueTool",
    "DocgenTool",
    "AnalyzeTool",
    "CacheMonitorTool",
    "ChatTool",
    "ConsensusTool",
    "ListModelsTool",
    "PlannerTool",
    "PrecommitTool",
    "ChallengeTool",
    "RefactorTool",
    "SecauditTool",
    "TestGenTool",
    "TracerTool",
    "VersionTool",
]
