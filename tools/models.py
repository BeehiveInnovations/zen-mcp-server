"""
Data models for tool responses and interactions
"""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ToolModelCategory(Enum):
    """Categories for tool model selection based on requirements."""

    EXTENDED_REASONING = "extended_reasoning"  # Requires deep thinking capabilities
    FAST_RESPONSE = "fast_response"  # Speed and cost efficiency preferred
    BALANCED = "balanced"  # Balance of capability and performance


class ContinuationOffer(BaseModel):
    """Offer for Claude to continue conversation when Gemini doesn't ask follow-up"""

    continuation_id: str = Field(
        ..., description="Thread continuation ID for multi-turn conversations across different tools"
    )
    note: str = Field(..., description="Message explaining continuation opportunity to Claude")
    suggested_tool_params: Optional[dict[str, Any]] = Field(
        None, description="Suggested parameters for continued tool usage"
    )
    remaining_turns: int = Field(..., description="Number of conversation turns remaining")


class ToolOutput(BaseModel):
    """Standardized output format for all tools"""

    status: Literal[
        "success",
        "error",
        "clarification_required",
        "full_codereview_required",
        "focused_review_required",
        "test_sample_needed",
        "more_tests_required",
        "refactor_analysis_complete",
        "resend_prompt",
        "continuation_available",
    ] = "success"
    content: Optional[str] = Field(None, description="The main content/response from the tool")
    content_type: Literal["text", "markdown", "json"] = "text"
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)
    continuation_offer: Optional[ContinuationOffer] = Field(
        None, description="Optional offer for Claude to continue conversation"
    )


class ClarificationRequest(BaseModel):
    """Request for additional context or clarification"""

    status: Literal["clarification_required"] = "clarification_required"
    question: str = Field(..., description="Question to ask Claude for more context")
    files_needed: Optional[list[str]] = Field(
        default_factory=list, description="Specific files that are needed for analysis"
    )
    suggested_next_action: Optional[dict[str, Any]] = Field(
        None,
        description="Suggested tool call with parameters after getting clarification",
    )


class FullCodereviewRequired(BaseModel):
    """Request for full code review when scope is too large for quick review"""

    status: Literal["full_codereview_required"] = "full_codereview_required"
    important: Optional[str] = Field(None, description="Important message about escalation")
    reason: Optional[str] = Field(None, description="Reason why full review is needed")


class FocusedReviewRequired(BaseModel):
    """Request for Claude to provide smaller, focused subsets of code for review"""

    status: Literal["focused_review_required"] = "focused_review_required"
    reason: str = Field(..., description="Why the current scope is too large for effective review")
    suggestion: str = Field(
        ..., description="Suggested approach for breaking down the review into smaller, focused parts"
    )


class TestSampleNeeded(BaseModel):
    """Request for additional test samples to determine testing framework"""

    status: Literal["test_sample_needed"] = "test_sample_needed"
    reason: str = Field(..., description="Reason why additional test samples are required")


class MoreTestsRequired(BaseModel):
    """Request for continuation to generate additional tests"""

    status: Literal["more_tests_required"] = "more_tests_required"
    pending_tests: str = Field(..., description="List of pending tests to be generated")


class RefactorOpportunity(BaseModel):
    """A single refactoring opportunity with precise targeting information"""

    id: str = Field(..., description="Unique identifier for this refactoring opportunity")
    type: Literal["decompose", "codesmells", "modernize", "organization"] = Field(
        ..., description="Type of refactoring"
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="Severity level")
    file: str = Field(..., description="Absolute path to the file")
    start_line: int = Field(..., description="Starting line number")
    end_line: int = Field(..., description="Ending line number")
    context_start_text: str = Field(..., description="Exact text from start line for verification")
    context_end_text: str = Field(..., description="Exact text from end line for verification")
    issue: str = Field(..., description="Clear description of what needs refactoring")
    suggestion: str = Field(..., description="Specific refactoring action to take")
    rationale: str = Field(..., description="Why this improves the code")
    code_to_replace: str = Field(..., description="Original code that should be changed")
    replacement_code_snippet: str = Field(..., description="Refactored version of the code")
    new_code_snippets: Optional[list[dict]] = Field(
        default_factory=list, description="Additional code snippets to be added"
    )


class RefactorAction(BaseModel):
    """Next action for Claude to implement refactoring"""

    action_type: Literal["EXTRACT_METHOD", "SPLIT_CLASS", "MODERNIZE_SYNTAX", "REORGANIZE_CODE", "DECOMPOSE_FILE"] = (
        Field(..., description="Type of action to perform")
    )
    target_file: str = Field(..., description="Absolute path to target file")
    source_lines: str = Field(..., description="Line range (e.g., '45-67')")
    description: str = Field(..., description="Step-by-step action description for Claude")


class RefactorAnalysisComplete(BaseModel):
    """Complete refactor analysis with prioritized opportunities"""

    status: Literal["refactor_analysis_complete"] = "refactor_analysis_complete"
    refactor_opportunities: list[RefactorOpportunity] = Field(..., description="List of refactoring opportunities")
    priority_sequence: list[str] = Field(..., description="Recommended order of refactoring IDs")
    next_actions_for_claude: list[RefactorAction] = Field(..., description="Specific actions for Claude to implement")


class ResendPromptRequest(BaseModel):
    """Request to resend prompt via file due to size limits"""

    status: Literal["resend_prompt"] = "resend_prompt"
    content: str = Field(..., description="Instructions for handling large prompt")
    content_type: Literal["text"] = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)


# Registry mapping status strings to their corresponding Pydantic models
SPECIAL_STATUS_MODELS = {
    "clarification_required": ClarificationRequest,
    "full_codereview_required": FullCodereviewRequired,
    "focused_review_required": FocusedReviewRequired,
    "test_sample_needed": TestSampleNeeded,
    "more_tests_required": MoreTestsRequired,
    "refactor_analysis_complete": RefactorAnalysisComplete,
    "resend_prompt": ResendPromptRequest,
}


class DiagnosticHypothesis(BaseModel):
    """A debugging hypothesis with context and next steps"""

    rank: int = Field(..., description="Ranking of this hypothesis (1 = most likely)")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Confidence level")
    hypothesis: str = Field(..., description="Description of the potential root cause")
    reasoning: str = Field(..., description="Why this hypothesis is plausible")
    next_step: str = Field(..., description="Suggested action to test/validate this hypothesis")


class StructuredDebugResponse(BaseModel):
    """Enhanced debug response with multiple hypotheses"""

    summary: str = Field(..., description="Brief summary of the issue")
    hypotheses: list[DiagnosticHypothesis] = Field(..., description="Ranked list of potential causes")
    immediate_actions: list[str] = Field(
        default_factory=list,
        description="Immediate steps to take regardless of root cause",
    )
    additional_context_needed: Optional[list[str]] = Field(
        default_factory=list,
        description="Additional files or information that would help with analysis",
    )
