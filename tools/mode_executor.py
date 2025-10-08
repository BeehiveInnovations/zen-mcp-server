"""
Mode Executor - Dynamic tool executor for the second stage

This module provides mode-specific executors with minimal schemas that are
dynamically loaded based on the mode selected in stage 1. Each executor
provides only the fields necessary for its specific mode and complexity,
dramatically reducing token consumption while maintaining full functionality.

Token usage per mode: 500-800 tokens (vs 3-4k tokens in original tools)
"""

import json
import logging
from typing import TYPE_CHECKING, Any, List, Optional, Type

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from mcp.types import TextContent

from tools.shared.base_models import ToolRequest

from .shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


# Mode-specific request models with minimal fields
class DebugSimpleRequest(ToolRequest):
    """Minimal debug request for simple cases"""

    problem: str = Field(..., description="The issue to debug")
    files: Optional[List[str]] = Field(None, description="Relevant files")
    confidence: Optional[str] = Field("exploring", description="Current confidence level")
    hypothesis: Optional[str] = Field(None, description="Initial theory about the issue")


class DebugWorkflowRequest(ToolRequest):
    """Debug workflow request for systematic investigation"""

    step: str = Field(..., description="Current investigation step")
    step_number: int = Field(..., description="Step number (starts at 1)")
    findings: str = Field(..., description="Discoveries so far")
    next_step_required: bool = Field(..., description="Continue investigation?")
    total_steps: Optional[int] = Field(3, description="Estimated total steps")
    files_checked: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[str] = Field("exploring")


class ReviewSimpleRequest(ToolRequest):
    """Minimal review request for quick checks"""

    files: List[str] = Field(..., description="Files to review")
    review_type: Optional[str] = Field("quality", description="Focus area")
    focus: Optional[str] = Field(None, description="Specific concerns")


class ReviewWorkflowRequest(ToolRequest):
    """Review workflow for comprehensive analysis - matches CodeReviewRequest schema"""

    # Required workflow fields (matches CodeReviewRequest)
    step: str = Field(..., description="Review step content and findings")
    step_number: int = Field(..., description="Current step number")
    total_steps: int = Field(..., description="Total estimated steps")
    next_step_required: bool = Field(..., description="Continue with another step")
    findings: str = Field(..., description="Review findings and insights")

    # Investigation tracking fields (matches CodeReviewRequest)
    files_checked: Optional[List[str]] = Field(default_factory=list, description="Files examined")
    relevant_files: Optional[List[str]] = Field(default_factory=list, description="Relevant files for review")
    relevant_context: Optional[List[str]] = Field(default_factory=list, description="Relevant methods/functions")
    issues_found: Optional[List[dict]] = Field(default_factory=list, description="Issues with severity levels")
    confidence: Optional[str] = Field("medium", description="Confidence level")

    # Optional CodeReview-specific fields
    review_validation_type: Optional[str] = Field("external", description="Validation type")


class AnalyzeSimpleRequest(ToolRequest):
    """Simple analysis request with required workflow fields"""

    # Required workflow fields (all tools need these)
    step: str = Field("Analysis", description="Current analysis step")
    step_number: int = Field(1, description="Step number")
    total_steps: int = Field(1, description="Total steps")
    next_step_required: bool = Field(False, description="Continue workflow?")
    findings: str = Field("Starting analysis", description="Current findings")
    files_checked: Optional[List[str]] = Field(default_factory=list)
    relevant_files: List[str] = Field(..., description="Files or directories to analyze (required for step 1)")
    relevant_context: Optional[List[str]] = Field(default_factory=list)
    issues_found: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[str] = Field("medium", description="Confidence level")

    # Tool-specific fields
    analysis_type: Optional[str] = Field("general", description="Type of analysis")
    output_format: Optional[str] = Field("detailed", description="Output format")


