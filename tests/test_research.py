"""Tests for Research tool functionality."""

import os
from unittest.mock import patch

import pytest

from tools.research import ResearchRequest, ResearchTool
from tools.shared.base_models import ToolRequest

os.environ["RESEARCH_DISABLE_EXPORT"] = "true"


class TestResearchTool:
    """Test ResearchTool basic functionality."""

    @pytest.fixture
    def tool(self):
        """Create a ResearchTool instance for testing."""
        return ResearchTool()

    def test_tool_name(self, tool):
        """Test that tool returns correct name."""
        assert tool.get_name() == "research"

    def test_tool_description(self, tool):
        """Test that tool returns a description."""
        description = tool.get_description()
        assert isinstance(description, str)
        assert "research" in description.lower()
        assert "perplexity" in description.lower()

    def test_get_default_model(self, tool):
        """Test that tool returns correct default model."""
        assert tool.get_default_model() == "sonar-pro"

    def test_get_system_prompt(self, tool):
        """Test that tool returns a system prompt."""
        prompt = tool.get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_request_model(self, tool):
        """Test that tool returns correct request model."""
        assert tool.get_request_model() == ResearchRequest

    def test_tool_fields(self, tool):
        """Test that tool defines required fields."""
        fields = tool.get_tool_fields()

        # Check required field
        assert "query" in fields
        assert fields["query"]["type"] == "string"

        # Check optional fields
        assert "domain_filter" in fields
        assert "recency_filter" in fields
        assert "search_mode" in fields
        assert "return_related_questions" in fields
        assert "max_tokens" in fields

    def test_required_fields(self, tool):
        """Test that tool specifies required fields."""
        required = tool.get_required_fields()
        assert "query" in required


