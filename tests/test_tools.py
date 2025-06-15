"""
Tests for individual tool implementations
"""

import json
from unittest.mock import Mock, patch

import pytest

from tests.mock_helpers import create_mock_provider
from tools import AnalyzeTool, ChatTool, CodeReviewTool, DebugIssueTool, ThinkDeepTool


class TestThinkDeepTool:
    """Test the thinkdeep tool"""

    @pytest.fixture
    def tool(self):
        return ThinkDeepTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.get_name() == "thinkdeep"
        assert "EXTENDED THINKING" in tool.get_description()
        assert tool.get_default_temperature() == 0.7

        schema = tool.get_input_schema()
        assert "prompt" in schema["properties"]
        assert schema["required"] == ["prompt"]

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_execute_success(self, mock_get_provider, tool):
        """Test successful execution"""
        # Mock provider
        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = True
        mock_provider.generate_content.return_value = Mock(
            content="Extended analysis", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result = await tool.execute(
            {
                "prompt": "Initial analysis",
                "problem_context": "Building a cache",
                "focus_areas": ["performance", "scalability"],
            }
        )

        assert len(result) == 1
        # Parse the JSON response
        output = json.loads(result[0].text)
        assert output["status"] == "success"
        assert "Critical Evaluation Required" in output["content"]
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
        assert "prompt" in schema["properties"]
        assert schema["required"] == ["files", "prompt"]

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_execute_with_review_type(self, mock_get_provider, tool, tmp_path):
        """Test execution with specific review type"""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def insecure(): pass", encoding="utf-8")

        # Mock provider
        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content="Security issues found", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result = await tool.execute(
            {
                "files": [str(test_file)],
                "review_type": "security",
                "focus_on": "authentication",
                "prompt": "Test code review for validation purposes",
            }
        )

        assert len(result) == 1
        assert "Security issues found" in result[0].text
        assert "Claude's Next Steps:" in result[0].text
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
        assert "prompt" in schema["properties"]
        assert schema["required"] == ["prompt"]

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_execute_with_context(self, mock_get_provider, tool):
        """Test execution with error context"""
        # Mock provider
        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content="Root cause: race condition", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result = await tool.execute(
            {
                "prompt": "Test fails intermittently",
                "error_context": "AssertionError in test_async",
                "previous_attempts": "Added sleep, still fails",
            }
        )

        assert len(result) == 1
        assert "Next Steps:" in result[0].text
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
        assert "prompt" in schema["properties"]
        assert set(schema["required"]) == {"files", "prompt"}

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_execute_with_analysis_type(self, mock_get_provider, tool, tmp_path):
        """Test execution with specific analysis type"""
        # Create test file
        test_file = tmp_path / "module.py"
        test_file.write_text("class Service: pass", encoding="utf-8")

        # Mock provider
        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content="Architecture analysis", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result = await tool.execute(
            {
                "files": [str(test_file)],
                "prompt": "What's the structure?",
                "analysis_type": "architecture",
                "output_format": "summary",
            }
        )

        assert len(result) == 1
        assert "Architecture analysis" in result[0].text
        assert "Next Steps:" in result[0].text
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
                "prompt": "What does this do?",
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
                "prompt": "Test code review for validation purposes",
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
                "prompt": "Something broke",
                "files": ["src/main.py"],  # relative path
            }
        )

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "error"
        assert "must be absolute" in response["content"]
        assert "src/main.py" in response["content"]

    @pytest.mark.asyncio
    async def test_thinkdeep_tool_relative_path_rejected(self):
        """Test that thinkdeep tool rejects relative paths"""
        tool = ThinkDeepTool()
        result = await tool.execute({"prompt": "My analysis", "files": ["./local/file.py"]})

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
    async def test_testgen_tool_relative_path_rejected(self):
        """Test that testgen tool rejects relative paths"""
        from tools import TestGenTool

        tool = TestGenTool()
        result = await tool.execute(
            {"files": ["src/main.py"], "prompt": "Generate tests for the functions"}  # relative path
        )

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "error"
        assert "must be absolute" in response["content"]
        assert "src/main.py" in response["content"]

    @pytest.mark.asyncio
    @patch("tools.AnalyzeTool.get_model_provider")
    async def test_analyze_tool_accepts_absolute_paths(self, mock_get_provider):
        """Test that analyze tool accepts absolute paths"""
        tool = AnalyzeTool()

        # Mock provider
        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content="Analysis complete", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result = await tool.execute({"files": ["/absolute/path/file.py"], "prompt": "What does this do?"})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "success"
        assert "Analysis complete" in response["content"]


class TestSpecialStatusModels:
    """Test SPECIAL_STATUS_MODELS registry and structured response handling"""

    def test_trace_complete_status_in_registry(self):
        """Test that trace_complete status is properly registered"""
        from tools.models import SPECIAL_STATUS_MODELS, TraceComplete

        assert "trace_complete" in SPECIAL_STATUS_MODELS
        assert SPECIAL_STATUS_MODELS["trace_complete"] == TraceComplete

    def test_trace_complete_model_validation(self):
        """Test TraceComplete model validation"""
        from tools.models import TraceComplete

        # Test precision mode
        precision_data = {
            "status": "trace_complete",
            "trace_type": "precision",
            "entry_point": {
                "file": "/path/to/file.py",
                "class_or_struct": "MyClass",
                "method": "myMethod",
                "signature": "def myMethod(self, param1: str) -> bool",
                "parameters": {"param1": "test"},
            },
            "call_path": [
                {
                    "from": {"file": "/path/to/file.py", "class": "MyClass", "method": "myMethod", "line": 10},
                    "to": {"file": "/path/to/other.py", "class": "OtherClass", "method": "otherMethod", "line": 20},
                    "reason": "direct call",
                    "condition": None,
                    "ambiguous": False,
                }
            ],
        }

        model = TraceComplete(**precision_data)
        assert model.status == "trace_complete"
        assert model.trace_type == "precision"
        assert model.entry_point.file == "/path/to/file.py"
        assert len(model.call_path) == 1

        # Test dependencies mode
        dependencies_data = {
            "status": "trace_complete",
            "trace_type": "dependencies",
            "target": {
                "file": "/path/to/file.py",
                "class_or_struct": "MyClass",
                "method": "myMethod",
                "signature": "def myMethod(self, param1: str) -> bool",
            },
            "incoming_dependencies": [
                {
                    "from_file": "/path/to/caller.py",
                    "from_class": "CallerClass",
                    "from_method": "callerMethod",
                    "line": 15,
                    "type": "direct_call",
                }
            ],
            "outgoing_dependencies": [
                {
                    "to_file": "/path/to/dependency.py",
                    "to_class": "DepClass",
                    "to_method": "depMethod",
                    "line": 25,
                    "type": "method_call",
                }
            ],
        }

        model = TraceComplete(**dependencies_data)
        assert model.status == "trace_complete"
        assert model.trace_type == "dependencies"
        assert model.target.file == "/path/to/file.py"
        assert len(model.incoming_dependencies) == 1
        assert len(model.outgoing_dependencies) == 1