class ConsensusSimpleRequest(ToolRequest):
    """Simplified consensus request - only essential fields"""

    prompt: str = Field(..., description="The question or proposal to evaluate")
    models: List[dict] = Field(..., description="Models to consult. Example: [{'model': 'o3', 'stance': 'neutral'}]")
    relevant_files: Optional[List[str]] = Field(None, description="Optional context files")
    images: Optional[List[str]] = Field(None, description="Optional images")

    @field_validator("models", mode="before")
    @classmethod
    def validate_models_required(cls, v):
        """Provide helpful error message when models field is missing"""
        if v is None or (isinstance(v, list) and len(v) == 0):
            raise ValueError(
                'Missing required "models" field. ' 'Example: "models": [{"model": "o3", "stance": "neutral"}]'
            )
        return v


class ConsensusWorkflowRequest(ToolRequest):
    """Full consensus workflow request for complex multi-step scenarios"""

    # Required workflow fields
    step: str = Field("Consensus building", description="Current consensus step")
    step_number: int = Field(1, description="Step number")
    total_steps: int = Field(1, description="Total steps")
    next_step_required: bool = Field(False, description="Continue workflow?")
    findings: str = Field("Starting consensus process", description="Current findings")
    files_checked: Optional[List[str]] = Field(default_factory=list)
    relevant_files: Optional[List[str]] = Field(default_factory=list)
    relevant_context: Optional[List[str]] = Field(default_factory=list)
    issues_found: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[str] = Field("medium", description="Confidence level")

    # Tool-specific fields
    models: List[dict] = Field(..., description="Models to consult for consensus")
    current_model_index: Optional[int] = Field(0, description="Current model index")
    model_responses: Optional[List[str]] = Field(default_factory=list, description="Model responses")


class ChatRequest(ToolRequest):
    """Simple chat request"""

    prompt: str = Field(..., description="Your question or request")
    working_directory: str = Field(..., description="Absolute directory path for generated code")
    model: Optional[str] = Field(None, description="Model preference")
    temperature: Optional[float] = Field(None)
    images: Optional[List[str]] = Field(None)
    files: Optional[List[str]] = Field(None, description="Optional file paths")


class SecurityWorkflowRequest(ToolRequest):
    """Security audit workflow request with all required fields"""

    # Required workflow fields
    step: str = Field("Security audit", description="Current audit step")
    step_number: int = Field(1, description="Step number")
    total_steps: int = Field(1, description="Total steps")
    next_step_required: bool = Field(False, description="Continue workflow?")
    findings: str = Field("Starting security audit", description="Current findings")
    files_checked: Optional[List[str]] = Field(default_factory=list)
    relevant_files: Optional[List[str]] = Field(default_factory=list)
    relevant_context: Optional[List[str]] = Field(default_factory=list)
    issues_found: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[str] = Field("medium", description="Confidence level")

    # Tool-specific fields
    security_scope: Optional[str] = Field("comprehensive", description="Security scope")
    threat_level: Optional[str] = Field("medium", description="Threat level")
    compliance_requirements: Optional[List[str]] = Field(default_factory=list)
    audit_focus: Optional[str] = Field("comprehensive", description="Audit focus")
    severity_filter: Optional[str] = Field("all", description="Severity filter")


class RefactorSimpleRequest(ToolRequest):
    """Simple refactoring request with required workflow fields"""

    # Required workflow fields
    step: str = Field("Refactoring analysis", description="Current refactoring step")
    step_number: int = Field(1, description="Step number")
    total_steps: int = Field(1, description="Total steps")
    next_step_required: bool = Field(False, description="Continue workflow?")
    findings: str = Field("Starting refactoring analysis", description="Current findings")
    files_checked: Optional[List[str]] = Field(default_factory=list)
    relevant_files: Optional[List[str]] = Field(default_factory=list)
    relevant_context: Optional[List[str]] = Field(default_factory=list)
    issues_found: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[str] = Field(
        "incomplete", description="Confidence level - exploring|incomplete|partial|complete"
    )

    # Tool-specific fields
    refactor_type: Optional[str] = Field(
        "codesmells", description="Type of refactoring - codesmells|decompose|modernize|organization"
    )
    focus_areas: Optional[List[str]] = Field(default_factory=list, description="Focus areas")
    style_guide_examples: Optional[List[str]] = Field(default_factory=list, description="Style examples")