class TestResearchRequest:
    """Test ResearchRequest model validation."""

    def test_minimal_request(self):
        """Test creating request with minimal data."""
        request = ResearchRequest(
            query="test query",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        assert request.query == "test query"
        assert request.domain_filter is None
        assert request.recency_filter is None
        assert request.search_mode == "medium"
        assert request.return_related_questions is True
        assert request.max_tokens == 2048

    def test_full_request(self):
        """Test creating request with all parameters."""
        request = ResearchRequest(
            query="test query",
            domain_filter=["stackoverflow.com", "github.com"],
            recency_filter="week",
            search_mode="high",
            return_related_questions=False,
            max_tokens=1024,
            model="sonar-pro",
            temperature=0.8,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )

        assert request.query == "test query"
        assert request.domain_filter == ["stackoverflow.com", "github.com"]
        assert request.recency_filter == "week"
        assert request.search_mode == "high"
        assert request.return_related_questions is False
        assert request.max_tokens == 1024
        assert request.model == "sonar-pro"
        assert request.temperature == 0.8

    def test_max_tokens_validation(self):
        """Test max_tokens field validation."""
        # Valid range
        request = ResearchRequest(
            query="test",
            max_tokens=100,
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        assert request.max_tokens == 100

        request = ResearchRequest(
            query="test",
            max_tokens=4096,
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        assert request.max_tokens == 4096

        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            ResearchRequest(
                query="test",
                max_tokens=50,  # Below minimum
                model="sonar-pro",
                temperature=0.0,
                thinking_mode=None,
                use_websearch=False,
                continuation_id=None,
                images=None,
            )

        with pytest.raises(ValueError):
            ResearchRequest(
                query="test",
                max_tokens=5000,  # Above maximum
                model="sonar-pro",
                temperature=0.0,
                thinking_mode=None,
                use_websearch=False,
                continuation_id=None,
                images=None,
            )

    def test_inheritance_from_tool_request(self):
        """Test that ResearchRequest inherits from ToolRequest."""
        request = ResearchRequest(
            query="test",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        assert isinstance(request, ToolRequest)


class TestResearchToolParameterExtraction:
    """Test Perplexity parameter extraction and handling."""

    @pytest.fixture
    def tool(self):
        """Create a ResearchTool instance for testing."""
        return ResearchTool()

    def test_get_perplexity_params_minimal(self, tool):
        """Test parameter extraction with minimal request."""
        request = ResearchRequest(
            query="test query",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        params = tool.get_perplexity_params(request)

        # Should include defaults
        assert params["search_mode"] == "medium"
        assert params["return_related_questions"] is True
        assert params["max_tokens"] == 2048

        # Should not include empty optional parameters
        assert "search_domain_filter" not in params
        assert "search_recency_filter" not in params

    def test_get_perplexity_params_full(self, tool):
        """Test parameter extraction with full request."""
        request = ResearchRequest(
            query="test query",
            domain_filter=["example.com"],
            recency_filter="day",
            search_mode="high",
            return_related_questions=False,
            max_tokens=1024,
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        params = tool.get_perplexity_params(request)

        assert params["search_domain_filter"] == ["example.com"]
        assert params["search_recency_filter"] == "day"
        assert params["search_mode"] == "high"
        assert params["return_related_questions"] is False
        assert params["max_tokens"] == 1024

    def test_get_perplexity_params_empty_domain_filter(self, tool):
        """Test parameter extraction with empty domain filter."""
        request = ResearchRequest(
            query="test",
            domain_filter=[],
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        params = tool.get_perplexity_params(request)

        # Empty list should not be included
        assert "search_domain_filter" not in params


class TestResearchToolPromptPreparation:
    """Test prompt preparation for research tasks."""

    @pytest.fixture
    def tool(self):
        """Create a ResearchTool instance for testing."""
        return ResearchTool()

    @pytest.mark.asyncio
    async def test_prepare_prompt_basic(self, tool):
        """Test basic prompt preparation."""
        request = ResearchRequest(
            query="Python async patterns",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )

        prompt = await tool.prepare_prompt(request)

        assert isinstance(prompt, str)
        assert "Python async patterns" in prompt
        assert "research" in prompt.lower()
        assert "web search" in prompt.lower()

    @pytest.mark.asyncio
    async def test_prepare_prompt_includes_guidelines(self, tool):
        """Test that prompt includes research guidelines."""
        request = ResearchRequest(
            query="test query",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )

        prompt = await tool.prepare_prompt(request)

        # Should include research guidance
        assert "accurate" in prompt.lower()
        assert "sources" in prompt.lower()
        assert "citations" in prompt.lower()


class TestResearchToolResponseFormatting:
    """Test response formatting with metadata and sources."""

    @pytest.fixture
    def tool(self):
        """Create a ResearchTool instance for testing."""
        return ResearchTool()

    def test_format_response_basic(self, tool):
        """Test basic response formatting without metadata."""
        request = ResearchRequest(
            query="test",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        response = "This is a test response"

        formatted = tool.format_response(response, request)

        assert formatted == response

    def test_format_response_with_search_results(self, tool):
        """Test response formatting with search results metadata."""
        request = ResearchRequest(
            query="test",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        response = "This is a test response"
        model_info = {
            "metadata": {
                "search_results": [
                    {"title": "Example Article", "url": "https://example.com/article", "date": "2025-01-01"},
                    {"title": "Another Source", "url": "https://another.com/source"},
                ]
            }
        }

        formatted = tool.format_response(response, request, model_info)

        assert "## Sources" in formatted
        assert "Example Article" in formatted
        assert "https://example.com/article" in formatted
        assert "2025-01-01" in formatted
        assert "Another Source" in formatted

    def test_format_response_with_citations_fallback(self, tool):
        """Test response formatting with citations as fallback."""
        request = ResearchRequest(
            query="test",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        response = "This is a test response"
        model_info = {"metadata": {"citations": ["https://example.com", "https://another.com"]}}

        formatted = tool.format_response(response, request, model_info)

        assert "## Citations" in formatted
        assert "https://example.com" in formatted
        assert "https://another.com" in formatted

    def test_format_response_with_related_questions(self, tool):
        """Test response formatting with related questions."""
        request = ResearchRequest(
            query="test",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        response = "This is a test response"
        model_info = {"metadata": {"related_questions": ["What about X?", "How does Y work?"]}}

        formatted = tool.format_response(response, request, model_info)

        assert "## Related Questions" in formatted
        assert "What about X?" in formatted
        assert "How does Y work?" in formatted

    def test_format_response_with_search_efficiency(self, tool):
        """Test response formatting with search efficiency info."""
        request = ResearchRequest(
            query="test",
            model="sonar-pro",
            temperature=0.0,
            thinking_mode=None,
            use_websearch=False,
            continuation_id=None,
            images=None,
        )
        response = "This is a test response"
        model_info = {"metadata": {"search_efficiency": 2.5, "search_queries_count": 3}}

        formatted = tool.format_response(response, request, model_info)

        assert "Search efficiency: 2.50" in formatted
        assert "Queries used: 3" in formatted


class TestResearchToolExecution:
    """Test research tool execution flow."""

    @pytest.fixture
    def tool(self):
        """Create a ResearchTool instance for testing."""
        return ResearchTool()

    @pytest.mark.asyncio
    async def test_execute_parameter_injection(self, tool):
        """Test that execute method injects Perplexity parameters."""
        arguments = {"query": "test query", "search_mode": "high", "domain_filter": ["example.com"]}

        with patch.object(tool, "get_perplexity_params") as mock_params:
            mock_params.return_value = {
                "search_mode": "high",
                "search_domain_filter": ["example.com"],
                "max_tokens": 2048,
            }

            with patch("tools.simple.base.SimpleTool.execute") as mock_super:
                mock_super.return_value = []

                await tool.execute(arguments)

                # Verify parameters were injected
                mock_super.assert_called_once()
                call_args = mock_super.call_args[0][0]

                assert "search_mode" in call_args
                assert "search_domain_filter" in call_args
                assert "max_tokens" in call_args


class TestResearchToolIntegration:
    """Integration tests for ResearchTool with mocked dependencies."""

    @pytest.fixture
    def tool(self):
        """Create a ResearchTool instance for testing."""
        return ResearchTool()

    def test_tool_registration_ready(self, tool):
        """Test that tool is ready for registration."""
        # Tool should have all required methods for registration
        assert hasattr(tool, "get_name")
        assert hasattr(tool, "get_description")
        assert hasattr(tool, "execute")
        assert hasattr(tool, "get_input_schema")

        # Test that get_input_schema works
        schema = tool.get_input_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "required" in schema
        assert "query" in schema["required"]

    def test_system_prompt_import(self, tool):
        """Test that system prompt can be imported successfully."""
        try:
            from systemprompts.research_prompt import RESEARCH_PROMPT

            assert isinstance(RESEARCH_PROMPT, str)
            assert len(RESEARCH_PROMPT) > 0
        except ImportError:
            pytest.fail("Cannot import RESEARCH_PROMPT from systemprompts.research_prompt")

    def test_tool_fields_comprehensive(self, tool):
        """Test that all tool fields are properly defined."""
        fields = tool.get_tool_fields()

        # Check that all expected fields are present
        expected_fields = [
            "query",
            "domain_filter",
            "recency_filter",
            "search_mode",
            "return_related_questions",
            "max_tokens",
        ]

        for field in expected_fields:
            assert field in fields
            assert "type" in fields[field]
            assert "description" in fields[field]

        # Check field types
        assert fields["query"]["type"] == "string"
        assert fields["domain_filter"]["type"] == "array"
        assert fields["recency_filter"]["type"] == "string"
        assert fields["search_mode"]["type"] == "string"
        assert fields["return_related_questions"]["type"] == "boolean"
        assert fields["max_tokens"]["type"] == "integer"

    def test_model_inheritance_chain(self, tool):
        """Test that the tool properly inherits from SimpleTool."""
        from tools.shared.base_tool import BaseTool
        from tools.simple.base import SimpleTool

        assert isinstance(tool, SimpleTool)
        assert isinstance(tool, BaseTool)

        # Should have inherited methods
        assert hasattr(tool, "get_input_schema")
        assert hasattr(tool, "get_annotations")
        assert hasattr(tool, "format_response")
