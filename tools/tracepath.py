"""
TracePath tool - Static call path prediction and control flow analysis

This tool analyzes code to predict and explain full call paths and control flow without executing code.
Given a method name, its owning class/module, and parameter combinations or runtime values, it predicts
the complete chain of method/function calls that would be triggered.

Key Features:
- Static call path prediction with confidence levels
- Polymorphism and dynamic dispatch analysis
- Value-driven flow analysis based on parameter combinations
- Side effects identification (database, network, filesystem)
- Branching analysis for conditional logic
- Hybrid AI-first approach with optional AST preprocessing for enhanced accuracy
"""

import logging
import os
import re
from typing import Any, Literal, Optional

from pydantic import Field

from config import TEMPERATURE_ANALYTICAL
from systemprompts import TRACEPATH_PROMPT

from .base import BaseTool, ToolRequest

logger = logging.getLogger(__name__)


class TracePathRequest(ToolRequest):
    """
    Request model for the tracepath tool.

    This model defines all parameters for customizing the call path analysis process.
    """

    entry_point: str = Field(
        ...,
        description="Method/function to trace (e.g., 'BookingManager::finalizeInvoice', 'utils.validate_input')",
    )
    files: list[str] = Field(
        ...,
        description="Code files or directories to analyze (must be absolute paths)",
    )
    parameters: Optional[dict[str, Any]] = Field(
        None,
        description="Parameter values to analyze - format: {param_name: value_or_type}",
    )
    context: Optional[str] = Field(
        None,
        description="Additional context about analysis goals or specific scenarios to focus on",
    )
    analysis_depth: Literal["shallow", "medium", "deep"] = Field(
        "medium",
        description="Analysis depth: shallow (direct calls), medium (2-3 levels), deep (full trace)",
    )
    language: Optional[str] = Field(
        None,
        description="Override auto-detection: python, javascript, typescript, csharp, java",
    )
    signature: Optional[str] = Field(
        None,
        description="Fully-qualified signature for overload resolution in languages like C#/Java",
    )
    confidence_threshold: Optional[float] = Field(
        0.7,
        description="Filter speculative branches (0-1, default 0.7)",
        ge=0.0,
        le=1.0,
    )
    include_db: bool = Field(
        True,
        description="Include database interactions in side effects analysis",
    )
    include_network: bool = Field(
        True,
        description="Include network calls in side effects analysis",
    )
    include_fs: bool = Field(
        True,
        description="Include filesystem operations in side effects analysis",
    )
    export_format: Literal["markdown", "json", "plantuml"] = Field(
        "markdown",
        description="Output format for the analysis results",
    )
    focus_areas: Optional[list[str]] = Field(
        None,
        description="Specific aspects to focus on (e.g., 'performance', 'security', 'error_handling')",
    )


