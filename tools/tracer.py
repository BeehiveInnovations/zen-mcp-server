"""
Tracer tool - Static call path prediction and control flow analysis

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
from typing import Any, Literal, Optional

from pydantic import Field

from config import TEMPERATURE_ANALYTICAL
from systemprompts import TRACER_PROMPT

from .base import BaseTool, ToolRequest

logger = logging.getLogger(__name__)


class TracerRequest(ToolRequest):
    """
    Request model for the tracer tool.

    This model defines the simplified parameters for static code analysis.
    """

    prompt: str = Field(
        ...,
        description="Description of what to trace including method/function name and class/file context (e.g., 'Trace BookingManager::finalizeInvoice method' or 'Analyze dependencies for validate_input function in utils module')",
    )
    files: list[str] = Field(
        ...,
        description="Code files or directories to analyze (must be absolute paths)",
    )
    trace_mode: Literal["precision", "dependencies"] = Field(
        ...,
        description="Trace mode: 'precision' (follows actual code execution path from entry point) or 'dependencies' (analyzes bidirectional dependency mapping showing what calls this target and what it calls)",
    )


class TracerTool(BaseTool):
    """
    Tracer tool implementation.

    This tool analyzes code to predict static call paths and control flow without execution.
    Uses a hybrid AI-first approach with optional AST preprocessing for enhanced accuracy.
    """

    def get_name(self) -> str:
        return "tracer"

    def get_description(self) -> str:
        return (
            "STATIC CODE ANALYSIS - Analyzes code to provide either execution flow traces or dependency mappings without executing code. "
            "Type 'precision': Follows the actual code path from a specified method/function, resolving calls, branching, and side effects. "
            "Type 'dependencies': Analyzes bidirectional dependencies showing what calls the target and what it calls, including imports and inheritance. "
            "Perfect for: understanding complex code flows, impact analysis, debugging assistance, architecture review. "
            "Responds in structured JSON format for easy parsing and visualization. "
            "Choose thinking_mode based on code complexity: 'medium' for standard analysis (default), "
            "'high' for complex systems, 'max' for legacy codebases requiring deep analysis. "
            "Note: If you're not currently using a top-tier model such as Opus 4 or above, these tools can provide enhanced capabilities."
        )

    def get_input_schema(self) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of what to trace including method/function name and class/file context (e.g., 'Trace BookingManager::finalizeInvoice method' or 'Analyze dependencies for validate_input function in utils module')",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Code files or directories to analyze (must be absolute paths)",
                },
                "trace_mode": {
                    "type": "string",
                    "enum": ["precision", "dependencies"],
                    "description": "Trace mode: 'precision' (follows actual code execution path from entry point) or 'dependencies' (analyzes bidirectional dependency mapping showing what calls this target and what it calls)",
                },
                "model": self.get_model_field_schema(),
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
            "required": ["prompt", "files", "trace_mode"] + (["model"] if self.is_effective_auto_mode() else []),
        }

        return schema

    def get_system_prompt(self) -> str:
        return TRACER_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    # Line numbers are enabled by default for precise code references

    def get_model_category(self):
        """Tracer requires extended reasoning for complex flow analysis"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.EXTENDED_REASONING

    def get_request_model(self):
        return TracerRequest

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

    async def prepare_prompt(self, request: TracerRequest) -> str:
        """
        Prepare the complete prompt for code analysis.

        This method combines:
        - System prompt with analysis instructions
        - User request and trace type
        - File contents with line numbers
        - Analysis parameters

        Args:
            request: The validated tracer request

        Returns:
            str: Complete prompt for the model

        Raises:
            ValueError: If the prompt exceeds token limits
        """
        logger.info(
            f"[TRACER] Preparing prompt for {request.trace_mode} trace analysis with {len(request.files)} files"
        )
        logger.debug(f"[TRACER] User request: {request.prompt[:100]}...")

        # Check for prompt.txt in files
        prompt_content, updated_files = self.handle_prompt_file(request.files)

        # If prompt.txt was found, incorporate it into the request prompt
        if prompt_content:
            logger.debug("[TRACER] Found prompt.txt file, incorporating content")
            request.prompt = prompt_content + "\n\n" + request.prompt

        # Update request files list
        if updated_files is not None:
            logger.debug(f"[TRACER] Updated files list after prompt.txt processing: {len(updated_files)} files")
            request.files = updated_files

        # Check user input size at MCP transport boundary (before adding internal content)
        size_check = self.check_prompt_size(request.prompt)
        if size_check:
            from tools.models import ToolOutput

            raise ValueError(f"MCP_SIZE_CHECK:{ToolOutput(**size_check).model_dump_json()}")

        # Detect primary language
        primary_language = self.detect_primary_language(request.files)
        logger.debug(f"[TRACER] Detected primary language: {primary_language}")

        # Use centralized file processing logic for main code files (with line numbers enabled)
        continuation_id = getattr(request, "continuation_id", None)
        logger.debug(f"[TRACER] Preparing {len(request.files)} code files for analysis")
        code_content = self._prepare_file_content_for_prompt(request.files, continuation_id, "Code to analyze")

        if code_content:
            from utils.token_utils import estimate_tokens

            code_tokens = estimate_tokens(code_content)
            logger.info(f"[TRACER] Code files embedded successfully: {code_tokens:,} tokens")
        else:
            logger.warning("[TRACER] No code content after file processing")

        # Build the complete prompt
        prompt_parts = []

        # Add system prompt
        prompt_parts.append(self.get_system_prompt())

        # Add user request and analysis parameters
        prompt_parts.append("\n=== ANALYSIS REQUEST ===")
        prompt_parts.append(f"User Request: {request.prompt}")
        prompt_parts.append(f"Trace Mode: {request.trace_mode}")
        prompt_parts.append(f"Language: {primary_language}")
        prompt_parts.append("=== END REQUEST ===")

        # Add web search instruction if enabled
        websearch_instruction = self.get_websearch_instruction(
            getattr(request, "use_websearch", True),
            f"""When analyzing code for {primary_language}, consider if searches for these would help:
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
        prompt_parts.append(f"\nPlease perform a {request.trace_mode} trace analysis based on the user request.")

        full_prompt = "\n".join(prompt_parts)

        # Log final prompt statistics
        from utils.token_utils import estimate_tokens

        total_tokens = estimate_tokens(full_prompt)
        logger.info(f"[TRACER] Complete prompt prepared: {total_tokens:,} tokens, {len(full_prompt):,} characters")

        return full_prompt

    def format_response(self, response: str, request: TracerRequest, model_info: Optional[dict] = None) -> str:
        """
        Format the code analysis response with mode-specific rendering instructions.

        The base tool handles structured response validation via SPECIAL_STATUS_MODELS,
        so this method focuses on providing clear rendering instructions for Claude.

        Args:
            response: The raw analysis from the model
            request: The original request for context
            model_info: Optional dict with model metadata

        Returns:
            str: The response with mode-specific rendering instructions
        """
        logger.debug(f"[TRACER] Formatting response for {request.trace_mode} trace analysis")

        # Get the friendly model name
        model_name = "the model"
        if model_info and model_info.get("model_response"):
            model_name = model_info["model_response"].friendly_name or "the model"

        # Base tool will handle trace_complete JSON responses via SPECIAL_STATUS_MODELS
        # No need for manual JSON parsing here

        # Generate mode-specific rendering instructions
        rendering_instructions = self._get_rendering_instructions(request.trace_mode)

        # Create the complete response with rendering instructions
        footer = f"""
---

**Analysis Complete**: {model_name} has completed a {request.trace_mode} analysis as requested.

{rendering_instructions}

**GENERAL REQUIREMENTS:**
- Follow the rendering instructions EXACTLY as specified above
- Use only the data provided in the JSON response
- Maintain exact formatting for readability
- Include file paths and line numbers as provided
- Do not add explanations or commentary outside the specified format"""

        return f"{response}{footer}"

    def _get_rendering_instructions(self, trace_mode: str) -> str:
        """
        Get mode-specific rendering instructions for Claude.

        Args:
            trace_mode: Either "precision" or "dependencies"

        Returns:
            str: Complete rendering instructions for the specified mode
        """
        if trace_mode == "precision":
            return self._get_precision_rendering_instructions()
        else:  # dependencies mode
            return self._get_dependencies_rendering_instructions()

    def _get_precision_rendering_instructions(self) -> str:
        """Get rendering instructions for precision trace mode."""
        return """
## MANDATORY RENDERING INSTRUCTIONS FOR PRECISION TRACE

You MUST render the trace analysis in exactly two views:

### 1. CALL FLOW DIAGRAM (TOP-DOWN)

Use this exact format:
```
[Class::Method] (file: /path, line: ##)
↓
[Class::CalledMethod] (file: /path, line: ##)
↓
...
```

**Rules:**
- Chain each call using ↓ or → for readability
- Include file name and line number per method
- If the call is conditional, append `? if condition`
- If ambiguous, mark with `⚠️ ambiguous branch`
- Indent nested calls appropriately

### 2. BRANCHING & SIDE EFFECT TABLE

Render exactly this table format:

| Location | Condition | Branches | Ambiguous |
|----------|-----------|----------|-----------|
| /file/path:## | if condition | method1(), method2() | ✅/❌ |

**Side Effects section:**
```
Side Effects:
- [database] description (File.ext:##)
- [network] description (File.ext:##)
- [filesystem] description (File.ext:##)
```

**CRITICAL RULES:**
- ALWAYS render both views unless data is missing
- Use exact filenames, class names, and line numbers from JSON
- DO NOT invent function names or examples
- Mark ambiguous branches with ⚠️ or ✅
- If sections are empty, omit them cleanly"""

    def _get_dependencies_rendering_instructions(self) -> str:
        """Get rendering instructions for dependencies trace mode."""
        return """
## MANDATORY RENDERING INSTRUCTIONS FOR DEPENDENCIES TRACE

You MUST render the trace analysis in exactly two views:

### 1. DEPENDENCY FLOW GRAPH

Use this exact format:

**Incoming:**
```
Called by:
- [CallerClass::callerMethod] ← /path/file.ext:##
- [ServiceImpl::run]          ← /path/file.ext:##
```

**Outgoing:**
```
Calls:
- [Logger::logAction]    → /utils/log.ext:##
- [PaymentClient::send]  → /clients/pay.ext:##
```

**Type Dependencies:**
```
- conforms_to: ProtocolName
- implements: InterfaceName
- imports: ModuleName, LibraryName
```

**State Access:**
```
- reads: property.name (line ##)
- writes: object.field (line ##)
```

**Arrow Rules:**
- `←` for incoming (who calls this)
- `→` for outgoing (what this calls)

### 2. DEPENDENCY TABLE

Render exactly this table format:

| Type | From/To | Method | File | Line |
|------|---------|--------|------|------|
| direct_call | From: CallerClass | callerMethod | /path/file.ext | ## |
| method_call | To: TargetClass | targetMethod | /path/file.ext | ## |
| uses_property | To: ObjectClass | .propertyName | /path/file.ext | ## |
| conforms_to | Self: ThisClass | — | /path/file.ext | — |

**CRITICAL RULES:**
- ALWAYS render both views unless data is missing
- Use exact filenames, class names, and line numbers from JSON
- DO NOT invent function names or examples
- If sections (state access, type dependencies) are empty, omit them cleanly
- Show directional dependencies with proper arrows"""
