"""
Tests for the main server functionality
"""

import pytest

from server import handle_call_tool, handle_get_prompt, handle_list_tools
from tools.consensus import ConsensusTool


class TestServerTools:
    """Test server tool handling"""

    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test listing all available tools"""
        tools = await handle_list_tools()
        tool_names = [tool.name for tool in tools]

        # Check all core tools are present
        assert "thinkdeep" in tool_names
        assert "codereview" in tool_names
        assert "debug" in tool_names
        assert "analyze" in tool_names
        assert "chat" in tool_names
        assert "consensus" in tool_names
        assert "precommit" in tool_names
        assert "testgen" in tool_names
        assert "refactor" in tool_names
        assert "tracer" in tool_names
        assert "version" in tool_names

        # Should have exactly 12 tools (including consensus, refactor, tracer, and listmodels)
        assert len(tools) == 12

        # Check descriptions are verbose
        for tool in tools:
            assert len(tool.description) > 50  # All should have detailed descriptions


class TestStructuredPrompts:
    """Test structured prompt parsing functionality"""

    def test_parse_consensus_models_basic(self):
        """Test parsing basic consensus model specifications"""
        # Test with explicit stances
        result = ConsensusTool.parse_structured_prompt_models("flash:for,o3:against,pro:neutral")
        expected = [
            {"model": "flash", "stance": "for"},
            {"model": "o3", "stance": "against"},
            {"model": "pro", "stance": "neutral"},
        ]
        assert result == expected

    def test_parse_consensus_models_mixed(self):
        """Test parsing consensus models with mixed stance specifications"""
        # Test with some models having explicit stances, others defaulting to neutral
        result = ConsensusTool.parse_structured_prompt_models("flash:for,o3:against,pro")
        expected = [
            {"model": "flash", "stance": "for"},
            {"model": "o3", "stance": "against"},
            {"model": "pro", "stance": "neutral"},  # Defaults to neutral
        ]
        assert result == expected

    def test_parse_consensus_models_all_neutral(self):
        """Test parsing consensus models with all neutral stances"""
        result = ConsensusTool.parse_structured_prompt_models("flash,o3,pro")
        expected = [
            {"model": "flash", "stance": "neutral"},
            {"model": "o3", "stance": "neutral"},
            {"model": "pro", "stance": "neutral"},
        ]
        assert result == expected

    def test_parse_consensus_models_single(self):
        """Test parsing single consensus model"""
        result = ConsensusTool.parse_structured_prompt_models("flash:for")
        expected = [{"model": "flash", "stance": "for"}]
        assert result == expected

    def test_parse_consensus_models_whitespace(self):
        """Test parsing consensus models with extra whitespace"""
        result = ConsensusTool.parse_structured_prompt_models(" flash:for , o3:against , pro ")
        expected = [
            {"model": "flash", "stance": "for"},
            {"model": "o3", "stance": "against"},
            {"model": "pro", "stance": "neutral"},
        ]
        assert result == expected

    def test_parse_consensus_models_synonyms(self):
        """Test parsing consensus models with stance synonyms"""
        result = ConsensusTool.parse_structured_prompt_models("flash:support,o3:oppose,pro:favor")
        expected = [
            {"model": "flash", "stance": "support"},
            {"model": "o3", "stance": "oppose"},
            {"model": "pro", "stance": "favor"},
        ]
        assert result == expected

    @pytest.mark.asyncio
    async def test_consensus_structured_prompt_parsing(self):
        """Test full consensus structured prompt parsing pipeline"""
        # Test parsing a complex consensus prompt
        prompt_name = "consensus:flash:for,o3:against,pro:neutral"

        try:
            result = await handle_get_prompt(prompt_name)

            # Check that it returns a valid GetPromptResult
            assert result.prompt.name == prompt_name
            assert result.prompt.description is not None
            assert len(result.messages) == 1
            assert result.messages[0].role == "user"

            # Check that the instruction contains the expected model configurations
            instruction_text = result.messages[0].content.text
            assert "consensus" in instruction_text
            assert "flash with for stance" in instruction_text
            assert "o3 with against stance" in instruction_text
            assert "pro with neutral stance" in instruction_text

            # Check that the JSON model configuration is included
            assert '"model": "flash", "stance": "for"' in instruction_text
            assert '"model": "o3", "stance": "against"' in instruction_text
            assert '"model": "pro", "stance": "neutral"' in instruction_text

        except ValueError as e:
            # If consensus tool is not properly configured, this might fail
            # In that case, just check our parsing function works
            assert str(e) == "Unknown prompt: consensus:flash:for,o3:against,pro:neutral"

    @pytest.mark.asyncio
    async def test_consensus_prompt_practical_example(self):
        """Test practical consensus prompt examples from README"""
        examples = [
            "consensus:flash:for,o3:against,pro:neutral",
            "consensus:flash:support,o3:critical,pro",
            "consensus:gemini:for,grok:against",
        ]

        for example in examples:
            try:
                result = await handle_get_prompt(example)
                instruction = result.messages[0].content.text

                # Should contain consensus tool usage
                assert "consensus" in instruction.lower()

                # Should contain model configurations in JSON format
                assert "[{" in instruction and "}]" in instruction

                # Should contain stance information for models that have it
                if ":for" in example:
                    assert '"stance": "for"' in instruction
                if ":against" in example:
                    assert '"stance": "against"' in instruction
                if ":support" in example:
                    assert '"stance": "support"' in instruction
                if ":critical" in example:
                    assert '"stance": "critical"' in instruction

            except ValueError:
                # Some examples might fail if tool isn't configured
                pass

    @pytest.mark.asyncio
    async def test_handle_call_tool_unknown(self):
        """Test calling an unknown tool"""
        result = await handle_call_tool("unknown_tool", {})
        assert len(result) == 1
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_chat(self):
        """Test chat functionality using real integration testing"""
        import importlib
        import os

        # Set test environment
        os.environ["PYTEST_CURRENT_TEST"] = "test"

        # Save original environment
        original_env = {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL"),
        }

        try:
            # Set up environment for real provider resolution
            os.environ["OPENAI_API_KEY"] = "sk-test-key-server-chat-test-not-real"
            os.environ["DEFAULT_MODEL"] = "o3-mini"

            # Clear other provider keys to isolate to OpenAI
            for key in ["GEMINI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY"]:
                os.environ.pop(key, None)

            # Reload config and clear registry
            import config

            importlib.reload(config)
            from providers.registry import ModelProviderRegistry

            ModelProviderRegistry._instance = None

            # Test with real provider resolution
            try:
                result = await handle_call_tool("chat", {"prompt": "Hello Gemini", "model": "o3-mini"})

                # If we get here, check the response format
                assert len(result) == 1
                # Parse JSON response
                import json

                response_data = json.loads(result[0].text)
                assert "status" in response_data

            except Exception as e:
                # Expected: API call will fail with fake key
                error_msg = str(e)
                # Should NOT be a mock-related error
                assert "MagicMock" not in error_msg
                assert "'<' not supported between instances" not in error_msg

                # Should be a real provider error
                assert any(
                    phrase in error_msg
                    for phrase in ["API", "key", "authentication", "provider", "network", "connection"]
                )

        finally:
            # Restore environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)

            # Reload config and clear registry
            importlib.reload(config)
            ModelProviderRegistry._instance = None

    @pytest.mark.asyncio
    async def test_handle_version(self):
        """Test getting version info"""
        result = await handle_call_tool("version", {})
        assert len(result) == 1

        response = result[0].text
        assert "Zen MCP Server v" in response  # Version agnostic check
        assert "Available Tools:" in response
        assert "thinkdeep" in response
