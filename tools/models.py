"""
Data models for tool responses and interactions
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ContinuationOffer(BaseModel):
    """Offer for Claude to continue conversation when Gemini doesn't ask follow-up"""

    continuation_id: str = Field(
        ..., description="Thread continuation ID for multi-turn conversations across different tools"
    )
    message_to_user: str = Field(..., description="Message explaining continuation opportunity to Claude")
    suggested_tool_params: Optional[dict[str, Any]] = Field(
        None, description="Suggested parameters for continued tool usage"
    )
    remaining_turns: int = Field(..., description="Number of conversation turns remaining")


class ToolOutput(BaseModel):
    """Standardized output format for all tools"""

    status: Literal[
        "success",
        "error",
        "requires_clarification",
        "requires_file_prompt",
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

    question: str = Field(..., description="Question to ask Claude for more context")
    files_needed: Optional[list[str]] = Field(
        default_factory=list, description="Specific files that are needed for analysis"
    )
    suggested_next_action: Optional[dict[str, Any]] = Field(
        None,
        description="Suggested tool call with parameters after getting clarification",
    )


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