class TracePathTool(BaseTool):
    """
    TracePath tool implementation.

    This tool analyzes code to predict static call paths and control flow without execution.
    Uses a hybrid AI-first approach with optional AST preprocessing for enhanced accuracy.
    """

    def get_name(self) -> str:
        return "tracepath"

    def get_description(self) -> str:
        return (
            "STATIC CALL PATH ANALYSIS - Predicts and explains full call paths and control flow without executing code. "
            "Given a method/function name and parameter values, traces the complete execution path including "
            "conditional branches, polymorphism resolution, and side effects. "
            "Perfect for: understanding complex code flows, impact analysis, debugging assistance, architecture review. "
            "Provides confidence levels for predictions and identifies uncertain calls due to dynamic behavior. "
            "Choose thinking_mode based on code complexity: 'low' for simple functions, "
            "'medium' for standard analysis (default), 'high' for complex systems, "
            "'max' for legacy codebases requiring deep analysis. "
            "Note: If you're not currently using a top-tier model such as Opus 4 or above, these tools can provide enhanced capabilities."
        )

    def get_input_schema(self) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "entry_point": {
                    "type": "string",
                    "description": "Method/function to trace (e.g., 'BookingManager::finalizeInvoice', 'utils.validate_input')",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Code files or directories to analyze (must be absolute paths)",
                },
                "model": self.get_model_field_schema(),
                "parameters": {
                    "type": "object",
                    "description": "Parameter values to analyze - format: {param_name: value_or_type}",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about analysis goals or specific scenarios to focus on",
                },
                "analysis_depth": {
                    "type": "string",
                    "enum": ["shallow", "medium", "deep"],
                    "default": "medium",
                    "description": "Analysis depth: shallow (direct calls), medium (2-3 levels), deep (full trace)",
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "typescript", "csharp", "java"],
                    "description": "Override auto-detection for programming language",
                },
                "signature": {
                    "type": "string",
                    "description": "Fully-qualified signature for overload resolution",
                },
                "confidence_threshold": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.7,
                    "description": "Filter speculative branches (0-1)",
                },
                "include_db": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include database interactions in analysis",
                },
                "include_network": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include network calls in analysis",
                },
                "include_fs": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include filesystem operations in analysis",
                },
                "export_format": {
                    "type": "string",
                    "enum": ["markdown", "json", "plantuml"],
                    "default": "markdown",
                    "description": "Output format for analysis results",
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific aspects to focus on",
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature (0-1, default 0.2 for analytical precision)",
                    "minimum": 0,
                    "maximum": 1,
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Thinking depth: minimal (0.5% of model max), low (8%), medium (33%), high (67%), max (100% of model max)",
                },
                "use_websearch": {
                    "type": "boolean",
                    "description": "Enable web search for framework documentation and patterns",
                    "default": True,
                },
                "continuation_id": {
                    "type": "string",
                    "description": "Thread continuation ID for multi-turn conversations across tools",
                },
            },
            "required": ["entry_point", "files"] + (["model"] if self.is_effective_auto_mode() else []),
        }

        return schema

    def get_system_prompt(self) -> str:
        return TRACEPATH_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    # Line numbers are enabled by default for precise code references

    def get_model_category(self):
        """TracePath requires extended reasoning for complex flow analysis"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.EXTENDED_REASONING

    def get_request_model(self):
        return TracePathRequest

    def detect_primary_language(self, file_paths: list[str]) -> str:
        """
        Detect the primary programming language from file extensions.

        Args:
            file_paths: List of file paths to analyze

        Returns:
            str: Detected language or "mixed" if multiple languages found
        """
        # Language detection based on file extensions
        language_extensions = {
            "python": {".py", ".pyx", ".pyi"},
            "javascript": {".js", ".jsx", ".mjs", ".cjs"},
            "typescript": {".ts", ".tsx", ".mts", ".cts"},
            "java": {".java"},
            "csharp": {".cs"},
            "cpp": {".cpp", ".cc", ".cxx", ".c", ".h", ".hpp"},
            "go": {".go"},
            "rust": {".rs"},
            "swift": {".swift"},
            "kotlin": {".kt", ".kts"},
            "ruby": {".rb"},
            "php": {".php"},
            "scala": {".scala"},
        }

        # Count files by language
        language_counts = {}
        for file_path in file_paths:
            extension = os.path.splitext(file_path.lower())[1]
            for lang, exts in language_extensions.items():
                if extension in exts:
                    language_counts[lang] = language_counts.get(lang, 0) + 1
                    break

        if not language_counts:
            return "unknown"

        # Return most common language, or "mixed" if multiple languages
        max_count = max(language_counts.values())
        dominant_languages = [lang for lang, count in language_counts.items() if count == max_count]

        if len(dominant_languages) == 1:
            return dominant_languages[0]
        else:
            return "mixed"

    def parse_entry_point(self, entry_point: str, language: str) -> dict[str, str]:
        """
        Parse entry point string to extract class/module and method/function information.

        Args:
            entry_point: Entry point string (e.g., "BookingManager::finalizeInvoice", "utils.validate_input")
            language: Detected or specified programming language

        Returns:
            dict: Parsed entry point information
        """
        result = {
            "raw": entry_point,
            "class_or_module": "",
            "method_or_function": "",
            "type": "unknown",
        }

        # Common patterns across languages
        patterns = {
            # Class::method (C++, PHP style)
            "class_method_double_colon": r"^([A-Za-z_][A-Za-z0-9_]*?)::([A-Za-z_][A-Za-z0-9_]*?)$",
            # Module.function or Class.method (Python, JavaScript, etc.)
            "module_function_dot": r"^([A-Za-z_][A-Za-z0-9_]*?)\.([A-Za-z_][A-Za-z0-9_]*?)$",
            # Nested module.submodule.function
            "nested_module_dot": r"^([A-Za-z_][A-Za-z0-9_.]*?)\.([A-Za-z_][A-Za-z0-9_]*?)$",
            # Just function name
            "function_only": r"^([A-Za-z_][A-Za-z0-9_]*?)$",
        }

        # Try patterns in order of specificity
        for pattern_name, pattern in patterns.items():
            match = re.match(pattern, entry_point.strip())
            if match:
                if pattern_name == "function_only":
                    result["method_or_function"] = match.group(1)
                    result["type"] = "function"
                else:
                    result["class_or_module"] = match.group(1)
                    result["method_or_function"] = match.group(2)

                    # Determine if it's a class method or module function based on naming conventions
                    if pattern_name == "class_method_double_colon":
                        result["type"] = "method"
                    elif result["class_or_module"][0].isupper():
                        result["type"] = "method"  # Likely class method (CamelCase)
                    else:
                        result["type"] = "function"  # Likely module function (snake_case)
                break

        logger.debug(f"[TRACEPATH] Parsed entry point '{entry_point}' as: {result}")
        return result

    async def _generate_structural_summary(self, files: list[str], language: str) -> str:
        """
        Generate structural summary of the code using AST parsing.

        Phase 1: Returns empty string (pure AI-driven approach)
        Phase 2: Will contain language-specific AST parsing logic

        Args:
            files: List of file paths to analyze
            language: Detected programming language

        Returns:
            str: Structural summary or empty string for Phase 1
        """
        # Phase 1 implementation: Pure AI-driven approach
        # Phase 2 will add AST parsing for enhanced context

        if language == "python":
            # Placeholder for Python AST parsing using built-in 'ast' module
            # Will extract class definitions, method signatures, and direct calls
            pass
        elif language in ["javascript", "typescript"]:
            # Placeholder for JavaScript/TypeScript parsing using acorn or TS compiler API
            pass
        elif language == "csharp":
            # Placeholder for C# parsing using Microsoft Roslyn SDK
            pass
        elif language == "java":
            # Placeholder for Java parsing (future implementation)
            pass

        # For Phase 1, return empty to rely on pure LLM analysis
        logger.debug(f"[TRACEPATH] Phase 1: No structural summary generated for {language}")
        return ""

    async def prepare_prompt(self, request: TracePathRequest) -> str:
        """
        Prepare the complete prompt for call path analysis.

        This method combines:
        - System prompt with analysis instructions
        - User context and entry point information
        - File contents with line numbers
        - Structural summary (Phase 2)
        - Analysis parameters and constraints

        Args:
            request: The validated tracepath request

        Returns:
            str: Complete prompt for the model

        Raises:
            ValueError: If the prompt exceeds token limits
        """
        logger.info(
            f"[TRACEPATH] Preparing prompt for entry point '{request.entry_point}' with {len(request.files)} files"
        )
        logger.debug(f"[TRACEPATH] Analysis depth: {request.analysis_depth}, Export format: {request.export_format}")

        # Check for prompt.txt in files
        prompt_content, updated_files = self.handle_prompt_file(request.files)

        # If prompt.txt was found, incorporate it into the context
        if prompt_content:
            logger.debug("[TRACEPATH] Found prompt.txt file, incorporating content")
            if request.context:
                request.context = prompt_content + "\n\n" + request.context
            else:
                request.context = prompt_content

        # Update request files list
        if updated_files is not None:
            logger.debug(f"[TRACEPATH] Updated files list after prompt.txt processing: {len(updated_files)} files")
            request.files = updated_files

        # Check user input size at MCP transport boundary (before adding internal content)
        if request.context:
            size_check = self.check_prompt_size(request.context)
            if size_check:
                from tools.models import ToolOutput

                raise ValueError(f"MCP_SIZE_CHECK:{ToolOutput(**size_check).model_dump_json()}")

        # Detect or use specified language
        if request.language:
            primary_language = request.language
            logger.debug(f"[TRACEPATH] Using specified language: {primary_language}")
        else:
            primary_language = self.detect_primary_language(request.files)
            logger.debug(f"[TRACEPATH] Detected primary language: {primary_language}")

        # Parse entry point
        entry_point_info = self.parse_entry_point(request.entry_point, primary_language)
        logger.debug(f"[TRACEPATH] Entry point parsed as: {entry_point_info}")

        # Generate structural summary (Phase 1: returns empty, Phase 2: AST analysis)
        continuation_id = getattr(request, "continuation_id", None)
        structural_summary = await self._generate_structural_summary(request.files, primary_language)

        # Use centralized file processing logic for main code files (with line numbers enabled)
        logger.debug(f"[TRACEPATH] Preparing {len(request.files)} code files for analysis")
        code_content = self._prepare_file_content_for_prompt(request.files, continuation_id, "Code to analyze")

        if code_content:
            from utils.token_utils import estimate_tokens

            code_tokens = estimate_tokens(code_content)
            logger.info(f"[TRACEPATH] Code files embedded successfully: {code_tokens:,} tokens")
        else:
            logger.warning("[TRACEPATH] No code content after file processing")

        # Build the complete prompt
        prompt_parts = []

        # Add system prompt
        prompt_parts.append(self.get_system_prompt())

        # Add structural summary if available (Phase 2)
        if structural_summary:
            prompt_parts.append("\n=== STRUCTURAL SUMMARY ===")
            prompt_parts.append(structural_summary)
            prompt_parts.append("=== END STRUCTURAL SUMMARY ===")

        # Add user context and analysis parameters
        prompt_parts.append("\n=== ANALYSIS REQUEST ===")
        prompt_parts.append(f"Entry Point: {request.entry_point}")
        if entry_point_info["type"] != "unknown":
            prompt_parts.append(
                f"Parsed as: {entry_point_info['type']} '{entry_point_info['method_or_function']}' in {entry_point_info['class_or_module'] or 'global scope'}"
            )

        prompt_parts.append(f"Language: {primary_language}")
        prompt_parts.append(f"Analysis Depth: {request.analysis_depth}")
        prompt_parts.append(f"Confidence Threshold: {request.confidence_threshold}")

        if request.signature:
            prompt_parts.append(f"Method Signature: {request.signature}")

        if request.parameters:
            prompt_parts.append(f"Parameter Values: {request.parameters}")

        # Side effects configuration
        side_effects = []
        if request.include_db:
            side_effects.append("database")
        if request.include_network:
            side_effects.append("network")
        if request.include_fs:
            side_effects.append("filesystem")
        if side_effects:
            prompt_parts.append(f"Include Side Effects: {', '.join(side_effects)}")

        if request.focus_areas:
            prompt_parts.append(f"Focus Areas: {', '.join(request.focus_areas)}")

        if request.context:
            prompt_parts.append(f"Additional Context: {request.context}")

        prompt_parts.append(f"Export Format: {request.export_format}")
        prompt_parts.append("=== END REQUEST ===")

        # Add web search instruction if enabled
        websearch_instruction = self.get_websearch_instruction(
            request.use_websearch,
            f"""When analyzing call paths for {primary_language} code, consider if searches for these would help:
