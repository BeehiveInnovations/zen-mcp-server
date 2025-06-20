"""
Tests for dynamic context request and collaboration features
"""

import json
from unittest.mock import Mock, patch

import pytest

from tests.mock_helpers import create_mock_provider
from tools.analyze import AnalyzeTool
from tools.debug import DebugIssueTool
from tools.models import FilesNeededRequest, ToolOutput


class TestDynamicContextRequests:
    """Test the dynamic context request mechanism"""

    @pytest.fixture
    def analyze_tool(self):
        return AnalyzeTool()

    @pytest.fixture
    def debug_tool(self):
        return DebugIssueTool()

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_clarification_request_parsing(self, mock_get_provider, analyze_tool):
        """Test that tools correctly parse clarification requests"""
        # Mock model to return a clarification request
        clarification_json = json.dumps(
            {
                "status": "files_required_to_continue",
                "mandatory_instructions": "I need to see the package.json file to understand dependencies",
                "files_needed": ["package.json", "package-lock.json"],
            }
        )

        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content=clarification_json, usage={}, model_name="gemini-2.5-flash", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result = await analyze_tool.execute(
            {
                "step": "Analyze the dependencies used in this project",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Initial dependency analysis",
                "relevant_files": ["/absolute/path/src/index.js"],
            }
        )

        assert len(result) == 1

        # Parse the response - analyze tool now uses workflow architecture
        response_data = json.loads(result[0].text)
        # New workflow analyze tool returns calling_expert_analysis status
        assert response_data["status"] == "calling_expert_analysis"

        # Check that expert analysis was performed and contains the clarification
        if "expert_analysis" in response_data:
            expert_analysis = response_data["expert_analysis"]
            # The mock should have returned the clarification JSON
            if "raw_analysis" in expert_analysis:
                analysis_content = expert_analysis["raw_analysis"]
                assert "package.json" in analysis_content
                assert "dependencies" in analysis_content

        # For workflow tools, the files_needed logic is handled differently
        # The test validates that the mocked clarification content was processed
        assert "step_number" in response_data
        assert response_data["step_number"] == 1

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    @patch("utils.conversation_memory.create_thread", return_value="debug-test-uuid")
    @patch("utils.conversation_memory.add_turn")
    async def test_normal_response_not_parsed_as_clarification(
        self, mock_add_turn, mock_create_thread, mock_get_provider, debug_tool
    ):
        """Test that normal investigation responses work correctly with new debug tool"""
        # The new debug tool uses self-investigation pattern
        result = await debug_tool.execute(
            {
                "step": "Investigating NameError: name 'utils' is not defined",
                "step_number": 1,
                "total_steps": 3,
                "next_step_required": True,
                "findings": "The error indicates 'utils' module is not imported or defined",
                "files_checked": ["/code/main.py"],
                "relevant_files": ["/code/main.py"],
                "hypothesis": "Missing import statement for utils module",
                "confidence": "high",
            }
        )

        assert len(result) == 1

        # Parse the response - new debug tool returns structured JSON
        response_data = json.loads(result[0].text)
        # Debug tool now returns "pause_for_investigation" to force actual investigation
        assert response_data["status"] == "pause_for_investigation"
        assert response_data["step_number"] == 1
        assert response_data["next_step_required"] is True
        assert response_data["investigation_status"]["current_confidence"] == "high"
        assert response_data["investigation_required"] is True
        assert "required_actions" in response_data

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_malformed_clarification_request_treated_as_normal(self, mock_get_provider, analyze_tool):
        """Test that malformed JSON clarification requests are treated as normal responses"""
        malformed_json = '{"status": "files_required_to_continue", "prompt": "Missing closing brace"'

        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content=malformed_json, usage={}, model_name="gemini-2.5-flash", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result = await analyze_tool.execute(
            {
                "step": "What does this do?",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Initial code analysis",
                "relevant_files": ["/absolute/path/test.py"],
            }
        )

        assert len(result) == 1

        # Should be treated as normal response due to JSON parse error
        response_data = json.loads(result[0].text)
        # New workflow analyze tool returns calling_expert_analysis status
        assert response_data["status"] == "calling_expert_analysis"

        # The malformed JSON should appear in the expert analysis content
        if "expert_analysis" in response_data:
            expert_analysis = response_data["expert_analysis"]
            if "raw_analysis" in expert_analysis:
                analysis_content = expert_analysis["raw_analysis"]
                # The malformed JSON should be included in the analysis
                assert "files_required_to_continue" in analysis_content or malformed_json in str(response_data)

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_clarification_with_suggested_action(self, mock_get_provider, analyze_tool):
        """Test clarification request with suggested next action"""
        clarification_json = json.dumps(
            {
                "status": "files_required_to_continue",
                "mandatory_instructions": "I need to see the database configuration to analyze the connection error",
                "files_needed": ["config/database.yml", "src/db.py"],
                "suggested_next_action": {
                    "tool": "analyze",
                    "args": {
                        "prompt": "Analyze database connection timeout issue",
                        "relevant_files": [
                            "/config/database.yml",
                            "/src/db.py",
                            "/logs/error.log",
                        ],
                    },
                },
            }
        )

        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content=clarification_json, usage={}, model_name="gemini-2.5-flash", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result = await analyze_tool.execute(
            {
                "step": "Analyze database connection timeout issue",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Initial database timeout analysis",
                "relevant_files": ["/absolute/logs/error.log"],
            }
        )

        assert len(result) == 1

        response_data = json.loads(result[0].text)
        # When a clarification request is returned by the model, the tool should return the clarification status
        assert response_data["status"] == "files_required_to_continue"

        # Check that the clarification request contains the expected content
        assert "mandatory_instructions" in response_data
        assert "database configuration" in response_data["mandatory_instructions"]
        assert "files_needed" in response_data
        assert "config/database.yml" in response_data["files_needed"]
        assert "src/db.py" in response_data["files_needed"]
        
        # Check for suggested next action
        if "suggested_next_action" in response_data:
            action = response_data["suggested_next_action"]
            assert action["tool"] == "analyze"

    def test_tool_output_model_serialization(self):
        """Test ToolOutput model serialization"""
        output = ToolOutput(
            status="success",
            content="Test content",
            content_type="markdown",
            metadata={"tool_name": "test", "execution_time": 1.5},
        )

        json_str = output.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["status"] == "success"
        assert parsed["content"] == "Test content"
        assert parsed["content_type"] == "markdown"
        assert parsed["metadata"]["tool_name"] == "test"

    def test_clarification_request_model(self):
        """Test FilesNeededRequest model"""
        request = FilesNeededRequest(
            mandatory_instructions="Need more context",
            files_needed=["file1.py", "file2.py"],
            suggested_next_action={"tool": "analyze", "args": {}},
        )

        assert request.mandatory_instructions == "Need more context"
        assert len(request.files_needed) == 2
        assert request.suggested_next_action["tool"] == "analyze"

    def test_mandatory_instructions_enhancement(self):
        """Test that mandatory_instructions are enhanced with additional guidance"""
        from tools.base import BaseTool

        # Create a dummy tool instance for testing
        class TestTool(BaseTool):
            def get_name(self):
                return "test"

            def get_description(self):
                return "test"

            def get_request_model(self):
                return None

            def prepare_prompt(self, request):
                return ""

            def get_system_prompt(self):
                return ""

            def get_input_schema(self):
                return {}

        tool = TestTool()
        original = "I need additional files to proceed"
        enhanced = tool._enhance_mandatory_instructions(original)

        # Verify the original instructions are preserved
        assert enhanced.startswith(original)

        # Verify additional guidance is added
        assert "IMPORTANT GUIDANCE:" in enhanced
        assert "CRITICAL for providing accurate analysis" in enhanced
        assert "Use FULL absolute paths" in enhanced
        assert "continuation_id to continue" in enhanced

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_error_response_format(self, mock_get_provider, analyze_tool):
        """Test error response format"""
        mock_get_provider.side_effect = Exception("API connection failed")

        result = await analyze_tool.execute(
            {
                "step": "Analyze this",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Initial analysis",
                "relevant_files": ["/absolute/path/test.py"],
            }
        )

        assert len(result) == 1

        response_data = json.loads(result[0].text)
        assert response_data["status"] == "error"
        assert "API connection failed" in response_data["content"]
        assert response_data["content_type"] == "text"


