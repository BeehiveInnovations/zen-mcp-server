"""
Documentation Generation tool - Automated code documentation with complexity analysis

This tool provides a structured workflow for adding comprehensive documentation to codebases.
It guides you through systematic code analysis to generate modern documentation with:
- Function/method parameter documentation
- Big O complexity analysis
- Call flow and dependency documentation
- Inline comments for complex logic
- Smart updating of existing documentation

Key features:
- Step-by-step documentation workflow with progress tracking
- Context-aware file embedding (references during analysis, full content for documentation)
- Automatic conversation threading and history preservation
- Expert analysis integration with external models
- Support for multiple programming languages and documentation styles
- Configurable documentation features via parameters
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_ANALYTICAL
from systemprompts import DOCGEN_PROMPT
from tools.shared.base_models import WorkflowRequest

from .workflow.base import WorkflowTool

logger = logging.getLogger(__name__)

# Tool-specific field descriptions for documentation generation
DOCGEN_FIELD_DESCRIPTIONS = {
    "step": (
        "Describe what you're currently analyzing for documentation generation by thinking deeply about the code structure, "
        "functions, and documentation needs. In step 1, clearly state your documentation plan and begin forming a systematic "
        "approach after thinking carefully about what needs to be documented. Consider not only missing documentation but also "
        "opportunities to improve existing docs with complexity analysis, call flow information, and better parameter descriptions. "
        "Map out the codebase structure, understand the business logic, and identify areas requiring documentation. "
        "In later steps, continue exploring with precision: analyze function complexity, trace dependencies, and adapt your "
        "understanding as you uncover more documentation opportunities."
    ),
    "step_number": (
        "The index of the current step in the documentation generation sequence, beginning at 1. Each step should build upon or "
        "revise the previous one."
    ),
    "total_steps": (
        "Your current estimate for how many steps will be needed to complete the documentation analysis. "
        "Adjust as new documentation needs emerge."
    ),
    "next_step_required": (
        "Set to true if you plan to continue the documentation analysis with another step. False means you believe the "
        "documentation plan is complete and ready for implementation."
    ),
    "findings": (
        "Summarize everything discovered in this step about the code and its documentation needs. Include analysis of missing "
        "documentation, complexity assessments, call flow understanding, and opportunities for improvement. Be specific and "
        "avoid vague language—document what you now know about the code structure and how it affects your documentation plan. "
        "IMPORTANT: Document both well-documented areas (good examples to follow) and areas needing documentation. "
        "In later steps, confirm or update past findings with additional evidence."
    ),
    "files_checked": (
        "List all files (as absolute paths, do not clip or shrink file names) examined during "
        "the documentation analysis so far. "
        "Include even files that are already well-documented, as this tracks your exploration path."
    ),
    "relevant_files": (
        "Subset of files_checked (as full absolute paths) that contain code requiring documentation or are directly relevant "
        "to the documentation generation task. Only list those that need documentation work, serve as good examples, or "
        "contain dependencies that affect documentation."
    ),
    "relevant_context": (
        "List methods, functions, or classes that need documentation, in the format "
        "'ClassName.methodName' or 'functionName'. "
        "Prioritize those with complex logic, important interfaces, or missing/inadequate documentation."
    ),
    "document_complexity": (
        "Whether to include algorithmic complexity (Big O) analysis in function/method documentation. "
        "Default: true. When enabled, analyzes and documents the computational complexity of algorithms."
    ),
    "document_flow": (
        "Whether to include call flow and dependency information in documentation. "
        "Default: true. When enabled, documents which methods this function calls and which methods call this function."
    ),
    "update_existing": (
        "Whether to update existing documentation when it's found to be incorrect or incomplete. "
        "Default: true. When enabled, improves existing docs rather than just adding new ones."
    ),
    "comments_on_complex_logic": (
        "Whether to add inline comments around complex logic within functions. "
        "Default: true. When enabled, adds explanatory comments for non-obvious algorithmic steps."
    ),
}


class DocgenRequest(WorkflowRequest):
    """Request model for documentation generation steps"""

    # Required workflow fields
    step: str = Field(..., description=DOCGEN_FIELD_DESCRIPTIONS["step"])
    step_number: int = Field(..., description=DOCGEN_FIELD_DESCRIPTIONS["step_number"])
    total_steps: int = Field(..., description=DOCGEN_FIELD_DESCRIPTIONS["total_steps"])
    next_step_required: bool = Field(..., description=DOCGEN_FIELD_DESCRIPTIONS["next_step_required"])

    # Documentation analysis tracking fields
    findings: str = Field(..., description=DOCGEN_FIELD_DESCRIPTIONS["findings"])
    files_checked: list[str] = Field(default_factory=list, description=DOCGEN_FIELD_DESCRIPTIONS["files_checked"])
    relevant_files: list[str] = Field(default_factory=list, description=DOCGEN_FIELD_DESCRIPTIONS["relevant_files"])
    relevant_context: list[str] = Field(default_factory=list, description=DOCGEN_FIELD_DESCRIPTIONS["relevant_context"])

    # Documentation generation configuration parameters
    document_complexity: Optional[bool] = Field(True, description=DOCGEN_FIELD_DESCRIPTIONS["document_complexity"])
    document_flow: Optional[bool] = Field(True, description=DOCGEN_FIELD_DESCRIPTIONS["document_flow"])
    update_existing: Optional[bool] = Field(True, description=DOCGEN_FIELD_DESCRIPTIONS["update_existing"])
    comments_on_complex_logic: Optional[bool] = Field(
        True, description=DOCGEN_FIELD_DESCRIPTIONS["comments_on_complex_logic"]
    )


class DocgenTool(WorkflowTool):
    """
    Documentation generation tool for automated code documentation with complexity analysis.

    This tool implements a structured documentation workflow that guides users through
    methodical code analysis to generate comprehensive documentation including:
    - Function/method signatures and parameter descriptions
    - Algorithmic complexity (Big O) analysis
    - Call flow and dependency documentation
    - Inline comments for complex logic
    - Modern documentation style appropriate for the language/platform
    """

    def __init__(self):
        super().__init__()
        self.initial_request = None

    def get_name(self) -> str:
        return "docgen"

    def get_description(self) -> str:
        return (
            "COMPREHENSIVE DOCUMENTATION GENERATION - Step-by-step code documentation with expert analysis. "
            "This tool guides you through a systematic investigation process where you:\n\n"
            "1. Start with step 1: describe your documentation investigation plan\n"
            "2. STOP and investigate code structure, patterns, and documentation needs\n"
            "3. Report findings in step 2 with concrete evidence from actual code analysis\n"
            "4. Continue investigating between each step\n"
            "5. Track findings, relevant files, and documentation opportunities throughout\n"
            "6. Update assessments as understanding evolves\n"
            "7. Once investigation is complete, receive expert analysis\n\n"
            "IMPORTANT: This tool enforces investigation between steps:\n"
            "- After each call, you MUST investigate before calling again\n"
            "- Each step must include NEW evidence from code examination\n"
            "- No recursive calls without actual investigation work\n"
            "- The tool will specify which step number to use next\n"
            "- Follow the required_actions list for investigation guidance\n\n"
            "Perfect for: comprehensive documentation generation, code documentation analysis, "
            "complexity assessment, documentation modernization, API documentation."
        )

    def get_system_prompt(self) -> str:
        return DOCGEN_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self) -> "ToolModelCategory":
        """Docgen requires analytical and reasoning capabilities"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.EXTENDED_REASONING

    def requires_model(self) -> bool:
        """
        Docgen tool doesn't require model resolution at the MCP boundary.

        The docgen tool is a self-contained workflow tool that guides Claude through
        systematic documentation generation without calling external AI models.

        Returns:
            bool: False - docgen doesn't need external AI model access
        """
        return False

    def requires_expert_analysis(self) -> bool:
        """Docgen is self-contained and doesn't need expert analysis."""
        return False

    def get_workflow_request_model(self):
        """Return the docgen-specific request model."""
        return DocgenRequest

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Return the tool-specific fields for docgen."""
        return {
            "document_complexity": {
                "type": "boolean",
                "default": True,
                "description": DOCGEN_FIELD_DESCRIPTIONS["document_complexity"],
            },
            "document_flow": {
                "type": "boolean",
                "default": True,
                "description": DOCGEN_FIELD_DESCRIPTIONS["document_flow"],
            },
            "update_existing": {
                "type": "boolean",
                "default": True,
                "description": DOCGEN_FIELD_DESCRIPTIONS["update_existing"],
            },
            "comments_on_complex_logic": {
                "type": "boolean",
                "default": True,
                "description": DOCGEN_FIELD_DESCRIPTIONS["comments_on_complex_logic"],
            },
        }

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema using WorkflowSchemaBuilder with field exclusions."""
        from .workflow.schema_builders import WorkflowSchemaBuilder

        # Exclude workflow fields that documentation generation doesn't need
        excluded_workflow_fields = [
            "confidence",  # Documentation doesn't use confidence levels
            "hypothesis",  # Documentation doesn't use hypothesis
            "backtrack_from_step",  # Documentation uses simpler error recovery
        ]

        # Exclude common fields that documentation generation doesn't need
        excluded_common_fields = [
            "temperature",  # Documentation doesn't need temperature control
            "thinking_mode",  # Documentation doesn't need thinking mode
            "use_websearch",  # Documentation doesn't need web search
            "images",  # Documentation doesn't use images
        ]

        return WorkflowSchemaBuilder.build_schema(
            tool_specific_fields=self.get_tool_fields(),
            required_fields=[],  # No additional required fields beyond workflow defaults
            model_field_schema=self.get_model_field_schema(),
            auto_mode=self.is_effective_auto_mode(),
            tool_name=self.get_name(),
            excluded_workflow_fields=excluded_workflow_fields,
            excluded_common_fields=excluded_common_fields,
        )

    def get_required_actions(self, step_number: int, confidence: str, findings: str, total_steps: int) -> list[str]:
        """Define required actions for each documentation analysis phase."""
        if step_number == 1:
            # Initial analysis tasks with immediate documentation
            return [
                "Examine the codebase structure and identify files that need documentation",
                "Analyze existing documentation patterns and style in the project",
                "Start documenting functions/methods AS YOU DISCOVER THEM - don't wait until the end",
                "Add documentation for 2-3 simple functions you encounter during your analysis",
            ]
        elif confidence in ["exploring", "low"]:
            # Continue analysis with incremental documentation
            return [
                "Examine specific functions and methods - ADD DOCUMENTATION as you analyze each one",
                "Document algorithmic complexity for functions you're currently analyzing",
                "Add call flow information to functions you've already started documenting",
                "Continue building documentation incrementally while gathering more insights",
            ]
        elif confidence in ["medium", "high"]:
            # Advanced analysis with continued incremental documentation
            return [
                "Continue documenting remaining undocumented functions/methods",
                "Refine and improve documentation you've already added in previous steps",
                "Ensure consistency across all documentation added so far",
                "Add complexity analysis and flow information to previously documented functions",
            ]
        else:
            # General continued analysis with documentation
            return [
                "Continue examining code patterns while adding documentation incrementally",
                "Document any new functions/methods you discover during analysis",
                "Improve existing documentation you've added in previous steps",
                "Maintain momentum by documenting as you analyze rather than deferring to the end",
            ]

    def should_call_expert_analysis(self, consolidated_findings, request=None) -> bool:
        """Docgen is self-contained and doesn't need expert analysis."""
        return False

    def prepare_expert_analysis_context(self, consolidated_findings) -> str:
        """Docgen doesn't use expert analysis."""
        return ""

    def get_step_guidance(self, step_number: int, confidence: str, request) -> dict[str, Any]:
        """
        Provide step-specific guidance for documentation generation workflow.

        This method generates docgen-specific guidance used by get_step_guidance_message().
        """
        # Generate the next steps instruction based on required actions
        required_actions = self.get_required_actions(step_number, confidence, request.findings, request.total_steps)

        if step_number == 1:
            next_steps = (
                f"MANDATORY: DO NOT call the {self.get_name()} tool again immediately. You MUST first analyze "
                f"the codebase AND START DOCUMENTING FUNCTIONS AS YOU DISCOVER THEM. This incremental approach "
                f"provides immediate value. Examine existing code, identify undocumented functions/classes, "
                f"ADD DOCUMENTATION to 2-3 simple functions during your analysis, and understand the project's "
                f"documentation standards. Only call {self.get_name()} again AFTER both analyzing AND adding "
                f"initial documentation. When you call {self.get_name()} next time, use step_number: {step_number + 1} "
                f"and report both files examined AND functions you've already documented."
            )
        elif confidence in ["exploring", "low"]:
            next_steps = (
                f"CONTINUE INCREMENTAL APPROACH! Do NOT call {self.get_name()} again yet. You should be "
                f"DOCUMENTING FUNCTIONS AS YOU ANALYZE THEM for immediate value. MANDATORY ACTIONS before calling {self.get_name()} step {step_number + 1}:\n"
                + "\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
                + "\n\nRemember: Add documentation incrementally as you work, don't defer it all to the end. "
                + f"Only call {self.get_name()} again with step_number: {step_number + 1} AFTER completing these tasks "
                + "AND adding documentation to more functions."
            )
        elif confidence in ["medium", "high"]:
            next_steps = (
                "KEEP DOCUMENTING! You're making good progress with incremental documentation. Continue this approach. REQUIRED ACTIONS:\n"
                + "\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
                + f"\n\nYou should have already documented several functions - now refine and expand that work. "
                f"Continue adding documentation to remaining functions while improving what you've already done. "
                f"Document findings with specific file:line references, then call {self.get_name()} with step_number: {step_number + 1}."
            )
        else:
            next_steps = (
                f"PAUSE ANALYSIS. Before calling {self.get_name()} step {step_number + 1}, you MUST examine more code. "
                + "Required: "
                + ", ".join(required_actions[:2])
                + ". "
                + f"Your next {self.get_name()} call (step_number: {step_number + 1}) must include "
                f"NEW evidence from actual code examination, not just theories. NO recursive {self.get_name()} calls "
                f"without investigation work!"
            )

        return {"next_steps": next_steps}

    # Hook method overrides for docgen-specific behavior

    def prepare_step_data(self, request) -> dict:
        """
        Prepare docgen-specific step data for processing.
        """
        step_data = {
            "step": request.step,
            "step_number": request.step_number,
            "findings": request.findings,
            "files_checked": request.files_checked,
            "relevant_files": request.relevant_files,
            "relevant_context": request.relevant_context,
            "issues_found": [],  # Docgen uses this for documentation gaps
            "confidence": request.confidence,
            "hypothesis": request.hypothesis,
            "images": [],  # Docgen doesn't typically use images
        }
        return step_data

    def should_skip_expert_analysis(self, request, consolidated_findings) -> bool:
        """
        Docgen tool skips expert analysis when Claude has "certain" confidence.
        """
        return request.confidence == "certain" and not request.next_step_required

    # Override inheritance hooks for docgen-specific behavior

    def get_completion_status(self) -> str:
        """Docgen tools use docgen-specific status."""
        return "documentation_analysis_complete"

    def get_completion_data_key(self) -> str:
        """Docgen uses 'complete_documentation_analysis' key."""
        return "complete_documentation_analysis"

    def get_final_analysis_from_request(self, request):
        """Docgen tools use 'hypothesis' field for documentation strategy."""
        return request.hypothesis

    def get_confidence_level(self, request) -> str:
        """Docgen tools use 'certain' for high confidence."""
        return request.confidence or "high"

    def get_completion_message(self) -> str:
        """Docgen-specific completion message."""
        return (
            "Documentation analysis complete with high confidence. You have identified the comprehensive "
            "documentation needs and strategy. MANDATORY: Present the user with the documentation plan "
            "and IMMEDIATELY proceed with implementing the documentation without requiring further "
            "consultation. Focus on the precise documentation improvements needed."
        )

    def get_skip_reason(self) -> str:
        """Docgen-specific skip reason."""
        return "Claude completed comprehensive documentation analysis"

    def get_request_relevant_context(self, request) -> list:
        """Get relevant_context for docgen tool."""
        try:
            return request.relevant_context or []
        except AttributeError:
            return []

    def get_skip_expert_analysis_status(self) -> str:
        """Docgen-specific expert analysis skip status."""
        return "skipped_due_to_complete_analysis"

    def prepare_work_summary(self) -> str:
        """Docgen-specific work summary."""
        try:
            return f"Completed {len(self.work_history)} documentation analysis steps"
        except AttributeError:
            return "Completed documentation analysis"

    def get_completion_next_steps_message(self, expert_analysis_used: bool = False) -> str:
        """
        Docgen-specific completion message.
        """
        return (
            "DOCUMENTATION ANALYSIS IS COMPLETE. YOU MUST now summarize and present ALL key findings, "
            "identified documentation needs, and recommended documentation improvements. Clearly identify "
            "functions/methods that need documentation, specify the documentation style to use, and provide "
            "concrete examples of improved documentation including complexity analysis and call flow information. "
            "Make it easy for a developer to understand exactly what documentation is needed and how to implement it."
        )

    def get_step_guidance_message(self, request) -> str:
        """
        Docgen-specific step guidance with detailed analysis instructions.
        """
        step_guidance = self.get_step_guidance(request.step_number, request.confidence, request)
        return step_guidance["next_steps"]

    def customize_workflow_response(self, response_data: dict, request) -> dict:
        """
        Customize response to match docgen tool format.
        """
        # Store initial request on first step
        if request.step_number == 1:
            self.initial_request = request.step

        # Convert generic status names to docgen-specific ones
        tool_name = self.get_name()
        status_mapping = {
            f"{tool_name}_in_progress": "documentation_analysis_in_progress",
            f"pause_for_{tool_name}": "pause_for_documentation_analysis",
            f"{tool_name}_required": "documentation_analysis_required",
            f"{tool_name}_complete": "documentation_analysis_complete",
        }

        if response_data["status"] in status_mapping:
            response_data["status"] = status_mapping[response_data["status"]]

        # Rename status field to match docgen tool
        if f"{tool_name}_status" in response_data:
            response_data["documentation_analysis_status"] = response_data.pop(f"{tool_name}_status")
            # Add docgen-specific status fields
            response_data["documentation_analysis_status"]["documentation_strategies"] = len(
                self.consolidated_findings.hypotheses
            )

        # Rename complete documentation analysis data
        if f"complete_{tool_name}" in response_data:
            response_data["complete_documentation_analysis"] = response_data.pop(f"complete_{tool_name}")

        # Map the completion flag to match docgen tool
        if f"{tool_name}_complete" in response_data:
            response_data["documentation_analysis_complete"] = response_data.pop(f"{tool_name}_complete")

        # Map the required flag to match docgen tool
        if f"{tool_name}_required" in response_data:
            response_data["documentation_analysis_required"] = response_data.pop(f"{tool_name}_required")

        return response_data

    # Required abstract methods from BaseTool
    def get_request_model(self):
        """Return the docgen-specific request model."""
        return DocgenRequest

    async def prepare_prompt(self, request) -> str:
        """Not used - workflow tools use execute_workflow()."""
        return ""  # Workflow tools use execute_workflow() directly
