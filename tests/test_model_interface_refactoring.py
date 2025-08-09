from tools.consensus import ConsensusTool


class TestModelInterfaceRefactoring:
    """Test suite for model interface refactoring that supports both old and new signatures."""

    def test_new_interface_single_model_tools(self):
        """Test that single-model tools return list with one model."""
        # This will initially fail until we implement get_request_model_names()
        from tools.chat import ChatTool

        tool = ChatTool()

        # New interface
        model_names = tool.get_request_model_names()
        assert isinstance(model_names, list)
        assert len(model_names) <= 1  # Single model or empty

    def test_new_interface_multi_model_tools(self):
        """Test that multi-model tools return list with multiple models."""
        # This will initially fail until we implement get_request_model_names()
        tool = ConsensusTool()
        tool.models = [type("Model", (), {"name": "gemini-2.5-pro"}), type("Model", (), {"name": "claude-sonnet-4"})]

        # New interface
        model_names = tool.get_request_model_names()
        assert isinstance(model_names, list)
        assert len(model_names) == 2
        assert "gemini-2.5-pro" in model_names
        assert "claude-sonnet-4" in model_names

    def test_backward_compatibility_bridge(self):
        """Test that old interface still works via compatibility bridge."""
        from tools.chat import ChatTool

        tool = ChatTool()

        # Old interface should work via bridge
        request = type("Request", (), {"model": "test-model"})
        model_name = tool.get_request_model_name(request)
        assert isinstance(model_name, str)

    def test_consensus_compatibility_bridge(self):
        """Test that consensus tool compatibility bridge returns meaningful name."""
        tool = ConsensusTool()
        tool.models = [type("Model", (), {"name": "gemini-2.5-pro"}), type("Model", (), {"name": "claude-sonnet-4"})]

        # Old interface via bridge should return multi-model indicator
        request = type("Request", (), {})
        model_name = tool.get_request_model_name(request)
        assert "multi-model" in model_name
        assert "consensus" in model_name
