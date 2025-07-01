"""
Shared workflow utilities to eliminate code duplication across workflow tools.

This module provides centralized utilities for workflow tools to:
1. Standardize field mapping and validation
2. Centralize response customization logic
3. Unify workflow step processing
4. Reduce maintenance overhead and improve consistency

Key utilities:
- WorkflowFieldMapper: Centralized field mapping for workflow tools
- ResponseCustomizer: Workflow response customization and status mapping
- WorkflowStepProcessor: Common step processing logic
- WorkflowUtilities: Common helper functions
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkflowFieldMapper:
    """
    Centralized field mapping for workflow tools.

    Provides standardized field extraction, validation, and mapping
    for all workflow tools with support for tool-specific overrides.
    """

    # Standard workflow fields that all tools share
    STANDARD_WORKFLOW_FIELDS = {
        "step": {
            "type": "string",
            "description": "Describe what you're currently investigating in this step.",
        },
        "step_number": {
            "type": "integer",
            "minimum": 1,
            "description": "The index of the current step in the workflow sequence, beginning at 1.",
        },
        "total_steps": {
            "type": "integer",
            "minimum": 1,
            "description": "Your current estimate for how many steps will be needed to complete the workflow.",
        },
        "next_step_required": {
            "type": "boolean",
            "description": "Set to true if you plan to continue with another step. False means the workflow is complete.",
        },
        "findings": {
            "type": "string",
            "description": "Summarize everything discovered in this step. Be specific and avoid vague language.",
        },
        "files_checked": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List all files examined during the investigation so far (absolute paths).",
        },
        "relevant_files": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Subset of files_checked that are directly relevant to the workflow (absolute paths).",
        },
        "relevant_context": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List methods, functions, classes central to the workflow findings.",
        },
        "confidence": {
            "type": "string",
            "description": "Your confidence level in the current workflow assessment.",
        },
        "backtrack_from_step": {
            "type": "integer",
            "minimum": 1,
            "description": "If an earlier finding needs revision, specify the step number to start over from.",
        },
        "images": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional list of paths to visual references that assist understanding.",
        },
    }

    @classmethod
    def map_standard_fields(cls) -> dict[str, Any]:
        """
        Get standard workflow fields that all tools share.

        Returns:
            Dictionary of standard workflow field definitions
        """
        return cls.STANDARD_WORKFLOW_FIELDS.copy()

    @classmethod
    def map_with_overrides(cls, tool_specific_overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map standard fields with tool-specific overrides.

        Args:
            tool_specific_overrides: Tool-specific field definitions that override standard ones

        Returns:
            Combined field mapping with tool-specific customizations
        """
        fields = cls.map_standard_fields()
        fields.update(tool_specific_overrides)
        return fields

    @classmethod
    def extract_step_data(cls, request: Any) -> Dict[str, Any]:
        """
        Extract and validate standard step data from request.

        Args:
            request: Workflow request object

        Returns:
            Dictionary containing extracted step data
        """
        step_data = {
            "step": getattr(request, "step", ""),
            "step_number": getattr(request, "step_number", 1),
            "findings": getattr(request, "findings", ""),
            "files_checked": getattr(request, "files_checked", []),
            "relevant_files": getattr(request, "relevant_files", []),
            "relevant_context": getattr(request, "relevant_context", []),
            "issues_found": getattr(request, "issues_found", []),
            "confidence": getattr(request, "confidence", "low"),
            "hypothesis": getattr(request, "hypothesis", None) or getattr(request, "findings", ""),
            "images": getattr(request, "images", []) or [],
        }
        return step_data

    @classmethod
    def validate_step_requirements(cls, request: Any, step_number: int) -> None:
        """
        Validate step requirements for workflow tools.

        Args:
            request: Workflow request object
            step_number: Current step number

        Raises:
            ValueError: If required fields are missing
        """
        if step_number == 1:
            if not getattr(request, "relevant_files", None):
                raise ValueError("Step 1 requires 'relevant_files' field to specify files or directories to analyze")


