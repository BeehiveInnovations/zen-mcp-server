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
        "approach after thinking carefully about what needs to be documented. Focus on ONE FILE at a time to ensure complete "
        "coverage of all functions and methods within that file. Consider not only missing documentation but also "
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
        "If you discover any glaring, super-critical bugs that could cause serious harm or data corruption, IMMEDIATELY STOP "
        "the documentation workflow and ask the user directly if this critical bug should be addressed first before continuing. "
        "For any other non-critical bugs, flaws, or potential improvements, note them here so they can be surfaced later for review. "
        "In later steps, confirm or update past findings with additional evidence."
    ),
    "doc_files": (
        "List of files with their documentation dependency status. Each entry should be a dictionary with: "
        "'file_path' (relative path), 'functions_documented' (list of functions already documented), "
        "'functions_remaining' (list of functions still needing documentation), "
        "'incoming_deps' (list of files that call into this file), "
        "'outgoing_deps' (list of files this file calls). "
        "This structure allows comprehensive tracking of documentation progress and dependency relationships."
    ),
    "doc_methods": (
        "Granular tracking of individual methods/functions and their documentation status. Each entry should be "
        "a dictionary with: 'method_name' (full qualified name like 'ClassName.method_name'), "
        "'file_path' (relative path to file containing method), "
        "'documented' (boolean indicating if documentation is complete), "
        "'calls_to' (list of other methods this method calls), "
        "'called_by' (list of methods that call this method), "
        "'complexity_analyzed' (boolean indicating if Big O analysis is done). "
        "This enables precise tracking of every function's documentation status."
    ),
    "relevant_files": (
        "Current focus files (as full absolute paths) for this step. In each step, focus on documenting "
        "ONE FILE COMPLETELY before moving to the next. This should contain only the file(s) being "
        "actively documented in the current step, not all files that might need documentation."
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
    doc_files: list[dict] = Field(default_factory=list, description=DOCGEN_FIELD_DESCRIPTIONS["doc_files"])
    doc_methods: list[dict] = Field(default_factory=list, description=DOCGEN_FIELD_DESCRIPTIONS["doc_methods"])
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
            "doc_files": {
                "type": "array",
                "items": {"type": "object"},
                "default": [],
                "description": DOCGEN_FIELD_DESCRIPTIONS["doc_files"],
            },
            "doc_methods": {
                "type": "array",
                "items": {"type": "object"},
                "default": [],
                "description": DOCGEN_FIELD_DESCRIPTIONS["doc_methods"],
            },
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
            "files_checked",  # Documentation uses doc_files and doc_methods instead for better tracking
        ]

        # Exclude common fields that documentation generation doesn't need
        excluded_common_fields = [
            "model",  # Documentation doesn't need external model selection
            "temperature",  # Documentation doesn't need temperature control
            "thinking_mode",  # Documentation doesn't need thinking mode
            "use_websearch",  # Documentation doesn't need web search
            "images",  # Documentation doesn't use images
        ]

        return WorkflowSchemaBuilder.build_schema(
            tool_specific_fields=self.get_tool_fields(),
            required_fields=[],  # No additional required fields beyond workflow defaults
            model_field_schema=None,  # Exclude model field - docgen doesn't need external model selection
            auto_mode=False,  # Force non-auto mode to prevent model field addition
            tool_name=self.get_name(),
            excluded_workflow_fields=excluded_workflow_fields,
            excluded_common_fields=excluded_common_fields,
        )

    def get_required_actions(self, step_number: int, confidence: str, findings: str, total_steps: int) -> list[str]:
        """Define required actions for comprehensive documentation analysis with file-by-file thoroughness."""
        if step_number == 1:
            # Initial discovery and start with first file
            return [
                "Discover ALL files in the current directory (not nested) that need documentation",
                "Choose ONE file to start with and focus COMPLETELY on that file in this step",
                "For the chosen file: identify ALL functions, classes, and methods within it",
                "Begin documenting ALL functions/methods in the chosen file with complete coverage",
                "Track incoming/outgoing dependencies for the chosen file and update doc_files structure",
                "Update doc_methods tracking for every function documented in this step",
            ]
        elif step_number <= 3:
            # Continue with focused file-by-file approach
            return [
                "Complete documentation of ALL remaining functions/methods in the current focus file",
                "Verify that EVERY function in the current file has proper documentation (no skipping)",
                "Update doc_files and doc_methods tracking to reflect completed work",
                "If current file is complete, choose the NEXT file that needs documentation",
                "For the next file: map ALL its functions and begin documenting them systematically",
                "Track dependency relationships between files as you work",
            ]
        else:
            # Continue systematic file-by-file coverage
            return [
                "Focus on ONE file at a time - complete ALL functions in current file before moving on",
                "Document every function, method, and class in the current file with no exceptions",
                "Update doc_methods tracking to show progress on individual function documentation",
                "When current file is 100% complete, move to next file that needs documentation",
                "Trace any nested file dependencies if functions call into subdirectories",
                "Maintain accurate doc_files tracking showing which files are complete vs. in-progress",
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
                f"MANDATORY: DO NOT call the {self.get_name()} tool again immediately. You MUST first perform "
                f"FILE-BY-FILE DOCUMENTATION with systematic tracking. FOCUS ON ONE FILE AT A TIME. "
                f"MANDATORY ACTIONS before calling {self.get_name()} step {step_number + 1}:\n"
                + "\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
                + f"\n\nCRITICAL: Use the new tracking structures - update doc_files with file progress and "
                f"doc_methods with individual function status. Document EVERY function in your chosen file "
                f"before moving to the next. Only call {self.get_name()} again AFTER completing documentation "
                f"of your first chosen file and updating the tracking structures."
            )
        elif step_number <= 3:
            next_steps = (
                f"CONTINUE FILE-BY-FILE APPROACH! Focus on ONE file until 100% complete. "
                f"MANDATORY ACTIONS before calling {self.get_name()} step {step_number + 1}:\n"
                + "\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
                + f"\n\nUpdate doc_files and doc_methods tracking structures to show your progress. "
                f"Do NOT move to a new file until the current one is completely documented. "
                f"When ready for step {step_number + 1}, provide updated tracking data showing completed work."
            )
        else:
            next_steps = (
                f"MAINTAIN FILE-BY-FILE DISCIPLINE! Complete current file before starting new ones. "
                f"REQUIRED ACTIONS before calling {self.get_name()} step {step_number + 1}:\n"
                + "\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
                + f"\n\nYour doc_methods tracking should show which functions are documented vs. remaining. "
                f"Only call {self.get_name()} again after documenting more functions and updating tracking data. "
                f"NO recursive {self.get_name()} calls without actual documentation work!"
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
            "doc_files": request.doc_files,
            "doc_methods": request.doc_methods,
            "relevant_files": request.relevant_files,
            "relevant_context": request.relevant_context,
            "issues_found": [],  # Docgen uses this for documentation gaps
            "confidence": "medium",  # Default confidence for docgen
            "hypothesis": "systematic_documentation_needed",  # Default hypothesis
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
            "DOCUMENTATION ANALYSIS IS COMPLETE. YOU MUST now summarize ALL key findings using the doc_files "
            "and doc_methods tracking data. Present a clear summary showing: 1) Which files are completely "
            "documented vs. partially documented vs. not started, 2) Specific functions/methods documented "
            "vs. remaining (from doc_methods tracking), 3) Dependency relationships discovered between files, "
            "4) Recommended documentation improvements with concrete examples including complexity analysis and "
            "call flow information. Make it easy for a developer to see exactly which functions still need "
            "documentation and what the implementation plan should be."
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
