"""
TestGen tool - Comprehensive test suite generation with edge case coverage

This tool generates comprehensive test suites by analyzing code paths,
identifying edge cases, and producing test scaffolding that follows
project conventions when test examples are provided.

Key Features:
- Multi-file and directory support
- Framework detection from existing tests
- Edge case identification (nulls, boundaries, async issues, etc.)
- Test pattern following when examples provided
- Deterministic test example sampling for large test suites
"""

import logging
import os
from typing import Any, Optional

from mcp.types import TextContent
from pydantic import Field

from config import TEMPERATURE_ANALYTICAL
from systemprompts import TESTGEN_PROMPT

from .base import BaseTool, ToolRequest
from .models import ToolOutput

logger = logging.getLogger(__name__)


class TestGenRequest(ToolRequest):
    """
    Request model for the test generation tool.

    This model defines all parameters that can be used to customize
    the test generation process, from selecting code files to providing
    test examples for style consistency.
    """

    files: list[str] = Field(
        ...,
        description="Code files or directories to generate tests for (must be absolute paths)",
    )
    prompt: str = Field(
        ...,
        description="Description of what to test, testing objectives, and specific scope/focus areas",
    )
    test_examples: Optional[list[str]] = Field(
        None,
        description=(
            "Optional existing test files or directories to use as style/pattern reference (must be absolute paths). "
            "If not provided, the tool will determine the best testing approach based on the code structure. "
            "For large test directories, only the smallest representative tests should be included to determine testing patterns. "
            "If similar tests exist for the code being tested, include those for the most relevant patterns."
        ),
    )


