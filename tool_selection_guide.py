"""
Tool Selection Guide for Gemini MCP Server

This module provides guidance for Claude on which tool to use for different scenarios.
"""

TOOL_BOUNDARIES = {
    "analyze": {
        "purpose": "Understanding and exploration (read-only analysis)",
        "best_for": [
            "Understanding code structure and architecture",
            "Exploring unfamiliar codebases",
            "Identifying patterns and dependencies",
            "Documenting existing functionality",
            "Learning how systems work",
        ],
        "avoid_for": [
            "Finding bugs or security issues (use review_code)",
            "Debugging errors (use debug_issue)",
            "Extending existing analysis (use think_deeper)",
        ],
        "output": "Descriptive explanations and architectural insights",
    },
    "review_code": {
        "purpose": "Finding issues and suggesting fixes (prescriptive analysis)",
        "best_for": [
            "Finding bugs, security vulnerabilities, performance issues",
            "Code quality assessment with actionable feedback",
            "Pre-merge code reviews",
            "Security audits",
            "Performance optimization recommendations",
        ],
        "avoid_for": [
            "Understanding how code works (use analyze)",
            "Debugging runtime errors (use debug_issue)",
            "Architectural discussions (use think_deeper or chat)",
        ],
        "output": "Severity-ranked issues with specific fixes",
    },
    "debug_issue": {
        "purpose": "Root cause analysis for errors (diagnostic analysis)",
        "best_for": [
            "Analyzing runtime errors and exceptions",
            "Troubleshooting failing tests",
            "Investigating performance problems",
            "Tracing execution issues",
            "System-level debugging",
        ],
        "avoid_for": [
            "Code quality issues (use review_code)",
            "Understanding working code (use analyze)",
            "Design discussions (use think_deeper or chat)",
        ],
        "output": "Ranked hypotheses with validation steps",
    },
    "think_deeper": {
        "purpose": "Extending and validating specific analysis (collaborative validation)",
        "best_for": [
            "Getting second opinion on Claude's analysis",
            "Challenging assumptions and finding edge cases",
            "Validating architectural decisions",
            "Exploring alternative approaches",
            "Risk assessment for proposed changes",
        ],
        "avoid_for": [
            "Initial analysis (use analyze first)",
            "Bug hunting (use review_code)",
            "Open-ended brainstorming (use chat)",
        ],
        "output": "Extended analysis building on existing work",
    },
    "chat": {
        "purpose": "Open-ended collaboration and brainstorming (exploratory discussion)",
        "best_for": [
            "Brainstorming solutions and approaches",
            "Technology comparisons and recommendations",
            "Discussing trade-offs and design decisions",
            "Getting opinions on implementation strategies",
            "General development questions and explanations",
        ],
        "avoid_for": [
            "Analyzing specific code files (use analyze)",
            "Finding bugs in code (use review_code)",
            "Debugging specific errors (use debug_issue)",
        ],
        "output": "Conversational insights and recommendations",
    },
}

DECISION_FLOWCHART = """
Tool Selection Decision Flow:

1. Do you have a specific error/exception to debug?
   → YES: Use debug_issue

2. Do you want to find bugs/issues in code?
   → YES: Use review_code

3. Do you want to understand how code works?
   → YES: Use analyze

4. Do you have existing analysis that needs extension/validation?
   → YES: Use think_deeper

5. Do you want to brainstorm, discuss, or get opinions?
   → YES: Use chat
"""

COMMON_OVERLAPS = {
    "analyze vs review_code": {
        "confusion": "Both examine code quality",
        "distinction": "analyze explains, review_code prescribes fixes",
        "rule": "Use analyze to understand, review_code to improve",
    },
    "chat vs think_deeper": {
        "confusion": "Both provide collaborative thinking",
        "distinction": "chat is open-ended, think_deeper builds on specific analysis",
        "rule": "Use think_deeper to extend analysis, chat for open discussion",
    },
    "debug_issue vs review_code": {
        "confusion": "Both find problems in code",
        "distinction": "debug_issue diagnoses runtime errors, review_code finds static issues",
        "rule": "Use debug_issue for 'why is this failing?', review_code for 'what could go wrong?'",
    },
}


def get_tool_recommendation(intent: str, context: str = "") -> dict:
    """
    Recommend the best tool based on user intent and context.

    Args:
        intent: What the user wants to accomplish
        context: Additional context about the situation

    Returns:
        Dictionary with recommended tool and reasoning
    """

    # Keywords that strongly indicate specific tools
    debug_keywords = [
        "error",
        "exception",
        "failing",
        "crash",
        "bug",
        "not working",
        "trace",
    ]
    review_keywords = [
        "review",
        "issues",
        "problems",
        "security",
        "vulnerabilities",
        "quality",
    ]
    analyze_keywords = [
        "understand",
        "how does",
        "what is",
        "structure",
        "architecture",
        "explain",
    ]
    deeper_keywords = [
        "extend",
        "validate",
        "challenge",
        "alternative",
        "edge case",
        "think deeper",
    ]
    chat_keywords = [
        "brainstorm",
        "discuss",
        "opinion",
        "compare",
        "recommend",
        "what about",
    ]

    intent_lower = intent.lower()

    if any(keyword in intent_lower for keyword in debug_keywords):
        return {
            "tool": "debug_issue",
            "confidence": "high",
            "reasoning": "Intent indicates debugging/troubleshooting a specific issue",
        }

    if any(keyword in intent_lower for keyword in review_keywords):
        return {
            "tool": "review_code",
            "confidence": "high",
            "reasoning": "Intent indicates finding issues or reviewing code quality",
        }

    if any(keyword in intent_lower for keyword in analyze_keywords):
        return {
            "tool": "analyze",
            "confidence": "high",
            "reasoning": "Intent indicates understanding or exploring code",
        }

    if any(keyword in intent_lower for keyword in deeper_keywords):
        return {
            "tool": "think_deeper",
            "confidence": "medium",
            "reasoning": "Intent suggests extending or validating existing analysis",
        }

    if any(keyword in intent_lower for keyword in chat_keywords):
        return {
            "tool": "chat",
            "confidence": "medium",
            "reasoning": "Intent suggests open-ended discussion or brainstorming",
        }

    # Default to chat for ambiguous requests
    return {
        "tool": "chat",
        "confidence": "low",
        "reasoning": "Intent unclear, defaulting to conversational tool",
    }