- Framework-specific call patterns and lifecycle methods
- Language-specific dispatch mechanisms and polymorphism
- Common side-effect patterns for libraries used in the code
- Documentation for external APIs and services called
- Known design patterns that affect call flow""",
        )
        if websearch_instruction:
            prompt_parts.append(websearch_instruction)

        # Add main code to analyze
        prompt_parts.append("\n=== CODE TO ANALYZE ===")
        prompt_parts.append(code_content)
        prompt_parts.append("=== END CODE ===")

        # Add analysis instructions
        analysis_instructions = [
            f"\nPlease perform a {request.analysis_depth} static call path analysis for the entry point '{request.entry_point}'."
        ]

        if request.parameters:
            analysis_instructions.append(
                "Pay special attention to how the provided parameter values affect the execution flow."
            )

        if request.confidence_threshold < 1.0:
            analysis_instructions.append(
                f"Filter out speculative paths with confidence below {request.confidence_threshold}."
            )

        analysis_instructions.append(f"Format the output as {request.export_format}.")

        prompt_parts.extend(analysis_instructions)

        full_prompt = "\n".join(prompt_parts)

        # Log final prompt statistics
        from utils.token_utils import estimate_tokens

        total_tokens = estimate_tokens(full_prompt)
        logger.info(f"[TRACEPATH] Complete prompt prepared: {total_tokens:,} tokens, {len(full_prompt):,} characters")

        return full_prompt

    def format_response(self, response: str, request: TracePathRequest, model_info: Optional[dict] = None) -> str:
        """
        Format the call path analysis response.

        The base tool handles structured response validation via SPECIAL_STATUS_MODELS,
        so this method focuses on providing clear guidance for next steps.

        Args:
            response: The raw analysis from the model
            request: The original request for context
            model_info: Optional dict with model metadata

        Returns:
            str: The response with additional guidance
        """
        logger.debug(f"[TRACEPATH] Formatting response for entry point '{request.entry_point}'")

        # Get the friendly model name
        model_name = "the model"
        if model_info and model_info.get("model_response"):
            model_name = model_info["model_response"].friendly_name or "the model"

        # Add contextual footer based on analysis depth and format
        if request.export_format == "json":
            footer = f"""
---

**Analysis Complete**: {model_name} has provided a structured JSON analysis of the call path for `{request.entry_point}`.

**Next Steps**:
- Review the confidence levels for each predicted call
- Investigate any uncertain calls marked with low confidence
- Use this analysis for impact assessment, debugging, or architecture review
- For deeper analysis, increase analysis_depth to 'deep' or provide additional context files
"""
        elif request.export_format == "plantuml":
            footer = f"""
---

**Analysis Complete**: {model_name} has generated a PlantUML diagram showing the call path for `{request.entry_point}`.

**Next Steps**:
- Render the PlantUML diagram to visualize the call flow
- Review branching points and conditional logic
- Verify the predicted paths against your understanding of the code
- Use this for documentation or architectural discussions
"""
        else:  # markdown
            footer = f"""
---

**Analysis Complete**: {model_name} has traced the execution path for `{request.entry_point}` at {request.analysis_depth} depth.

**Next Steps**:
- Review the call path summary and confidence assessments
- Pay attention to uncertain calls that may require runtime verification
- Use the code anchors (file:line references) to navigate to critical decision points
- Consider this analysis for debugging, impact assessment, or refactoring decisions
"""

        return f"{response}{footer}"
