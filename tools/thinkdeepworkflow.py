"""
ThinkDeep Workflow tool - Step-by-step deep thinking and analysis with expert validation

This tool provides a structured workflow for comprehensive deep thinking and analysis.
It guides Claude through systematic thinking steps with forced pauses between each step
to ensure thorough consideration, analysis, and exploration before proceeding.
The tool supports complex analytical scenarios including architecture decisions,
problem solving, strategic planning, and comprehensive evaluation.

Key features:
- Step-by-step deep thinking workflow with progress tracking
- Context-aware file embedding (references during thinking, full content for analysis)
- Automatic thinking progression and hypothesis evolution
- Expert analysis integration with external models
- Support for focused analysis areas (architecture, performance, security, etc.)
- Confidence-based workflow optimization
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field, model_validator

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_CREATIVE
from systemprompts import THINKDEEP_PROMPT
from tools.shared.base_models import WorkflowRequest

from .workflow.base import WorkflowTool

logger = logging.getLogger(__name__)

# Tool-specific field descriptions for thinkdeep workflow
THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS = {
    "step": (
        "Describe what you're currently thinking about and analyzing by deeply considering the problem, question, or "
        "challenge at hand. In step 1, clearly state your thinking plan and begin forming a systematic approach after "
        "thinking carefully about what needs to be analyzed. CRITICAL: Remember to thoroughly explore different "
        "perspectives, consider pros and cons, examine assumptions, explore alternatives, and think through implications. "
        "Consider not only obvious solutions but also creative approaches, potential risks, edge cases, and ways to "
        "improve or refine ideas. Map out the problem space, understand the constraints, and identify areas requiring "
        "deeper analysis - but DO NOT overengineer. The best solutions are sometimes the simplest approaches. Breaking"
        "down ideas and simplifying larger problems can yield better results. In all later steps, continue exploring "
        "with precision: challenge your assumptions, verify your reasoning, and adapt your understanding as you "
        "uncover new insights."
    ),
    "step_number": (
        "The index of the current step in the thinking sequence, beginning at 1. Each step should build upon or "
        "revise the previous one."
    ),
    "total_steps": (
        "Your current estimate for how many steps will be needed to complete the deep thinking analysis. "
        "Adjust as new insights emerge."
    ),
    "next_step_required": (
        "Set to true if you plan to continue the thinking analysis with another step. False means you believe the "
        "deep thinking analysis is complete and ready for expert validation."
    ),
    "findings": (
        "Summarize everything you've discovered and analyzed in this step about the problem or question. Include "
        "insights, observations, pros and cons, alternative approaches, potential risks, assumptions challenged, "
        "and any new understanding gained. Be specific and avoid vague language—document what you now know and how "
        "it affects your overall analysis. IMPORTANT: Document both positive findings (good approaches, strong "
        "solutions, valid assumptions) and concerns (potential issues, risks, weaknesses, gaps in thinking). "
        "In later steps, confirm or update past findings with additional analysis."
    ),
    "files_checked": (
        "List all files (as absolute paths, do not clip or shrink file names) examined during the thinking analysis "
        "so far (where applicable). Include even files ruled out or found to be unrelated, as this tracks your "
        "exploration path."
    ),
    "relevant_files": (
        "Subset of files_checked (as full absolute paths) that contain information directly relevant to the thinking "
        "analysis or contain significant patterns, examples, or context worth highlighting. Only list those that are "
        "directly tied to important insights, solutions, or analysis areas. This could include reference materials, "
        "code examples, configuration files, or documentation relevant to the thinking process."
    ),
    "relevant_context": (
        "List concepts, methods, functions, approaches, or frameworks that are central to the thinking analysis, "
        "in formats like 'ConceptName', 'method.approach', or 'framework.pattern'. Prioritize those that are key "
        "to the analysis, represent important alternatives, or demonstrate significant insights."
    ),
    "issues_found": (
        "List of concerns, risks, or problems identified during the analysis. Each issue should be a dictionary with "
        "'severity' (critical, high, medium, low) and 'description' fields. Include potential risks, assumptions that "
        "may be flawed, gaps in reasoning, overlooked considerations, implementation challenges, etc."
    ),
    "confidence": (
        "Indicate your current confidence in the thinking analysis. Use: 'exploring' (starting analysis), 'low' (early "
        "thinking), 'medium' (some insights gathered), 'high' (strong analysis), 'certain' (only when the thinking "
        "analysis is thoroughly complete and all major aspects are considered). Do NOT use 'certain' unless the "
        "deep thinking is comprehensively complete, use 'high' instead when not 100% sure. Using 'certain' prevents "
        "additional expert analysis."
    ),
    "backtrack_from_step": (
        "If an earlier finding or line of thinking needs to be revised or discarded, specify the step number from "
        "which to start over. Use this to acknowledge thinking dead ends and correct the analytical course."
    ),
    "images": (
        "Optional list of absolute paths to diagrams, charts, mockups, or visual references that help with the "
        "thinking analysis. Only include if they materially assist understanding or analysis."
    ),
    "problem_context": (
        "Additional context about the problem or goal. Be as expressive as possible. More information will be very "
        "helpful for comprehensive analysis."
    ),
    "focus_areas": "Specific aspects to focus on (architecture, performance, security, user experience, etc.)",
}


class ThinkDeepWorkflowRequest(WorkflowRequest):
    """Request model for thinkdeep workflow thinking steps"""

    # Required fields for each thinking step
    step: str = Field(..., description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["step"])
    step_number: int = Field(..., description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["step_number"])
    total_steps: int = Field(..., description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["total_steps"])
    next_step_required: bool = Field(..., description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["next_step_required"])

    # Thinking tracking fields
    findings: str = Field(..., description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["findings"])
    files_checked: list[str] = Field(
        default_factory=list, description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["files_checked"]
    )
    relevant_files: list[str] = Field(
        default_factory=list, description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["relevant_files"]
    )
    relevant_context: list[str] = Field(
        default_factory=list, description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["relevant_context"]
    )
    issues_found: list[dict] = Field(
        default_factory=list, description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["issues_found"]
    )
    confidence: Optional[str] = Field("low", description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["confidence"])

    # Optional backtracking field
    backtrack_from_step: Optional[int] = Field(
        None, description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["backtrack_from_step"]
    )

    # Optional images for visual analysis
    images: Optional[list[str]] = Field(default=None, description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["images"])

    # ThinkDeep-specific fields (only used in step 1 to initialize)
    files: Optional[list[str]] = Field(
        None,
        description="Optional absolute file paths or directories for additional context (must be FULL absolute paths to real files / folders - DO NOT SHORTEN)",
    )
    problem_context: Optional[str] = Field(None, description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["problem_context"])
    focus_areas: Optional[list[str]] = Field(None, description=THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["focus_areas"])

    # Keep these fields available for configuring the final assistant model in expert analysis
    temperature: Optional[float] = Field(default=None)
    thinking_mode: Optional[str] = Field(default=None)
    use_websearch: Optional[bool] = Field(default=None)


class ThinkDeepWorkflowTool(WorkflowTool):
    """
    ThinkDeep workflow tool for step-by-step deep thinking and expert analysis.

    This tool implements a structured deep thinking workflow that guides users through
    methodical thinking steps, ensuring thorough analysis, consideration of alternatives,
    and comprehensive evaluation before reaching conclusions. It supports complex analytical
    scenarios including architecture decisions, problem solving, strategic planning,
    and performance optimization.
    """

    def __init__(self):
        super().__init__()
        self.initial_request = None
        self.thinking_config = {}
        self.stored_request_params = {}

    def get_name(self) -> str:
        return "thinkdeepworkflow"

    def get_description(self) -> str:
        return (
            "COMPREHENSIVE DEEP THINKING WORKFLOW - Step-by-step thinking and analysis with expert validation. "
            "This tool guides you through a systematic thinking process where you:\\n\\n"
            "1. Start with step 1: describe your deep thinking plan\\n"
            "2. STOP and do your own deep thinking, analysis, and exploration\\n"
            "3. Report findings in step 2 with concrete insights from actual thinking\\n"
            "4. Continue thinking between each step\\n"
            "5. Track insights, relevant context, and considerations throughout\\n"
            "6. Update analysis as understanding evolves\\n"
            "7. Once thinking is complete, receive expert analysis\\n\\n"
            "IMPORTANT: This tool enforces thinking between steps:\\n"
            "- After each call, you MUST think deeply before calling again\\n"
            "- Each step must include NEW insights from actual analysis\\n"
            "- No recursive calls without actual thinking work\\n"
            "- The tool will specify which step number to use next\\n"
            "- Follow the required_actions list for thinking guidance\\n\\n"
            "Perfect for: architecture decisions, complex problem solving, strategic planning, "
            "comprehensive analysis, alternative evaluation, risk assessment."
        )

    def get_system_prompt(self) -> str:
        return THINKDEEP_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_CREATIVE

    def get_model_category(self) -> "ToolModelCategory":
        """ThinkDeep workflow requires extended reasoning capabilities"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.EXTENDED_REASONING

    def get_workflow_request_model(self):
        """Return the thinkdeep workflow-specific request model."""
        return ThinkDeepWorkflowRequest

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema using WorkflowSchemaBuilder with thinkdeep-specific overrides."""
        from .workflow.schema_builders import WorkflowSchemaBuilder

        # ThinkDeep workflow-specific field overrides
        thinkdeep_field_overrides = {
            "step": {
                "type": "string",
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["step"],
            },
            "step_number": {
                "type": "integer",
                "minimum": 1,
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["step_number"],
            },
            "total_steps": {
                "type": "integer",
                "minimum": 1,
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["total_steps"],
            },
            "next_step_required": {
                "type": "boolean",
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["next_step_required"],
            },
            "findings": {
                "type": "string",
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["findings"],
            },
            "files_checked": {
                "type": "array",
                "items": {"type": "string"},
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["files_checked"],
            },
            "relevant_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["relevant_files"],
            },
            "confidence": {
                "type": "string",
                "enum": ["exploring", "low", "medium", "high", "certain"],
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["confidence"],
            },
            "backtrack_from_step": {
                "type": "integer",
                "minimum": 1,
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["backtrack_from_step"],
            },
            "issues_found": {
                "type": "array",
                "items": {"type": "object"},
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["issues_found"],
            },
            "images": {
                "type": "array",
                "items": {"type": "string"},
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["images"],
            },
            # ThinkDeep-specific fields (for step 1)
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional absolute file paths or directories for additional context (must be FULL absolute paths to real files / folders - DO NOT SHORTEN)",
            },
            "problem_context": {
                "type": "string",
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["problem_context"],
            },
            "focus_areas": {
                "type": "array",
                "items": {"type": "string"},
                "description": THINKDEEP_WORKFLOW_FIELD_DESCRIPTIONS["focus_areas"],
            },
            # Expert analysis configuration parameters
            "temperature": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Temperature for expert analysis model (0-1, default 0.7)",
            },
            "thinking_mode": {
                "type": "string",
                "enum": ["minimal", "low", "medium", "high", "max"],
                "description": "Thinking depth for expert analysis: minimal (0.5% of model max), low (8%), medium (33%), high (67%), max (100% of model max)",
            },
            "use_websearch": {
                "type": "boolean",
                "description": "Enable web search for expert analysis to access current information and best practices",
            },
        }

        # Use WorkflowSchemaBuilder with thinkdeep-specific tool fields
        return WorkflowSchemaBuilder.build_schema(
            tool_specific_fields=thinkdeep_field_overrides,
            model_field_schema=self.get_model_field_schema(),
            auto_mode=self.is_effective_auto_mode(),
            tool_name=self.get_name(),
        )

    def get_required_actions(self, step_number: int, confidence: str, findings: str, total_steps: int) -> list[str]:
        """Define required actions for each thinking phase."""
        if step_number == 1:
            # Initial deep thinking tasks
            return [
                "Think deeply about the problem, question, or challenge at hand",
                "Consider multiple perspectives and approaches to understanding the issue",
                "Examine your assumptions and identify areas that need deeper analysis",
                "Explore potential solutions or approaches, considering their pros and cons",
                "Identify what you don't know or what requires further investigation",
                "Read any relevant files or context that could inform your thinking",
            ]
        elif confidence in ["exploring", "low"]:
            # Need deeper thinking
            return [
                "Dive deeper into the specific aspects you've identified as important",
                "Challenge your initial assumptions and explore alternative viewpoints",
                "Consider edge cases, potential risks, and failure modes",
                "Analyze trade-offs between different approaches or solutions",
                "Look for patterns, precedents, or similar problems that could inform your thinking",
                "Examine any relevant code, documentation, or context files more thoroughly",
            ]
        elif confidence in ["medium", "high"]:
            # Close to completion - need final verification
            return [
                "Verify that your analysis is comprehensive and considers all major aspects",
                "Double-check your reasoning and ensure your conclusions are well-supported",
                "Consider any remaining risks, gaps, or areas that need attention",
                "Validate that your proposed solutions or recommendations are practical",
                "Ensure you've addressed the original problem or question thoroughly",
                "Review all insights and considerations to ensure nothing important is missed",
            ]
        else:
            # General thinking needed
            return [
                "Continue your deep analysis of the problem or question",
                "Gather more insights using appropriate thinking and analysis techniques",
                "Test your assumptions and validate your reasoning",
                "Look for additional perspectives that could enhance your understanding",
                "Focus on areas that haven't been thoroughly analyzed yet",
            ]

    def should_call_expert_analysis(self, consolidated_findings, request=None) -> bool:
        """
        Decide when to call external model based on thinking completeness.

        Always call expert analysis for thinkdeep workflow unless explicitly disabled.
        """
        # Check if user requested to skip assistant model
        if request and not self.get_request_use_assistant_model(request):
            return False

        # For thinkdeep workflow, we almost always want expert analysis
        # since the goal is to get Claude's thinking validated and extended
        return True

    def prepare_expert_analysis_context(self, consolidated_findings) -> str:
        """Prepare context for external model call for final thinking analysis validation."""
        context_parts = [
            f"=== DEEP THINKING REQUEST ===\\n{self.initial_request or 'Deep thinking workflow initiated'}\\n=== END REQUEST ==="
        ]

        # Add thinking summary
        thinking_summary = self._build_thinking_summary(consolidated_findings)
        context_parts.append(
            f"\\n=== CLAUDE'S DEEP THINKING ANALYSIS ===\\n{thinking_summary}\\n=== END THINKING ==="
        )

        # Add thinking configuration context if available
        if self.thinking_config:
            config_text = "\\n".join(f"- {key}: {value}" for key, value in self.thinking_config.items() if value)
            context_parts.append(f"\\n=== THINKING CONFIGURATION ===\\n{config_text}\\n=== END CONFIGURATION ===")

        # Add relevant concepts/context if available
        if consolidated_findings.relevant_context:
            concepts_text = "\\n".join(f"- {concept}" for concept in consolidated_findings.relevant_context)
            context_parts.append(f"\\n=== RELEVANT CONCEPTS/APPROACHES ===\\n{concepts_text}\\n=== END CONCEPTS ===")

        # Add concerns/issues found if available
        if consolidated_findings.issues_found:
            issues_text = "\\n".join(
                f"[{issue.get('severity', 'unknown').upper()}] {issue.get('description', 'No description')}"
                for issue in consolidated_findings.issues_found
            )
            context_parts.append(f"\\n=== CONCERNS IDENTIFIED ===\\n{issues_text}\\n=== END CONCERNS ===")

        # Add thinking evolution if available
        if consolidated_findings.hypotheses:
            thinking_evolution_text = "\\n".join(
                f"Step {h['step']} ({h['confidence']} confidence): {h['hypothesis']}"
                for h in consolidated_findings.hypotheses
            )
            context_parts.append(f"\\n=== THINKING EVOLUTION ===\\n{thinking_evolution_text}\\n=== END EVOLUTION ===")

        # Add images if available
        if consolidated_findings.images:
            images_text = "\\n".join(f"- {img}" for img in consolidated_findings.images)
            context_parts.append(
                f"\\n=== VISUAL ANALYSIS INFORMATION ===\\n{images_text}\\n=== END VISUAL INFORMATION ==="
            )

        return "\\n".join(context_parts)

    def _build_thinking_summary(self, consolidated_findings) -> str:
        """Prepare a comprehensive summary of the deep thinking analysis."""
        summary_parts = [
            "=== SYSTEMATIC DEEP THINKING ANALYSIS SUMMARY ===",
            f"Total thinking steps: {len(consolidated_findings.findings)}",
            f"Files examined: {len(consolidated_findings.files_checked)}",
            f"Relevant files identified: {len(consolidated_findings.relevant_files)}",
            f"Concepts/approaches analyzed: {len(consolidated_findings.relevant_context)}",
            f"Concerns identified: {len(consolidated_findings.issues_found)}",
            "",
            "=== THINKING PROGRESSION ===",
        ]

        for finding in consolidated_findings.findings:
            summary_parts.append(finding)

        return "\\n".join(summary_parts)

    def should_include_files_in_expert_prompt(self) -> bool:
        """Include files in expert analysis for comprehensive thinking validation."""
        return True

    def should_embed_system_prompt(self) -> bool:
        """Embed system prompt in expert analysis for proper context."""
        return True

    def get_expert_thinking_mode(self) -> str:
        """Use high thinking mode for thorough deep thinking analysis."""
        return "high"

    def get_expert_analysis_instruction(self) -> str:
        """Get specific instruction for deep thinking expert analysis."""
        return (
            "Please provide comprehensive analysis and extension of Claude's deep thinking. "
            "Focus on validating the reasoning, identifying any gaps or blind spots, "
            "suggesting alternative approaches, and providing additional insights that could "
            "enhance the analysis. Challenge assumptions where appropriate and provide "
            "constructive critique to improve the overall thinking."
        )

    # Hook method overrides for thinkdeep-specific behavior

    def prepare_step_data(self, request) -> dict:
        """
        Map thinkdeep-specific fields for internal processing.
        """
        step_data = {
            "step": request.step,
            "step_number": request.step_number,
            "findings": request.findings,
            "files_checked": request.files_checked,
            "relevant_files": request.relevant_files,
            "relevant_context": request.relevant_context,
            "issues_found": request.issues_found,
            "confidence": request.confidence,
            "hypothesis": request.findings,  # Map findings to hypothesis for compatibility
            "images": request.images or [],
        }
        return step_data

    def should_skip_expert_analysis(self, request, consolidated_findings) -> bool:
        """
        ThinkDeep workflow skips expert analysis when Claude has "certain" confidence.
        """
        return request.confidence == "certain" and not request.next_step_required

    def store_initial_issue(self, step_description: str):
        """Store initial request for expert analysis."""
        self.initial_request = step_description

    # Override inheritance hooks for thinkdeep-specific behavior

    def get_completion_status(self) -> str:
        """ThinkDeep tools use thinking-specific status."""
        return "deep_thinking_complete_ready_for_implementation"

    def get_completion_data_key(self) -> str:
        """ThinkDeep uses 'complete_thinking' key."""
        return "complete_thinking"

    def get_final_analysis_from_request(self, request):
        """ThinkDeep tools use 'findings' field."""
        return request.findings

    def get_confidence_level(self, request) -> str:
        """ThinkDeep tools use 'certain' for high confidence."""
        return "certain"

    def get_completion_message(self) -> str:
        """ThinkDeep-specific completion message."""
        return (
            "Deep thinking analysis complete with CERTAIN confidence. You have thoroughly analyzed the problem "
            "and explored multiple perspectives. MANDATORY: Present the user with the complete thinking results "
            "and IMMEDIATELY proceed with implementing the best solution or provide specific next steps based "
            "on the analysis. Focus on actionable recommendations from the deep thinking process."
        )

    def get_skip_reason(self) -> str:
        """ThinkDeep-specific skip reason."""
        return "Claude completed comprehensive deep thinking analysis with full confidence"

    def get_skip_expert_analysis_status(self) -> str:
        """ThinkDeep-specific expert analysis skip status."""
        return "skipped_due_to_certain_thinking_confidence"

    def prepare_work_summary(self) -> str:
        """ThinkDeep-specific work summary."""
        return self._build_thinking_summary(self.consolidated_findings)

    def get_completion_next_steps_message(self) -> str:
        """
        ThinkDeep-specific completion message.
        """
        return (
            "DEEP THINKING ANALYSIS IS COMPLETE. You MUST now summarize and present ALL thinking insights, "
            "alternative approaches considered, risks and trade-offs identified, and final recommendations. "
            "Clearly prioritize the top solutions or next steps that emerged from the analysis. "
            "Provide concrete, actionable guidance based on the deep thinking—make it easy for the user to "
            "understand exactly what to do next and how to implement the best solution."
        )
    
    # Override hook methods to use stored request parameters for expert analysis
    
    def get_request_temperature(self, request) -> float:
        """Use stored temperature from initial request."""
        if hasattr(self, 'stored_request_params') and self.stored_request_params.get("temperature") is not None:
            return self.stored_request_params["temperature"]
        return super().get_request_temperature(request)
    
    def get_request_thinking_mode(self, request) -> str:
        """Use stored thinking mode from initial request."""
        if hasattr(self, 'stored_request_params') and self.stored_request_params.get("thinking_mode") is not None:
            return self.stored_request_params["thinking_mode"]
        return super().get_request_thinking_mode(request)
    
    def get_request_use_websearch(self, request) -> bool:
        """Use stored use_websearch from initial request."""
        if hasattr(self, 'stored_request_params') and self.stored_request_params.get("use_websearch") is not None:
            return self.stored_request_params["use_websearch"]
        return super().get_request_use_websearch(request)

    def get_step_guidance_message(self, request) -> str:
        """
        ThinkDeep-specific step guidance with detailed thinking instructions.
        """
        step_guidance = self.get_thinkdeep_step_guidance(request.step_number, request.confidence, request)
        return step_guidance["next_steps"]

    def get_thinkdeep_step_guidance(self, step_number: int, confidence: str, request) -> dict[str, Any]:
        """
        Provide step-specific guidance for thinkdeep workflow.
        """
        # Generate the next steps instruction based on required actions
        required_actions = self.get_required_actions(step_number, confidence, request.findings, request.total_steps)

        if step_number == 1:
            next_steps = (
                f"MANDATORY: DO NOT call the {self.get_name()} tool again immediately. You MUST first think deeply "
                f"about the problem or question using your own analytical capabilities. CRITICAL AWARENESS: You need to "
                f"explore the problem space, consider multiple perspectives, challenge assumptions, think through "
                f"alternatives, and develop comprehensive insights before proceeding. Use your reasoning, any relevant "
                f"files or context, and systematic analysis to gather deep understanding. Only call {self.get_name()} "
                f"again AFTER completing your deep thinking. When you call {self.get_name()} next time, "
                f"use step_number: {step_number + 1} and report specific insights discovered, approaches considered, "
                f"and analytical findings from your thinking process."
            )
        elif confidence in ["exploring", "low"]:
            next_steps = (
                f"STOP! Do NOT call {self.get_name()} again yet. Based on your findings, you've identified areas that need "
                f"deeper thinking. MANDATORY ACTIONS before calling {self.get_name()} step {step_number + 1}:\\n"
                + "\\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
                + f"\\n\\nOnly call {self.get_name()} again with step_number: {step_number + 1} AFTER "
                + "completing this deep thinking work."
            )
        elif confidence in ["medium", "high"]:
            next_steps = (
                f"WAIT! Your thinking analysis needs final validation. DO NOT call {self.get_name()} immediately. REQUIRED ACTIONS:\\n"
                + "\\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
                + f"\\n\\nREMEMBER: Ensure you have thoroughly analyzed the problem from all important angles and "
                f"considered the best solutions. Document your final insights and reasoning, then call {self.get_name()} "
                f"with step_number: {step_number + 1}."
            )
        else:
            next_steps = (
                f"PAUSE THINKING. Before calling {self.get_name()} step {step_number + 1}, you MUST think more deeply about the problem. "
                + "Required: "
                + ", ".join(required_actions[:2])
                + ". "
                + f"Your next {self.get_name()} call (step_number: {step_number + 1}) must include "
                f"NEW insights from actual deep thinking, not just surface-level observations. NO recursive {self.get_name()} calls "
                f"without thinking work!"
            )

        return {"next_steps": next_steps}

    def customize_workflow_response(self, response_data: dict, request) -> dict:
        """
        Customize response to match thinkdeep workflow format.
        """
        # Store initial request on first step
        if request.step_number == 1:
            self.initial_request = request.step
            # Store thinking configuration for expert analysis
            self.thinking_config = {
                "files": getattr(request, "files", None),
                "problem_context": request.problem_context,
                "focus_areas": request.focus_areas,
            }
            # Store request parameters for expert analysis
            self.stored_request_params = {
                "temperature": getattr(request, "temperature", None),
                "thinking_mode": getattr(request, "thinking_mode", None),
                "use_websearch": getattr(request, "use_websearch", None),
            }

        # Convert generic status names to thinkdeep-specific ones
        tool_name = self.get_name()
        status_mapping = {
            f"{tool_name}_in_progress": "thinking_in_progress",
            f"pause_for_{tool_name}": "pause_for_thinking",
            f"{tool_name}_required": "thinking_required",
            f"{tool_name}_complete": "thinking_complete",
        }

        if response_data["status"] in status_mapping:
            response_data["status"] = status_mapping[response_data["status"]]

        # Rename status field to match thinkdeep workflow
        if f"{tool_name}_status" in response_data:
            response_data["thinking_status"] = response_data.pop(f"{tool_name}_status")
            # Add thinkdeep-specific status fields
            response_data["thinking_status"]["insights_generated"] = len(self.consolidated_findings.findings) if hasattr(self, 'consolidated_findings') else 0
            response_data["thinking_status"]["thinking_confidence"] = self.get_request_confidence(request)

        # Map complete_thinkdeepworkflow to complete_thinking
        if f"complete_{tool_name}" in response_data:
            response_data["complete_thinking"] = response_data.pop(f"complete_{tool_name}")

        # Map the completion flag to match thinkdeep workflow
        if f"{tool_name}_complete" in response_data:
            response_data["thinking_complete"] = response_data.pop(f"{tool_name}_complete")

        return response_data

    # Required abstract methods from BaseTool
    def get_request_model(self):
        """Return the thinkdeep workflow-specific request model."""
        return ThinkDeepWorkflowRequest

    async def prepare_prompt(self, request) -> str:
        """Not used - workflow tools use execute_workflow()."""
        return ""  # Workflow tools use execute_workflow() directly