class TestGenTool(BaseTool):
    """
    Test generation tool implementation.

    This tool analyzes code to generate comprehensive test suites with
    edge case coverage, following existing test patterns when examples
    are provided.
    """

    def get_name(self) -> str:
        return "testgen"

    def get_description(self) -> str:
        return (
            "COMPREHENSIVE TEST GENERATION - Creates thorough test suites with edge case coverage. "
            "Use this when you need to generate tests for code, create test scaffolding, or improve test coverage. "
            "BE SPECIFIC about scope: target specific functions/classes/modules rather than testing everything. "
            "Examples: 'Generate tests for User.login() method', 'Test payment processing validation', "
            "'Create tests for authentication error handling'. If user request is vague, either ask for "
            "clarification about specific components to test, or make focused scope decisions and explain them. "
            "Analyzes code paths, identifies realistic failure modes, and generates framework-specific tests. "
            "Supports test pattern following when examples are provided. "
            "Choose thinking_mode based on code complexity: 'low' for simple functions, "
            "'medium' for standard modules (default), 'high' for complex systems with many interactions, "
            "'max' for critical systems requiring exhaustive test coverage. "
            "Note: If you're not currently using a top-tier model such as Opus 4 or above, these tools can provide enhanced capabilities."
        )

    def get_input_schema(self) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Code files or directories to generate tests for (must be absolute paths)",
                },
                "model": self.get_model_field_schema(),
                "prompt": {
                    "type": "string",
                    "description": "Description of what to test, testing objectives, and specific scope/focus areas",
                },
                "test_examples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional existing test files or directories to use as style/pattern reference (must be absolute paths). "
                        "If not provided, the tool will determine the best testing approach based on the code structure. "
                        "For large test directories, only the smallest representative tests will be included to determine testing patterns. "
                        "If similar tests exist for the code being tested, include those for the most relevant patterns."
                    ),
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Thinking depth: minimal (0.5% of model max), low (8%), medium (33%), high (67%), max (100% of model max)",
                },
                "continuation_id": {
                    "type": "string",
                    "description": "Thread continuation ID for multi-turn conversations. Can be used to continue conversations across different tools. Only provide this if continuing a previous conversation thread.",
                },
            },
            "required": ["files", "prompt"] + (["model"] if self.is_effective_auto_mode() else []),
        }

        return schema

    def get_system_prompt(self) -> str:
        return TESTGEN_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self):
        """TestGen requires extended reasoning for comprehensive test analysis"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.EXTENDED_REASONING

    def get_request_model(self):
        return TestGenRequest

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Override execute to check prompt size before processing"""
        # First validate request
        request_model = self.get_request_model()
        request = request_model(**arguments)

        # Check prompt size if provided
        if request.prompt:
            size_check = self.check_prompt_size(request.prompt)
            if size_check:
                return [TextContent(type="text", text=ToolOutput(**size_check).model_dump_json())]

        # Continue with normal execution
        return await super().execute(arguments)

    def _process_test_examples(
        self, test_examples: list[str], continuation_id: Optional[str], available_tokens: int = None
    ) -> tuple[str, str]:
        """
        Process test example files using available token budget for optimal sampling.

        Args:
            test_examples: List of test file paths
            continuation_id: Continuation ID for filtering already embedded files
            available_tokens: Available token budget for test examples

        Returns:
            tuple: (formatted_content, summary_note)
        """
        logger.debug(f"[TESTGEN] Processing {len(test_examples)} test examples")

        if not test_examples:
            logger.debug("[TESTGEN] No test examples provided")
            return "", ""

        # Use existing file filtering to avoid duplicates in continuation
        examples_to_process = self.filter_new_files(test_examples, continuation_id)
        logger.debug(f"[TESTGEN] After filtering: {len(examples_to_process)} new test examples to process")

        if not examples_to_process:
            logger.info(f"[TESTGEN] All {len(test_examples)} test examples already in conversation history")
            return "", ""

        # Calculate token budget for test examples (25% of available tokens, or fallback)
        if available_tokens:
            test_examples_budget = int(available_tokens * 0.25)  # 25% for test examples
            logger.debug(
                f"[TESTGEN] Allocating {test_examples_budget:,} tokens (25% of {available_tokens:,}) for test examples"
            )
        else:
            test_examples_budget = 30000  # Fallback if no budget provided
            logger.debug(f"[TESTGEN] Using fallback budget of {test_examples_budget:,} tokens for test examples")

        original_count = len(examples_to_process)
        logger.debug(
            f"[TESTGEN] Processing {original_count} test example files with {test_examples_budget:,} token budget"
        )

        # Sort by file size (smallest first) for pattern-focused selection
        file_sizes = []
        for file_path in examples_to_process:
            try:
                size = os.path.getsize(file_path)
                file_sizes.append((file_path, size))
                logger.debug(f"[TESTGEN] Test example {os.path.basename(file_path)}: {size:,} bytes")
            except (OSError, FileNotFoundError) as e:
                # If we can't get size, put it at the end
                logger.warning(f"[TESTGEN] Could not get size for {file_path}: {e}")
                file_sizes.append((file_path, float("inf")))

        # Sort by size and take smallest files for pattern reference
        file_sizes.sort(key=lambda x: x[1])
        examples_to_process = [f[0] for f in file_sizes]  # All files, sorted by size
        logger.debug(
            f"[TESTGEN] Sorted test examples by size (smallest first): {[os.path.basename(f) for f in examples_to_process]}"
        )

        # Use standard file content preparation with dynamic token budget
        try:
            logger.debug(f"[TESTGEN] Preparing file content for {len(examples_to_process)} test examples")
            content = self._prepare_file_content_for_prompt(
                examples_to_process,
                continuation_id,
                "Test examples",
                max_tokens=test_examples_budget,
                reserve_tokens=1000,
            )

            # Determine how many files were actually included
            if content:
                from utils.token_utils import estimate_tokens

                used_tokens = estimate_tokens(content)
                logger.info(
                    f"[TESTGEN] Successfully embedded test examples: {used_tokens:,} tokens used ({test_examples_budget:,} available)"
                )
                if original_count > 1:
                    truncation_note = f"Note: Used {used_tokens:,} tokens ({test_examples_budget:,} available) for test examples from {original_count} files to determine testing patterns."
                else:
                    truncation_note = ""
            else:
                logger.warning("[TESTGEN] No content generated for test examples")
                truncation_note = ""

            return content, truncation_note

        except Exception as e:
            # If test example processing fails, continue without examples rather than failing
            logger.error(f"[TESTGEN] Failed to process test examples: {type(e).__name__}: {e}")
            return "", f"Warning: Could not process test examples: {str(e)}"

    async def prepare_prompt(self, request: TestGenRequest) -> str:
        """
        Prepare the test generation prompt with code analysis and optional test examples.

        This method reads the requested files, processes any test examples,
        and constructs a detailed prompt for comprehensive test generation.

        Args:
            request: The validated test generation request

        Returns:
            str: Complete prompt for the model

        Raises:
            ValueError: If the code exceeds token limits
        """
        logger.debug(f"[TESTGEN] Preparing prompt for {len(request.files)} code files")
        if request.test_examples:
            logger.debug(f"[TESTGEN] Including {len(request.test_examples)} test examples for pattern reference")
        # Check for prompt.txt in files
        prompt_content, updated_files = self.handle_prompt_file(request.files)

        # If prompt.txt was found, incorporate it into the prompt
        if prompt_content:
            logger.debug("[TESTGEN] Found prompt.txt file, incorporating content")
            request.prompt = prompt_content + "\n\n" + request.prompt

        # Update request files list
        if updated_files is not None:
            logger.debug(f"[TESTGEN] Updated files list after prompt.txt processing: {len(updated_files)} files")
            request.files = updated_files

        # Calculate available token budget for dynamic allocation
        continuation_id = getattr(request, "continuation_id", None)

        # Get model context for token budget calculation
        model_name = getattr(self, "_current_model_name", None)
        available_tokens = None

        if model_name:
            try:
                provider = self.get_model_provider(model_name)
                capabilities = provider.get_capabilities(model_name)
                # Use 75% of context for content (code + test examples), 25% for response
                available_tokens = int(capabilities.context_window * 0.75)
                logger.debug(
                    f"[TESTGEN] Token budget calculation: {available_tokens:,} tokens (75% of {capabilities.context_window:,}) for model {model_name}"
                )
            except Exception as e:
                # Fallback to conservative estimate
                logger.warning(f"[TESTGEN] Could not get model capabilities for {model_name}: {e}")
                available_tokens = 120000  # Conservative fallback
                logger.debug(f"[TESTGEN] Using fallback token budget: {available_tokens:,} tokens")

        # Process test examples first to determine token allocation
        test_examples_content = ""
        test_examples_note = ""

        if request.test_examples:
            logger.debug(f"[TESTGEN] Processing {len(request.test_examples)} test examples")
            test_examples_content, test_examples_note = self._process_test_examples(
                request.test_examples, continuation_id, available_tokens
            )
            if test_examples_content:
                logger.info("[TESTGEN] Test examples processed successfully for pattern reference")
            else:
                logger.info("[TESTGEN] No test examples content after processing")

        # Calculate remaining tokens for main code after test examples
        if test_examples_content and available_tokens:
            from utils.token_utils import estimate_tokens

            test_tokens = estimate_tokens(test_examples_content)
            remaining_tokens = available_tokens - test_tokens - 5000  # Reserve for prompt structure
            logger.debug(
                f"[TESTGEN] Token allocation: {test_tokens:,} for examples, {remaining_tokens:,} remaining for code files"
            )
        else:
            remaining_tokens = available_tokens - 10000 if available_tokens else None
            if remaining_tokens:
                logger.debug(
                    f"[TESTGEN] Token allocation: {remaining_tokens:,} tokens available for code files (no test examples)"
                )

        # Use centralized file processing logic for main code files
        logger.debug(f"[TESTGEN] Preparing {len(request.files)} code files for analysis")
        code_content = self._prepare_file_content_for_prompt(
            request.files, continuation_id, "Code to test", max_tokens=remaining_tokens, reserve_tokens=2000
        )

        if code_content:
            from utils.token_utils import estimate_tokens

            code_tokens = estimate_tokens(code_content)
            logger.info(f"[TESTGEN] Code files embedded successfully: {code_tokens:,} tokens")
        else:
            logger.warning("[TESTGEN] No code content after file processing")

        # Test generation is based on code analysis, no web search needed
        logger.debug("[TESTGEN] Building complete test generation prompt")

        # Build the complete prompt
        prompt_parts = []

        # Add system prompt
        prompt_parts.append(self.get_system_prompt())

        # Add user context
        prompt_parts.append("=== USER CONTEXT ===")
        prompt_parts.append(request.prompt)
        prompt_parts.append("=== END CONTEXT ===")

        # Add test examples if provided
        if test_examples_content:
            prompt_parts.append("\n=== TEST EXAMPLES FOR STYLE REFERENCE ===")
            if test_examples_note:
                prompt_parts.append(f"// {test_examples_note}")
            prompt_parts.append(test_examples_content)
            prompt_parts.append("=== END TEST EXAMPLES ===")

        # Add main code to test
        prompt_parts.append("\n=== CODE TO TEST ===")
        prompt_parts.append(code_content)
        prompt_parts.append("=== END CODE ===")

        # Add generation instructions
        prompt_parts.append(
            "\nPlease analyze the code and generate comprehensive tests following the multi-agent workflow specified in the system prompt."
        )
        if test_examples_content:
            prompt_parts.append(
                "Use the provided test examples as a reference for style, framework, and testing patterns."
            )

        full_prompt = "\n".join(prompt_parts)

        # Log final prompt statistics
        from utils.token_utils import estimate_tokens

        total_tokens = estimate_tokens(full_prompt)
        logger.info(f"[TESTGEN] Complete prompt prepared: {total_tokens:,} tokens, {len(full_prompt):,} characters")

        return full_prompt

    def format_response(self, response: str, request: TestGenRequest, model_info: Optional[dict] = None) -> str:
        """
        Format the test generation response.

        Args:
            response: The raw test generation from the model
            request: The original request for context
            model_info: Optional dict with model metadata

        Returns:
            str: Formatted response with next steps
        """
        return f"""{response}

---

**Next Steps:**

Claude must now:

1. **Create and save the test files** - Write the generated tests to appropriate test files in your project structure

2. **Display to the user** - Show each new test file/function created with a brief line explaining what it covers

3. **Install any missing test dependencies** - Set up required testing frameworks if not already available

4. **Run the tests** - Execute the test suite to verify functionality and fix any issues

5. **Integrate the tests** - Ensure tests are properly connected to your existing test infrastructure

The tests are ready for immediate implementation and integration into your codebase."""
