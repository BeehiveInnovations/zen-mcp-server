"""
Tests for individual tool implementations
"""

from unittest.mock import Mock, patch

import pytest

from tools import AnalyzeTool, DebugIssueTool, ReviewCodeTool, ThinkDeeperTool


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
        assert "Extended Analysis by Gemini:" in result[0].text
        assert "Extended analysis" in result[0].text


class TestReviewCodeTool:
    """Test the review_code tool"""

    @pytest.fixture
    def tool(self):
        return ReviewCodeTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.get_name() == "review_code"
        assert "PROFESSIONAL CODE REVIEW" in tool.get_description()
        assert tool.get_default_temperature() == 0.2

        schema = tool.get_input_schema()
        assert "files" in schema["properties"]
        assert schema["required"] == ["files"]

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
            }
        )

        assert len(result) == 1
        assert "Code Review (SECURITY)" in result[0].text
        assert "Focus: authentication" in result[0].text
        assert "Security issues found" in result[0].text


class TestDebugIssueTool:
    """Test the debug_issue tool"""

    @pytest.fixture
    def tool(self):
        return DebugIssueTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.get_name() == "debug_issue"
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
            candidates=[
                Mock(content=Mock(parts=[Mock(text="Root cause: race condition")]))
            ]
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
