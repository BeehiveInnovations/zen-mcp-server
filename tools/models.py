"""
Data models for tool responses and interactions
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ToolOutput(BaseModel):
    """Standardized output format for all tools"""

    status: Literal[
        "success", "error", "requires_clarification", "requires_file_prompt"
    ] = "success"
    content: str = Field(..., description="The main content/response from the tool")
    content_type: Literal["text", "markdown", "json"] = "text"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ClarificationRequest(BaseModel):
    """Request for additional context or clarification"""

    question: str = Field(..., description="Question to ask Claude for more context")
    files_needed: Optional[List[str]] = Field(
        default_factory=list, description="Specific files that are needed for analysis"
    )
    suggested_next_action: Optional[Dict[str, Any]] = Field(
        None,
        description="Suggested tool call with parameters after getting clarification",
    )


class DiagnosticHypothesis(BaseModel):
    """A debugging hypothesis with context and next steps"""

    rank: int = Field(..., description="Ranking of this hypothesis (1 = most likely)")
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence level"
    )
    hypothesis: str = Field(..., description="Description of the potential root cause")
    reasoning: str = Field(..., description="Why this hypothesis is plausible")
    next_step: str = Field(
        ..., description="Suggested action to test/validate this hypothesis"
    )


class StructuredDebugResponse(BaseModel):
    """Enhanced debug response with multiple hypotheses"""

    summary: str = Field(..., description="Brief summary of the issue")
    hypotheses: List[DiagnosticHypothesis] = Field(
        ..., description="Ranked list of potential causes"
    )
    immediate_actions: List[str] = Field(
        default_factory=list,
        description="Immediate steps to take regardless of root cause",
    )
    additional_context_needed: Optional[List[str]] = Field(
        default_factory=list,
        description="Additional files or information that would help with analysis",
    )
