"""
Debug tool - Systematic root cause analysis and debugging assistance

This tool provides a structured workflow for investigating complex bugs and issues.
It guides you through systematic investigation steps with forced pauses between each step
to ensure thorough code examination before proceeding. The tool supports backtracking,
hypothesis evolution, and expert analysis integration for comprehensive debugging.

Key features:
- Step-by-step investigation workflow with progress tracking
- Context-aware file embedding (references during investigation, full content for analysis)
- Automatic conversation threading and history preservation
- Expert analysis integration with external models
- Support for visual debugging with image context
- Confidence-based workflow optimization
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_ANALYTICAL
from systemprompts import DEBUG_ISSUE_PROMPT
from tools.shared.base_models import WorkflowRequest

from .workflow.base import WorkflowTool
from .workflow.shared_utilities import (
    ResponseCustomizer,
    WorkflowFieldMapper,
    WorkflowStepProcessor,
    WorkflowUtilities,
)

logger = logging.getLogger(__name__)

# Tool-specific field descriptions using shared utilities base
DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS = WorkflowFieldMapper.map_with_overrides(
    {
        "step": {
            "type": "string",
            "description": (
                "Describe what you're currently investigating by thinking deeply about the issue and its possible causes. "
                "In step 1, clearly state the issue and begin forming an investigative direction after thinking carefully "
                "about the described problem. CRITICAL: Remember that reported symptoms might originate from code far from "
                "where they manifest. Also be aware that after thorough investigation, you might find NO BUG EXISTS - it could "
                "be a misunderstanding or expectation mismatch. Consider not only obvious failures, but also subtle "
                "contributing factors like upstream logic, invalid inputs, missing preconditions, or hidden side effects. "
                "In all later steps, continue exploring with precision: trace deeper dependencies, verify "
                "hypotheses, and adapt your understanding as you uncover more evidence."
            ),
        },
        "findings": {
            "type": "string",
            "description": (
                "Summarize everything discovered in this step. Include new clues, unexpected behavior, evidence from code or "
                "logs, or disproven theories. Be specific and avoid vague language—document what you now know and how it "
                "affects your hypothesis. IMPORTANT: If you find no evidence supporting the reported issue after thorough "
                "investigation, document this clearly. Finding 'no bug' is a valid outcome if the "
                "investigation was comprehensive. In later steps, confirm or disprove past findings with reason."
            ),
        },
        "hypothesis": {
            "type": "string",
            "description": (
                "A concrete theory for what's causing the issue based on the evidence so far. This can include suspected "
                "failures, incorrect assumptions, or violated constraints. VALID HYPOTHESES INCLUDE: 'No bug found - possible "
                "user misunderstanding' or 'Symptoms appear unrelated to any code issue' if evidence supports this. When "
                "no bug is found, consider suggesting: 'Recommend discussing with thought partner/engineering assistant for "
                "clarification of expected behavior.' You are encouraged to revise or abandon hypotheses in later steps as "
                "needed based on evidence."
            ),
        },
        "confidence": {
            "type": "string",
            "enum": ["exploring", "low", "medium", "high", "very_high", "almost_certain", "certain"],
            "description": (
                "Indicate your current confidence in the hypothesis. Use: 'exploring' (starting out), 'low' (early idea), "
                "'medium' (some supporting evidence), 'high' (strong evidence), 'very_high' (very strong evidence), "
                "'almost_certain' (nearly confirmed), 'certain' (100% confidence - root cause and minimal fix are both "
                "confirmed locally with no need for external model validation). Do NOT use 'certain' unless the issue can be "
                "fully resolved with a fix, use 'very_high' or 'almost_certain' instead when not 100% sure. Using 'certain' "
                "means you have complete confidence locally and prevents external model validation."
            ),
        },
    }
)


class DebugInvestigationRequest(WorkflowRequest):
    """Request model for debug investigation steps matching original debug tool exactly"""

    # Required fields for each investigation step
    step: str = Field(..., description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["step"])
    step_number: int = Field(..., description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["step_number"])
    total_steps: int = Field(..., description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["total_steps"])
    next_step_required: bool = Field(..., description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["next_step_required"])

    # Investigation tracking fields
    findings: str = Field(..., description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["findings"])
    files_checked: list[str] = Field(
        default_factory=list, description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["files_checked"]
    )
    relevant_files: list[str] = Field(
        default_factory=list, description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["relevant_files"]
    )
    relevant_context: list[str] = Field(
        default_factory=list, description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["relevant_context"]
    )
    hypothesis: Optional[str] = Field(None, description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["hypothesis"])
    confidence: Optional[str] = Field("low", description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["confidence"])

    # Optional backtracking field
    backtrack_from_step: Optional[int] = Field(
        None, description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["backtrack_from_step"]
    )

    # Optional images for visual debugging
    images: Optional[list[str]] = Field(default=None, description=DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS["images"])

    # Override inherited fields to exclude them from schema (except model which needs to be available)
    temperature: Optional[float] = Field(default=None, exclude=True)
    thinking_mode: Optional[str] = Field(default=None, exclude=True)
    use_websearch: Optional[bool] = Field(default=None, exclude=True)


class DebugIssueTool(WorkflowTool):
    """
    Debug tool for systematic root cause analysis and issue investigation.

    This tool implements a structured debugging workflow that guides users through
    methodical investigation steps, ensuring thorough code examination and evidence
    gathering before reaching conclusions. It supports complex debugging scenarios
    including race conditions, memory leaks, performance issues, and integration problems.
    """

    def __init__(self):
        super().__init__()
        self.initial_issue = None

    def get_name(self) -> str:
        return "debug"

    def get_description(self) -> str:
        return (
            "DEBUG & ROOT CAUSE ANALYSIS - Systematic self-investigation followed by expert analysis. "
            "This tool guides you through a step-by-step investigation process where you:\n\n"
            "1. Start with step 1: describe the issue to investigate\n"
            "2. STOP and investigate using appropriate tools\n"
            "3. Report findings in step 2 with concrete evidence from actual code\n"
            "4. Continue investigating between each debug step\n"
            "5. Track findings, relevant files, and methods throughout\n"
            "6. Update hypotheses as understanding evolves\n"
            "7. Once investigation is complete, receive expert analysis\n\n"
            "IMPORTANT: This tool enforces investigation between steps:\n"
            "- After each debug call, you MUST investigate before calling debug again\n"
            "- Each step must include NEW evidence from code examination\n"
            "- No recursive debug calls without actual investigation work\n"
            "- The tool will specify which step number to use next\n"
            "- Follow the required_actions list for investigation guidance\n\n"
            "Perfect for: complex bugs, mysterious errors, performance issues, "
            "race conditions, memory leaks, integration problems."
        )

    def get_system_prompt(self) -> str:
        return DEBUG_ISSUE_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self) -> "ToolModelCategory":
        """Debug requires deep analysis and reasoning"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.EXTENDED_REASONING

    def get_workflow_request_model(self):
        """Return the debug-specific request model."""
        return DebugInvestigationRequest

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema using WorkflowSchemaBuilder with debug-specific overrides."""
        from .workflow.schema_builders import WorkflowSchemaBuilder

        # Use shared utilities for field mapping
        debug_field_overrides = DEBUG_INVESTIGATION_FIELD_DESCRIPTIONS

        # Use WorkflowSchemaBuilder with debug-specific tool fields
        return WorkflowSchemaBuilder.build_schema(
            tool_specific_fields=debug_field_overrides,
            model_field_schema=self.get_model_field_schema(),
            auto_mode=self.is_effective_auto_mode(),
            tool_name=self.get_name(),
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
        Decide when to call external model using shared utilities.
        """
        # Check if user requested to skip assistant model
        if request and not self.get_request_use_assistant_model(request):
            return False

        # Use shared utility to determine expert analysis usage
        return WorkflowUtilities.should_use_expert_analysis(consolidated_findings, confidence_threshold="certain")

    async def prepare_expert_analysis_context(self, consolidated_findings) -> str:
        """Prepare context for external model call matching original debug tool format."""
        context_parts = [
            f"=== ISSUE DESCRIPTION ===\n{self.initial_issue or 'Investigation initiated'}\n=== END DESCRIPTION ==="
        ]

        # Add special note if confidence is almost_certain
        if consolidated_findings.confidence == "almost_certain":
            context_parts.append(
                "\n=== IMPORTANT: ALMOST CERTAIN CONFIDENCE ===\n"
                "The agent has reached 'almost_certain' confidence but has NOT confirmed the bug with 100% certainty. "
                "Your role is to:\n"
                "1. Validate the agent's hypothesis and investigation\n"
                "2. Identify any missing evidence or overlooked aspects\n"
                "3. Provide additional insights that could confirm or refute the hypothesis\n"
                "4. Help finalize the root cause analysis with complete certainty\n"
                "=== END IMPORTANT ==="
            )

        # Add investigation summary
        investigation_summary = self._build_investigation_summary(consolidated_findings)
        context_parts.append(f"\n=== AGENT'S INVESTIGATION FINDINGS ===\n{investigation_summary}\n=== END FINDINGS ===")

        # Add error context if available
        error_context = self._extract_error_context(consolidated_findings)
        if error_context:
            context_parts.append(f"\n=== ERROR CONTEXT/STACK TRACE ===\n{error_context}\n=== END CONTEXT ===")

        # Add relevant methods/functions if available
        if consolidated_findings.relevant_context:
            methods_text = "\n".join(f"- {method}" for method in consolidated_findings.relevant_context)
            context_parts.append(f"\n=== RELEVANT METHODS/FUNCTIONS ===\n{methods_text}\n=== END METHODS ===")

        # Add hypothesis evolution if available
        if consolidated_findings.hypotheses:
            hypotheses_text = "\n".join(
                f"Step {h['step']} ({h['confidence']} confidence): {h['hypothesis']}"
                for h in consolidated_findings.hypotheses
            )
            context_parts.append(f"\n=== HYPOTHESIS EVOLUTION ===\n{hypotheses_text}\n=== END HYPOTHESES ===")

        # Add images if available
        if consolidated_findings.images:
            images_text = "\n".join(f"- {img}" for img in consolidated_findings.images)
            context_parts.append(
                f"\n=== VISUAL DEBUGGING INFORMATION ===\n{images_text}\n=== END VISUAL INFORMATION ==="
            )

        # Add file content if we have relevant files
        if consolidated_findings.relevant_files:
            file_content, _ = await self._prepare_file_content_for_prompt(
                list(consolidated_findings.relevant_files), None, "Essential debugging files"
            )
            if file_content:
                context_parts.append(
                    f"\n=== ESSENTIAL FILES FOR DEBUGGING ===\n{file_content}\n=== END ESSENTIAL FILES ==="
                )

        return "\n".join(context_parts)

    def _build_investigation_summary(self, consolidated_findings) -> str:
        """Prepare a comprehensive summary using shared utilities."""
        return WorkflowUtilities.build_expert_context_summary(consolidated_findings, self.get_name())

    def _extract_error_context(self, consolidated_findings) -> Optional[str]:
        """Extract error context from investigation findings."""
        error_patterns = ["error", "exception", "stack trace", "traceback", "failure"]
        error_context_parts = []

        for finding in consolidated_findings.findings:
            if any(pattern in finding.lower() for pattern in error_patterns):
                error_context_parts.append(finding)

        return "\n".join(error_context_parts) if error_context_parts else None

    # Hook method overrides for debug-specific behavior

    def prepare_step_data(self, request) -> dict:
        """
        Prepare debug-specific step data using shared utilities.
        """
        step_data = WorkflowStepProcessor.process_step_data(request, self.get_name())

        # Debug-specific adjustments - ensure hypothesis and confidence are preserved
        step_data["hypothesis"] = request.hypothesis
        step_data["confidence"] = request.confidence
        step_data["issues_found"] = []  # Debug tool doesn't use issues_found field

        return step_data

    def should_skip_expert_analysis(self, request, consolidated_findings) -> bool:
        """
        Debug tool skips expert analysis when agent has "certain" confidence.
        """
        return request.confidence == "certain" and not request.next_step_required

    # Override inheritance hooks for debug-specific behavior

    def get_completion_status(self) -> str:
        """Debug tools use debug-specific status."""
        return "certain_confidence_proceed_with_fix"

    def get_completion_data_key(self) -> str:
        """Debug uses 'complete_investigation' key."""
        return "complete_investigation"

    def get_final_analysis_from_request(self, request):
        """Debug tools use 'hypothesis' field."""
        return request.hypothesis

    def get_confidence_level(self, request) -> str:
        """Debug tools use 'certain' for high confidence."""
        return "certain"

    def get_completion_message(self) -> str:
        """Debug-specific completion message."""
        return (
            "Investigation complete with CERTAIN confidence. You have identified the exact "
            "root cause and a minimal fix. MANDATORY: Present the user with the root cause analysis "
            "and IMMEDIATELY proceed with implementing the simple fix without requiring further "
            "consultation. Focus on the precise, minimal change needed."
        )

    def get_skip_reason(self) -> str:
        """Debug-specific skip reason."""
        return "Identified exact root cause with minimal fix requirement locally"

    def get_request_relevant_context(self, request) -> list:
        """Get relevant_context for debug tool."""
        try:
            return request.relevant_context or []
        except AttributeError:
            return []

    def get_skip_expert_analysis_status(self) -> str:
        """Debug-specific expert analysis skip status."""
        return "skipped_due_to_certain_confidence"

    def prepare_work_summary(self) -> str:
        """Debug-specific work summary."""
        return self._build_investigation_summary(self.consolidated_findings)

    def get_completion_next_steps_message(self, expert_analysis_used: bool = False) -> str:
        """
        Debug-specific completion message.

        Args:
            expert_analysis_used: True if expert analysis was successfully executed
        """
        base_message = (
            "INVESTIGATION IS COMPLETE. YOU MUST now summarize and present ALL key findings, confirmed "
            "hypotheses, and exact recommended fixes. Clearly identify the most likely root cause and "
            "provide concrete, actionable implementation guidance. Highlight affected code paths and display "
            "reasoning that led to this conclusion—make it easy for a developer to understand exactly where "
            "the problem lies. Where necessary, show cause-and-effect / bug-trace call graph."
        )

        # Add expert analysis guidance only when expert analysis was actually used
        if expert_analysis_used:
            expert_guidance = self.get_expert_analysis_guidance()
            if expert_guidance:
                return f"{base_message}\n\n{expert_guidance}"

        return base_message

    def get_expert_analysis_guidance(self) -> str:
        """
        Get additional guidance for handling expert analysis results in debug context.

        Returns:
            Additional guidance text for validating and using expert analysis findings
        """
        return (
            "IMPORTANT: Expert debugging analysis has been provided above. You MUST validate "
            "the expert's root cause analysis and proposed fixes against your own investigation. "
            "Ensure the expert's findings align with the evidence you've gathered and that the "
            "recommended solutions address the actual problem, not just symptoms. If the expert "
            "suggests a different root cause than you identified, carefully consider both perspectives "
            "and present a balanced assessment to the user."
        )

    def get_step_guidance_message(self, request) -> str:
        """
        Debug-specific step guidance using shared utilities.
        """
        required_actions = self.get_required_actions(
            request.step_number, request.confidence, request.findings, request.total_steps
        )
        return WorkflowUtilities.generate_step_guidance_message(
            request.step_number, request.confidence, self.get_name(), required_actions
        )

    def customize_workflow_response(self, response_data: dict, request) -> dict:
        """
        Customize response using shared utilities.
        """
        # Store initial issue on first step
        if request.step_number == 1:
            self.initial_issue = request.step

        # Use shared utilities for response customization
        status_mappings = ResponseCustomizer.get_standard_status_mappings(self.get_name())

        # Add debug-specific status data
        additional_data = {}
        if hasattr(self, "consolidated_findings") and self.consolidated_findings:
            if f"{self.get_name()}_status" in response_data:
                additional_data["investigation_status"] = {
                    "hypotheses_formed": len(getattr(self.consolidated_findings, "hypotheses", [])),
                }

        return ResponseCustomizer.customize_response(response_data, self.get_name(), status_mappings, additional_data)

    # Required abstract methods from BaseTool
    def get_request_model(self):
        """Return the debug-specific request model."""
        return DebugInvestigationRequest

    async def prepare_prompt(self, request) -> str:
        """Not used - workflow tools use execute_workflow()."""
        return ""  # Workflow tools use execute_workflow() directly
