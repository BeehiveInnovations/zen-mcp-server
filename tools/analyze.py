"""
AnalyzeWorkflow tool - Step-by-step code analysis with systematic investigation

This tool provides a structured workflow for comprehensive code and file analysis.
It guides the CLI agent through systematic investigation steps with forced pauses between each step
to ensure thorough code examination, pattern identification, and architectural assessment before proceeding.
The tool supports complex analysis scenarios including architectural review, performance analysis,
security assessment, and maintainability evaluation.

Key features:
- Step-by-step analysis workflow with progress tracking
- Context-aware file embedding (references during investigation, full content for analysis)
- Automatic pattern and insight tracking with categorization
- Expert analysis integration with external models
- Support for focused analysis (architecture, performance, security, quality)
- Confidence-based workflow optimization
"""

import logging
from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import Field, model_validator

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_ANALYTICAL
from systemprompts import ANALYZE_PROMPT
from tools.shared.base_models import WorkflowRequest

from .workflow.base import WorkflowTool
from .workflow.shared_utilities import (
    ResponseCustomizer,
    WorkflowFieldMapper,
    WorkflowStepProcessor,
    WorkflowUtilities,
)

logger = logging.getLogger(__name__)

# Tool-specific field descriptions for analyze workflow (using shared utilities base)
ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS = WorkflowFieldMapper.map_with_overrides(
    {
        "step": {
            "type": "string",
            "description": (
                "What to analyze or look for in this step. In step 1, describe what you want to analyze and begin forming "
                "an analytical approach after thinking carefully about what needs to be examined. Consider code quality, "
                "performance implications, architectural patterns, and design decisions. Map out the codebase structure, "
                "understand the business logic, and identify areas requiring deeper analysis. In later steps, continue "
                "exploring with precision and adapt your understanding as you uncover more insights."
            ),
        },
        "findings": {
            "type": "string",
            "description": (
                "Summarize everything discovered in this step about the code being analyzed. Include analysis of architectural "
                "patterns, design decisions, tech stack assessment, scalability characteristics, performance implications, "
                "maintainability factors, security posture, and strategic improvement opportunities. Be specific and avoid "
                "vague language—document what you now know about the codebase and how it affects your assessment. "
                "IMPORTANT: Document both strengths (good patterns, solid architecture, well-designed components) and "
                "concerns (tech debt, scalability risks, overengineering, unnecessary complexity). In later steps, confirm "
                "or update past findings with additional evidence."
            ),
        },
        "confidence": {
            "type": "string",
            "enum": ["exploring", "low", "medium", "high", "very_high", "almost_certain", "certain"],
            "description": (
                "Your confidence level in the current analysis findings: exploring (early investigation), "
                "low (some insights but more needed), medium (solid understanding), high (comprehensive insights), "
                "very_high (very comprehensive insights), almost_certain (nearly complete analysis), "
                "certain (100% confidence - complete analysis ready for expert validation)"
            ),
        },
        "analysis_type": {
            "type": "string",
            "enum": ["architecture", "performance", "security", "quality", "general"],
            "default": "general",
            "description": "Type of analysis to perform (architecture, performance, security, quality, general)",
        },
        "output_format": {
            "type": "string",
            "enum": ["summary", "detailed", "actionable"],
            "default": "detailed",
            "description": "How to format the output (summary, detailed, actionable)",
        },
    }
)


class AnalyzeWorkflowRequest(WorkflowRequest):
    """Request model for analyze workflow investigation steps"""

    # Required fields for each investigation step
    step: str = Field(..., description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["step"])
    step_number: int = Field(..., description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["step_number"])
    total_steps: int = Field(..., description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["total_steps"])
    next_step_required: bool = Field(..., description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["next_step_required"])

    # Investigation tracking fields
    findings: str = Field(..., description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["findings"])
    files_checked: list[str] = Field(
        default_factory=list, description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["files_checked"]
    )
    relevant_files: list[str] = Field(
        default_factory=list, description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["relevant_files"]
    )
    relevant_context: list[str] = Field(
        default_factory=list, description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["relevant_context"]
    )

    # Issues found during analysis (structured with severity)
    issues_found: list[dict] = Field(
        default_factory=list,
        description="Issues or concerns identified during analysis, each with severity level (critical, high, medium, low)",
    )

    # Optional backtracking field
    backtrack_from_step: Optional[int] = Field(
        None, description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["backtrack_from_step"]
    )

    # Optional images for visual context
    images: Optional[list[str]] = Field(default=None, description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["images"])

    # Analyze-specific fields (only used in step 1 to initialize)
    # Note: Use relevant_files field instead of files for consistency across workflow tools
    analysis_type: Optional[Literal["architecture", "performance", "security", "quality", "general"]] = Field(
        "general", description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["analysis_type"]
    )
    output_format: Optional[Literal["summary", "detailed", "actionable"]] = Field(
        "detailed", description=ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["output_format"]
    )

    # Keep thinking_mode and use_websearch from original analyze tool
    # temperature is inherited from WorkflowRequest

    @model_validator(mode="after")
    def validate_step_one_requirements(self):
        """Ensure step 1 has required relevant_files."""
        if self.step_number == 1:
            if not self.relevant_files:
                raise ValueError("Step 1 requires 'relevant_files' field to specify files or directories to analyze")
        return self