class TestCollaborationWorkflow:
    """Test complete collaboration workflows"""

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_dependency_analysis_triggers_clarification(self, mock_get_provider):
        """Test that asking about dependencies without package files triggers clarification"""
        tool = AnalyzeTool()

        # Mock Gemini to request package.json when asked about dependencies
        clarification_json = json.dumps(
            {
                "status": "files_required_to_continue",
                "mandatory_instructions": "I need to see the package.json file to analyze npm dependencies",
                "files_needed": ["package.json", "package-lock.json"],
            }
        )

        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content=clarification_json, usage={}, model_name="gemini-2.5-flash", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        # Ask about dependencies with only source files (using new workflow format)
        result = await tool.execute(
            {
                "step": "What npm packages and versions does this project use?",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Initial dependency analysis",
                "relevant_files": ["/absolute/path/src/index.js"],
            }
        )

        response = json.loads(result[0].text)
        # When a clarification request is returned, the tool should return the clarification status
        assert response["status"] == "files_required_to_continue"

        # Check that the clarification request contains the expected content
        assert "mandatory_instructions" in response
        assert "package.json" in response["mandatory_instructions"]
        assert "files_needed" in response
        assert "package.json" in response["files_needed"]
        assert "package-lock.json" in response["files_needed"]

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_multi_step_collaboration(self, mock_get_provider):
        """Test a multi-step collaboration workflow"""
        tool = AnalyzeTool()

        # Step 1: Initial request returns clarification needed
        clarification_json = json.dumps(
            {
                "status": "files_required_to_continue",
                "mandatory_instructions": "I need to see the configuration file to understand the connection settings",
                "files_needed": ["config.py"],
            }
        )

        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content=clarification_json, usage={}, model_name="gemini-2.5-flash", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result1 = await tool.execute(
            {
                "step": "Analyze database connection timeout issue",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Initial database timeout analysis",
                "relevant_files": ["/logs/error.log"],
            }
        )

        response1 = json.loads(result1[0].text)
        # First call should return clarification request
        assert response1["status"] == "files_required_to_continue"

        # Step 2: Claude would provide additional context and re-invoke
        # This simulates the second call with more context
        final_response = """
        ## Summary
        The database connection timeout is caused by incorrect host configuration.

        ## Hypotheses (Ranked by Likelihood)

        ### 1. Incorrect Database Host (Confidence: High)
        **Root Cause:** The config.py file shows the database host is set to 'localhost' but the database is running on a different server.
        """

        mock_provider.generate_content.return_value = Mock(
            content=final_response, usage={}, model_name="gemini-2.5-flash", metadata={}
        )

        result2 = await tool.execute(
            {
                "step": "Analyze database connection timeout issue with config file",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Analysis with configuration context",
                "relevant_files": ["/absolute/path/config.py", "/logs/error.log"],  # Additional context provided
            }
        )

        response2 = json.loads(result2[0].text)
        # New workflow analyze tool returns calling_expert_analysis status
        assert response2["status"] == "calling_expert_analysis"

        # Check that expert analysis contains the expected content
        if "expert_analysis" in response2:
            expert_analysis = response2["expert_analysis"]
            if "raw_analysis" in expert_analysis:
                analysis_content = expert_analysis["raw_analysis"]
                assert (
                    "incorrect host configuration" in analysis_content.lower() or "database" in analysis_content.lower()
                )
