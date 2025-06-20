"""
Workflow Mixin for Zen MCP Tools

This module provides the workflow-based pattern that enables tools to
perform multi-step work with structured findings and expert analysis.

Key Components:
- BaseWorkflowMixin: Mixin class providing workflow functionality

The workflow pattern enables tools like debug, precommit, and codereview
to perform systematic multi-step work with pause/resume capabilities.
"""

import json
import logging
from abc import abstractmethod
from typing import Any, Optional

from mcp.types import TextContent

from utils.conversation_memory import add_turn, create_thread

from ..shared.base_models import ConsolidatedFindings

logger = logging.getLogger(__name__)


class BaseWorkflowMixin:
    """
    Mixin providing guided workflow functionality for tools.

    This mixin implements the sophisticated workflow pattern from the debug tool,
    where Claude performs systematic local work before calling external models
    for expert analysis. Tools can inherit from this mixin to gain workflow capabilities.

    NOTE: This mixin expects to be used with BaseTool and requires the following methods:
    - get_model_provider(model_name)
    - _resolve_model_context(arguments, request)
    - get_system_prompt()
    - get_default_temperature()
    - _prepare_file_content_for_prompt()
    """

    def __init__(self):
        super().__init__()
        self.work_history = []
        self.consolidated_findings = ConsolidatedFindings()
        self.initial_request = None

    # Abstract methods each workflow tool must implement

    # Abstract methods that must be provided by BaseTool or implementing class

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this tool. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def get_workflow_request_model(self):
        """Return the request model class for this workflow tool."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this tool. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def get_default_temperature(self) -> float:
        """Return the default temperature for this tool. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def get_model_provider(self, model_name: str):
        """Get model provider for the given model. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def _resolve_model_context(self, arguments: dict, request):
        """Resolve model context from arguments. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def _prepare_file_content_for_prompt(self, files: list, request, description: str):
        """Prepare file content for prompts. Usually provided by BaseTool."""
        pass

    # Abstract methods each workflow tool must implement

    @abstractmethod
    def get_work_steps(self, request) -> list[str]:
        """Define tool-specific work steps and criteria"""
        pass

    @abstractmethod
    def get_required_actions(self, step_number: int, confidence: str, findings: str, total_steps: int) -> list[str]:
        """Define required actions for each work phase.

        Args:
            step_number: Current step (1-based)
            confidence: Current confidence level (exploring, low, medium, high, certain)
            findings: Current findings text
            total_steps: Total estimated steps for this work

        Returns:
            List of specific actions Claude should take before calling tool again
        """
        pass

    def should_call_expert_analysis(self, consolidated_findings: ConsolidatedFindings) -> bool:
        """
        Decide when to call external model based on tool-specific criteria.

        Default implementation for tools that don't use expert analysis.
        Override this for tools that do use expert analysis.
        """
        if not self.requires_expert_analysis():
            return False

        # Default logic for tools that support expert analysis
        return (
            len(consolidated_findings.relevant_files) > 0
            or len(consolidated_findings.findings) >= 2
            or len(consolidated_findings.issues_found) > 0
        )

    def prepare_expert_analysis_context(self, consolidated_findings: ConsolidatedFindings) -> str:
        """
        Prepare context for external model call.

        Default implementation for tools that don't use expert analysis.
        Override this for tools that do use expert analysis.
        """
        if not self.requires_expert_analysis():
            return ""

        # Default context preparation
        context_parts = [
            f"=== {self.get_name().upper()} WORK SUMMARY ===",
            f"Total steps: {len(consolidated_findings.findings)}",
            f"Files examined: {len(consolidated_findings.files_checked)}",
            f"Relevant files: {len(consolidated_findings.relevant_files)}",
            "",
            "=== WORK PROGRESSION ===",
        ]

        for finding in consolidated_findings.findings:
            context_parts.append(finding)

        return "\n".join(context_parts)

    def requires_expert_analysis(self) -> bool:
        """
        Override this to completely disable expert analysis for the tool.

        Returns True if the tool supports expert analysis (default).
        Returns False if the tool is self-contained (like planner).
        """
        return True

    def should_include_files_in_expert_prompt(self) -> bool:
        """
        Whether to include file content in the expert analysis prompt.
        Override this to return True if your tool needs files in the prompt.
        """
        return False

    def should_embed_system_prompt(self) -> bool:
        """
        Whether to embed the system prompt in the main prompt.
        Override this to return True if your tool needs the system prompt embedded.
        """
        return False

    def get_expert_thinking_mode(self) -> str:
        """
        Get the thinking mode for expert analysis.
        Override this to customize the thinking mode.
        """
        return "high"

    def get_expert_analysis_instruction(self) -> str:
        """
        Get the instruction to append after the expert context.
        Override this to provide tool-specific instructions.
        """
        return "Please provide expert analysis based on the investigation findings."

    def get_step_guidance_message(self, request) -> str:
        """
        Get step guidance message. Override for tool-specific guidance.
        Default implementation uses required actions.
        """
        required_actions = self.get_required_actions(
            request.step_number, self.get_request_confidence(request),
            request.findings, request.total_steps
        )

        next_step_number = request.step_number + 1
        return (
            f"MANDATORY: DO NOT call the {self.get_name()} tool again immediately. "
            f"You MUST first work using appropriate tools. "
            f"REQUIRED ACTIONS before calling {self.get_name()} step {next_step_number}:\n"
            + "\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
            + f"\n\nOnly call {self.get_name()} again with step_number: {next_step_number} "
            f"AFTER completing this work."
        )

    def _prepare_files_for_expert_analysis(self) -> str:
        """
        Prepare file content for inclusion in expert analysis.
        Override this to customize how files are prepared.
        """
        if not self.consolidated_findings.relevant_files:
            return ""

        # Use BaseTool's file preparation method
        file_content, _ = self._prepare_file_content_for_prompt(
            list(self.consolidated_findings.relevant_files), None, "Essential files for analysis"
        )
        return file_content

    def _add_files_to_expert_context(self, expert_context: str, file_content: str) -> str:
        """
        Add file content to the expert context.
        Override this to customize how files are added to the context.
        """
        return f"{expert_context}\n\n=== ESSENTIAL FILES ===\n{file_content}\n=== END ESSENTIAL FILES ==="


    # Shared workflow methods

    async def execute_workflow(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Main workflow orchestration following debug tool pattern.

        Comprehensive workflow implementation that handles all common patterns:
        1. Request validation and step management
        2. Continuation and backtracking support
        3. Step data processing and consolidation
        4. Tool-specific field mapping and customization
        5. Completion logic with optional expert analysis
        6. Generic "certain confidence" handling
        7. Step guidance and required actions
        8. Conversation memory integration
        """
        from mcp.types import TextContent

        try:
            # Store arguments for access by helper methods
            self._current_arguments = arguments

            # Validate request using tool-specific model
            request = self.get_workflow_request_model()(**arguments)

            # Adjust total steps if needed
            if request.step_number > request.total_steps:
                request.total_steps = request.step_number

            # Handle continuation
            continuation_id = request.continuation_id

            # Create thread for first step
            if not continuation_id and request.step_number == 1:
                clean_args = {k: v for k, v in arguments.items() if k not in ["_model_context", "_resolved_model_name"]}
                continuation_id = create_thread(self.get_name(), clean_args)
                self.initial_request = request.step
                # Allow tools to store initial description for expert analysis
                self.store_initial_issue(request.step)

            # Handle backtracking if requested
            backtrack_step = self.get_backtrack_step(request)
            if backtrack_step:
                self._handle_backtracking(backtrack_step)

            # Process work step - allow tools to customize field mapping
            step_data = self.prepare_step_data(request)

            # Store in history
            self.work_history.append(step_data)

            # Update consolidated findings
            self._update_consolidated_findings(step_data)

            # Build response with tool-specific customization
            response_data = self.build_base_response(request, continuation_id)

            # If work is complete, handle completion logic
            if not request.next_step_required:
                response_data = await self.handle_work_completion(response_data, request, arguments)
            else:
                # Force Claude to work before calling tool again
                response_data = self.handle_work_continuation(response_data, request)

            # Allow tools to customize the final response
            response_data = self.customize_workflow_response(response_data, request)

            # Store in conversation memory
            if continuation_id:
                self.store_conversation_turn(continuation_id, response_data, request)

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]

        except Exception as e:
            logger.error(f"Error in {self.get_name()} work: {e}", exc_info=True)
            error_data = {
                "status": f"{self.get_name()}_failed",
                "error": str(e),
                "step_number": arguments.get("step_number", 0),
            }
            return [TextContent(type="text", text=json.dumps(error_data, indent=2))]

    # Hook methods for tool customization

    def prepare_step_data(self, request) -> dict:
        """
        Prepare step data from request. Tools can override to customize field mapping.

        For example, debug tool maps relevant_methods to relevant_context.
        """
        step_data = {
            "step": request.step,
            "step_number": request.step_number,
            "findings": request.findings,
            "files_checked": request.files_checked,
            "relevant_files": request.relevant_files,
            "relevant_context": self.get_request_relevant_context(request),
            "issues_found": self.get_request_issues_found(request),
            "confidence": self.get_request_confidence(request),
            "hypothesis": self.get_request_hypothesis(request),
            "images": self.get_request_images(request),
        }
        return step_data

    def build_base_response(self, request, continuation_id: str = None) -> dict:
        """
        Build the base response structure. Tools can override for custom response fields.
        """
        response_data = {
            "status": f"{self.get_name()}_in_progress",
            "step_number": request.step_number,
            "total_steps": request.total_steps,
            "next_step_required": request.next_step_required,
            f"{self.get_name()}_status": {
                "files_checked": len(self.consolidated_findings.files_checked),
                "relevant_files": len(self.consolidated_findings.relevant_files),
                "relevant_context": len(self.consolidated_findings.relevant_context),
                "issues_found": len(self.consolidated_findings.issues_found),
                "images_collected": len(self.consolidated_findings.images),
                "current_confidence": self.get_request_confidence(request),
            },
        }

        if continuation_id:
            response_data["continuation_id"] = continuation_id

        return response_data

    def should_skip_expert_analysis(self, request, consolidated_findings) -> bool:
        """
        Determine if expert analysis should be skipped due to high certainty.

        Default: False (always call expert analysis)
        Override in tools like debug to check for "certain" confidence.
        """
        return False

    def handle_completion_without_expert_analysis(self, request, consolidated_findings) -> dict:
        """
        Handle completion when skipping expert analysis.

        Tools can override this for custom high-confidence completion handling.
        Default implementation provides generic response.
        """
        work_summary = self.prepare_work_summary()

        return {
            "status": self.get_completion_status(),
            f"complete_{self.get_name()}": {
                "initial_request": self.get_initial_request(request.step),
                "steps_taken": len(consolidated_findings.findings),
                "files_examined": list(consolidated_findings.files_checked),
                "relevant_files": list(consolidated_findings.relevant_files),
                "relevant_context": list(consolidated_findings.relevant_context),
                "work_summary": work_summary,
                "final_analysis": self.get_final_analysis_from_request(request),
                "confidence_level": self.get_confidence_level(request),
            },
            "next_steps": self.get_completion_message(),
            "skip_expert_analysis": True,
            "expert_analysis": {
                "status": self.get_skip_expert_analysis_status(),
                "reason": self.get_skip_reason(),
            }
        }

    # Inheritance hooks for request field access - replace getattr() usage

    def get_request_confidence(self, request) -> str:
        """Get confidence from request. Override for custom confidence handling."""
        try:
            return request.confidence or 'low'
        except AttributeError:
            return 'low'

    def get_request_relevant_context(self, request) -> list:
        """Get relevant context from request. Override for custom field mapping."""
        try:
            return request.relevant_context or []
        except AttributeError:
            return []

    def get_request_issues_found(self, request) -> list:
        """Get issues found from request. Override for custom field mapping."""
        try:
            return request.issues_found or []
        except AttributeError:
            return []

    def get_request_hypothesis(self, request):
        """Get hypothesis from request. Override for custom field mapping."""
        try:
            return request.hypothesis
        except AttributeError:
            return None

    def get_request_images(self, request) -> list:
        """Get images from request. Override for custom field mapping."""
        try:
            return request.images or []
        except AttributeError:
            return []

    def get_backtrack_step(self, request) -> Optional[int]:
        """Get backtrack step from request. Override for custom backtrack handling."""
        try:
            return request.backtrack_from_step
        except AttributeError:
            return None

    def store_initial_issue(self, step_description: str):
        """Store initial issue description. Override for custom storage."""
        # Default implementation - tools can override to store differently
        self.initial_issue = step_description

    def get_initial_request(self, fallback_step: str) -> str:
        """Get initial request description. Override for custom retrieval."""
        try:
            return self.initial_request or fallback_step
        except AttributeError:
            return fallback_step

    # Default implementations for inheritance hooks

    def prepare_work_summary(self) -> str:
        """Prepare work summary. Override for custom implementation."""
        return f"Completed {len(self.consolidated_findings.findings)} work steps"

    def get_completion_status(self) -> str:
        """Get completion status. Override for tool-specific status."""
        return "high_confidence_completion"

    def get_final_analysis_from_request(self, request):
        """Extract final analysis from request. Override for tool-specific fields."""
        return self.get_request_hypothesis(request)

    def get_confidence_level(self, request) -> str:
        """Get confidence level. Override for tool-specific confidence handling."""
        return self.get_request_confidence(request) or 'high'

    def get_completion_message(self) -> str:
        """Get completion message. Override for tool-specific messaging."""
        return (
            f"{self.get_name().capitalize()} complete with high confidence. Present results "
            "and proceed with implementation without requiring further consultation."
        )

    def get_skip_reason(self) -> str:
        """Get reason for skipping expert analysis. Override for tool-specific reasons."""
        return f"{self.get_name()} completed with sufficient confidence"

    def get_skip_expert_analysis_status(self) -> str:
        """Get status for skipped expert analysis. Override for tool-specific status."""
        return "skipped_by_tool_design"

    def get_completion_next_steps_message(self) -> str:
        """
        Get the message to show when work is complete and expert analysis was called.
        Tools can override for custom messaging.
        """
        return (
            f"{self.get_name().upper()} IS COMPLETE. You MUST now summarize and present ALL key findings, confirmed "
            "hypotheses, and exact recommended solutions. Clearly identify the most likely root cause and "
            "provide concrete, actionable implementation guidance. Highlight affected code paths and display "
            "reasoning that led to this conclusion—make it easy for a developer to understand exactly where "
            "the problem lies."
        )

    def customize_workflow_response(self, response_data: dict, request) -> dict:
        """
        Allow tools to customize the workflow response before returning.

        Tools can override this to add tool-specific fields, modify status names,
        customize field mapping, etc. Default implementation returns unchanged.
        """
        return response_data

    def store_conversation_turn(self, continuation_id: str, response_data: dict, request):
        """
        Store the conversation turn. Tools can override for custom memory storage.
        """
        add_turn(
            thread_id=continuation_id,
            role="assistant",
            content=json.dumps(response_data, indent=2),
            tool_name=self.get_name(),
            files=request.relevant_files,
            images=self.get_request_images(request),
        )

    # Core workflow logic methods

    async def handle_work_completion(self, response_data: dict, request, arguments: dict) -> dict:
        """
        Handle work completion logic - expert analysis decision and response building.
        """
        response_data[f"{self.get_name()}_complete"] = True

        # Check if tool wants to skip expert analysis due to high certainty
        if self.should_skip_expert_analysis(request, self.consolidated_findings):
            # Handle completion without expert analysis
            completion_response = self.handle_completion_without_expert_analysis(request, self.consolidated_findings)
            response_data.update(completion_response)
        elif self.requires_expert_analysis() and self.should_call_expert_analysis(self.consolidated_findings):
            # Standard expert analysis path
            response_data["status"] = "calling_expert_analysis"

            # Call expert analysis
            expert_analysis = await self._call_expert_analysis(arguments, request)
            response_data["expert_analysis"] = expert_analysis

            # Handle special expert analysis statuses
            if isinstance(expert_analysis, dict) and expert_analysis.get("status") in [
                "files_required_to_continue",
                "investigation_paused",
                "refactoring_paused",
            ]:
                # Promote the special status to the main response
                special_status = expert_analysis["status"]
                response_data["status"] = special_status
                response_data["content"] = expert_analysis.get("raw_analysis", json.dumps(expert_analysis))
                del response_data["expert_analysis"]

                # Update next steps for special status
                if special_status == "files_required_to_continue":
                    response_data["next_steps"] = "Provide the requested files and continue the analysis."
                else:
                    response_data["next_steps"] = expert_analysis.get(
                        "next_steps", "Continue based on expert analysis."
                    )
            elif isinstance(expert_analysis, dict) and expert_analysis.get("status") == "analysis_error":
                # Expert analysis failed - promote error status
                response_data["status"] = "error"
                response_data["content"] = expert_analysis.get("error", "Expert analysis failed")
                response_data["content_type"] = "text"
                del response_data["expert_analysis"]
            else:
                response_data["next_steps"] = self.get_completion_next_steps_message()

            # Prepare complete work summary
            work_summary = self._prepare_work_summary()
            response_data[f"complete_{self.get_name()}"] = {
                "initial_request": self.get_initial_request(request.step),
                "steps_taken": len(self.work_history),
                "files_examined": list(self.consolidated_findings.files_checked),
                "relevant_files": list(self.consolidated_findings.relevant_files),
                "relevant_context": list(self.consolidated_findings.relevant_context),
                "issues_found": self.consolidated_findings.issues_found,
                "work_summary": work_summary,
            }
        else:
            # Tool doesn't require expert analysis or local work was sufficient
            if not self.requires_expert_analysis():
                # Tool is self-contained (like planner)
                response_data["status"] = f"{self.get_name()}_complete"
                response_data["next_steps"] = (
                    f"{self.get_name().capitalize()} work complete. Present results to the user."
                )
            else:
                # Local work was sufficient for tools that support expert analysis
                response_data["status"] = "local_work_complete"
                response_data["next_steps"] = (
                    f"Local {self.get_name()} complete with sufficient confidence. Present findings "
                    "and recommendations to the user based on the work results."
                )

        return response_data

    def handle_work_continuation(self, response_data: dict, request) -> dict:
        """
        Handle work continuation - force pause and provide guidance.
        """
        response_data["status"] = f"pause_for_{self.get_name()}"
        response_data[f"{self.get_name()}_required"] = True

        # Get tool-specific required actions
        required_actions = self.get_required_actions(
            request.step_number, self.get_request_confidence(request),
            request.findings, request.total_steps
        )
        response_data["required_actions"] = required_actions

        # Generate step guidance
        response_data["next_steps"] = self.get_step_guidance_message(request)

        return response_data

    def _handle_backtracking(self, backtrack_step: int):
        """Handle backtracking to a previous step"""
        # Remove findings after the backtrack point
        self.work_history = [s for s in self.work_history if s["step_number"] < backtrack_step]
        # Reprocess consolidated findings
        self._reprocess_consolidated_findings()

    def _update_consolidated_findings(self, step_data: dict):
        """Update consolidated findings with new step data"""
        self.consolidated_findings.files_checked.update(step_data.get("files_checked", []))
        self.consolidated_findings.relevant_files.update(step_data.get("relevant_files", []))
        self.consolidated_findings.relevant_context.update(step_data.get("relevant_context", []))
        self.consolidated_findings.findings.append(f"Step {step_data['step_number']}: {step_data['findings']}")
        if step_data.get("hypothesis"):
            self.consolidated_findings.hypotheses.append(
                {
                    "step": step_data["step_number"],
                    "hypothesis": step_data["hypothesis"],
                    "confidence": step_data["confidence"],
                }
            )
        if step_data.get("issues_found"):
            self.consolidated_findings.issues_found.extend(step_data["issues_found"])
        if step_data.get("images"):
            self.consolidated_findings.images.extend(step_data["images"])
        # Update confidence to latest value from this step
        if step_data.get("confidence"):
            self.consolidated_findings.confidence = step_data["confidence"]

    def _reprocess_consolidated_findings(self):
        """Reprocess consolidated findings after backtracking"""
        self.consolidated_findings = ConsolidatedFindings()
        for step in self.work_history:
            self._update_consolidated_findings(step)

    def _prepare_work_summary(self) -> str:
        """Prepare a comprehensive summary of the work"""
        summary_parts = [
            f"=== {self.get_name().upper()} WORK SUMMARY ===",
            f"Total steps: {len(self.work_history)}",
            f"Files examined: {len(self.consolidated_findings.files_checked)}",
            f"Relevant files identified: {len(self.consolidated_findings.relevant_files)}",
            f"Methods/functions involved: {len(self.consolidated_findings.relevant_context)}",
            f"Issues found: {len(self.consolidated_findings.issues_found)}",
            "",
            "=== WORK PROGRESSION ===",
        ]

        for finding in self.consolidated_findings.findings:
            summary_parts.append(finding)

        if self.consolidated_findings.hypotheses:
            summary_parts.extend(
                [
                    "",
                    "=== HYPOTHESIS EVOLUTION ===",
                ]
            )
            for hyp in self.consolidated_findings.hypotheses:
                summary_parts.append(f"Step {hyp['step']} ({hyp['confidence']} confidence): {hyp['hypothesis']}")

        if self.consolidated_findings.issues_found:
            summary_parts.extend(
                [
                    "",
                    "=== ISSUES IDENTIFIED ===",
                ]
            )
            for issue in self.consolidated_findings.issues_found:
                severity = issue.get("severity", "unknown")
                description = issue.get("description", "No description")
                summary_parts.append(f"[{severity.upper()}] {description}")

        return "\n".join(summary_parts)

    async def _call_expert_analysis(self, arguments: dict, request) -> dict:
        """Call external model for expert analysis"""
        try:
            # Use the same model resolution logic as BaseTool
            model_context = arguments.get("_model_context")
            resolved_model_name = arguments.get("_resolved_model_name")

            if model_context and resolved_model_name:
                self._model_context = model_context
                model_name = resolved_model_name
            else:
                # Fallback for direct calls - requires BaseTool methods
                model_name, model_context = self._resolve_model_context(arguments, request)
                self._model_context = model_context

            self._current_model_name = model_name
            provider = self.get_model_provider(model_name)

            # Prepare expert analysis context
            expert_context = self.prepare_expert_analysis_context(self.consolidated_findings)

            # Check if tool wants to include files in prompt
            if self.should_include_files_in_expert_prompt():
                file_content = self._prepare_files_for_expert_analysis()
                if file_content:
                    expert_context = self._add_files_to_expert_context(expert_context, file_content)

            # Get system prompt for this tool
            system_prompt = self.get_system_prompt()

            # Check if tool wants system prompt embedded in main prompt
            if self.should_embed_system_prompt():
                prompt = f"{system_prompt}\n\n{expert_context}\n\n{self.get_expert_analysis_instruction()}"
                system_prompt = ""  # Clear it since we embedded it
            else:
                prompt = expert_context

            # Generate AI response
            model_response = provider.generate_content(
                prompt=prompt,
                model_name=model_name,
                system_prompt=system_prompt,
                temperature=self.get_default_temperature(),
                thinking_mode=self.get_expert_thinking_mode(),
                images=list(set(self.consolidated_findings.images)) if self.consolidated_findings.images else None,
            )

            if model_response.content:
                try:
                    # Try to parse as JSON
                    analysis_result = json.loads(model_response.content.strip())
                    return analysis_result
                except json.JSONDecodeError:
                    # Return as text if not valid JSON
                    return {
                        "status": "analysis_complete",
                        "raw_analysis": model_response.content,
                        "parse_error": "Response was not valid JSON",
                    }
            else:
                return {"error": "No response from model", "status": "empty_response"}

        except Exception as e:
            logger.error(f"Error calling expert analysis: {e}", exc_info=True)
            return {"error": str(e), "status": "analysis_error"}

    def _process_work_step(self, step_data: dict):
        """
        Process a single work step and update internal state.

        This method is useful for testing and manual step processing.
        It adds the step to work history and updates consolidated findings.

        Args:
            step_data: Dictionary containing step information including:
                      step, step_number, findings, files_checked, etc.
        """
        # Store in history
        self.work_history.append(step_data)

        # Update consolidated findings
        self._update_consolidated_findings(step_data)

    # Common execute method for workflow-based tools

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Common execute logic for workflow-based tools.

        This method provides common validation and delegates to execute_workflow.
        Tools that need custom execute logic can override this method.
        """
        try:
            # Common validation
            if not arguments:
                return [
                    TextContent(type="text", text=json.dumps({"status": "error", "content": "No arguments provided"}))
                ]

            # Delegate to execute_workflow
            return await self.execute_workflow(arguments)

        except Exception as e:
            logger.error(f"Error in {self.get_name()} tool execution: {e}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "content": f"Error in {self.get_name()}: {str(e)}"}),
                )
            ]

    # Default implementations for methods that workflow-based tools typically don't need

    def prepare_prompt(self, request, continuation_id=None, max_tokens=None, reserve_tokens=0):
        """
        Base implementation for workflow tools.

        Allows subclasses to customize prompt preparation behavior by overriding
        customize_prompt_preparation().
        """
        # Allow subclasses to customize the prompt preparation
        self.customize_prompt_preparation(request, continuation_id, max_tokens, reserve_tokens)

        # Workflow tools typically don't need to return a prompt
        # since they handle their own prompt preparation internally
        return "", ""

    def customize_prompt_preparation(self, request, continuation_id=None, max_tokens=None, reserve_tokens=0):
        """
        Override this method in subclasses to customize prompt preparation.

        Base implementation does nothing - subclasses can extend this to add
        custom prompt preparation logic without the base class needing to
        know about specific tool capabilities.

        Args:
            request: The request object (may have files, prompt, etc.)
            continuation_id: Optional continuation ID
            max_tokens: Optional max token limit
            reserve_tokens: Optional reserved token count
        """
        # Base implementation does nothing - subclasses override as needed
        pass

    def format_response(self, response: str, request, model_info=None):
        """
        Workflow tools handle their own response formatting.
        The BaseWorkflowMixin formats responses internally.
        """
        return response