class ResponseCustomizer:
    """
    Workflow response customization and status mapping.

    Provides centralized response formatting, status mapping,
    and metadata addition for workflow tools.
    """

    @classmethod
    def customize_response(
        cls,
        response_data: Dict[str, Any],
        tool_name: str,
        status_mappings: Optional[Dict[str, str]] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Customize workflow response with tool-specific formatting.

        Args:
            response_data: Base response data to customize
            tool_name: Name of the workflow tool
            status_mappings: Tool-specific status mappings
            additional_data: Additional data to add to response

        Returns:
            Customized response data
        """
        # Apply status mappings
        if status_mappings:
            current_status = response_data.get("status")
            if current_status in status_mappings:
                response_data["status"] = status_mappings[current_status]

        # Rename tool-specific status fields
        cls._rename_status_fields(response_data, tool_name)

        # Rename completion fields
        cls._rename_completion_fields(response_data, tool_name)

        # Add additional data if provided
        if additional_data:
            response_data.update(additional_data)

        return response_data

    @classmethod
    def _rename_status_fields(cls, response_data: Dict[str, Any], tool_name: str) -> None:
        """Rename generic status fields to tool-specific names."""
        # Map tool_status to tool-specific status
        tool_status_key = f"{tool_name}_status"
        if tool_status_key in response_data:
            new_status_key = cls._get_tool_status_name(tool_name)
            response_data[new_status_key] = response_data.pop(tool_status_key)

    @classmethod
    def _rename_completion_fields(cls, response_data: Dict[str, Any], tool_name: str) -> None:
        """Rename generic completion fields to tool-specific names."""
        # Map complete_tool to tool-specific completion
        complete_key = f"complete_{tool_name}"
        if complete_key in response_data:
            new_complete_key = cls._get_completion_key(tool_name)
            response_data[new_complete_key] = response_data.pop(complete_key)

        # Map tool_complete flag
        complete_flag = f"{tool_name}_complete"
        if complete_flag in response_data:
            new_flag = cls._get_completion_flag(tool_name)
            response_data[new_flag] = response_data.pop(complete_flag)

    @classmethod
    def _get_tool_status_name(cls, tool_name: str) -> str:
        """Get tool-specific status field name."""
        status_names = {
            "analyze": "analysis_status",
            "debug": "investigation_status",
            "codereview": "code_review_status",
            "refactor": "refactor_status",
            "testgen": "test_generation_status",
        }
        return status_names.get(tool_name, f"{tool_name}_status")

    @classmethod
    def _get_completion_key(cls, tool_name: str) -> str:
        """Get tool-specific completion data key."""
        completion_keys = {
            "analyze": "complete_analysis",
            "debug": "complete_investigation",
            "codereview": "complete_code_review",
            "refactor": "complete_refactor",
            "testgen": "complete_test_generation",
        }
        return completion_keys.get(tool_name, f"complete_{tool_name}")

    @classmethod
    def _get_completion_flag(cls, tool_name: str) -> str:
        """Get tool-specific completion flag name."""
        completion_flags = {
            "analyze": "analysis_complete",
            "debug": "investigation_complete",
            "codereview": "code_review_complete",
            "refactor": "refactor_complete",
            "testgen": "test_generation_complete",
        }
        return completion_flags.get(tool_name, f"{tool_name}_complete")

    @classmethod
    def get_standard_status_mappings(cls, tool_name: str) -> Dict[str, str]:
        """
        Get standard status mappings for a workflow tool.

        Args:
            tool_name: Name of the workflow tool

        Returns:
            Dictionary mapping generic statuses to tool-specific ones
        """
        tool_specific_names = {
            "analyze": "analysis",
            "debug": "investigation",
            "codereview": "code_review",
            "refactor": "refactor",
            "testgen": "test_generation",
        }

        specific_name = tool_specific_names.get(tool_name, tool_name)

        return {
            f"{tool_name}_in_progress": f"{specific_name}_in_progress",
            f"pause_for_{tool_name}": f"pause_for_{specific_name}",
            f"{tool_name}_required": f"{specific_name}_required",
            f"{tool_name}_complete": f"{specific_name}_complete",
        }


class WorkflowStepProcessor:
    """
    Common step processing logic for workflow tools.

    Provides standardized step validation, normalization,
    and data preparation for workflow tools.
    """

    @classmethod
    def process_step_data(cls, request: Any, tool_name: str) -> Dict[str, Any]:
        """
        Process and normalize step data from request.

        Args:
            request: Workflow request object
            tool_name: Name of the workflow tool

        Returns:
            Processed step data dictionary
        """
        # Extract standard step data
        step_data = WorkflowFieldMapper.extract_step_data(request)

        # Add tool-specific processing
        step_data = cls._add_tool_specific_data(step_data, request, tool_name)

        # Validate step data
        cls._validate_step_data(step_data, request.step_number)

        return step_data

    @classmethod
    def _add_tool_specific_data(cls, step_data: Dict[str, Any], request: Any, tool_name: str) -> Dict[str, Any]:
        """Add tool-specific data to step data."""
        # Tool-specific field mapping
        tool_specific_fields = {
            "analyze": ["analysis_type", "output_format"],
            "debug": [],  # Debug tool uses standard fields
            "codereview": ["review_type", "focus_on", "standards", "severity_filter"],
            "refactor": ["refactor_type", "focus_areas", "style_guide_examples"],
            "testgen": [],  # TestGen tool uses standard fields
        }

        # Add tool-specific fields if they exist
        for field in tool_specific_fields.get(tool_name, []):
            if hasattr(request, field):
                step_data[field] = getattr(request, field)

        return step_data

    @classmethod
    def _validate_step_data(cls, step_data: Dict[str, Any], step_number: int) -> None:
        """Validate processed step data."""
        required_fields = ["step", "step_number", "findings"]

        for field in required_fields:
            if not step_data.get(field):
                raise ValueError(f"Required field '{field}' is missing or empty")

        if step_number != step_data.get("step_number"):
            raise ValueError(f"Step number mismatch: expected {step_number}, got {step_data.get('step_number')}")

    @classmethod
    def generate_required_actions(
        cls, step_number: int, confidence: str, tool_name: str, findings: str = "", total_steps: int = 3
    ) -> List[str]:
        """
        Generate standard required actions based on step and confidence.

        Args:
            step_number: Current step number
            confidence: Current confidence level
            tool_name: Name of the workflow tool
            findings: Current findings (optional)
            total_steps: Total estimated steps

        Returns:
            List of required actions for the current state
        """
        if step_number == 1:
            return cls._get_initial_actions(tool_name)
        elif confidence in ["exploring", "low", "incomplete"]:
            return cls._get_deep_investigation_actions(tool_name)
        elif confidence in ["medium", "high", "partial"]:
            return cls._get_verification_actions(tool_name)
        else:
            return cls._get_general_actions(tool_name)

    @classmethod
    def _get_initial_actions(cls, tool_name: str) -> List[str]:
        """Get initial investigation actions."""
        base_actions = [
            "Read and understand the relevant files specified for analysis",
            "Examine the overall structure and understand the implementation",
            "Identify the main components and their relationships",
            "Understand the business logic and intended functionality",
        ]

        tool_specific_actions = {
            "analyze": [
                "Map the tech stack, frameworks, and overall architecture",
                "Look for strengths, risks, and strategic improvement areas",
            ],
            "debug": [
                "Search for code related to the reported issue or symptoms",
                "Identify how the affected functionality is supposed to work",
            ],
            "codereview": [
                "Look for obvious issues: bugs, security concerns, performance problems",
                "Note any code smells, anti-patterns, or areas of concern",
            ],
            "refactor": [
                "Identify refactoring opportunities and code smells",
                "Look for decomposition and modernization opportunities",
            ],
            "testgen": [
                "Identify critical paths, edge cases, and potential failure modes",
                "Map out testable behaviors and coverage requirements",
            ],
        }

        return base_actions + tool_specific_actions.get(tool_name, [])

    @classmethod
    def _get_deep_investigation_actions(cls, tool_name: str) -> List[str]:
        """Get actions for deeper investigation phase."""
        base_actions = [
            "Examine specific areas you've identified as requiring attention",
            "Trace method calls and data flow through the system",
            "Check for edge cases, boundary conditions, and assumptions",
            "Look for related configuration, dependencies, or external factors",
        ]

        tool_specific_actions = {
            "analyze": [
                "Analyze scalability characteristics and performance implications",
                "Assess maintainability factors and identify tech debt",
            ],
            "debug": [
                "Look for race conditions, shared state, or timing dependencies",
                "Consider upstream logic, invalid inputs, missing preconditions",
            ],
            "codereview": [
                "Analyze security implications and performance concerns",
                "Search for over-engineering and unnecessary complexity",
            ],
            "refactor": [
                "Identify specific refactoring patterns and opportunities",
                "Look for modernization and organization improvements",
            ],
            "testgen": [
                "Identify test frameworks and existing patterns",
                "Plan comprehensive test scenarios and coverage strategies",
            ],
        }

        return base_actions + tool_specific_actions.get(tool_name, [])

    @classmethod
    def _get_verification_actions(cls, tool_name: str) -> List[str]:
        """Get actions for verification phase."""
        base_actions = [
            "Verify all significant findings have been properly documented",
            "Confirm that your assessment is comprehensive and complete",
            "Ensure findings are actionable and provide clear guidance",
            "Double-check that nothing important has been missed",
        ]

        tool_specific_actions = {
            "analyze": [
                "Verify strategic improvement opportunities are captured",
                "Confirm both strengths and risks are identified with evidence",
            ],
            "debug": [
                "Finalize root cause analysis with specific evidence",
                "Document the complete chain of causation",
            ],
            "codereview": [
                "Check for any missed critical security vulnerabilities",
                "Validate that architectural concerns are comprehensively captured",
            ],
            "refactor": [
                "Confirm all refactoring opportunities are identified",
                "Verify recommendations align with project patterns",
            ],
            "testgen": [
                "Ensure comprehensive test coverage is planned",
                "Verify edge cases and failure modes are covered",
            ],
        }

        return base_actions + tool_specific_actions.get(tool_name, [])

    @classmethod
    def _get_general_actions(cls, tool_name: str) -> List[str]:
        """Get general investigation actions."""
        return [
            "Continue examining the codebase for additional patterns",
            "Gather more evidence using appropriate analysis techniques",
            "Test your assumptions about code behavior and design decisions",
            "Look for patterns that confirm or refute your current assessment",
        ]


class WorkflowUtilities:
    """
    Common helper functions for workflow tools.

    Provides utility functions for file validation, error handling,
    and common workflow operations.
    """

    @classmethod
    def validate_file_paths(cls, file_paths: List[str]) -> List[str]:
        """
        Validate and normalize file paths.

        Args:
            file_paths: List of file paths to validate

        Returns:
            List of validated file paths
        """
        if not file_paths:
            return []

        validated_paths = []
        for path in file_paths:
            if path and isinstance(path, str):
                # Ensure absolute path
                if not path.startswith("/"):
                    logger.warning(f"Relative path provided: {path}")
                validated_paths.append(path)

        return validated_paths

    @classmethod
    def format_issues_summary(cls, issues_found: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Format issues summary by severity.

        Args:
            issues_found: List of issues with severity information

        Returns:
            Dictionary mapping severity levels to counts
        """
        summary = {}
        for issue in issues_found:
            severity = issue.get("severity", "unknown")
            summary[severity] = summary.get(severity, 0) + 1
        return summary

    @classmethod
    def should_use_expert_analysis(cls, consolidated_findings: Any, confidence_threshold: str = "certain") -> bool:
        """
        Determine if expert analysis should be used.

        Args:
            consolidated_findings: Consolidated findings object
            confidence_threshold: Confidence level that skips expert analysis

        Returns:
            True if expert analysis should be used
        """
        # Skip expert analysis if confidence is at threshold
        if hasattr(consolidated_findings, "confidence"):
            if consolidated_findings.confidence == confidence_threshold:
                return False

        # Use expert analysis if we have meaningful data
        return (
            len(getattr(consolidated_findings, "relevant_files", [])) > 0
            or len(getattr(consolidated_findings, "findings", [])) >= 2
            or len(getattr(consolidated_findings, "issues_found", [])) > 0
        )

    @classmethod
    def build_expert_context_summary(cls, consolidated_findings: Any, tool_name: str) -> str:
        """
        Build a comprehensive summary for expert analysis context.

        Args:
            consolidated_findings: Consolidated findings object
            tool_name: Name of the workflow tool

        Returns:
            Formatted summary string for expert analysis
        """
        summary_parts = [
            f"=== SYSTEMATIC {tool_name.upper()} INVESTIGATION SUMMARY ===",
            f"Total steps: {len(getattr(consolidated_findings, 'findings', []))}",
            f"Files examined: {len(getattr(consolidated_findings, 'files_checked', []))}",
            f"Relevant files identified: {len(getattr(consolidated_findings, 'relevant_files', []))}",
            f"Code elements analyzed: {len(getattr(consolidated_findings, 'relevant_context', []))}",
        ]

        # Add tool-specific metrics
        if hasattr(consolidated_findings, "issues_found"):
            summary_parts.append(f"Issues identified: {len(consolidated_findings.issues_found)}")

        summary_parts.extend(
            [
                "",
                "=== INVESTIGATION PROGRESSION ===",
            ]
        )

        # Add findings progression
        for finding in getattr(consolidated_findings, "findings", []):
            summary_parts.append(finding)

        return "\n".join(summary_parts)

    @classmethod
    def generate_step_guidance_message(
        cls, step_number: int, confidence: str, tool_name: str, required_actions: List[str]
    ) -> str:
        """
        Generate step guidance message for workflow tools.

        Args:
            step_number: Current step number
            confidence: Current confidence level
            tool_name: Name of the workflow tool
            required_actions: List of required actions

        Returns:
            Formatted step guidance message
        """
        if step_number == 1:
            return (
                f"MANDATORY: DO NOT call the {tool_name} tool again immediately. You MUST first examine "
                f"the files thoroughly using appropriate tools. Use file reading tools, code analysis, "
                f"and systematic examination to gather comprehensive information. Only call {tool_name} "
                f"again AFTER completing your investigation. When you call {tool_name} next time, "
                f"use step_number: {step_number + 1} and report specific files examined and findings discovered."
            )
        elif confidence in ["exploring", "low", "incomplete"]:
            actions_text = "\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
            return (
                f"STOP! Do NOT call {tool_name} again yet. Based on your findings, you need deeper analysis. "
                f"MANDATORY ACTIONS before calling {tool_name} step {step_number + 1}:\n{actions_text}\n\n"
                f"Only call {tool_name} again with step_number: {step_number + 1} AFTER completing these tasks."
            )
        elif confidence in ["medium", "high", "partial"]:
            actions_text = "\n".join(f"{i+1}. {action}" for i, action in enumerate(required_actions))
            return (
                f"WAIT! Your {tool_name} needs final verification. DO NOT call {tool_name} immediately. "
                f"REQUIRED ACTIONS:\n{actions_text}\n\nDocument findings with specific file references, "
                f"then call {tool_name} with step_number: {step_number + 1}."
            )
        else:
            actions_preview = ", ".join(required_actions[:2])
            return (
                f"PAUSE {tool_name.upper()}. Before calling {tool_name} step {step_number + 1}, you MUST examine code. "
                f"Required: {actions_preview}. Your next {tool_name} call (step_number: {step_number + 1}) must include "
                f"NEW evidence from actual code examination, not just theories. NO recursive {tool_name} calls "
                f"without investigation work!"
            )
