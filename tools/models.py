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


# Registry mapping status strings to their corresponding Pydantic models
SPECIAL_STATUS_MODELS = {
    "clarification_required": ClarificationRequest,
    "full_codereview_required": FullCodereviewRequired,
    "focused_review_required": FocusedReviewRequired,
    "test_sample_needed": TestSampleNeeded,
    "more_tests_required": MoreTestsRequired,
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
