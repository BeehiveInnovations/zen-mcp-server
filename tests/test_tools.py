"""
Tests for individual tool implementations
"""

import json
from unittest.mock import Mock, patch

import pytest

from tools import AnalyzeTool, ChatTool, CodeReviewTool, DebugIssueTool, ThinkDeeperTool


class TestThinkDeeperTool:
    """Test the think_deeper tool"""

    @pytest.fixture
    def tool(self):
        return ThinkDeeperTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.get_name() == "think_deeper"
        assert "EXTENDED THINKING" in tool.get_description()
        assert tool.get_default_temperature() == 0.7

        schema = tool.get_input_schema()
        assert "current_analysis" in schema["properties"]
        assert schema["required"] == ["current_analysis"]

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.create_model")
    async def test_execute_success(self, mock_create_model, tool):
        """Test successful execution"""
        # Mock model
        mock_model = Mock()
        mock_model.generate_content.return_value = Mock(
            candidates=[Mock(content=Mock(parts=[Mock(text="Extended analysis")]))]
        )
        mock_create_model.return_value = mock_model

        result = await tool.execute(
            {
                "current_analysis": "Initial analysis",
                "problem_context": "Building a cache",
                "focus_areas": ["performance", "scalability"],
            }
        )

        assert len(result) == 1
        # Parse the JSON response
        output = json.loads(result[0].text)
        assert output["status"] == "success"
        assert "Extended Analysis by Gemini" in output["content"]
        assert "Extended analysis" in output["content"]


class TestCodeReviewTool:
    """Test the codereview tool"""

    @pytest.fixture
    def tool(self):
        return CodeReviewTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.get_name() == "codereview"
        assert "PROFESSIONAL CODE REVIEW" in tool.get_description()
        assert tool.get_default_temperature() == 0.2

        schema = tool.get_input_schema()
        assert "files" in schema["properties"]
        assert "context" in schema["properties"]
        assert schema["required"] == ["files", "context"]

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.create_model")
    async def test_execute_with_review_type(self, mock_create_model, tool, tmp_path):
        """Test execution with specific review type"""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def insecure(): pass", encoding="utf-8")

        # Mock model
        mock_model = Mock()
        mock_model.generate_content.return_value = Mock(
            candidates=[Mock(content=Mock(parts=[Mock(text="Security issues found")]))]
        )
        mock_create_model.return_value = mock_model

        result = await tool.execute(
            {
                "files": [str(test_file)],
                "review_type": "security",
                "focus_on": "authentication",
                "context": "Test code review for validation purposes",
            }
        )

        assert len(result) == 1
        assert "Code Review (SECURITY)" in result[0].text
        assert "Focus: authentication" in result[0].text
        assert "Security issues found" in result[0].text


class TestDebugIssueTool:
    """Test the debug tool"""

    @pytest.fixture
    def tool(self):
        return DebugIssueTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.get_name() == "debug"
        assert "DEBUG & ROOT CAUSE ANALYSIS" in tool.get_description()
        assert tool.get_default_temperature() == 0.2

        schema = tool.get_input_schema()
        assert "error_description" in schema["properties"]
        assert schema["required"] == ["error_description"]

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.create_model")
    async def test_execute_with_context(self, mock_create_model, tool):
        """Test execution with error context"""
        # Mock model
        mock_model = Mock()
        mock_model.generate_content.return_value = Mock(
            candidates=[Mock(content=Mock(parts=[Mock(text="Root cause: race condition")]))]
        )
        mock_create_model.return_value = mock_model

        result = await tool.execute(
            {
                "error_description": "Test fails intermittently",
                "error_context": "AssertionError in test_async",
                "previous_attempts": "Added sleep, still fails",
            }
        )

        assert len(result) == 1
        assert "Debug Analysis" in result[0].text
        assert "Root cause: race condition" in result[0].text


