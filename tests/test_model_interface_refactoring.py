from tools.consensus import ConsensusTool


class TestModelInterfaceRefactoring:
    """Test suite for the new model interface using get_request_model_names()."""

    def test_new_interface_single_model_tools(self):
        """Test that single-model tools return list with one model."""
        from tools.chat import ChatTool

        tool = ChatTool()

        # New interface
        model_names = tool.get_request_model_names()
        assert isinstance(model_names, list)
        assert len(model_names) <= 1  # Single model or empty

    def test_new_interface_multi_model_tools(self):
        """Test that multi-model tools return list with multiple models."""
        tool = ConsensusTool()
        tool.models = [type("Model", (), {"name": "gemini-2.5-pro"}), type("Model", (), {"name": "claude-sonnet-4"})]

        # New interface
        model_names = tool.get_request_model_names()
        assert isinstance(model_names, list)
        assert len(model_names) == 2
        assert "gemini-2.5-pro" in model_names
        assert "claude-sonnet-4" in model_names

    def test_utility_tools_return_empty_list(self):
        """Test that utility tools that don't use models return empty list."""
        from tools.listmodels import ListModelsTool
        from tools.version import VersionTool

        listmodels_tool = ListModelsTool()
        version_tool = VersionTool()

        assert listmodels_tool.get_request_model_names() == []
        assert version_tool.get_request_model_names() == []

    def test_dynamic_tools_return_empty_list(self):
        """Test that tools with dynamic model selection return empty list."""
        from tools.simple.base import SimpleTool
        from tools.workflow.base import WorkflowTool

        # Create minimal concrete implementations for testing
        class TestSimpleTool(SimpleTool):
            def get_name(self):
                return "test"

            def get_description(self):
                return "test"

            def get_input_schema(self):
                return {}

            def get_system_prompt(self):
                return "test"

            def get_tool_fields(self):
                return {}

            async def prepare_prompt(self, request):
                return "test"

        class TestWorkflowTool(WorkflowTool):
            def get_name(self):
                return "test"

            def get_description(self):
                return "test"

            def get_input_schema(self):
                return {}

            def get_system_prompt(self):
                return "test"

            def get_work_steps(self, request):
                return ["step1"]

            def get_request_model(self):
                from tools.shared.base_models import WorkflowRequest

                return WorkflowRequest

            def get_required_actions(self):
                return []

            def should_call_expert_analysis(self, request):
                return False

            async def prepare_expert_analysis_context(self, arguments, request):
                return ""

            async def prepare_prompt(self, request):
                return "test"

            async def execute_workflow_step(self, request, step_name, step_number, total_steps, accumulated_results):
                return {"content": "test"}

        simple_tool = TestSimpleTool()
        workflow_tool = TestWorkflowTool()

        # Dynamic tools return empty list - they get model from request at runtime
        assert simple_tool.get_request_model_names() == []
        assert workflow_tool.get_request_model_names() == []
