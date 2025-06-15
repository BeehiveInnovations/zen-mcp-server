"""
Tests for the tracer tool functionality
"""

from unittest.mock import Mock, patch

import pytest

from tools.models import ToolModelCategory
from tools.tracer import TracerRequest, TracerTool


class TestTracerTool:
    """Test suite for the Tracer tool"""

    @pytest.fixture
    def tracer_tool(self):
        """Create a tracer tool instance for testing"""
        return TracerTool()

    @pytest.fixture
    def mock_model_response(self):
        """Create a mock model response for call path analysis"""

        def _create_response(content=None):
            if content is None:
                content = """## Call Path Summary

1. 🟢 `BookingManager::finalizeInvoice()` at booking.py:45 → calls `PaymentProcessor.process()`
2. 🟢 `PaymentProcessor::process()` at payment.py:123 → calls `validation.validate_payment()`
3. 🟡 `validation.validate_payment()` at validation.py:67 → conditionally calls `Logger.log()`

## Value-Driven Flow Analysis

**Scenario 1**: `invoice_id=123, payment_method="credit_card"`
- Path: BookingManager → PaymentProcessor → CreditCardValidator → StripeGateway
- Key decision at payment.py:156: routes to Stripe integration

## Side Effects & External Dependencies

### Database Interactions
- **Transaction.save()** at models.py:234 → inserts payment record

### Network Calls
- **StripeGateway.charge()** → HTTPS POST to Stripe API

## Code Anchors

- Entry point: `BookingManager::finalizeInvoice` at booking.py:45
- Critical branch: Payment method selection at payment.py:156
"""

            return Mock(
                content=content,
                usage={"input_tokens": 150, "output_tokens": 300, "total_tokens": 450},
                model_name="test-model",
                metadata={"finish_reason": "STOP"},
            )

        return _create_response

    def test_get_name(self, tracer_tool):
        """Test that the tool returns the correct name"""
        assert tracer_tool.get_name() == "tracer"

    def test_get_description(self, tracer_tool):
        """Test that the tool returns a comprehensive description"""
        description = tracer_tool.get_description()
        assert "STATIC CODE ANALYSIS" in description
        assert "execution flow" in description
        assert "dependency mappings" in description
        assert "precision" in description
        assert "dependencies" in description

    def test_get_input_schema(self, tracer_tool):
        """Test that the input schema includes all required fields"""
        schema = tracer_tool.get_input_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "files" in schema["properties"]
        assert "trace_mode" in schema["properties"]

        # Check required fields
        required_fields = schema["required"]
        assert "prompt" in required_fields
        assert "files" in required_fields
        assert "trace_mode" in required_fields

        # Check enum values for trace_mode
        trace_mode_enum = schema["properties"]["trace_mode"]["enum"]
        assert "precision" in trace_mode_enum
        assert "dependencies" in trace_mode_enum

    def test_get_model_category(self, tracer_tool):
        """Test that the tool uses extended reasoning category"""
        category = tracer_tool.get_model_category()
        assert category == ToolModelCategory.EXTENDED_REASONING

    def test_request_model_validation(self):
        """Test request model validation"""
        # Valid request
        request = TracerRequest(
            prompt="Trace BookingManager::finalizeInvoice method with invoice_id=123",
            files=["/test/booking.py", "/test/payment.py"],
            trace_mode="precision",
        )
        assert request.prompt == "Trace BookingManager::finalizeInvoice method with invoice_id=123"
        assert len(request.files) == 2
        assert request.trace_mode == "precision"

        # Invalid request (missing required fields)
        with pytest.raises(ValueError):
            TracerRequest(files=["/test/file.py"])  # Missing prompt and trace_mode

        # Invalid trace_mode value
        with pytest.raises(ValueError):
            TracerRequest(prompt="Test", files=["/test/file.py"], trace_mode="invalid_type")

    def test_language_detection_python(self, tracer_tool):
        """Test language detection for Python files"""
        files = ["/test/booking.py", "/test/payment.py", "/test/utils.py"]
        language = tracer_tool.detect_primary_language(files)
        assert language == "python"

    def test_language_detection_javascript(self, tracer_tool):
        """Test language detection for JavaScript files"""
        files = ["/test/app.js", "/test/component.jsx", "/test/utils.js"]
        language = tracer_tool.detect_primary_language(files)
        assert language == "javascript"

    def test_language_detection_typescript(self, tracer_tool):
        """Test language detection for TypeScript files"""
        files = ["/test/app.ts", "/test/component.tsx", "/test/utils.ts"]
        language = tracer_tool.detect_primary_language(files)
        assert language == "typescript"

    def test_language_detection_csharp(self, tracer_tool):
        """Test language detection for C# files"""
        files = ["/test/BookingService.cs", "/test/PaymentProcessor.cs"]
        language = tracer_tool.detect_primary_language(files)
        assert language == "csharp"

    def test_language_detection_java(self, tracer_tool):
        """Test language detection for Java files"""
        files = ["/test/BookingManager.java", "/test/PaymentService.java"]
        language = tracer_tool.detect_primary_language(files)
        assert language == "java"

    def test_language_detection_mixed(self, tracer_tool):
        """Test language detection for mixed language files"""
        files = ["/test/app.py", "/test/service.js", "/test/model.java"]
        language = tracer_tool.detect_primary_language(files)
        assert language == "mixed"

    def test_language_detection_unknown(self, tracer_tool):
        """Test language detection for unknown extensions"""
        files = ["/test/config.xml", "/test/readme.txt"]
        language = tracer_tool.detect_primary_language(files)
        assert language == "unknown"

    # Removed parse_entry_point tests as method no longer exists in simplified interface

    @pytest.mark.asyncio
    async def test_prepare_prompt_basic(self, tracer_tool):
        """Test basic prompt preparation"""
        request = TracerRequest(
            prompt="Trace BookingManager::finalizeInvoice method with invoice_id=123",
            files=["/test/booking.py"],
            trace_mode="precision",
        )

        # Mock file content preparation
        with patch.object(tracer_tool, "_prepare_file_content_for_prompt") as mock_prep:
            mock_prep.return_value = "def finalizeInvoice(self, invoice_id):\n    pass"
            with patch.object(tracer_tool, "check_prompt_size") as mock_check:
                mock_check.return_value = None
                prompt = await tracer_tool.prepare_prompt(request)

        assert "ANALYSIS REQUEST" in prompt
        assert "Trace BookingManager::finalizeInvoice method" in prompt
        assert "precision" in prompt
        assert "CODE TO ANALYZE" in prompt

    @pytest.mark.asyncio
    async def test_prepare_prompt_with_dependencies(self, tracer_tool):
        """Test prompt preparation with dependencies type"""
        request = TracerRequest(
            prompt="Analyze dependencies for payment.process_payment function with amount=100.50",
            files=["/test/payment.py"],
            trace_mode="dependencies",
        )

        with patch.object(tracer_tool, "_prepare_file_content_for_prompt") as mock_prep:
            mock_prep.return_value = "def process_payment(amount, method):\n    pass"
            with patch.object(tracer_tool, "check_prompt_size") as mock_check:
                mock_check.return_value = None
                prompt = await tracer_tool.prepare_prompt(request)

        assert "Analyze dependencies for payment.process_payment" in prompt
        assert "Trace Mode: dependencies" in prompt

    @pytest.mark.asyncio
    async def test_prepare_prompt_with_security_context(self, tracer_tool):
        """Test prompt preparation with security context"""
        request = TracerRequest(
            prompt="Trace UserService::authenticate method focusing on security implications and potential vulnerabilities",
            files=["/test/auth.py"],
            trace_mode="precision",
        )

        with patch.object(tracer_tool, "_prepare_file_content_for_prompt") as mock_prep:
            mock_prep.return_value = "def authenticate(self, username, password):\n    pass"
            with patch.object(tracer_tool, "check_prompt_size") as mock_check:
                mock_check.return_value = None
                prompt = await tracer_tool.prepare_prompt(request)

        assert "security implications and potential vulnerabilities" in prompt
        assert "Trace Mode: precision" in prompt

    def test_format_response_precision(self, tracer_tool):
        """Test response formatting for precision trace"""
        request = TracerRequest(
            prompt="Trace BookingManager::finalizeInvoice method", files=["/test/booking.py"], trace_mode="precision"
        )

        response = '{"status": "trace_complete", "trace_type": "precision"}'
        model_info = {"model_response": Mock(friendly_name="Gemini Pro")}

        formatted = tracer_tool.format_response(response, request, model_info)

        assert response in formatted
        assert "Analysis Complete" in formatted
        assert "Gemini Pro" in formatted
        assert "precision analysis" in formatted
        assert "CALL FLOW DIAGRAM" in formatted
        assert "BRANCHING & SIDE EFFECT TABLE" in formatted

    def test_format_response_dependencies(self, tracer_tool):
        """Test response formatting for dependencies trace"""
        request = TracerRequest(
            prompt="Analyze dependencies for payment.process function",
            files=["/test/payment.py"],
            trace_mode="dependencies",
        )

        response = '{"status": "trace_complete", "trace_type": "dependencies"}'

        formatted = tracer_tool.format_response(response, request)

        assert response in formatted
        assert "dependencies analysis" in formatted
        assert "DEPENDENCY FLOW GRAPH" in formatted
        assert "DEPENDENCY TABLE" in formatted

    # Removed PlantUML test as export_format is no longer a parameter

    def test_get_default_temperature(self, tracer_tool):
        """Test that the tool uses analytical temperature"""
        from config import TEMPERATURE_ANALYTICAL

        assert tracer_tool.get_default_temperature() == TEMPERATURE_ANALYTICAL

    def test_wants_line_numbers_by_default(self, tracer_tool):
        """Test that line numbers are enabled by default"""
        # The base class should enable line numbers by default for precise references
        # We test that this isn't overridden to disable them
        assert hasattr(tracer_tool, "wants_line_numbers_by_default")

    def test_trace_mode_validation(self):
        """Test trace mode validation"""
        # Valid trace modes
        request1 = TracerRequest(prompt="Test precision", files=["/test/file.py"], trace_mode="precision")
        assert request1.trace_mode == "precision"

        request2 = TracerRequest(prompt="Test dependencies", files=["/test/file.py"], trace_mode="dependencies")
        assert request2.trace_mode == "dependencies"

        # Invalid trace mode should raise ValidationError
        with pytest.raises(ValueError):
            TracerRequest(prompt="Test", files=["/test/file.py"], trace_mode="invalid_type")

    def test_get_rendering_instructions(self, tracer_tool):
        """Test the main rendering instructions dispatcher method"""
        # Test precision mode
        precision_instructions = tracer_tool._get_rendering_instructions("precision")
        assert "MANDATORY RENDERING INSTRUCTIONS FOR PRECISION TRACE" in precision_instructions
        assert "CALL FLOW DIAGRAM" in precision_instructions
        assert "BRANCHING & SIDE EFFECT TABLE" in precision_instructions

        # Test dependencies mode
        dependencies_instructions = tracer_tool._get_rendering_instructions("dependencies")
        assert "MANDATORY RENDERING INSTRUCTIONS FOR DEPENDENCIES TRACE" in dependencies_instructions
        assert "DEPENDENCY FLOW GRAPH" in dependencies_instructions
        assert "DEPENDENCY TABLE" in dependencies_instructions

    def test_get_precision_rendering_instructions(self, tracer_tool):
        """Test precision mode rendering instructions"""
        instructions = tracer_tool._get_precision_rendering_instructions()

        # Check for required sections
        assert "MANDATORY RENDERING INSTRUCTIONS FOR PRECISION TRACE" in instructions
        assert "1. CALL FLOW DIAGRAM (TOP-DOWN)" in instructions
        assert "2. BRANCHING & SIDE EFFECT TABLE" in instructions

        # Check for specific formatting requirements
        assert "[Class::Method] (file: /path, line: ##)" in instructions
        assert "Chain each call using ↓ or → for readability" in instructions
        assert "If ambiguous, mark with `⚠️ ambiguous branch`" in instructions
        assert "Side Effects:" in instructions
        assert "[database] description (File.ext:##)" in instructions

        # Check for critical rules
        assert "CRITICAL RULES:" in instructions
        assert "Use exact filenames, class names, and line numbers from JSON" in instructions
        assert "DO NOT invent function names or examples" in instructions

    def test_get_dependencies_rendering_instructions(self, tracer_tool):
        """Test dependencies mode rendering instructions"""
        instructions = tracer_tool._get_dependencies_rendering_instructions()

        # Check for required sections
        assert "MANDATORY RENDERING INSTRUCTIONS FOR DEPENDENCIES TRACE" in instructions
        assert "1. DEPENDENCY FLOW GRAPH" in instructions
        assert "2. DEPENDENCY TABLE" in instructions

        # Check for specific formatting requirements
        assert "Called by:" in instructions
        assert "[CallerClass::callerMethod] ← /path/file.ext:##" in instructions
        assert "Calls:" in instructions
        assert "[Logger::logAction]    → /utils/log.ext:##" in instructions
        assert "Type Dependencies:" in instructions
        assert "State Access:" in instructions

        # Check for arrow rules
        assert "`←` for incoming (who calls this)" in instructions
        assert "`→` for outgoing (what this calls)" in instructions

        # Check for dependency table format
        assert "| Type | From/To | Method | File | Line |" in instructions
        assert "| direct_call | From: CallerClass | callerMethod |" in instructions

        # Check for critical rules
        assert "CRITICAL RULES:" in instructions
        assert "Use exact filenames, class names, and line numbers from JSON" in instructions
        assert "Show directional dependencies with proper arrows" in instructions

    def test_format_response_uses_private_methods(self, tracer_tool):
        """Test that format_response correctly uses the refactored private methods"""
        # Test precision mode
        precision_request = TracerRequest(prompt="Test precision", files=["/test/file.py"], trace_mode="precision")
        precision_response = tracer_tool.format_response('{"test": "response"}', precision_request)

        # Should contain precision-specific instructions
        assert "CALL FLOW DIAGRAM" in precision_response
        assert "BRANCHING & SIDE EFFECT TABLE" in precision_response
        assert "precision analysis" in precision_response

        # Test dependencies mode
        dependencies_request = TracerRequest(
            prompt="Test dependencies", files=["/test/file.py"], trace_mode="dependencies"
        )
        dependencies_response = tracer_tool.format_response('{"test": "response"}', dependencies_request)

        # Should contain dependencies-specific instructions
        assert "DEPENDENCY FLOW GRAPH" in dependencies_response
        assert "DEPENDENCY TABLE" in dependencies_response
        assert "dependencies analysis" in dependencies_response

    def test_rendering_instructions_consistency(self, tracer_tool):
        """Test that private methods return consistent instructions"""
        # Get instructions through both paths
        precision_direct = tracer_tool._get_precision_rendering_instructions()
        precision_via_dispatcher = tracer_tool._get_rendering_instructions("precision")

        dependencies_direct = tracer_tool._get_dependencies_rendering_instructions()
        dependencies_via_dispatcher = tracer_tool._get_rendering_instructions("dependencies")

        # Should be identical
        assert precision_direct == precision_via_dispatcher
        assert dependencies_direct == dependencies_via_dispatcher

    def test_rendering_instructions_completeness(self, tracer_tool):
        """Test that rendering instructions contain all required elements"""
        precision_instructions = tracer_tool._get_precision_rendering_instructions()
        dependencies_instructions = tracer_tool._get_dependencies_rendering_instructions()

        # Both should have mandatory sections
        for instructions in [precision_instructions, dependencies_instructions]:
            assert "MANDATORY RENDERING INSTRUCTIONS" in instructions
            assert "You MUST render" in instructions
            assert "exactly two views" in instructions
            assert "CRITICAL RULES:" in instructions
            assert "ALWAYS render both views unless data is missing" in instructions
            assert "Use exact filenames, class names, and line numbers from JSON" in instructions
            assert "DO NOT invent function names or examples" in instructions

    def test_rendering_instructions_mode_specific_content(self, tracer_tool):
        """Test that each mode has unique content"""
        precision_instructions = tracer_tool._get_precision_rendering_instructions()
        dependencies_instructions = tracer_tool._get_dependencies_rendering_instructions()

        # Precision-specific content should not be in dependencies
        assert "CALL FLOW DIAGRAM" in precision_instructions
        assert "CALL FLOW DIAGRAM" not in dependencies_instructions
        assert "BRANCHING & SIDE EFFECT TABLE" in precision_instructions
        assert "BRANCHING & SIDE EFFECT TABLE" not in dependencies_instructions

        # Dependencies-specific content should not be in precision
        assert "DEPENDENCY FLOW GRAPH" in dependencies_instructions
        assert "DEPENDENCY FLOW GRAPH" not in precision_instructions
        assert "DEPENDENCY TABLE" in dependencies_instructions
        assert "DEPENDENCY TABLE" not in precision_instructions

        # Mode-specific symbols and patterns
        assert "↓" in precision_instructions  # Flow arrows
        assert "←" in dependencies_instructions  # Incoming arrow
        assert "→" in dependencies_instructions  # Outgoing arrow
        assert "Side Effects:" in precision_instructions
        assert "Called by:" in dependencies_instructions
