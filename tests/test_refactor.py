"""
Tests for the refactor tool functionality
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tools.refactor import RefactorTool
from utils.file_utils import read_file_content


class TestRefactorTool:
    """Test suite for the refactor tool"""

    @pytest.fixture
    def refactor_tool(self):
        """Create a refactor tool instance for testing"""
        return RefactorTool()

    @pytest.fixture
    def mock_model_response(self):
        """Create a mock model response with valid JSON"""

        def _create_response(content=None):
            if content is None:
                content = json.dumps(
                    {
                        "refactor_opportunities": [
                            {
                                "id": "refactor-001",
                                "type": "codesmells",
                                "severity": "high",
                                "file": "/test/file.py",
                                "start_line": 10,
                                "end_line": 25,
                                "context_start_text": "def long_method():",
                                "context_end_text": "    return result",
                                "issue": "Method too long with multiple responsibilities",
                                "suggestion": "Extract helper methods",
                                "rationale": "Improves readability and maintainability",
                                "code_to_replace": "# original code",
                                "replacement_code_snippet": "# refactored code",
                                "new_code_snippets": [],
                            }
                        ],
                        "priority_sequence": ["refactor-001"],
                        "next_actions_for_claude": [],
                    }
                )

            from unittest.mock import Mock

            return Mock(
                content=content,
                usage={"input_tokens": 100, "output_tokens": 200, "total_tokens": 300},
                model_name="test-model",
                metadata={"finish_reason": "STOP"},
            )

        return _create_response

    def test_get_name(self, refactor_tool):
        """Test that the tool returns the correct name"""
        assert refactor_tool.get_name() == "refactor"

    def test_get_description(self, refactor_tool):
        """Test that the tool returns a comprehensive description"""
        description = refactor_tool.get_description()
        assert "INTELLIGENT CODE REFACTORING" in description
        assert "codesmells" in description
        assert "decompose" in description
        assert "modernize" in description
        assert "organization" in description

    def test_get_input_schema(self, refactor_tool):
        """Test that the input schema includes all required fields"""
        schema = refactor_tool.get_input_schema()

        assert schema["type"] == "object"
        assert "files" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "refactor_type" in schema["properties"]

        # Check refactor_type enum values
        refactor_enum = schema["properties"]["refactor_type"]["enum"]
        expected_types = ["codesmells", "decompose", "modernize", "organization"]
        assert all(rt in refactor_enum for rt in expected_types)

    def test_language_detection_python(self, refactor_tool):
        """Test language detection for Python files"""
        files = ["/test/file1.py", "/test/file2.py", "/test/utils.py"]
        language = refactor_tool.detect_primary_language(files)
        assert language == "python"

    def test_language_detection_javascript(self, refactor_tool):
        """Test language detection for JavaScript files"""
        files = ["/test/app.js", "/test/component.jsx", "/test/utils.js"]
        language = refactor_tool.detect_primary_language(files)
        assert language == "javascript"

    def test_language_detection_mixed(self, refactor_tool):
        """Test language detection for mixed language files"""
        files = ["/test/app.py", "/test/script.js", "/test/main.java"]
        language = refactor_tool.detect_primary_language(files)
        assert language == "mixed"

    def test_language_detection_unknown(self, refactor_tool):
        """Test language detection for unknown file types"""
        files = ["/test/data.txt", "/test/config.json"]
        language = refactor_tool.detect_primary_language(files)
        assert language == "unknown"

    def test_language_specific_guidance_python(self, refactor_tool):
        """Test language-specific guidance for Python modernization"""
        guidance = refactor_tool.get_language_specific_guidance("python", "modernize")
        assert "f-strings" in guidance
        assert "dataclasses" in guidance
        assert "type hints" in guidance

    def test_language_specific_guidance_javascript(self, refactor_tool):
        """Test language-specific guidance for JavaScript modernization"""
        guidance = refactor_tool.get_language_specific_guidance("javascript", "modernize")
        assert "async/await" in guidance
        assert "destructuring" in guidance
        assert "arrow functions" in guidance

    def test_language_specific_guidance_unknown(self, refactor_tool):
        """Test language-specific guidance for unknown languages"""
        guidance = refactor_tool.get_language_specific_guidance("unknown", "modernize")
        assert guidance == ""

    @pytest.mark.asyncio
    async def test_execute_basic_refactor(self, refactor_tool, mock_model_response):
        """Test basic refactor tool execution"""
        with patch.object(refactor_tool, "get_model_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.get_provider_type.return_value = MagicMock(value="test")
            mock_provider.supports_thinking_mode.return_value = False
            mock_provider.generate_content.return_value = mock_model_response()
            mock_get_provider.return_value = mock_provider

            # Mock file processing
            with patch.object(refactor_tool, "_prepare_file_content_for_prompt") as mock_prepare:
                mock_prepare.return_value = "def test(): pass"

                result = await refactor_tool.execute(
                    {
                        "files": ["/test/file.py"],
                        "prompt": "Find code smells in this Python code",
                        "refactor_type": "codesmells",
                    }
                )

                assert len(result) == 1
                output = json.loads(result[0].text)
                assert output["status"] == "success"
                # The format_response method adds markdown instructions, so content_type should be "markdown"
                # It could also be "json" or "text" depending on the response format
                assert output["content_type"] in ["json", "text", "markdown"]

    @pytest.mark.asyncio
    async def test_execute_with_style_guide(self, refactor_tool, mock_model_response):
        """Test refactor tool execution with style guide examples"""
        with patch.object(refactor_tool, "get_model_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.get_provider_type.return_value = MagicMock(value="test")
            mock_provider.supports_thinking_mode.return_value = False
            mock_provider.generate_content.return_value = mock_model_response()
            mock_get_provider.return_value = mock_provider

            # Mock file processing
            with patch.object(refactor_tool, "_prepare_file_content_for_prompt") as mock_prepare:
                mock_prepare.return_value = "def example(): pass"

            with patch.object(refactor_tool, "_process_style_guide_examples") as mock_style:
                mock_style.return_value = ("# style guide content", "")

                result = await refactor_tool.execute(
                    {
                        "files": ["/test/file.py"],
                        "prompt": "Modernize this code following our style guide",
                        "refactor_type": "modernize",
                        "style_guide_examples": ["/test/style_example.py"],
                    }
                )

                assert len(result) == 1
                output = json.loads(result[0].text)
                assert output["status"] == "success"

    def test_format_response_valid_json(self, refactor_tool):
        """Test response formatting with valid structured JSON"""
        valid_json_response = json.dumps(
            {
                "status": "refactor_analysis_complete",
                "refactor_opportunities": [
                    {
                        "id": "test-001",
                        "type": "codesmells",
                        "severity": "medium",
                        "file": "/test.py",
                        "start_line": 1,
                        "end_line": 5,
                        "context_start_text": "def test():",
                        "context_end_text": "    pass",
                        "issue": "Test issue",
                        "suggestion": "Test suggestion",
                        "rationale": "Test rationale",
                        "code_to_replace": "old code",
                        "replacement_code_snippet": "new code",
                    }
                ],
                "priority_sequence": ["test-001"],
                "next_actions_for_claude": [],
            }
        )

        # Create a mock request
        request = MagicMock()
        request.refactor_type = "codesmells"

        formatted = refactor_tool.format_response(valid_json_response, request)

        # Should contain the original response plus implementation instructions
        assert valid_json_response in formatted
        assert "MANDATORY NEXT STEPS" in formatted
        assert "Start executing the refactoring plan immediately" in formatted
        assert "MANDATORY: MUST start executing the refactor plan" in formatted

    def test_format_response_invalid_json(self, refactor_tool):
        """Test response formatting with invalid JSON - now handled by base tool"""
        invalid_response = "This is not JSON content"

        # Create a mock request
        request = MagicMock()
        request.refactor_type = "codesmells"

        formatted = refactor_tool.format_response(invalid_response, request)

        # Should contain the original response plus implementation instructions
        assert invalid_response in formatted
        assert "MANDATORY NEXT STEPS" in formatted
        assert "Start executing the refactoring plan immediately" in formatted

    def test_model_category(self, refactor_tool):
        """Test that the refactor tool uses EXTENDED_REASONING category"""
        from tools.models import ToolModelCategory

        category = refactor_tool.get_model_category()
        assert category == ToolModelCategory.EXTENDED_REASONING

    def test_default_temperature(self, refactor_tool):
        """Test that the refactor tool uses analytical temperature"""
        from config import TEMPERATURE_ANALYTICAL

        temp = refactor_tool.get_default_temperature()
        assert temp == TEMPERATURE_ANALYTICAL

    def test_format_response_more_refactor_required(self, refactor_tool):
        """Test that format_response handles more_refactor_required field"""
        more_refactor_response = json.dumps(
            {
                "status": "refactor_analysis_complete",
                "refactor_opportunities": [
                    {
                        "id": "refactor-001",
                        "type": "decompose",
                        "severity": "critical",
                        "file": "/test/file.py",
                        "start_line": 1,
                        "end_line": 10,
                        "context_start_text": "def test_function():",
                        "context_end_text": "    return True",
                        "issue": "Function too large",
                        "suggestion": "Break into smaller functions",
                        "rationale": "Improves maintainability",
                        "code_to_replace": "original code",
                        "replacement_code_snippet": "refactored code",
                        "new_code_snippets": [],
                    }
                ],
                "priority_sequence": ["refactor-001"],
                "next_actions_for_claude": [
                    {
                        "action_type": "EXTRACT_METHOD",
                        "target_file": "/test/file.py",
                        "source_lines": "1-10",
                        "description": "Extract method from large function",
                    }
                ],
                "more_refactor_required": True,
                "continuation_message": "Large codebase requires extensive refactoring across multiple files",
            }
        )

        # Create a mock request
        request = MagicMock()
        request.refactor_type = "decompose"

        formatted = refactor_tool.format_response(more_refactor_response, request)

        # Should contain the original response plus continuation instructions
        assert more_refactor_response in formatted
        assert "MANDATORY NEXT STEPS" in formatted
        assert "Start executing the refactoring plan immediately" in formatted
        assert "MANDATORY: MUST start executing the refactor plan" in formatted
        assert "AFTER IMPLEMENTING ALL ABOVE" in formatted  # Special instruction for more_refactor_required
        assert "continuation_id" in formatted


class TestFileUtilsLineNumbers:
    """Test suite for line numbering functionality in file_utils"""

    def test_read_file_content_with_line_numbers(self, project_path):
        """Test reading file content with line numbers enabled"""

        # Create a test file within the workspace
        temp_path = project_path / "test_file.py"
        with open(temp_path, "w") as f:
            f.write("def hello():\n    print('Hello')\n    return True")

        # Read with line numbers explicitly enabled
        content, tokens = read_file_content(str(temp_path), include_line_numbers=True)

        # Check that line numbers are present
        assert "1│ def hello():" in content
        assert "2│     print('Hello')" in content
        assert "3│     return True" in content
        assert "--- BEGIN FILE:" in content
        assert "--- END FILE:" in content

    def test_read_file_content_without_line_numbers(self, project_path):
        """Test reading file content with line numbers disabled"""

        # Create a test file within the workspace
        temp_path = project_path / "test_file.txt"
        with open(temp_path, "w") as f:
            f.write("Line 1\nLine 2\nLine 3")

        # Read with line numbers explicitly disabled
        content, tokens = read_file_content(str(temp_path), include_line_numbers=False)

        # Check that line numbers are NOT present
        assert "1│" not in content
        assert "Line 1" in content
        assert "Line 2" in content
        assert "--- BEGIN FILE:" in content

    def test_read_file_content_auto_detect_programming(self, project_path):
        """Test that auto-detection is OFF by default (backwards compatibility)"""

        # Create a test file within the workspace
        temp_path = project_path / "test_auto.py"
        with open(temp_path, "w") as f:
            f.write("import os\nprint('test')")

        # Read without specifying line numbers (should NOT auto-detect for backwards compatibility)
        content, tokens = read_file_content(str(temp_path))

        # Should NOT automatically add line numbers for .py files (default behavior)
        assert "1│" not in content
        assert "import os" in content
        assert "print('test')" in content

    def test_read_file_content_auto_detect_text(self, project_path):
        """Test auto-detection of line numbers for text files"""

        # Create a test file within the workspace
        temp_path = project_path / "test_auto.txt"
        with open(temp_path, "w") as f:
            f.write("This is a text file\nWith multiple lines")

        # Read without specifying line numbers (should auto-detect)
        content, tokens = read_file_content(str(temp_path))

        # Should NOT automatically add line numbers for .txt files
        assert "1│" not in content
        assert "This is a text file" in content

    def test_line_ending_normalization(self):
        """Test that different line endings are normalized consistently"""
        from utils.file_utils import _add_line_numbers, _normalize_line_endings

        # Test different line ending formats
        content_crlf = "Line 1\r\nLine 2\r\nLine 3"
        content_cr = "Line 1\rLine 2\rLine 3"
        content_lf = "Line 1\nLine 2\nLine 3"

        # All should normalize to the same result
        normalized_crlf = _normalize_line_endings(content_crlf)
        normalized_cr = _normalize_line_endings(content_cr)
        normalized_lf = _normalize_line_endings(content_lf)

        assert normalized_crlf == normalized_cr == normalized_lf
        assert normalized_lf == "Line 1\nLine 2\nLine 3"

        # Line numbering should work consistently
        numbered = _add_line_numbers(content_crlf)
        assert "   1│ Line 1" in numbered
        assert "   2│ Line 2" in numbered
        assert "   3│ Line 3" in numbered

    def test_detect_file_type(self):
        """Test file type detection"""
        from utils.file_utils import detect_file_type

        # Test programming language files
        assert detect_file_type("test.py") == "text"
        assert detect_file_type("test.js") == "text"
        assert detect_file_type("test.java") == "text"

        # Test image files
        assert detect_file_type("image.png") == "image"
        assert detect_file_type("photo.jpg") == "image"

        # Test binary files
        assert detect_file_type("program.exe") == "binary"
        assert detect_file_type("library.dll") == "binary"

    def test_should_add_line_numbers(self):
        """Test line number detection logic"""
        from utils.file_utils import should_add_line_numbers

        # NO files should get line numbers by default (backwards compatibility)
        assert not should_add_line_numbers("test.py")
        assert not should_add_line_numbers("app.js")
        assert not should_add_line_numbers("Main.java")
        assert not should_add_line_numbers("readme.txt")
        assert not should_add_line_numbers("data.csv")

        # Explicit override should work
        assert should_add_line_numbers("readme.txt", True)
        assert not should_add_line_numbers("test.py", False)

    def test_line_numbers_double_triple_digits(self, project_path):
        """Test line numbering with double and triple digit line numbers"""
        from utils.file_utils import _add_line_numbers

        # Create content with many lines to test double and triple digit formatting
        lines = []
        for i in range(1, 125):  # Lines 1-124 for testing up to triple digits
            if i < 10:
                lines.append(f"# Single digit line {i}")
            elif i < 100:
                lines.append(f"# Double digit line {i}")
            else:
                lines.append(f"# Triple digit line {i}")

        content = "\n".join(lines)
        numbered_content = _add_line_numbers(content)

        # Test single digit formatting (should be right-aligned with spaces)
        assert "   1│ # Single digit line 1" in numbered_content
        assert "   9│ # Single digit line 9" in numbered_content

        # Test double digit formatting (should be right-aligned)
        assert "  10│ # Double digit line 10" in numbered_content  # Line 10 has "double digit" content
        assert "  50│ # Double digit line 50" in numbered_content
        assert "  99│ # Double digit line 99" in numbered_content

        # Test triple digit formatting (should be right-aligned)
        assert " 100│ # Triple digit line 100" in numbered_content
        assert " 124│ # Triple digit line 124" in numbered_content

        # Verify consistent alignment - all line numbers should end with "│ "
        lines_with_numbers = numbered_content.split("\n")
        for line in lines_with_numbers:
            if "│" in line:
                # Find the pipe character position
                pipe_pos = line.find("│")
                # Ensure the character before pipe is a digit
                assert line[pipe_pos - 1].isdigit(), f"Line format issue: {line}"
                # Ensure the character after pipe is a space
                assert line[pipe_pos + 1] == " ", f"Line format issue: {line}"

    def test_line_numbers_with_file_reading(self, project_path):
        """Test line numbering through file reading with large file"""

        # Create a test file with 150 functions (600 total lines: 4 lines per function)
        temp_path = project_path / "large_test_file.py"
        with open(temp_path, "w") as f:
            for i in range(1, 151):  # Functions 1-150
                f.write(f"def function_{i}():\n")
                f.write(f"    # This is function number {i}\n")
                f.write(f"    return {i}\n")
                f.write("\n")

        # Read with line numbers enabled
        content, tokens = read_file_content(str(temp_path), include_line_numbers=True)

        # Calculate actual line numbers based on file structure (4 lines per function)
        # Function 1: lines 1-4, Function 2: lines 5-8, etc.
        # Line 1: def function_1():
        # Line 2: # This is function number 1
        # Line 3: return 1
        # Line 4: (empty)

        # Test various line number formats in the actual file content
        assert "   1│ def function_1():" in content

        # Function 13 starts at line 49 (12*4 + 1), so line 50 is "    # This is function number 13"
        assert "  50│     # This is function number 13" in content

        # Line 100 is actually an empty line after function 25 (line 99 was "return 25")
        assert " 100│ " in content  # Empty line

        # Line 99 is "return 25" from function 25
        assert "  99│     return 25" in content

        # Test more line numbers - line 147 is "return 37" from function 37
        assert " 147│     return 37" in content

        # Test that we have the final lines (600 total lines)
        assert " 599│     return 150" in content
        assert " 600│ " in content  # Final empty line

        # Verify the file structure is preserved
        assert "--- BEGIN FILE:" in content
        assert "--- END FILE:" in content
        assert str(temp_path) in content

    def test_line_numbers_large_files_22k_lines(self, project_path):
        """Test line numbering for very large files (22,500+ lines)"""
        from utils.file_utils import _add_line_numbers

        # Create content simulating a very large file with 25,000 lines
        lines = []
        for i in range(1, 25001):  # Lines 1-25000
            lines.append(f"// Large file line {i}")

        content = "\n".join(lines)
        numbered_content = _add_line_numbers(content)

        # Test that width dynamically adjusts to 5 digits for large files
        # Small line numbers should now have 5-digit width
        assert "    1│ // Large file line 1" in numbered_content
        assert "    9│ // Large file line 9" in numbered_content
        assert "   10│ // Large file line 10" in numbered_content
        assert "   99│ // Large file line 99" in numbered_content
        assert "  100│ // Large file line 100" in numbered_content
        assert "  999│ // Large file line 999" in numbered_content
        assert " 1000│ // Large file line 1000" in numbered_content
        assert " 9999│ // Large file line 9999" in numbered_content
        assert "10000│ // Large file line 10000" in numbered_content
        assert "22500│ // Large file line 22500" in numbered_content
        assert "25000│ // Large file line 25000" in numbered_content

        # Verify consistent alignment - all line numbers should end with "│ "
        lines_with_numbers = numbered_content.split("\n")
        for i, line in enumerate(lines_with_numbers[:100]):  # Check first 100 lines
            if "│" in line:
                pipe_pos = line.find("│")
                # For large files, should be 5-character width plus pipe
                assert line[pipe_pos - 1].isdigit(), f"Line {i+1} format issue: {line}"
                assert line[pipe_pos + 1] == " ", f"Line {i+1} format issue: {line}"

    def test_line_numbers_boundary_conditions(self):
        """Test line numbering at boundary conditions (9999 vs 10000 lines)"""
        from utils.file_utils import _add_line_numbers

        # Test exactly 9999 lines (should use 4-digit width)
        lines_9999 = [f"Line {i}" for i in range(1, 10000)]  # 9999 lines
        content_9999 = "\n".join(lines_9999)
        numbered_9999 = _add_line_numbers(content_9999)

        # Should use 4-digit format
        assert "   1│ Line 1" in numbered_9999
        assert "9999│ Line 9999" in numbered_9999

        # Test exactly 10000 lines (should use 5-digit width)
        lines_10000 = [f"Line {i}" for i in range(1, 10001)]  # 10000 lines
        content_10000 = "\n".join(lines_10000)
        numbered_10000 = _add_line_numbers(content_10000)

        # Should use 5-digit format
        assert "    1│ Line 1" in numbered_10000
        assert "10000│ Line 10000" in numbered_10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