class TestGenSimpleRequest(ToolRequest):
    """Test generation request with required workflow fields"""

    # Required workflow fields
    step: str = Field("Test generation", description="Current test generation step")
    step_number: int = Field(1, description="Step number")
    total_steps: int = Field(1, description="Total steps")
    next_step_required: bool = Field(False, description="Continue workflow?")
    findings: str = Field("Starting test generation", description="Current findings")
    files_checked: Optional[List[str]] = Field(default_factory=list)
    relevant_files: List[str] = Field(..., description="Code files to generate tests for (required for step 1)")
    relevant_context: Optional[List[str]] = Field(default_factory=list)
    issues_found: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[str] = Field("medium", description="Confidence level")


class PlannerWorkflowRequest(ToolRequest):
    """Planning workflow request with all required fields"""

    # Required workflow fields
    step: str = Field("Planning", description="Current planning step")
    step_number: int = Field(1, description="Step number")
    total_steps: int = Field(1, description="Total steps")
    next_step_required: bool = Field(False, description="Continue planning?")
    findings: str = Field("Starting planning process", description="Current findings")
    files_checked: Optional[List[str]] = Field(default_factory=list)
    relevant_files: Optional[List[str]] = Field(default_factory=list)
    relevant_context: Optional[List[str]] = Field(default_factory=list)
    issues_found: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[str] = Field("medium", description="Confidence level")

    # Tool-specific fields
    is_step_revision: Optional[bool] = Field(False, description="Is step revision")
    revises_step_number: Optional[int] = Field(None, description="Revises step number")
    is_branch_point: Optional[bool] = Field(False, description="Is branch point")
    branch_from_step: Optional[int] = Field(None, description="Branch from step")
    branch_id: Optional[str] = Field(None, description="Branch ID")
    more_steps_needed: Optional[bool] = Field(True, description="More steps needed")


class TracerSimpleRequest(ToolRequest):
    """Simple tracing request with required workflow fields"""

    # Required workflow fields (all tools need these)
    step: str = Field("Tracing", description="Current tracing step")
    step_number: int = Field(1, description="Step number")
    total_steps: int = Field(1, description="Total steps")
    next_step_required: bool = Field(False, description="Continue tracing?")
    findings: str = Field("Starting trace analysis", description="Current findings")
    files_checked: Optional[List[str]] = Field(default_factory=list)
    relevant_files: Optional[List[str]] = Field(default_factory=list)
    relevant_context: Optional[List[str]] = Field(default_factory=list)
    issues_found: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[str] = Field("medium", description="Confidence level")

    # Tool-specific fields
    target: str = Field(..., description="Function or code to trace")
    trace_mode: Optional[str] = Field("ask", description="Type of tracing - precision|dependencies|ask")
    files: Optional[List[str]] = Field(None, description="Files to analyze")


# Mode to request model mapping
MODE_REQUEST_MAP = {
    ("debug", "simple"): DebugSimpleRequest,
    ("debug", "workflow"): DebugWorkflowRequest,
    ("codereview", "simple"): ReviewSimpleRequest,
    ("codereview", "workflow"): ReviewWorkflowRequest,
    ("analyze", "simple"): AnalyzeSimpleRequest,
    ("analyze", "workflow"): AnalyzeSimpleRequest,  # Reuse simple for now
    ("consensus", "simple"): ConsensusSimpleRequest,  # Use simplified model
    ("consensus", "workflow"): ConsensusWorkflowRequest,  # Use full workflow model
    ("chat", "simple"): ChatRequest,
    ("chat", "workflow"): ChatRequest,
    ("security", "simple"): SecurityWorkflowRequest,  # Add simple variant
    ("security", "workflow"): SecurityWorkflowRequest,
    ("refactor", "simple"): RefactorSimpleRequest,
    ("refactor", "workflow"): RefactorSimpleRequest,  # Reuse simple for now
    ("testgen", "simple"): TestGenSimpleRequest,
    ("testgen", "workflow"): TestGenSimpleRequest,  # Reuse simple for now
    ("planner", "simple"): PlannerWorkflowRequest,  # Planning is inherently workflow-based
    ("planner", "workflow"): PlannerWorkflowRequest,
    ("tracer", "simple"): TracerSimpleRequest,
    ("tracer", "workflow"): TracerSimpleRequest,  # Reuse simple for now
}