class TestAnalyzeTool:
    """Test the analyze tool"""

    @pytest.fixture
    def tool(self):
        return AnalyzeTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.get_name() == "analyze"
        assert "ANALYZE FILES & CODE" in tool.get_description()
        assert tool.get_default_temperature() == 0.2

        schema = tool.get_input_schema()
        assert "files" in schema["properties"]
        assert "question" in schema["properties"]
        assert set(schema["required"]) == {"files", "question"}

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.create_model")
    async def test_execute_with_analysis_type(self, mock_model, tool, tmp_path):
        """Test execution with specific analysis type"""
        # Create test file
        test_file = tmp_path / "module.py"
        test_file.write_text("class Service: pass", encoding="utf-8")

        # Mock response
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(text="Architecture analysis")]

        mock_instance = Mock()
        mock_instance.generate_content.return_value = mock_response
        mock_model.return_value = mock_instance

        result = await tool.execute(
            {
                "files": [str(test_file)],
                "question": "What's the structure?",
                "analysis_type": "architecture",
                "output_format": "summary",
            }
        )

        assert len(result) == 1
        assert "ARCHITECTURE Analysis" in result[0].text
        assert "Analyzed 1 file(s)" in result[0].text
        assert "Architecture analysis" in result[0].text


class TestAbsolutePathValidation:
    """Test absolute path validation across all tools"""

    @pytest.mark.asyncio
    async def test_analyze_tool_relative_path_rejected(self):
        """Test that analyze tool rejects relative paths"""
        tool = AnalyzeTool()
        result = await tool.execute(
            {
                "files": ["./relative/path.py", "/absolute/path.py"],
                "question": "What does this do?",
            }
        )

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "error"
        assert "must be absolute" in response["content"]
        assert "./relative/path.py" in response["content"]

    @pytest.mark.asyncio
    async def test_codereview_tool_relative_path_rejected(self):
        """Test that codereview tool rejects relative paths"""
        tool = CodeReviewTool()
        result = await tool.execute(
            {
                "files": ["../parent/file.py"],
                "review_type": "full",
                "context": "Test code review for validation purposes",
            }
        )

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "error"
        assert "must be absolute" in response["content"]
        assert "../parent/file.py" in response["content"]

    @pytest.mark.asyncio
    async def test_debug_tool_relative_path_rejected(self):
        """Test that debug tool rejects relative paths"""
        tool = DebugIssueTool()
        result = await tool.execute(
            {
                "error_description": "Something broke",
                "files": ["src/main.py"],  # relative path
            }
        )

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "error"
        assert "must be absolute" in response["content"]
        assert "src/main.py" in response["content"]

    @pytest.mark.asyncio
    async def test_think_deeper_tool_relative_path_rejected(self):
        """Test that think_deeper tool rejects relative paths"""
        tool = ThinkDeeperTool()
        result = await tool.execute({"current_analysis": "My analysis", "files": ["./local/file.py"]})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "error"
        assert "must be absolute" in response["content"]
        assert "./local/file.py" in response["content"]

    @pytest.mark.asyncio
    async def test_chat_tool_relative_path_rejected(self):
        """Test that chat tool rejects relative paths"""
        tool = ChatTool()
        result = await tool.execute(
            {
                "prompt": "Explain this code",
                "files": ["code.py"],  # relative path without ./
            }
        )

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "error"
        assert "must be absolute" in response["content"]
        assert "code.py" in response["content"]

    @pytest.mark.asyncio
    @patch("tools.AnalyzeTool.create_model")
    async def test_analyze_tool_accepts_absolute_paths(self, mock_model):
        """Test that analyze tool accepts absolute paths"""
        tool = AnalyzeTool()

        # Mock the model response
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(text="Analysis complete")]

        mock_instance = Mock()
        mock_instance.generate_content.return_value = mock_response
        mock_model.return_value = mock_instance

        result = await tool.execute({"files": ["/absolute/path/file.py"], "question": "What does this do?"})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "success"
        assert "Analysis complete" in response["content"]
