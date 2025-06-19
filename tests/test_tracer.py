"""
Tests for the tracer tool functionality
"""

import pytest

from tools.models import ToolModelCategory
from tools.tracer import TracerRequest, TracerTool


class TestTracerTool:
    """Test suite for the Tracer tool"""

    @pytest.fixture
    def tracer_tool(self):
        """Create a tracer tool instance for testing"""
        return TracerTool()

    def test_get_name(self, tracer_tool):
        """Test that the tool returns the correct name"""
        assert tracer_tool.get_name() == "tracer"

    def test_get_description(self, tracer_tool):
        """Test that the tool returns a comprehensive description"""
        description = tracer_tool.get_description()
        assert "ANALYSIS PROMPT GENERATOR" in description
        assert "precision" in description
        assert "dependencies" in description
        assert "static code analysis" in description

    def test_get_input_schema(self, tracer_tool):
        """Test that the input schema includes required fields"""
        schema = tracer_tool.get_input_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "trace_mode" in schema["properties"]

        # Check trace_mode enum values
        trace_enum = schema["properties"]["trace_mode"]["enum"]
        assert "precision" in trace_enum
        assert "dependencies" in trace_enum

        # Check required fields
        assert set(schema["required"]) == {"prompt", "trace_mode"}

    def test_get_model_category(self, tracer_tool):
        """Test that the tracer tool uses FAST_RESPONSE category"""
        category = tracer_tool.get_model_category()
        assert category == ToolModelCategory.FAST_RESPONSE

    def test_request_model_validation(self, tracer_tool):
        """Test TracerRequest model validation"""
        # Valid request
        request = TracerRequest(
            prompt="BookingManager finalizeInvoice method",
            trace_mode="precision",
        )
        assert request.prompt == "BookingManager finalizeInvoice method"
        assert request.trace_mode == "precision"

        # Test invalid trace_mode
        with pytest.raises(ValueError):
            TracerRequest(
                prompt="Test",
                trace_mode="invalid_mode",
            )

    @pytest.mark.asyncio
    async def test_execute_precision_mode(self, tracer_tool):
        """Test executing tracer with precision mode"""
        request_args = {
            "prompt": "BookingManager finalizeInvoice method",
            "trace_mode": "precision",
        }

        result = await tracer_tool.execute(request_args)

        assert len(result) == 1
        output = result[0]
        assert output.type == "text"

        # Check content includes expected sections
        content = output.text
        assert "STATIC CODE ANALYSIS REQUEST" in content
        assert "Analysis Instructions" in content
        assert "BookingManager finalizeInvoice method" in content
        assert "precision" in content
        assert "CALL FLOW DIAGRAM" in content

    @pytest.mark.asyncio
    async def test_execute_dependencies_mode(self, tracer_tool):
        """Test executing tracer with dependencies mode"""
        request_args = {
            "prompt": "payment processing flow",
            "trace_mode": "dependencies",
        }

        result = await tracer_tool.execute(request_args)

        assert len(result) == 1
        output = result[0]
        assert output.type == "text"

        # Check content includes expected sections
        content = output.text
        assert "STATIC CODE ANALYSIS REQUEST" in content
        assert "payment processing flow" in content
        assert "dependencies" in content
        assert "DEPENDENCY FLOW DIAGRAM" in content

    def test_create_enhanced_prompt_precision(self, tracer_tool):
        """Test enhanced prompt creation for precision mode"""
        prompt = tracer_tool._create_enhanced_prompt("BookingManager::finalizeInvoice", "precision")

        assert "TARGET:" in prompt
        assert "BookingManager::finalizeInvoice" in prompt
        assert "precision" in prompt
        assert "execution path" in prompt
        assert "method calls" in prompt
        assert "line numbers" in prompt

    def test_create_enhanced_prompt_dependencies(self, tracer_tool):
        """Test enhanced prompt creation for dependencies mode"""
        prompt = tracer_tool._create_enhanced_prompt("validation function", "dependencies")

        assert "TARGET:" in prompt
        assert "validation function" in prompt
        assert "dependencies" in prompt
        assert "bidirectional dependencies" in prompt
        assert "incoming" in prompt
        assert "outgoing" in prompt

    def test_get_rendering_instructions_precision(self, tracer_tool):
        """Test rendering instructions for precision mode"""
        instructions = tracer_tool._get_rendering_instructions("precision")

        assert "PRECISION TRACE" in instructions
        assert "CALL FLOW DIAGRAM" in instructions
        assert "ADDITIONAL ANALYSIS VIEWS" in instructions
        assert "ClassName::MethodName" in instructions
        assert "↓" in instructions

    def test_get_rendering_instructions_dependencies(self, tracer_tool):
        """Test rendering instructions for dependencies mode"""
        instructions = tracer_tool._get_rendering_instructions("dependencies")

        assert "DEPENDENCIES TRACE" in instructions
        assert "DEPENDENCY FLOW DIAGRAM" in instructions
        assert "DEPENDENCY TABLE" in instructions
        assert "INCOMING DEPENDENCIES" in instructions
        assert "OUTGOING DEPENDENCIES" in instructions
        assert "←" in instructions
        assert "→" in instructions

    def test_get_precision_rendering_instructions(self, tracer_tool):
        """Test precision rendering instructions content"""
        instructions = tracer_tool._get_precision_rendering_instructions()

        assert "MANDATORY RENDERING INSTRUCTIONS" in instructions
        assert "ADDITIONAL ANALYSIS VIEWS" in instructions
        assert "CALL FLOW DIAGRAM" in instructions
        assert "line number" in instructions
        assert "ambiguous branch" in instructions
        assert "SIDE EFFECTS" in instructions

    def test_get_dependencies_rendering_instructions(self, tracer_tool):
        """Test dependencies rendering instructions content"""
        instructions = tracer_tool._get_dependencies_rendering_instructions()

        assert "MANDATORY RENDERING INSTRUCTIONS" in instructions
        assert "Bidirectional Arrow Flow Style" in instructions
        assert "CallerClass::callerMethod" in instructions
        assert "FirstDependency::method" in instructions
        assert "TYPE RELATIONSHIPS" in instructions
        assert "DEPENDENCY TABLE" in instructions

    def test_rendering_instructions_consistency(self, tracer_tool):
        """Test that rendering instructions are consistent between modes"""
        precision_instructions = tracer_tool._get_precision_rendering_instructions()
        dependencies_instructions = tracer_tool._get_dependencies_rendering_instructions()

        # Both should have mandatory instructions
        assert "MANDATORY RENDERING INSTRUCTIONS" in precision_instructions
        assert "MANDATORY RENDERING INSTRUCTIONS" in dependencies_instructions

        # Both should have specific styling requirements
        assert "ONLY" in precision_instructions
        assert "ONLY" in dependencies_instructions

        # Both should have absolute requirements
        assert "ABSOLUTE REQUIREMENTS" in precision_instructions
        assert "ABSOLUTE REQUIREMENTS" in dependencies_instructions

    def test_rendering_instructions_completeness(self, tracer_tool):
        """Test that rendering instructions include all necessary elements"""
        precision = tracer_tool._get_precision_rendering_instructions()
        dependencies = tracer_tool._get_dependencies_rendering_instructions()

        # Precision mode should include call flow and additional analysis views
        assert "CALL FLOW DIAGRAM" in precision
        assert "ADDITIONAL ANALYSIS VIEWS" in precision

        # Dependencies mode should include flow diagram and table
        assert "DEPENDENCY FLOW DIAGRAM" in dependencies
        assert "DEPENDENCY TABLE" in dependencies

    def test_rendering_instructions_mode_specific_content(self, tracer_tool):
        """Test that each mode has its specific content requirements"""
        precision = tracer_tool._get_precision_rendering_instructions()
        dependencies = tracer_tool._get_dependencies_rendering_instructions()

        # Precision-specific content
        assert "USAGE POINTS" in precision
        assert "ENTRY POINTS" in precision

        # Dependencies-specific content
        assert "INCOMING DEPENDENCIES" in dependencies
        assert "OUTGOING DEPENDENCIES" in dependencies
        assert "Bidirectional Arrow" in dependencies

    @pytest.mark.asyncio
    async def test_execute_returns_textcontent_format(self, tracer_tool):
        """Test that execute returns proper TextContent format for MCP protocol"""
        from mcp.types import TextContent

        request_args = {
            "prompt": "test method analysis",
            "trace_mode": "precision",
        }

        result = await tracer_tool.execute(request_args)

        # Verify structure
        assert isinstance(result, list)
        assert len(result) == 1

        # Verify TextContent format
        output = result[0]
        assert isinstance(output, TextContent)
        assert hasattr(output, "type")
        assert hasattr(output, "text")
        assert output.type == "text"
        assert isinstance(output.text, str)
        assert len(output.text) > 0

    @pytest.mark.asyncio
    async def test_mcp_protocol_compatibility(self, tracer_tool):
        """Test that the tool output is compatible with MCP protocol expectations"""
        request_args = {
            "prompt": "analyze method dependencies",
            "trace_mode": "dependencies",
        }

        result = await tracer_tool.execute(request_args)

        # Should return list of TextContent objects
        assert isinstance(result, list)

        for item in result:
            # Each item should be TextContent with required fields
            assert hasattr(item, "type")
            assert hasattr(item, "text")

            # Verify it can be serialized (MCP requirement)
            serialized = item.model_dump()
            assert "type" in serialized
            assert "text" in serialized
            assert serialized["type"] == "text"

    def test_mode_selection_guidance(self, tracer_tool):
        """Test that the schema provides clear guidance on when to use each mode"""
        schema = tracer_tool.get_input_schema()
        trace_mode_desc = schema["properties"]["trace_mode"]["description"]

        # Should clearly indicate precision is for methods/functions
        assert "methods/functions" in trace_mode_desc
        assert "execution flow" in trace_mode_desc
        assert "usage patterns" in trace_mode_desc

        # Should clearly indicate dependencies is for classes/modules/protocols
        assert "classes/modules/protocols" in trace_mode_desc
        assert "structural relationships" in trace_mode_desc

        # Should provide clear examples in prompt description
        prompt_desc = schema["properties"]["prompt"]["description"]
        assert "method" in prompt_desc and "precision mode" in prompt_desc
        assert "class" in prompt_desc and "dependencies mode" in prompt_desc
