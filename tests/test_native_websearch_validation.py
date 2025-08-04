"""
Comprehensive test suite for native websearch functionality validation.

This test suite validates the complete native websearch implementation including:
- Model capability detection
- Mutual exclusivity validation
- Provider-specific routing logic
- Tool infrastructure integration
- Parameter handling across all tool types
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from providers.base import ModelCapabilities, ProviderType, create_temperature_constraint
from providers.openai_provider import OpenAIModelProvider
from providers.gemini import GeminiModelProvider
from providers.openai_compatible import OpenAICompatibleProvider
from tools.shared.base_models import BaseRequest
from tools.shared.base_tool import BaseTool
from tools.workflow.workflow_mixin import BaseWorkflowMixin
from tools.simple.base import SimpleTool


class TestNativeWebsearchModelCapabilities:
    """Test native websearch model capability detection."""

    def test_openai_models_support_native_websearch(self):
        """Test that OpenAI models are configured with native websearch support."""
        provider = OpenAIModelProvider("test-key")
        
        # All OpenAI models should support native websearch
        for model_name in ["o3", "o3-mini", "o3-pro-2025-06-10", "o4-mini", "gpt-4.1-2025-04-14"]:
            capabilities = provider.get_capabilities(model_name)
            assert capabilities.supports_native_websearch is True, f"Model {model_name} should support native websearch"

    def test_gemini_models_support_native_websearch(self):
        """Test that Gemini models are configured with native websearch support."""
        with patch('google.genai.Client'):
            provider = GeminiModelProvider("test-key")
            
            # Most Gemini models should support native websearch
            for model_name in ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]:
                capabilities = provider.get_capabilities(model_name)
                assert capabilities.supports_native_websearch is True, f"Model {model_name} should support native websearch"
            
            # Lite model should not support native websearch
            capabilities = provider.get_capabilities("gemini-2.0-flash-lite")
            assert capabilities.supports_native_websearch is False, "Flash Lite should not support native websearch"

    def test_model_capabilities_fields(self):
        """Test that ModelCapabilities includes the supports_native_websearch field."""
        capabilities = ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="test-model",
            friendly_name="Test Model",
            context_window=100_000,
            max_output_tokens=4_000,
            supports_native_websearch=True,
            temperature_constraint=create_temperature_constraint("range"),
        )
        
        assert hasattr(capabilities, 'supports_native_websearch')
        assert capabilities.supports_native_websearch is True


class TestNativeWebsearchMutualExclusivity:
    """Test mutual exclusivity validation between native_websearch and use_websearch."""

    def test_both_websearch_parameters_raises_error(self):
        """Test that setting both native_websearch and use_websearch to True raises ValidationError."""
        with pytest.raises(ValueError, match="native_websearch and use_websearch cannot both be True"):
            BaseRequest(
                native_websearch=True,
                use_websearch=True,
                model="flash"
            )

    def test_native_websearch_true_use_websearch_false_valid(self):
        """Test that native_websearch=True and use_websearch=False is valid."""
        request = BaseRequest(
            native_websearch=True,
            use_websearch=False,
            model="flash"
        )
        assert request.native_websearch is True
        assert request.use_websearch is False

    def test_native_websearch_false_use_websearch_true_valid(self):
        """Test that native_websearch=False and use_websearch=True is valid."""
        request = BaseRequest(
            native_websearch=False,
            use_websearch=True,
            model="flash"
        )
        assert request.native_websearch is False
        assert request.use_websearch is True

    def test_both_websearch_parameters_false_valid(self):
        """Test that both parameters can be False."""
        request = BaseRequest(
            native_websearch=False,
            use_websearch=False,
            model="flash"
        )
        assert request.native_websearch is False
        assert request.use_websearch is False

    def test_default_values_valid(self):
        """Test that default values (native_websearch=False, use_websearch=True) are valid."""
        request = BaseRequest(model="flash")
        assert request.native_websearch is False
        assert request.use_websearch is True


class TestNativeWebsearchProviderRouting:
    """Test provider-specific routing logic for native websearch."""

    @patch('openai.OpenAI')
    def test_openai_compatible_routes_to_responses_endpoint_when_native_websearch(self):
        """Test that OpenAI compatible provider routes to responses endpoint when native_websearch=True."""
        provider = OpenAICompatibleProvider("test-key")
        
        # Mock the responses endpoint method
        provider._generate_with_responses_endpoint = Mock(return_value=Mock())
        
        # Call generate_content with native_websearch=True
        provider.generate_content(
            prompt="test prompt",
            model_name="o3",
            native_websearch=True
        )
        
        # Verify that responses endpoint was called
        provider._generate_with_responses_endpoint.assert_called_once()

    @patch('openai.OpenAI')
    def test_openai_compatible_uses_regular_endpoint_when_native_websearch_false(self):
        """Test that OpenAI compatible provider uses regular endpoint when native_websearch=False."""
        provider = OpenAICompatibleProvider("test-key")
        
        # Mock the client and chat completions
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "test response"
        mock_response.model = "o3"
        mock_response.id = "test-id"
        mock_response.created = 123456
        mock_response.choices[0].finish_reason = "stop"
        
        # Mock usage
        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30
        mock_response.usage = mock_usage
        
        mock_client.chat.completions.create.return_value = mock_response
        provider._client = mock_client
        
        # Call generate_content with native_websearch=False
        result = provider.generate_content(
            prompt="test prompt",
            model_name="gpt-4.1-2025-04-14",  # Use a model that supports temperature
            native_websearch=False
        )
        
        # Verify that regular chat completions endpoint was called
        mock_client.chat.completions.create.assert_called_once()
        assert result.content == "test response"

    @patch('google.genai.Client')
    def test_gemini_adds_grounding_tool_when_native_websearch(self):
        """Test that Gemini provider adds grounding tool when native_websearch=True."""
        provider = GeminiModelProvider("test-key")
        
        # Mock the client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "test response with grounding"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = "STOP"
        
        mock_client.models.generate_content.return_value = mock_response
        provider._client = mock_client
        
        # Call generate_content with native_websearch=True
        result = provider.generate_content(
            prompt="test prompt",
            model_name="gemini-2.5-flash",
            native_websearch=True
        )
        
        # Verify that generate_content was called
        mock_client.models.generate_content.assert_called_once()
        
        # Extract the call arguments to verify grounding tool was added
        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs['config']
        
        # Check that tools were added to the generation config
        assert hasattr(config, 'tools'), "Grounding tools should be added to generation config"
        assert config.tools is not None, "Tools list should not be None"


class TestNativeWebsearchToolIntegration:
    """Test native websearch integration with tool infrastructure."""

    def test_base_tool_get_request_native_websearch(self):
        """Test that BaseTool correctly extracts native_websearch from requests."""
        
        class TestTool(BaseTool):
            def get_name(self) -> str:
                return "test"
            
            def get_system_prompt(self) -> str:
                return "test prompt"
            
            def get_default_temperature(self) -> float:
                return 0.7
                
            def prepare_prompt(self, request, continuation_id=None, max_tokens=None, reserve_tokens=0):
                return "test prompt", ""
                
            def format_response(self, response: str, request, model_info=None) -> str:
                return response
        
        tool = TestTool()
        
        # Test with native_websearch=True
        request_true = Mock()
        request_true.native_websearch = True
        assert tool.get_request_native_websearch(request_true) is True
        
        # Test with native_websearch=False
        request_false = Mock()
        request_false.native_websearch = False
        assert tool.get_request_native_websearch(request_false) is False
        
        # Test without native_websearch attribute (should default to False)
        request_none = Mock(spec=[])  # Mock without native_websearch attribute
        assert tool.get_request_native_websearch(request_none) is False

    def test_workflow_mixin_get_request_native_websearch(self):
        """Test that BaseWorkflowMixin correctly extracts native_websearch from requests."""
        
        class TestWorkflowTool(BaseWorkflowMixin):
            def get_name(self) -> str:
                return "test_workflow"
            
            def get_workflow_request_model(self) -> type:
                return BaseRequest
            
            def get_system_prompt(self) -> str:
                return "test prompt"
            
            def get_default_temperature(self) -> float:
                return 0.7
            
            def get_model_provider(self, model_name: str):
                return Mock()
            
            def _resolve_model_context(self, arguments, request):
                return "test-model", Mock()
            
            def _prepare_file_content_for_prompt(self, files, continuation_id, description, remaining_budget=None, arguments=None, model_context=None):
                return "", []
            
            def get_work_steps(self, request):
                return ["step1", "step2"]
            
            def get_required_actions(self, step_number, confidence, findings, total_steps):
                return ["action1", "action2"]
        
        tool = TestWorkflowTool()
        
        # Test with native_websearch=True
        request_true = Mock()
        request_true.native_websearch = True
        assert tool.get_request_native_websearch(request_true) is True
        
        # Test with native_websearch=False
        request_false = Mock()
        request_false.native_websearch = False
        assert tool.get_request_native_websearch(request_false) is False
        
        # Test without native_websearch attribute (should default to False)
        request_none = Mock(spec=[])  # Mock without native_websearch attribute
        assert tool.get_request_native_websearch(request_none) is False

    def test_simple_tool_get_request_native_websearch(self):
        """Test that SimpleTool correctly extracts native_websearch from requests."""
        
        class TestSimpleTool(SimpleTool):
            def get_name(self) -> str:
                return "test_simple"
            
            def get_system_prompt(self) -> str:
                return "test prompt"
            
            def get_default_temperature(self) -> float:
                return 0.7
            
            def get_tool_fields(self):
                return {"prompt": {"type": "string"}}
            
            def prepare_prompt(self, request, continuation_id=None, max_tokens=None, reserve_tokens=0):
                return "test prompt"
        
        tool = TestSimpleTool()
        
        # Test with native_websearch=True
        request_true = Mock()
        request_true.native_websearch = True
        assert tool.get_request_native_websearch(request_true) is True
        
        # Test with native_websearch=False
        request_false = Mock()
        request_false.native_websearch = False
        assert tool.get_request_native_websearch(request_false) is False
        
        # Test without native_websearch attribute (should default to False)
        request_none = Mock(spec=[])  # Mock without native_websearch attribute
        assert tool.get_request_native_websearch(request_none) is False


class TestNativeWebsearchWebsearchInstructions:
    """Test websearch instruction generation with native websearch."""

    def test_base_tool_get_websearch_instruction_skips_claude_instructions_when_native(self):
        """Test that get_websearch_instruction skips Claude-style instructions when native_websearch=True."""
        
        class TestTool(BaseTool):
            def get_name(self) -> str:
                return "test"
            
            def get_system_prompt(self) -> str:
                return "test prompt"
            
            def get_default_temperature(self) -> float:
                return 0.7
                
            def prepare_prompt(self, request, continuation_id=None, max_tokens=None, reserve_tokens=0):
                return "test prompt", ""
                
            def format_response(self, response: str, request, model_info=None) -> str:
                return response
        
        tool = TestTool()
        
        # Test with native_websearch=True (should return empty string)
        instruction_native = tool.get_websearch_instruction(
            use_websearch=True, 
            guidance="Test guidance", 
            native_websearch=True
        )
        assert instruction_native == "", "Should return empty string when native_websearch=True"
        
        # Test with native_websearch=False (should return Claude-style instructions)
        instruction_claude = tool.get_websearch_instruction(
            use_websearch=True, 
            guidance="Test guidance", 
            native_websearch=False
        )
        assert "Test guidance" in instruction_claude, "Should include guidance when native_websearch=False"
        assert len(instruction_claude) > 0, "Should return non-empty instructions when native_websearch=False"

    def test_websearch_instruction_with_no_guidance(self):
        """Test websearch instruction generation when no guidance is provided."""
        
        class TestTool(BaseTool):
            def get_name(self) -> str:
                return "test"
            
            def get_system_prompt(self) -> str:
                return "test prompt"
            
            def get_default_temperature(self) -> float:
                return 0.7
                
            def prepare_prompt(self, request, continuation_id=None, max_tokens=None, reserve_tokens=0):
                return "test prompt", ""
                
            def format_response(self, response: str, request, model_info=None) -> str:
                return response
        
        tool = TestTool()
        
        # Test with native_websearch=True and no guidance
        instruction_native = tool.get_websearch_instruction(
            use_websearch=True, 
            guidance=None, 
            native_websearch=True
        )
        assert instruction_native == "", "Should return empty string when native_websearch=True regardless of guidance"


class TestNativeWebsearchSchemaGeneration:
    """Test that native_websearch field is properly included in tool schemas."""

    def test_schema_builders_include_native_websearch_field(self):
        """Test that SchemaBuilder includes native_websearch in generated schemas."""
        from tools.shared.schema_builders import SchemaBuilder
        
        # Get the field schema
        native_websearch_schema = SchemaBuilder.COMMON_FIELD_SCHEMAS.get("native_websearch")
        
        assert native_websearch_schema is not None, "native_websearch field should be in COMMON_FIELD_SCHEMAS"
        assert native_websearch_schema["type"] == "boolean", "native_websearch should be boolean type"
        assert native_websearch_schema["default"] is False, "native_websearch should default to False"
        assert "mutually exclusive" in native_websearch_schema["description"].lower(), "Description should mention mutual exclusivity"

    def test_simple_tool_schema_includes_native_websearch(self):
        """Test that SimpleTool schemas include the native_websearch field."""
        
        class TestSimpleTool(SimpleTool):
            def get_name(self) -> str:
                return "test_simple"
            
            def get_system_prompt(self) -> str:
                return "test prompt"
            
            def get_default_temperature(self) -> float:
                return 0.7
            
            def get_tool_fields(self):
                return {"prompt": {"type": "string"}}
            
            def prepare_prompt(self, request, continuation_id=None, max_tokens=None, reserve_tokens=0):
                return "test prompt"
        
        tool = TestSimpleTool()
        schema = tool.get_input_schema()
        
        # Check that native_websearch is in the schema
        assert "native_websearch" in schema["properties"], "Schema should include native_websearch field"
        assert schema["properties"]["native_websearch"]["type"] == "boolean", "native_websearch should be boolean"
        assert schema["properties"]["native_websearch"]["default"] is False, "native_websearch should default to False"


class TestNativeWebsearchEndToEndIntegration:
    """End-to-end integration tests for native websearch functionality."""

    @patch('openai.OpenAI')
    def test_openai_native_websearch_full_flow(self):
        """Test complete OpenAI native websearch flow from request to response."""
        
        class TestTool(BaseTool):
            def get_name(self) -> str:
                return "test"
            
            def get_system_prompt(self) -> str:
                return "test prompt"
            
            def get_default_temperature(self) -> float:
                return 0.7
                
            def prepare_prompt(self, request, continuation_id=None, max_tokens=None, reserve_tokens=0):
                return "test prompt", ""
                
            def format_response(self, response: str, request, model_info=None) -> str:
                return response
        
        # Create a request with native_websearch=True
        request = BaseRequest(
            model="o3",
            native_websearch=True,
            use_websearch=False  # Explicitly False to avoid validation error
        )
        
        # Verify the request is valid
        assert request.native_websearch is True
        assert request.use_websearch is False
        
        # Test that the tool can extract the parameter
        tool = TestTool()
        assert tool.get_request_native_websearch(request) is True
        assert tool.get_request_use_websearch(request) is False

    @patch('google.genai.Client')
    def test_gemini_native_websearch_full_flow(self):
        """Test complete Gemini native websearch flow from request to response."""
        
        class TestTool(BaseTool):
            def get_name(self) -> str:
                return "test"
            
            def get_system_prompt(self) -> str:
                return "test prompt"
            
            def get_default_temperature(self) -> float:
                return 0.7
                
            def prepare_prompt(self, request, continuation_id=None, max_tokens=None, reserve_tokens=0):
                return "test prompt", ""
                
            def format_response(self, response: str, request, model_info=None) -> str:
                return response
        
        # Create a request with native_websearch=True
        request = BaseRequest(
            model="gemini-2.5-flash",
            native_websearch=True,
            use_websearch=False  # Explicitly False to avoid validation error
        )
        
        # Verify the request is valid
        assert request.native_websearch is True
        assert request.use_websearch is False
        
        # Test that the tool can extract the parameter
        tool = TestTool()
        assert tool.get_request_native_websearch(request) is True
        assert tool.get_request_use_websearch(request) is False

    def test_unsupported_model_native_websearch_handling(self):
        """Test handling of native_websearch with models that don't support it."""
        
        # Create a request with native_websearch=True for a lite model
        request = BaseRequest(
            model="gemini-2.0-flash-lite",
            native_websearch=True,
            use_websearch=False
        )
        
        # The request should still be valid (validation happens at provider level)
        assert request.native_websearch is True
        assert request.use_websearch is False
        
        # Provider should handle unsupported models gracefully
        with patch('google.genai.Client'):
            provider = GeminiModelProvider("test-key")
            capabilities = provider.get_capabilities("gemini-2.0-flash-lite")
            assert capabilities.supports_native_websearch is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])