class ModeExecutor(BaseTool):
    """
    Dynamic mode executor for stage 2 of the two-stage architecture.

    This tool receives a mode and complexity from stage 1, then executes
    the appropriate Zen tool with minimal schema overhead.
    """

    def __init__(self, mode: str, complexity: str = "simple"):
        """
        Initialize executor for specific mode and complexity.

        Args:
            mode: The selected mode (debug, review, analyze, etc.)
            complexity: Task complexity (simple, workflow, expert)
        """
        # Set mode and complexity BEFORE calling super().__init__()
        # because get_name() needs these values
        self.mode = mode
        self.complexity = complexity
        self._actual_tool = None
        self._request_model = None

        # Now safe to call super().__init__() which calls get_name()
        super().__init__()

    def get_name(self) -> str:
        return f"zen_execute_{self.mode}"

    def get_description(self) -> str:
        descriptions = {
            "debug": "Execute debugging and root cause analysis",
            "codereview": "Perform code review and quality assessment",
            "analyze": "Analyze code architecture and patterns",
            "consensus": "Build multi-model consensus on decisions",
            "chat": "General AI consultation and brainstorming",
            "security": "Perform security audit and vulnerability assessment",
            "refactor": "Analyze refactoring opportunities",
            "testgen": "Generate comprehensive test suites",
            "planner": "Create sequential task plans",
            "tracer": "Trace code execution and dependencies",
        }

        base_desc = descriptions.get(self.mode, f"Execute {self.mode} task")
        complexity_note = {
            "simple": " (quick, single-shot analysis)",
            "workflow": " (systematic, multi-step investigation)",
            "expert": " (comprehensive expert analysis)",
        }.get(self.complexity, "")

        return base_desc + complexity_note

    def get_system_prompt(self) -> str:
        """Load system prompt from the actual tool"""
        tool = self._get_actual_tool()
        if tool:
            return tool.get_system_prompt()
        return ""

    def get_default_temperature(self) -> float:
        """Get temperature from actual tool"""
        tool = self._get_actual_tool()
        if tool:
            return tool.get_default_temperature()
        return 0.3

    def get_model_category(self) -> "ToolModelCategory":
        """Get model category from actual tool"""
        from tools.models import ToolModelCategory

        tool = self._get_actual_tool()
        if tool and hasattr(tool, "get_model_category"):
            return tool.get_model_category()

        # Default categories by mode
        category_map = {
            "debug": ToolModelCategory.EXTENDED_REASONING,
            "codereview": ToolModelCategory.EXTENDED_REASONING,
            "analyze": ToolModelCategory.EXTENDED_REASONING,
            "consensus": ToolModelCategory.EXTENDED_REASONING,
            "chat": ToolModelCategory.FAST_RESPONSE,
            "security": ToolModelCategory.EXTENDED_REASONING,
            "refactor": ToolModelCategory.EXTENDED_REASONING,
            "testgen": ToolModelCategory.EXTENDED_REASONING,
            "planner": ToolModelCategory.FAST_RESPONSE,
            "tracer": ToolModelCategory.EXTENDED_REASONING,
        }

        return category_map.get(self.mode, ToolModelCategory.FAST_RESPONSE)

    def get_input_schema(self) -> dict[str, Any]:
        """
        Generate minimal schema for the specific mode and complexity.

        This is the key to token reduction - we only expose the fields
        actually needed for the task.
        """
        request_model = self._get_request_model()

        if not request_model:
            # Fallback schema
            return {
                "type": "object",
                "properties": {"context": {"type": "object", "description": f"Parameters for {self.mode} execution"}},
                "required": ["context"],
            }

        # Generate schema from Pydantic model
        schema = {"type": "object", "properties": {}, "required": []}

        # Add fields from the request model
        for field_name, field_info in request_model.model_fields.items():
            # Skip excluded fields
            if field_info.exclude:
                continue

            # Build field schema
            field_schema = self._build_field_schema(field_info)
            schema["properties"][field_name] = field_schema

            # Add to required if not optional
            if field_info.is_required():
                schema["required"].append(field_name)

        schema["additionalProperties"] = False

        return schema

    def _build_field_schema(self, field_info) -> dict:
        """Build minimal JSON schema for a field"""
        from typing import get_args, get_origin

        field_type = field_info.annotation
        schema = {}

        # Handle Optional types
        if get_origin(field_type) is type(Optional):
            args = get_args(field_type)
            if args:
                field_type = args[0]

        # Map Python types to JSON schema
        if field_type == str:
            schema["type"] = "string"
        elif field_type == int:
            schema["type"] = "integer"
        elif field_type == float:
            schema["type"] = "number"
        elif field_type == bool:
            schema["type"] = "boolean"
        elif get_origin(field_type) == list:
            schema["type"] = "array"
            item_type = get_args(field_type)[0] if get_args(field_type) else str
            if item_type == str:
                schema["items"] = {"type": "string"}
            elif item_type == dict:
                schema["items"] = {"type": "object"}
        elif get_origin(field_type) == dict or field_type == dict:
            schema["type"] = "object"

        # Add description if available
        if field_info.description:
            schema["description"] = field_info.description

        # Add enum values if present
        if hasattr(field_info, "json_schema_extra") and field_info.json_schema_extra:
            if "enum" in field_info.json_schema_extra:
                schema["enum"] = field_info.json_schema_extra["enum"]

        # Add default if present (check for Pydantic sentinel values)
        try:
            from pydantic_core import PydanticUndefined

            has_pydantic_core = True
        except ImportError:
            # Fallback for older Pydantic versions
            PydanticUndefined = type("PydanticUndefined", (), {})()
            has_pydantic_core = False

        if (
            field_info.default is not None
            and field_info.default != ...
            and (not has_pydantic_core or field_info.default is not PydanticUndefined)
            and not (
                hasattr(field_info.default, "__class__") and "PydanticUndefined" in str(field_info.default.__class__)
            )
        ):
            # Only add default if it's a JSON-serializable value
            try:
                json.dumps(field_info.default)  # Test if serializable
                schema["default"] = field_info.default
            except (TypeError, ValueError):
                # Skip non-serializable defaults like factory functions
                pass

        return schema

    def _get_request_model(self) -> Optional[Type[BaseModel]]:
        """Get the appropriate request model for mode and complexity"""
        if not self._request_model:
            key = (self.mode, self.complexity)
            self._request_model = MODE_REQUEST_MAP.get(key)

        return self._request_model

    def _get_actual_tool(self) -> Optional[BaseTool]:
        """
        Lazy-load the actual tool implementation.

        This avoids importing all tools upfront, further reducing memory usage.
        """
        if self._actual_tool:
            return self._actual_tool

        try:
            # Dynamic import based on mode
            if self.mode == "debug":
                from .debug import DebugIssueTool

                self._actual_tool = DebugIssueTool()
            elif self.mode == "codereview":
                from .codereview import CodeReviewTool

                self._actual_tool = CodeReviewTool()
            elif self.mode == "analyze":
                from .analyze import AnalyzeTool

                self._actual_tool = AnalyzeTool()
            elif self.mode == "consensus":
                from .consensus import ConsensusTool

                self._actual_tool = ConsensusTool()
            elif self.mode == "chat":
                from .chat import ChatTool

                self._actual_tool = ChatTool()
            elif self.mode == "security":
                from .secaudit import SecauditTool

                self._actual_tool = SecauditTool()
            elif self.mode == "refactor":
                from .refactor import RefactorTool

                self._actual_tool = RefactorTool()
            elif self.mode == "testgen":
                from .testgen import TestGenTool

                self._actual_tool = TestGenTool()
            elif self.mode == "planner":
                from .planner import PlannerTool

                self._actual_tool = PlannerTool()
            elif self.mode == "tracer":
                from .tracer import TracerTool

                self._actual_tool = TracerTool()

            return self._actual_tool

        except ImportError as e:
            logger.error(f"Failed to import tool for mode {self.mode}: {e}")
            return None

    async def execute(self, arguments: dict[str, Any]) -> list:
        """
        Execute the appropriate tool with the provided arguments.

        This delegates to the actual tool implementation after validating
        the arguments against the minimal schema.
        """
        try:
            # Get the actual tool
            tool = self._get_actual_tool()
            if not tool:
                raise ValueError(f"Tool implementation not found for mode: {self.mode}")

            # Validate arguments against our minimal schema
            request_model = self._get_request_model()
            if request_model:
                # Validate with the minimal model
                validated = request_model(**arguments)
                # Convert back to dict for the actual tool
                arguments = validated.model_dump(exclude_none=True)

            # Special handling for consensus simple mode
            if self.mode == "consensus" and self.complexity == "simple":
                # Convert simple request to workflow format
                if "prompt" in arguments and "models" in arguments:
                    # This is a simple consensus request, convert to workflow
                    arguments = {
                        "step": arguments["prompt"],  # The question becomes the step
                        "step_number": 1,
                        "total_steps": len(arguments["models"]) + 1,  # One step per model + synthesis
                        "next_step_required": True,
                        "findings": "Starting consensus analysis",
                        "models": arguments["models"],
                        "relevant_files": arguments.get("relevant_files", []),
                        "images": arguments.get("images", []),
                        "current_model_index": 0,
                        "model_responses": [],
                    }

            # Special handling for debug simple mode
            if self.mode == "debug" and self.complexity == "simple":
                # Convert simple request to workflow format
                if "problem" in arguments:
                    # This is a simple debug request, convert to workflow
                    arguments = {
                        "step": arguments["problem"][:100],  # Use problem as first step
                        "step_number": 1,
                        "total_steps": 3,  # Default to 3-step investigation
                        "next_step_required": True,
                        "findings": arguments["problem"],
                        "files_checked": [],
                        "confidence": arguments.get("confidence", "exploring"),
                        "hypothesis": arguments.get("hypothesis"),
                    }

            # Special handling for codereview simple mode
            if self.mode == "codereview" and self.complexity == "simple":
                # Convert simple request to workflow format
                if "files" in arguments:
                    # This is a simple codereview request, convert to workflow
                    review_focus = arguments.get("focus", "code quality")
                    arguments = {
                        "step": f"Code review of {len(arguments['files'])} file(s) - {review_focus}",
                        "step_number": 1,
                        "total_steps": 1,
                        "next_step_required": False,
                        "findings": f"Starting {arguments.get('review_type', 'full')} code review",
                        "files_checked": [],
                        "relevant_files": arguments["files"],
                        "relevant_context": [],
                        "issues_found": [],
                        "confidence": "medium",
                        "review_type": arguments.get("review_type", "full"),
                        "focus": arguments.get("focus"),
                    }

            # Execute the actual tool
            result = await tool.execute(arguments)

            # Add metadata about token savings
            if result and isinstance(result[0], TextContent):
                try:
                    data = json.loads(result[0].text)
                    data["_meta"] = {
                        "mode": self.mode,
                        "complexity": self.complexity,
                        "token_optimized": True,
                        "schema_size": len(json.dumps(self.get_input_schema())),
                    }
                    result[0] = TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))
                except (json.JSONDecodeError, KeyError):
                    pass  # Keep original result if not JSON

            return result

        except Exception as e:
            logger.error(f"Error executing {self.mode} tool: {e}", exc_info=True)

            # Enhanced error handling for validation errors
            from pydantic import ValidationError

            if isinstance(e, ValidationError):
                # Parse validation errors to provide helpful guidance
                error_details = []
                for error in e.errors():
                    field = error['loc'][0] if error['loc'] else 'unknown'
                    error_type = error['type']

                    # Build detailed error info with field descriptions and examples
                    field_info = self._get_field_info(field)

                    error_detail = {
                        "field": field,
                        "error": error['msg'],
                        "description": field_info.get("description", "No description available"),
                        "type": field_info.get("type", "unknown"),
                        "example": field_info.get("example", "N/A")
                    }

                    error_details.append(error_detail)

                error_data = {
                    "status": "validation_error",
                    "mode": self.mode,
                    "complexity": self.complexity,
                    "message": f"Request validation failed for {self.mode} mode with {self.complexity} complexity",
                    "errors": error_details,
                    "hint": "💡 Use zen_select_mode first to get the correct schema and working examples",
                    "schema_reference": f"Required fields for {self.mode}/{self.complexity}",
                    "working_example": self._get_example_request()
                }
            else:
                # Generic error for non-validation errors
                error_data = {
                    "status": "error",
                    "mode": self.mode,
                    "complexity": self.complexity,
                    "message": str(e),
                    "suggestion": "Check the parameters match the minimal schema for this mode",
                }

            return [TextContent(type="text", text=json.dumps(error_data, indent=2, ensure_ascii=False))]

    def get_request_model(self):
        """Return the minimal request model for this mode and complexity"""
        return self._get_request_model()

    def _get_field_info(self, field_name: str) -> dict:
        """
        Get detailed information about a field for enhanced error messages.

        Returns field description, type, and example value.
        """
        request_model = self._get_request_model()
        if not request_model or field_name not in request_model.model_fields:
            return {
                "description": "Unknown field",
                "type": "unknown",
                "example": "N/A"
            }

        field_info = request_model.model_fields[field_name]

        # Extract type information
        from typing import get_args, get_origin
        field_type = field_info.annotation
        if get_origin(field_type) is type(Optional):
            args = get_args(field_type)
            if args:
                field_type = args[0]

        # Map Python types to readable strings
        type_map = {
            str: "string",
            int: "integer",
            bool: "boolean",
            float: "number",
            list: "array",
            dict: "object"
        }
        type_str = type_map.get(field_type, str(field_type))

        # Get examples based on field name and mode
        examples = {
            "problem": "OAuth tokens not persisting across browser sessions",
            "files": ["/src/auth.py", "/src/session.py"],
            "confidence": "exploring",
            "step": "Initial investigation of authentication issue",
            "step_number": 1,
            "total_steps": 3,
            "findings": "Users report needing to re-authenticate after closing browser",
            "next_step_required": True,
            "relevant_files": ["/src/app.py", "/src/models.py"],
            "analysis_type": "architecture",
            "context": "Understanding the current microservices design",
            "review_type": "security",
            "prompt": "Explain the tradeoffs between REST and GraphQL",
            "models": [{"model": "gemini-pro"}, {"model": "o3-mini"}]
        }

        return {
            "description": field_info.description or f"{field_name} field",
            "type": type_str,
            "example": examples.get(field_name, "")
        }

    def _get_example_request(self) -> dict:
        """Return a working example for the current mode/complexity combination"""
        examples = {
            ("debug", "simple"): {
                "problem": "OAuth tokens not persisting across browser sessions",
                "files": ["/src/auth.py", "/src/session.py"],
                "confidence": "exploring"
            },
            ("debug", "workflow"): {
                "step": "Initial investigation of token persistence issue",
                "step_number": 1,
                "total_steps": 3,
                "findings": "Users report needing to re-authenticate after closing browser",
                "next_step_required": True
            },
            ("codereview", "simple"): {
                "files": ["/src/auth_handler.py"],
                "review_type": "security"
            },
            ("codereview", "workflow"): {
                "step": "Initial security review",
                "step_number": 1,
                "total_steps": 3,
                "findings": "Starting code review",
                "next_step_required": True
            },
            ("analyze", "simple"): {
                "relevant_files": ["/src/app.py", "/src/models.py"],
                "analysis_type": "architecture",
                "context": "Understanding the current microservices design"
            },
            ("chat", "simple"): {
                "prompt": "Explain the difference between REST and GraphQL APIs"
            },
            ("consensus", "simple"): {
                "prompt": "Should we use microservices or monolith architecture?",
                "models": [{"model": "gemini-pro"}, {"model": "o3-mini"}]
            }
        }

        key = (self.mode, self.complexity)
        return examples.get(key, {"prompt": f"Example {self.mode} request"})

    async def prepare_prompt(self, request) -> str:
        """Not used - mode executors use execute() directly."""
        return ""  # Mode executors delegate to actual tools


def create_mode_executor(mode: str, complexity: str = "simple") -> ModeExecutor:
    """
    Factory function to create mode-specific executors.

    This is used by the server to dynamically create executors based on
    the mode selected in stage 1.
    """
    return ModeExecutor(mode, complexity)