class AnalyzeTool(WorkflowTool):
    """
    Analyze workflow tool for step-by-step code analysis and expert validation.

    This tool implements a structured analysis workflow that guides users through
    methodical investigation steps, ensuring thorough code examination, pattern identification,
    and architectural assessment before reaching conclusions. It supports complex analysis scenarios
    including architectural review, performance analysis, security assessment, and maintainability evaluation.
    """

    def __init__(self):
        super().__init__()
        self.initial_request = None
        self.analysis_config = {}

    def get_name(self) -> str:
        return "analyze"

    def get_description(self) -> str:
        return (
            "COMPREHENSIVE ANALYSIS WORKFLOW - Step-by-step code analysis with expert validation. "
            "This tool guides you through a systematic investigation process where you:\n\n"
            "1. Start with step 1: describe your analysis investigation plan\n"
            "2. STOP and investigate code structure, patterns, and architectural decisions\n"
            "3. Report findings in step 2 with concrete evidence from actual code analysis\n"
            "4. Continue investigating between each step\n"
            "5. Track findings, relevant files, and insights throughout\n"
            "6. Update assessments as understanding evolves\n"
            "7. Once investigation is complete, always receive expert validation\n\n"
            "IMPORTANT: This tool enforces investigation between steps:\n"
            "- After each call, you MUST investigate before calling again\n"
            "- Each step must include NEW evidence from code examination\n"
            "- No recursive calls without actual investigation work\n"
            "- The tool will specify which step number to use next\n"
            "- Follow the required_actions list for investigation guidance\n\n"
            "Perfect for: comprehensive code analysis, architectural assessment, performance evaluation, "
            "security analysis, maintainability review, pattern detection, strategic planning."
        )

    def get_system_prompt(self) -> str:
        return ANALYZE_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self) -> "ToolModelCategory":
        """Analyze workflow requires thorough analysis and reasoning"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.EXTENDED_REASONING

    def get_workflow_request_model(self):
        """Return the analyze workflow-specific request model."""
        return AnalyzeWorkflowRequest

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema using WorkflowSchemaBuilder with analyze-specific overrides."""
        from .workflow.schema_builders import WorkflowSchemaBuilder

        # Use shared utilities for field mapping
        analyze_field_overrides = ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS

        # Add issues_found field for analyze workflow
        analyze_field_overrides["issues_found"] = {
            "type": "array",
            "items": {"type": "object"},
            "description": "Issues or concerns identified during analysis, each with severity level (critical, high, medium, low)",
        }

        # Use WorkflowSchemaBuilder with analyze-specific tool fields
        return WorkflowSchemaBuilder.build_schema(
            tool_specific_fields=analyze_field_overrides,
            model_field_schema=self.get_model_field_schema(),
            auto_mode=self.is_effective_auto_mode(),
            tool_name=self.get_name(),
            excluded_workflow_fields=["hypothesis"],  # Analyze doesn't use hypothesis field
        )

    def get_required_actions(self, step_number: int, confidence: str, findings: str, total_steps: int) -> list[str]:
        """Define required actions for each investigation phase using shared utilities."""
        return WorkflowStepProcessor.generate_required_actions(
            step_number=step_number,
            confidence=confidence,
            tool_name=self.get_name(),
            findings=findings,
            total_steps=total_steps,
        )

    def should_call_expert_analysis(self, consolidated_findings, request=None) -> bool:
        """
        Always call expert analysis for comprehensive validation using shared utilities.
        """
        # Check if user explicitly requested to skip assistant model
        if request and not self.get_request_use_assistant_model(request):
            return False

        # Use shared utility to determine expert analysis usage
        return WorkflowUtilities.should_use_expert_analysis(consolidated_findings, confidence_threshold="certain")

    def prepare_expert_analysis_context(self, consolidated_findings) -> str:
        """Prepare context for external model call for final analysis validation."""
        context_parts = [
            f"=== ANALYSIS REQUEST ===\\n{self.initial_request or 'Code analysis workflow initiated'}\\n=== END REQUEST ==="
        ]

        # Add investigation summary
        investigation_summary = self._build_analysis_summary(consolidated_findings)
        context_parts.append(
            f"\\n=== AGENT'S ANALYSIS INVESTIGATION ===\\n{investigation_summary}\\n=== END INVESTIGATION ==="
        )

        # Add analysis configuration context if available
        if self.analysis_config:
            config_text = "\\n".join(f"- {key}: {value}" for key, value in self.analysis_config.items() if value)
            context_parts.append(f"\\n=== ANALYSIS CONFIGURATION ===\\n{config_text}\\n=== END CONFIGURATION ===")

        # Add relevant code elements if available
        if consolidated_findings.relevant_context:
            methods_text = "\\n".join(f"- {method}" for method in consolidated_findings.relevant_context)
            context_parts.append(f"\\n=== RELEVANT CODE ELEMENTS ===\\n{methods_text}\\n=== END CODE ELEMENTS ===")

        # Add assessment evolution if available
        if consolidated_findings.hypotheses:
            assessments_text = "\\n".join(
                f"Step {h['step']}: {h['hypothesis']}" for h in consolidated_findings.hypotheses
            )
            context_parts.append(f"\\n=== ASSESSMENT EVOLUTION ===\\n{assessments_text}\\n=== END ASSESSMENTS ===")

        # Add images if available
        if consolidated_findings.images:
            images_text = "\\n".join(f"- {img}" for img in consolidated_findings.images)
            context_parts.append(
                f"\\n=== VISUAL ANALYSIS INFORMATION ===\\n{images_text}\\n=== END VISUAL INFORMATION ==="
            )

        return "\\n".join(context_parts)

    def _build_analysis_summary(self, consolidated_findings) -> str:
        """Prepare a comprehensive summary using shared utilities."""
        return WorkflowUtilities.build_expert_context_summary(consolidated_findings, self.get_name())

    def should_include_files_in_expert_prompt(self) -> bool:
        """Include files in expert analysis for comprehensive validation."""
        return True

    def should_embed_system_prompt(self) -> bool:
        """Embed system prompt in expert analysis for proper context."""
        return True

    def get_expert_thinking_mode(self) -> str:
        """Use high thinking mode for thorough analysis."""
        return "high"

    def get_expert_analysis_instruction(self) -> str:
        """Get specific instruction for analysis expert validation."""
        return (
            "Please provide comprehensive analysis validation based on the investigation findings. "
            "Focus on identifying any remaining architectural insights, validating the completeness of the analysis, "
            "and providing final strategic recommendations following the structured format specified in the system prompt."
        )

    # Hook method overrides for analyze-specific behavior

    def prepare_step_data(self, request) -> dict:
        """
        Map analyze-specific fields for internal processing using shared utilities.
        """
        step_data = WorkflowStepProcessor.process_step_data(request, self.get_name())

        # Analyze-specific adjustments
        step_data["confidence"] = "medium"  # Fixed value for workflow compatibility
        step_data["hypothesis"] = request.findings  # Map findings to hypothesis for compatibility

        return step_data

    def should_skip_expert_analysis(self, request, consolidated_findings) -> bool:
        """
        Analyze workflow always uses expert analysis for comprehensive validation.

        Analysis benefits from a second opinion to ensure completeness and catch
        any missed insights or alternative perspectives.
        """
        return False

    def store_initial_issue(self, step_description: str):
        """Store initial request for expert analysis."""
        self.initial_request = step_description

    # Override inheritance hooks for analyze-specific behavior

    def get_completion_status(self) -> str:
        """Analyze tools use analysis-specific status."""
        return "analysis_complete_ready_for_implementation"

    def get_completion_data_key(self) -> str:
        """Analyze uses 'complete_analysis' key."""
        return "complete_analysis"

    def get_final_analysis_from_request(self, request):
        """Analyze tools use 'findings' field."""
        return request.findings

    def get_confidence_level(self, request) -> str:
        """Analyze tools use fixed confidence for consistency."""
        return "medium"

    def get_completion_message(self) -> str:
        """Analyze-specific completion message."""
        return (
            "Analysis complete. You have identified all significant patterns, "
            "architectural insights, and strategic opportunities. MANDATORY: Present the user with the complete "
            "analysis results organized by strategic impact, and IMMEDIATELY proceed with implementing the "
            "highest priority recommendations or provide specific guidance for improvements. Focus on actionable "
            "strategic insights."
        )

    def get_skip_reason(self) -> str:
        """Analyze-specific skip reason."""
        return "Completed comprehensive analysis locally"

    def get_skip_expert_analysis_status(self) -> str:
        """Analyze-specific expert analysis skip status."""
        return "skipped_due_to_complete_analysis"

    def prepare_work_summary(self) -> str:
        """Analyze-specific work summary."""
        return self._build_analysis_summary(self.consolidated_findings)

    def get_completion_next_steps_message(self, expert_analysis_used: bool = False) -> str:
        """
        Analyze-specific completion message.
        """
        base_message = (
            "ANALYSIS IS COMPLETE. You MUST now summarize and present ALL analysis findings organized by "
            "strategic impact (Critical → High → Medium → Low), specific architectural insights with code references, "
            "and exact recommendations for improvement. Clearly prioritize the top 3 strategic opportunities that need "
            "immediate attention. Provide concrete, actionable guidance for each finding—make it easy for a developer "
            "to understand exactly what strategic improvements to implement and how to approach them."
        )

        # Add expert analysis guidance only when expert analysis was actually used
        if expert_analysis_used:
            expert_guidance = self.get_expert_analysis_guidance()
            if expert_guidance:
                return f"{base_message}\n\n{expert_guidance}"

        return base_message

    def get_expert_analysis_guidance(self) -> str:
        """
        Provide specific guidance for handling expert analysis in code analysis.
        """
        return (
            "IMPORTANT: Analysis from an assistant model has been provided above. You MUST thoughtfully evaluate and validate "
            "the expert insights rather than treating them as definitive conclusions. Cross-reference the expert "
            "analysis with your own systematic investigation, verify that architectural recommendations are "
            "appropriate for this codebase's scale and context, and ensure suggested improvements align with "
            "the project's goals and constraints. Present a comprehensive synthesis that combines your detailed "
            "analysis with validated expert perspectives, clearly distinguishing between patterns you've "
            "independently identified and additional strategic insights from expert validation."
        )

    def get_step_guidance_message(self, request) -> str:
        """
        Analyze-specific step guidance using shared utilities.
        """
        required_actions = self.get_required_actions(
            request.step_number, "medium", request.findings, request.total_steps
        )
        return WorkflowUtilities.generate_step_guidance_message(
            request.step_number, "medium", self.get_name(), required_actions
        )

    def customize_workflow_response(self, response_data: dict, request) -> dict:
        """
        Customize response using shared utilities.
        """
        # Store initial request on first step
        if request.step_number == 1:
            self.initial_request = request.step
            # Store analysis configuration for expert analysis
            if request.relevant_files:
                self.analysis_config = {
                    "relevant_files": request.relevant_files,
                    "analysis_type": getattr(request, "analysis_type", "general"),
                    "output_format": getattr(request, "output_format", "detailed"),
                }

        # Use shared utilities for response customization
        status_mappings = ResponseCustomizer.get_standard_status_mappings(self.get_name())

        # Add analyze-specific status data
        additional_data = {}
        if hasattr(self, "consolidated_findings") and self.consolidated_findings:
            issues_summary = WorkflowUtilities.format_issues_summary(
                getattr(self.consolidated_findings, "issues_found", [])
            )
            if f"{self.get_name()}_status" in response_data:
                additional_data["analysis_status"] = {
                    "insights_by_severity": issues_summary,
                    "analysis_confidence": self.get_request_confidence(request),
                }

        return ResponseCustomizer.customize_response(response_data, self.get_name(), status_mappings, additional_data)

    # Required abstract methods from BaseTool
    def get_request_model(self):
        """Return the analyze workflow-specific request model."""
        return AnalyzeWorkflowRequest

    async def prepare_prompt(self, request) -> str:
        """Not used - workflow tools use execute_workflow()."""
        return ""  # Workflow tools use execute_workflow() directly
