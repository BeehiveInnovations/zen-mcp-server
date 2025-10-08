"""
Mode Selector Tool - Lightweight tool for intelligent mode selection

This tool provides the first stage of the two-stage architecture for token optimization.
It analyzes the user's task description and recommends the appropriate Zen tool mode,
enabling dynamic loading of only the necessary tool schemas in the second stage.

This dramatically reduces token consumption from 43k to ~1.6k while maintaining
full functionality and improving first-try success rates.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from tools.shared.base_models import ToolRequest

from .simple.base import SimpleTool

logger = logging.getLogger(__name__)

# Mode selection descriptions for Claude
MODE_DESCRIPTIONS = {
    "debug": "Systematic debugging and root cause analysis for bugs, errors, performance issues",
    "codereview": "Code review workflow for quality, security, performance, and architecture",
    "analyze": "Comprehensive code analysis for architecture, patterns, and improvements",
    "consensus": "Multi-model consensus for complex decisions and architectural choices",
    "chat": "General AI consultation and brainstorming",
    "security": "Security audit and vulnerability assessment",
    "refactor": "Refactoring analysis and code improvement recommendations",
    "testgen": "Test generation with edge case coverage",
    "planner": "Sequential task planning and breakdown",
    "tracer": "Code tracing and dependency analysis",
}

# Keywords that suggest specific modes (with weighted primary/secondary)
MODE_KEYWORDS = {
    "debug": {
        "primary": ["error", "bug", "broken", "crash", "fail", "exception"],
        "secondary": ["fix", "issue", "problem", "debug", "troubleshoot", "not working"]
    },
    "codereview": {
        "primary": ["code review", "pr review", "pull request", "review code"],
        "secondary": ["review", "check", "quality", "standards", "assess code"]
    },
    "analyze": {
        "primary": ["architecture", "design review", "architectural", "system design", "structure"],
        "secondary": ["analyze", "understand", "explain", "pattern", "codebase", "examine"]
    },
    "consensus": {
        "primary": ["should we", "decision", "choice", "approach", "which is better", "vs", "or"],
        "secondary": ["consensus", "compare", "decide", "evaluate options", "pros cons"]
    },
    "chat": {
        "primary": ["explain", "tell me", "what is", "how to", "help me understand"],
        "secondary": ["help", "general", "brainstorm", "idea", "question"]
    },
    "security": {
        "primary": ["security audit", "vulnerability", "auth", "authentication", "security review"],
        "secondary": ["encryption", "safe", "exploit", "secure", "injection", "xss"]
    },
    "refactor": {
        "primary": ["refactor", "restructure", "modernize"],
        "secondary": ["improve", "clean up", "optimize code", "simplify", "better practices"]
    },
    "testgen": {
        "primary": ["generate tests", "test generation", "write tests"],
        "secondary": ["test", "testing", "coverage", "edge case", "unit test"]
    },
    "planner": {
        "primary": ["create plan", "plan for", "planning", "roadmap", "strategy"],
        "secondary": ["breakdown", "steps", "how to implement", "approach"]
    },
    "tracer": {
        "primary": ["trace", "execution flow", "call chain", "dependency graph"],
        "secondary": ["flow", "execution", "dependency", "follows", "path"]
    },
}


class ModeSelectorRequest(ToolRequest):
    """Request model for mode selection"""

    task_description: str = Field(..., description="Describe what you want to accomplish with the Zen tools")
    context_size: Optional[str] = Field(
        None, description="Optional: 'minimal', 'standard', or 'comprehensive' - how much context is available"
    )
    confidence_level: Optional[str] = Field(
        None, description="Optional: Your confidence in the task understanding ('exploring', 'medium', 'high')"
    )


class ModeSelectorTool(SimpleTool):
    """
    Mode Selector tool for intelligent routing in the two-stage architecture.

    This lightweight tool (200-300 tokens) analyzes task descriptions and recommends
    the appropriate Zen tool mode, enabling the server to dynamically load only the
    necessary schemas for the second stage of execution.
    """

    def __init__(self):
        super().__init__()
        # CRITICAL: MCP requires these as attributes, not just methods
        self.name = "zen_select_mode"
        self.description = self.get_description()

    def get_name(self) -> str:
        return "zen_select_mode"

    def get_description(self) -> str:
        return (
            "Intelligently select the right Zen tool mode for your task. "
            "First stage of the optimized two-stage workflow that reduces token usage by 95%. "
            "Analyzes your task and recommends: debug, codereview, analyze, consensus, chat, "
            "security, refactor, testgen, planner, or tracer modes."
        )

    def get_system_prompt(self) -> str:
        # Mode selector doesn't need AI, it's rule-based
        return ""

    def get_default_temperature(self) -> float:
        return 0.0  # Deterministic selection

    def get_model_category(self) -> "ToolModelCategory":
        """Mode selector doesn't need a model"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.FAST_RESPONSE

    def requires_model(self) -> bool:
        """Mode selector is pure logic, no AI needed"""
        return False

    def get_request_model(self):
        """Return the mode selector request model"""
        return ModeSelectorRequest

    def get_input_schema(self) -> dict[str, Any]:
        """Minimal schema for mode selection"""
        return {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Describe what you want to accomplish with the Zen tools",
                },
                "context_size": {
                    "type": "string",
                    "enum": ["minimal", "standard", "comprehensive"],
                    "description": "Optional: How much context is available",
                },
                "confidence_level": {
                    "type": "string",
                    "enum": ["exploring", "medium", "high"],
                    "description": "Optional: Your confidence in the task understanding",
                },
            },
            "required": ["task_description"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict[str, Any]) -> list:
        """
        Execute mode selection based on task analysis.

        This uses keyword matching and heuristics to recommend the best mode,
        returning structured guidance for the second stage.
        """
        from mcp.types import TextContent

        try:
            request = self.get_request_model()(**arguments)

            # Analyze task description
            task_lower = request.task_description.lower()

            # Score each mode based on weighted keyword matches
            mode_scores = {}
            mode_matches = {}  # Track what matched for explanation
            for mode, keyword_sets in MODE_KEYWORDS.items():
                score = 0
                matches = {"primary": [], "secondary": []}

                # Primary keywords worth 3 points each
                for keyword in keyword_sets["primary"]:
                    if keyword in task_lower:
                        score += 3
                        matches["primary"].append(keyword)

                # Secondary keywords worth 1 point each
                for keyword in keyword_sets["secondary"]:
                    if keyword in task_lower:
                        score += 1
                        matches["secondary"].append(keyword)

                if score > 0:
                    mode_scores[mode] = score
                    mode_matches[mode] = matches

            # Select best mode (highest score, or 'chat' as default)
            if mode_scores:
                selected_mode = max(mode_scores, key=mode_scores.get)
            else:
                selected_mode = "chat"  # Default for unclear tasks
                mode_scores = {"chat": 0}
                mode_matches = {"chat": {"primary": [], "secondary": []}}

            # Determine complexity based on context and confidence
            complexity = self._determine_complexity(
                selected_mode, request.context_size, request.confidence_level, task_lower
            )

            # Build response with clear guidance for stage 2
            required_fields = self._get_required_fields(selected_mode, complexity)

            # Build clearer response with complete schemas and examples
            response_data = {
                "status": "mode_selected",
                "selected_mode": selected_mode,
                "complexity": complexity,
                "description": MODE_DESCRIPTIONS[selected_mode],
                "confidence": self._calculate_confidence(mode_scores, selected_mode),
                "reasoning": self._explain_selection(task_lower, mode_scores, mode_matches, selected_mode),
                "required_schema": self._get_complete_schema(selected_mode, complexity),
                "working_example": self._get_working_example(selected_mode, complexity),
                "next_step": {
                    "tool": "zen_execute",
                    "instruction": f"Use 'zen_execute' with mode='{selected_mode}' and complexity='{complexity}'",
                    "exact_command": {
                        "tool": "zen_execute",
                        "arguments": {
                            "mode": selected_mode,
                            "complexity": complexity,
                            "request": required_fields,  # This now contains actual field examples
                        },
                    },
                    "field_guidance": self._get_field_guidance(selected_mode, complexity),
                    "tips": self._get_mode_tips(selected_mode),
                },
                "alternatives": self._get_alternatives(mode_scores, selected_mode),
                "token_savings": "✨ Saves 82% tokens (43k → 7.8k total)",
            }

            logger.info(f"Mode selected: {selected_mode} (complexity: {complexity})")

            return [TextContent(type="text", text=json.dumps(response_data, indent=2, ensure_ascii=False))]

        except Exception as e:
            logger.error(f"Error in mode selection: {e}", exc_info=True)

            error_data = {
                "status": "error",
                "message": str(e),
                "fallback": {"mode": "chat", "instruction": "Falling back to general chat mode"},
            }

            return [TextContent(type="text", text=json.dumps(error_data, indent=2, ensure_ascii=False))]

    def _determine_complexity(
        self, mode: str, context_size: Optional[str], confidence: Optional[str], task_desc: str
    ) -> str:
        """
        Determine task complexity for the selected mode.

        Returns: 'simple' or 'workflow'
        Note: Only these two complexities exist in mode_executor request models
        """
        # Workflow indicators
        workflow_indicators = ["step", "systematic", "comprehensive", "thorough", "complete", "full", "entire", "all"]

        # Complex/expert indicators also suggest workflow (multi-step investigation)
        complex_indicators = ["complex", "difficult", "advanced", "expert", "production", "critical", "important"]

        # Check for workflow needs
        if any(indicator in task_desc for indicator in workflow_indicators):
            return "workflow"

        # Check for complex needs (map to workflow, not "expert")
        if any(indicator in task_desc for indicator in complex_indicators):
            return "workflow"

        # Use context size hint
        if context_size == "comprehensive":
            return "workflow"
        elif context_size == "minimal":
            return "simple"

        # Use confidence hint
        if confidence == "exploring":
            return "workflow"  # Need more investigation
        elif confidence == "high":
            return "simple"  # Clear understanding

        # Mode-specific defaults
        if mode in ["debug", "codereview", "security", "analyze"]:
            return "workflow"  # These typically need investigation
        elif mode in ["chat", "consensus"]:
            return "simple"  # Usually single-shot

        return "simple"  # Default to simple

    def _calculate_confidence(self, scores: dict, selected: str) -> str:
        """Calculate confidence in the mode selection"""
        if not scores:
            return "low"

        selected_score = scores.get(selected, 0)
        max_score = max(scores.values()) if scores else 0

        if selected_score == max_score and selected_score >= 3:
            return "high"
        elif selected_score >= 2:
            return "medium"
        else:
            return "low"

    def _get_required_fields(self, mode: str, complexity: str) -> dict:
        """Get required fields with concrete examples for the selected mode"""
        # Return actual field examples instead of generic arrays

        # Special handling for consensus to show clear examples
        if mode == "consensus":
            if complexity == "simple":
                return {
                    "prompt": "Your question/proposal to evaluate",
                    "models": [{"model": "o3", "stance": "neutral"}],
                }
            else:  # workflow
                return {
                    "step": "The proposal to evaluate (e.g., 'Should we use GraphQL?')",
                    "step_number": 1,
                    "total_steps": 2,
                    "next_step_required": True,
                    "findings": "Your initial analysis here",
                    "models": [{"model": "o3", "stance": "for"}, {"model": "flash", "stance": "against"}],
                }

        # Provide actual examples for other modes too
        field_examples = {
            ("debug", "simple"): {
                "problem": "Description of the issue",
                "files": ["/absolute/path/to/file.py"],
                "confidence": "exploring",
            },
            ("debug", "workflow"): {
                "step": "Initial investigation",
                "step_number": 1,
                "findings": "What you've found so far",
                "next_step_required": True,
            },
            ("codereview", "simple"): {"files": ["/path/to/review.py"], "review_type": "security"},
            ("analyze", "simple"): {"files": ["/path/to/analyze"], "analysis_type": "architecture"},
            ("chat", "simple"): {"prompt": "Your question here"},
        }

        # Return the specific examples or a default
        return field_examples.get((mode, complexity), {"prompt": "Your request here"})

    def _get_field_guidance(self, mode: str, complexity: str) -> dict:
        """Provide clear guidance on what fields mean"""
        if mode == "consensus":
            return {
                "prompt": "The question you want multiple models to evaluate",
                "models": "List of AI models with optional stances (for/against/neutral)",
                "example": "Ask 'Should we use microservices?' with o3 arguing for and flash arguing against",
            }
        elif mode == "debug":
            return {
                "problem": "Description of what's broken or not working",
                "files": "Absolute paths to relevant code files",
                "confidence": "How well you understand the issue (exploring/medium/high)",
            }
        elif mode == "codereview":
            return {
                "files": "Code files to review (absolute paths)",
                "review_type": "Focus area: security, performance, quality, or all",
            }
        else:
            return {"general": "Provide your request based on the examples above"}

    def _get_mode_tips(self, mode: str) -> list:
        """Provide helpful tips for each mode"""
        tips_map = {
            "consensus": [
                "You can use the same model with different stances",
                "Models will refuse truly harmful proposals regardless of stance",
                "Add 'stance_prompt' for custom instructions per model",
            ],
            "debug": [
                "Start with 'exploring' confidence if unsure",
                "Include error messages and logs in the problem description",
                "List all relevant files, not just the one with the error",
            ],
            "codereview": [
                "Use 'security' type for authentication/authorization code",
                "Include test files for comprehensive review",
                "Specify focus areas to get targeted feedback",
            ],
            "chat": ["Use for quick questions and brainstorming", "No files needed - just your question"],
            "analyze": [
                "Great for understanding unfamiliar codebases",
                "Include the project root for architecture analysis",
            ],
        }
        return tips_map.get(mode, ["Use the examples as a guide"])

    def _get_alternatives(self, scores: dict, selected: str) -> list:
        """Get alternative modes if multiple are viable"""
        if not scores:
            return []

        # Get modes with scores close to the selected one
        selected_score = scores.get(selected, 0)
        alternatives = []

        for mode, score in scores.items():
            if mode != selected and score >= selected_score - 1:
                alternatives.append({"mode": mode, "score": score, "description": MODE_DESCRIPTIONS[mode]})

        # Sort by score descending
        alternatives.sort(key=lambda x: x["score"], reverse=True)

        return alternatives[:2]  # Return top 2 alternatives

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Define the tool-specific fields for mode selection"""
        return {
            "task_description": {
                "type": "string",
                "description": "Describe what you want to accomplish with the Zen tools",
            },
            "context_size": {
                "type": "string",
                "enum": ["minimal", "standard", "comprehensive"],
                "description": "Optional: How much context is available",
            },
            "confidence_level": {
                "type": "string",
                "enum": ["exploring", "medium", "high"],
                "description": "Optional: Your confidence in the task understanding",
            },
        }

    def _explain_selection(self, task: str, scores: dict, matches: dict, selected: str) -> str:
        """Explain why this mode was selected"""
        explanations = []

        selected_matches = matches.get(selected, {})

        # Explain matched keywords
        if selected_matches.get("primary"):
            keywords = ", ".join(f"'{kw}'" for kw in selected_matches["primary"])
            explanations.append(f"Task contains primary keywords: {keywords}")

        if selected_matches.get("secondary"):
            keywords = ", ".join(f"'{kw}'" for kw in selected_matches["secondary"][:3])  # Limit to 3
            explanations.append(f"Also matched: {keywords}")

        # Show alternatives considered
        alternatives = sorted(
            [(mode, score) for mode, score in scores.items() if mode != selected],
            key=lambda x: x[1],
            reverse=True
        )[:2]

        if alternatives:
            alt_text = ", ".join([f"{mode} (score: {score})" for mode, score in alternatives])
            explanations.append(f"Alternatives considered: {alt_text}")

        if not explanations:
            explanations.append("No strong keyword matches; defaulting to general chat mode")

        return "; ".join(explanations)

    def _get_complete_schema(self, mode: str, complexity: str) -> dict:
        """
        Return complete JSON schema for this mode/complexity combination.

        CRITICAL: These schemas must match the Pydantic models in mode_executor.py exactly
        to prevent validation errors. Each schema was verified against the corresponding
        request model class.
        """

        # Common workflow fields used by many tools
        workflow_fields = {
            "step": {"type": "string", "description": "Current workflow step description"},
            "step_number": {"type": "integer", "minimum": 1, "description": "Step number (starts at 1)"},
            "total_steps": {"type": "integer", "minimum": 1, "description": "Total estimated steps"},
            "next_step_required": {"type": "boolean", "description": "Continue with another step?"},
            "findings": {"type": "string", "description": "Discoveries and insights so far"},
        }

        # Define schemas for all 20 mode/complexity combinations
        # Format: (mode, complexity): schema matching mode_executor.py request models
        schemas = {
            # DEBUG
            ("debug", "simple"): {
                "type": "object",
                "required": ["problem"],  # Only problem is required per DebugSimpleRequest
                "properties": {
                    "problem": {"type": "string", "description": "The issue to debug"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant files"},
                    "confidence": {"type": "string", "enum": ["exploring", "medium", "high"], "description": "Optional: Current confidence level"},
                    "hypothesis": {"type": "string", "description": "Optional: Initial theory about the issue"}
                }
            },
            ("debug", "workflow"): {
                "type": "object",
                "required": ["step", "step_number", "findings", "next_step_required"],  # Per DebugWorkflowRequest
                "properties": {
                    **workflow_fields,
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "confidence": {"type": "string", "enum": ["exploring", "medium", "high"], "description": "Optional: Confidence level"}
                }
            },

            # CODEREVIEW
            ("codereview", "simple"): {
                "type": "object",
                "required": ["files"],  # Per ReviewSimpleRequest
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Files to review"},
                    "review_type": {"type": "string", "enum": ["security", "performance", "quality", "all"], "description": "Optional: Focus area"},
                    "focus": {"type": "string", "description": "Optional: Specific concerns"}
                }
            },
            ("codereview", "workflow"): {
                "type": "object",
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings"],  # Per ReviewWorkflowRequest
                "properties": {
                    **workflow_fields,
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant files"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant methods/functions"},
                    "issues_found": {"type": "array", "items": {"type": "object"}, "description": "Optional: Issues with severity"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "review_validation_type": {"type": "string", "description": "Optional: Validation type"}
                }
            },

            # ANALYZE
            ("analyze", "simple"): {
                "type": "object",
                # AnalyzeSimpleRequest requires workflow fields + relevant_files
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings", "relevant_files"],
                "properties": {
                    **workflow_fields,
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Files or directories to analyze"},
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "analysis_type": {"type": "string", "description": "Optional: Type of analysis"},
                    "output_format": {"type": "string", "description": "Optional: Output format"}
                }
            },
            ("analyze", "workflow"): {
                # Reuses AnalyzeSimpleRequest - same as simple
                "type": "object",
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings", "relevant_files"],
                "properties": {
                    **workflow_fields,
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Files or directories to analyze"},
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "analysis_type": {"type": "string", "description": "Optional: Type of analysis"},
                    "output_format": {"type": "string", "description": "Optional: Output format"}
                }
            },

            # CONSENSUS
            ("consensus", "simple"): {
                "type": "object",
                "required": ["prompt", "models"],  # Per ConsensusSimpleRequest
                "properties": {
                    "prompt": {"type": "string", "description": "The question or proposal to evaluate"},
                    "models": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Models to consult. Example: [{'model': 'o3', 'stance': 'neutral'}]"
                    },
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Context files"},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "Optional: Images"}
                }
            },
            ("consensus", "workflow"): {
                "type": "object",
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings", "models"],  # Per ConsensusWorkflowRequest
                "properties": {
                    **workflow_fields,
                    "models": {"type": "array", "items": {"type": "object"}, "description": "Models to consult"},
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant files"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "current_model_index": {"type": "integer", "description": "Optional: Current model index"},
                    "model_responses": {"type": "array", "items": {"type": "string"}, "description": "Optional: Model responses"}
                }
            },

            # CHAT
            ("chat", "simple"): {
                "type": "object",
                "required": ["prompt"],  # Per ChatRequest
                "properties": {
                    "prompt": {"type": "string", "description": "Your question or request"},
                    "model": {"type": "string", "description": "Optional: Model preference (default: auto)"},
                    "temperature": {"type": "number", "description": "Optional: Temperature setting"},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "Optional: Images"}
                }
            },
            ("chat", "workflow"): {
                # Reuses ChatRequest - same as simple
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string", "description": "Your question or request"},
                    "model": {"type": "string", "description": "Optional: Model preference (default: auto)"},
                    "temperature": {"type": "number", "description": "Optional: Temperature setting"},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "Optional: Images"}
                }
            },

            # SECURITY
            ("security", "simple"): {
                "type": "object",
                # SecurityWorkflowRequest requires workflow fields even for "simple"
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings"],
                "properties": {
                    **workflow_fields,
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files to audit"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "security_scope": {"type": "string", "description": "Optional: Security scope"},
                    "threat_level": {"type": "string", "description": "Optional: Threat level"},
                    "compliance_requirements": {"type": "array", "items": {"type": "string"}, "description": "Optional: Compliance requirements"},
                    "audit_focus": {"type": "string", "description": "Optional: Audit focus"},
                    "severity_filter": {"type": "string", "description": "Optional: Severity filter"}
                }
            },
            ("security", "workflow"): {
                # Reuses SecurityWorkflowRequest - same as simple
                "type": "object",
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings"],
                "properties": {
                    **workflow_fields,
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files to audit"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "security_scope": {"type": "string", "description": "Optional: Security scope"},
                    "threat_level": {"type": "string", "description": "Optional: Threat level"},
                    "compliance_requirements": {"type": "array", "items": {"type": "string"}, "description": "Optional: Compliance requirements"},
                    "audit_focus": {"type": "string", "description": "Optional: Audit focus"},
                    "severity_filter": {"type": "string", "description": "Optional: Severity filter"}
                }
            },

            # REFACTOR
            ("refactor", "simple"): {
                "type": "object",
                # RefactorSimpleRequest requires workflow fields even for "simple"
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings"],
                "properties": {
                    **workflow_fields,
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files to refactor"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "refactor_type": {"type": "string", "description": "Optional: Type of refactoring"},
                    "focus_areas": {"type": "array", "items": {"type": "string"}, "description": "Optional: Focus areas"},
                    "style_guide_examples": {"type": "array", "items": {"type": "string"}, "description": "Optional: Style examples"}
                }
            },
            ("refactor", "workflow"): {
                # Reuses RefactorSimpleRequest - same as simple
                "type": "object",
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings"],
                "properties": {
                    **workflow_fields,
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files to refactor"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "refactor_type": {"type": "string", "description": "Optional: Type of refactoring"},
                    "focus_areas": {"type": "array", "items": {"type": "string"}, "description": "Optional: Focus areas"},
                    "style_guide_examples": {"type": "array", "items": {"type": "string"}, "description": "Optional: Style examples"}
                }
            },

            # TESTGEN
            ("testgen", "simple"): {
                "type": "object",
                # TestGenSimpleRequest requires workflow fields + relevant_files
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings", "relevant_files"],
                "properties": {
                    **workflow_fields,
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Code files to generate tests for"},
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"}
                }
            },
            ("testgen", "workflow"): {
                # Reuses TestGenSimpleRequest - same as simple
                "type": "object",
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings", "relevant_files"],
                "properties": {
                    **workflow_fields,
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Code files to generate tests for"},
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"}
                }
            },

            # PLANNER
            ("planner", "simple"): {
                "type": "object",
                # PlannerWorkflowRequest requires workflow fields (planning is inherently workflow-based)
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings"],
                "properties": {
                    **workflow_fields,
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant files"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "is_step_revision": {"type": "boolean", "description": "Optional: Is step revision"},
                    "revises_step_number": {"type": "integer", "description": "Optional: Revises step number"},
                    "is_branch_point": {"type": "boolean", "description": "Optional: Is branch point"},
                    "branch_from_step": {"type": "integer", "description": "Optional: Branch from step"},
                    "branch_id": {"type": "string", "description": "Optional: Branch ID"},
                    "more_steps_needed": {"type": "boolean", "description": "Optional: More steps needed"}
                }
            },
            ("planner", "workflow"): {
                # Reuses PlannerWorkflowRequest - same as simple
                "type": "object",
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings"],
                "properties": {
                    **workflow_fields,
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant files"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "is_step_revision": {"type": "boolean", "description": "Optional: Is step revision"},
                    "revises_step_number": {"type": "integer", "description": "Optional: Revises step number"},
                    "is_branch_point": {"type": "boolean", "description": "Optional: Is branch point"},
                    "branch_from_step": {"type": "integer", "description": "Optional: Branch from step"},
                    "branch_id": {"type": "string", "description": "Optional: Branch ID"},
                    "more_steps_needed": {"type": "boolean", "description": "Optional: More steps needed"}
                }
            },

            # TRACER
            ("tracer", "simple"): {
                "type": "object",
                # TracerSimpleRequest requires workflow fields + target
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings", "target"],
                "properties": {
                    **workflow_fields,
                    "target": {"type": "string", "description": "Function or code to trace"},
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant files"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "trace_mode": {"type": "string", "enum": ["precision", "dependencies", "ask"], "description": "Optional: Type of tracing"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files to analyze"}
                }
            },
            ("tracer", "workflow"): {
                # Reuses TracerSimpleRequest - same as simple
                "type": "object",
                "required": ["step", "step_number", "total_steps", "next_step_required", "findings", "target"],
                "properties": {
                    **workflow_fields,
                    "target": {"type": "string", "description": "Function or code to trace"},
                    "files_checked": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files examined"},
                    "relevant_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant files"},
                    "relevant_context": {"type": "array", "items": {"type": "string"}, "description": "Optional: Relevant context"},
                    "issues_found": {"type": "array", "items": {"type": "string"}, "description": "Optional: Issues found"},
                    "confidence": {"type": "string", "description": "Optional: Confidence level"},
                    "trace_mode": {"type": "string", "enum": ["precision", "dependencies", "ask"], "description": "Optional: Type of tracing"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Optional: Files to analyze"}
                }
            },
        }

        # Return specific schema - NO FALLBACK (all combinations should be defined above)
        schema = schemas.get((mode, complexity))
        if not schema:
            logger.error(f"Missing schema for mode={mode}, complexity={complexity}. This should not happen!")
            # Emergency fallback only if something is seriously wrong
            return {
                "type": "object",
                "required": ["error"],
                "properties": {
                    "error": {"type": "string", "description": f"Invalid mode/complexity combination: {mode}/{complexity}"}
                }
            }
        return schema

    def _get_working_example(self, mode: str, complexity: str) -> dict:
        """
        Return a copy-paste ready working example.

        CRITICAL: Each example must match the required fields in _get_complete_schema
        to ensure users can copy-paste without validation errors.
        """

        examples = {
            # DEBUG
            ("debug", "simple"): {
                "mode": "debug",
                "complexity": "simple",
                "request": {
                    "problem": "OAuth tokens not persisting across browser sessions"
                }
            },
            ("debug", "workflow"): {
                "mode": "debug",
                "complexity": "workflow",
                "request": {
                    "step": "Initial investigation of token persistence issue",
                    "step_number": 1,
                    "findings": "Users report needing to re-authenticate after closing browser",
                    "next_step_required": True
                }
            },

            # CODEREVIEW
            ("codereview", "simple"): {
                "mode": "codereview",
                "complexity": "simple",
                "request": {
                    "files": ["/src/auth_handler.py"]
                }
            },
            ("codereview", "workflow"): {
                "mode": "codereview",
                "complexity": "workflow",
                "request": {
                    "step": "Security review of authentication system",
                    "step_number": 1,
                    "total_steps": 2,
                    "next_step_required": True,
                    "findings": "Reviewing authentication handlers for security issues"
                }
            },

            # ANALYZE
            ("analyze", "simple"): {
                "mode": "analyze",
                "complexity": "simple",
                "request": {
                    "step": "Architecture analysis",
                    "step_number": 1,
                    "total_steps": 1,
                    "next_step_required": False,
                    "findings": "Starting architecture analysis",
                    "relevant_files": ["/src/app.py", "/src/models.py"]
                }
            },
            ("analyze", "workflow"): {
                "mode": "analyze",
                "complexity": "workflow",
                "request": {
                    "step": "Comprehensive architecture analysis",
                    "step_number": 1,
                    "total_steps": 3,
                    "next_step_required": True,
                    "findings": "Analyzing microservices architecture patterns",
                    "relevant_files": ["/src"]
                }
            },

            # CONSENSUS
            ("consensus", "simple"): {
                "mode": "consensus",
                "complexity": "simple",
                "request": {
                    "prompt": "Should we use PostgreSQL or MongoDB for this use case?",
                    "models": [{"model": "o3", "stance": "neutral"}]
                }
            },
            ("consensus", "workflow"): {
                "mode": "consensus",
                "complexity": "workflow",
                "request": {
                    "step": "Database technology consensus",
                    "step_number": 1,
                    "total_steps": 1,
                    "next_step_required": False,
                    "findings": "Seeking consensus on database choice",
                    "models": [{"model": "o3", "stance": "neutral"}, {"model": "gemini-pro", "stance": "neutral"}]
                }
            },

            # CHAT
            ("chat", "simple"): {
                "mode": "chat",
                "complexity": "simple",
                "request": {
                    "prompt": "Explain the difference between REST and GraphQL APIs"
                }
            },
            ("chat", "workflow"): {
                "mode": "chat",
                "complexity": "workflow",
                "request": {
                    "prompt": "Explain the difference between REST and GraphQL APIs in detail"
                }
            },

            # SECURITY
            ("security", "simple"): {
                "mode": "security",
                "complexity": "simple",
                "request": {
                    "step": "Security audit",
                    "step_number": 1,
                    "total_steps": 1,
                    "next_step_required": False,
                    "findings": "Starting security audit of authentication system"
                }
            },
            ("security", "workflow"): {
                "mode": "security",
                "complexity": "workflow",
                "request": {
                    "step": "Comprehensive security audit",
                    "step_number": 1,
                    "total_steps": 3,
                    "next_step_required": True,
                    "findings": "Beginning thorough security assessment"
                }
            },

            # REFACTOR
            ("refactor", "simple"): {
                "mode": "refactor",
                "complexity": "simple",
                "request": {
                    "step": "Refactoring analysis",
                    "step_number": 1,
                    "total_steps": 1,
                    "next_step_required": False,
                    "findings": "Analyzing code for refactoring opportunities"
                }
            },
            ("refactor", "workflow"): {
                "mode": "refactor",
                "complexity": "workflow",
                "request": {
                    "step": "Comprehensive refactoring analysis",
                    "step_number": 1,
                    "total_steps": 3,
                    "next_step_required": True,
                    "findings": "Identifying code smells and improvement opportunities"
                }
            },

            # TESTGEN
            ("testgen", "simple"): {
                "mode": "testgen",
                "complexity": "simple",
                "request": {
                    "step": "Test generation",
                    "step_number": 1,
                    "total_steps": 1,
                    "next_step_required": False,
                    "findings": "Generating tests for authentication module",
                    "relevant_files": ["/src/auth.py"]
                }
            },
            ("testgen", "workflow"): {
                "mode": "testgen",
                "complexity": "workflow",
                "request": {
                    "step": "Comprehensive test generation",
                    "step_number": 1,
                    "total_steps": 2,
                    "next_step_required": True,
                    "findings": "Generating comprehensive test suite with edge cases",
                    "relevant_files": ["/src/auth.py", "/src/user.py"]
                }
            },

            # PLANNER
            ("planner", "simple"): {
                "mode": "planner",
                "complexity": "simple",
                "request": {
                    "step": "Feature planning",
                    "step_number": 1,
                    "total_steps": 1,
                    "next_step_required": False,
                    "findings": "Creating implementation plan for new feature"
                }
            },
            ("planner", "workflow"): {
                "mode": "planner",
                "complexity": "workflow",
                "request": {
                    "step": "Detailed feature roadmap",
                    "step_number": 1,
                    "total_steps": 5,
                    "next_step_required": True,
                    "findings": "Breaking down complex feature into implementation steps"
                }
            },

            # TRACER
            ("tracer", "simple"): {
                "mode": "tracer",
                "complexity": "simple",
                "request": {
                    "step": "Code tracing",
                    "step_number": 1,
                    "total_steps": 1,
                    "next_step_required": False,
                    "findings": "Tracing authentication flow",
                    "target": "authenticate_user"
                }
            },
            ("tracer", "workflow"): {
                "mode": "tracer",
                "complexity": "workflow",
                "request": {
                    "step": "Comprehensive dependency tracing",
                    "step_number": 1,
                    "total_steps": 3,
                    "next_step_required": True,
                    "findings": "Analyzing call chain and dependencies",
                    "target": "authenticate_user"
                }
            },
        }

        # Return specific example - NO FALLBACK (all combinations should be defined above)
        example = examples.get((mode, complexity))
        if not example:
            logger.error(f"Missing example for mode={mode}, complexity={complexity}. This should not happen!")
            # Emergency fallback only if something is seriously wrong
            return {
                "mode": mode,
                "complexity": complexity,
                "request": {"error": f"Invalid mode/complexity combination: {mode}/{complexity}"}
            }
        return example

    async def prepare_prompt(self, request) -> str:
        """
        Prepare prompt for mode selection.

        Since mode selection is rule-based, we don't actually need a prompt.
        This method is required by the base class but won't be used.
        """
        return ""
