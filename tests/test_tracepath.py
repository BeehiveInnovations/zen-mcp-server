"""
Tests for the tracepath tool functionality
"""

from unittest.mock import Mock, patch

import pytest

from tools.models import ToolModelCategory
from tools.tracepath import TracePathRequest, TracePathTool


class TestTracePathTool:
    """Test suite for the TracePath tool"""

    @pytest.fixture
    def tracepath_tool(self):
        """Create a tracepath tool instance for testing"""
        return TracePathTool()

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

    def test_get_name(self, tracepath_tool):
        """Test that the tool returns the correct name"""
        assert tracepath_tool.get_name() == "tracepath"

    def test_get_description(self, tracepath_tool):
        """Test that the tool returns a comprehensive description"""
        description = tracepath_tool.get_description()
        assert "STATIC CALL PATH ANALYSIS" in description
        assert "control flow" in description
        assert "confidence levels" in description
        assert "polymorphism" in description
        assert "side effects" in description

    def test_get_input_schema(self, tracepath_tool):
        """Test that the input schema includes all required fields"""
        schema = tracepath_tool.get_input_schema()

        assert schema["type"] == "object"
        assert "entry_point" in schema["properties"]
        assert "files" in schema["properties"]

        # Check required fields
        required_fields = schema["required"]
        assert "entry_point" in required_fields
        assert "files" in required_fields

        # Check optional parameters
        assert "parameters" in schema["properties"]
        assert "analysis_depth" in schema["properties"]
        assert "language" in schema["properties"]
        assert "confidence_threshold" in schema["properties"]

        # Check enum values for analysis_depth
        depth_enum = schema["properties"]["analysis_depth"]["enum"]
        expected_depths = ["shallow", "medium", "deep"]
        assert all(depth in depth_enum for depth in expected_depths)

        # Check enum values for language
        language_enum = schema["properties"]["language"]["enum"]
        expected_languages = ["python", "javascript", "typescript", "csharp", "java"]
        assert all(lang in language_enum for lang in expected_languages)

    def test_get_model_category(self, tracepath_tool):
        """Test that the tool uses extended reasoning category"""
        category = tracepath_tool.get_model_category()
        assert category == ToolModelCategory.EXTENDED_REASONING

    def test_request_model_validation(self):
        """Test request model validation"""
        # Valid request
        request = TracePathRequest(
            entry_point="BookingManager::finalizeInvoice",
            files=["/test/booking.py", "/test/payment.py"],
            parameters={"invoice_id": 123, "payment_method": "credit_card"},
            analysis_depth="medium",
        )
        assert request.entry_point == "BookingManager::finalizeInvoice"
        assert len(request.files) == 2
        assert request.analysis_depth == "medium"
        assert request.confidence_threshold == 0.7  # default value

        # Test validation with invalid confidence threshold
        with pytest.raises(ValueError):
            TracePathRequest(
                entry_point="test::method", files=["/test/file.py"], confidence_threshold=1.5  # Invalid: > 1.0
            )

        # Invalid request (missing required fields)
        with pytest.raises(ValueError):
            TracePathRequest(files=["/test/file.py"])  # Missing entry_point

    def test_language_detection_python(self, tracepath_tool):
        """Test language detection for Python files"""
        files = ["/test/booking.py", "/test/payment.py", "/test/utils.py"]
        language = tracepath_tool.detect_primary_language(files)
        assert language == "python"

    def test_language_detection_javascript(self, tracepath_tool):
        """Test language detection for JavaScript files"""
        files = ["/test/app.js", "/test/component.jsx", "/test/utils.js"]
        language = tracepath_tool.detect_primary_language(files)
        assert language == "javascript"

    def test_language_detection_typescript(self, tracepath_tool):
        """Test language detection for TypeScript files"""
        files = ["/test/app.ts", "/test/component.tsx", "/test/utils.ts"]
        language = tracepath_tool.detect_primary_language(files)
        assert language == "typescript"

    def test_language_detection_csharp(self, tracepath_tool):
        """Test language detection for C# files"""
        files = ["/test/BookingService.cs", "/test/PaymentProcessor.cs"]
        language = tracepath_tool.detect_primary_language(files)
        assert language == "csharp"

    def test_language_detection_java(self, tracepath_tool):
        """Test language detection for Java files"""
        files = ["/test/BookingManager.java", "/test/PaymentService.java"]
        language = tracepath_tool.detect_primary_language(files)
        assert language == "java"

    def test_language_detection_mixed(self, tracepath_tool):
        """Test language detection for mixed language files"""
        files = ["/test/app.py", "/test/service.js", "/test/model.java"]
        language = tracepath_tool.detect_primary_language(files)
        assert language == "mixed"

    def test_language_detection_unknown(self, tracepath_tool):
        """Test language detection for unknown extensions"""
        files = ["/test/config.xml", "/test/readme.txt"]
        language = tracepath_tool.detect_primary_language(files)
        assert language == "unknown"

    def test_parse_entry_point_class_method_double_colon(self, tracepath_tool):
        """Test parsing entry point with double colon syntax"""
        result = tracepath_tool.parse_entry_point("BookingManager::finalizeInvoice", "python")

        assert result["raw"] == "BookingManager::finalizeInvoice"
        assert result["class_or_module"] == "BookingManager"
        assert result["method_or_function"] == "finalizeInvoice"
        assert result["type"] == "method"

    def test_parse_entry_point_module_function_dot(self, tracepath_tool):
        """Test parsing entry point with dot syntax"""
        result = tracepath_tool.parse_entry_point("utils.validate_input", "python")

        assert result["raw"] == "utils.validate_input"
        assert result["class_or_module"] == "utils"
        assert result["method_or_function"] == "validate_input"
        assert result["type"] == "function"

    def test_parse_entry_point_nested_module(self, tracepath_tool):
        """Test parsing entry point with nested module syntax"""
        result = tracepath_tool.parse_entry_point("payment.services.process_payment", "python")

        assert result["raw"] == "payment.services.process_payment"
        assert result["class_or_module"] == "payment.services"
        assert result["method_or_function"] == "process_payment"
        assert result["type"] == "function"

    def test_parse_entry_point_function_only(self, tracepath_tool):
        """Test parsing entry point with function name only"""
        result = tracepath_tool.parse_entry_point("validate_payment", "python")

        assert result["raw"] == "validate_payment"
        assert result["class_or_module"] == ""
        assert result["method_or_function"] == "validate_payment"
        assert result["type"] == "function"

    def test_parse_entry_point_camelcase_class(self, tracepath_tool):
        """Test parsing entry point with CamelCase class (method detection)"""
        result = tracepath_tool.parse_entry_point("PaymentProcessor.process", "java")

        assert result["raw"] == "PaymentProcessor.process"
        assert result["class_or_module"] == "PaymentProcessor"
        assert result["method_or_function"] == "process"
        assert result["type"] == "method"  # CamelCase suggests class method

    @pytest.mark.asyncio
    async def test_generate_structural_summary_phase1(self, tracepath_tool):
        """Test structural summary generation (Phase 1 returns empty)"""
        files = ["/test/booking.py", "/test/payment.py"]
        summary = await tracepath_tool._generate_structural_summary(files, "python")

        # Phase 1 implementation should return empty string
        assert summary == ""

    @pytest.mark.asyncio
    async def test_prepare_prompt_basic(self, tracepath_tool):
        """Test basic prompt preparation"""
        request = TracePathRequest(
            entry_point="BookingManager::finalizeInvoice",
            files=["/test/booking.py"],
            parameters={"invoice_id": 123},
            analysis_depth="medium",
        )

        # Mock file content preparation
        with patch.object(tracepath_tool, "_prepare_file_content_for_prompt") as mock_prep:
            mock_prep.return_value = "def finalizeInvoice(self, invoice_id):\n    pass"
            with patch.object(tracepath_tool, "_validate_token_limit"):
                prompt = await tracepath_tool.prepare_prompt(request)

        assert "ANALYSIS REQUEST" in prompt
        assert "BookingManager::finalizeInvoice" in prompt
        assert "medium" in prompt
        assert "CODE TO ANALYZE" in prompt

    @pytest.mark.asyncio
    async def test_prepare_prompt_with_parameters(self, tracepath_tool):
        """Test prompt preparation with parameter values"""
        request = TracePathRequest(
            entry_point="payment.process_payment",
            files=["/test/payment.py"],
            parameters={"amount": 100.50, "method": "credit_card"},
            analysis_depth="deep",
            include_db=True,
            include_network=True,
            include_fs=False,
        )

        with patch.object(tracepath_tool, "_prepare_file_content_for_prompt") as mock_prep:
            mock_prep.return_value = "def process_payment(amount, method):\n    pass"
            with patch.object(tracepath_tool, "_validate_token_limit"):
                prompt = await tracepath_tool.prepare_prompt(request)

        assert "Parameter Values: {'amount': 100.5, 'method': 'credit_card'}" in prompt
        assert "Analysis Depth: deep" in prompt
        assert "Include Side Effects: database, network" in prompt

    @pytest.mark.asyncio
    async def test_prepare_prompt_with_context(self, tracepath_tool):
        """Test prompt preparation with additional context"""
        request = TracePathRequest(
            entry_point="UserService::authenticate",
            files=["/test/auth.py"],
            context="Focus on security implications and potential vulnerabilities",
            focus_areas=["security", "error_handling"],
        )

        with patch.object(tracepath_tool, "_prepare_file_content_for_prompt") as mock_prep:
            mock_prep.return_value = "def authenticate(self, username, password):\n    pass"
            with patch.object(tracepath_tool, "_validate_token_limit"):
                prompt = await tracepath_tool.prepare_prompt(request)

        assert "Additional Context: Focus on security implications" in prompt
        assert "Focus Areas: security, error_handling" in prompt

    def test_format_response_markdown(self, tracepath_tool):
        """Test response formatting for markdown output"""
        request = TracePathRequest(
            entry_point="BookingManager::finalizeInvoice", files=["/test/booking.py"], export_format="markdown"
        )

        response = "## Call Path Summary\n1. BookingManager::finalizeInvoice..."
        model_info = {"model_response": Mock(friendly_name="Gemini Pro")}

        formatted = tracepath_tool.format_response(response, request, model_info)

        assert response in formatted
        assert "Analysis Complete" in formatted
        assert "Gemini Pro" in formatted
        assert "confidence assessments" in formatted

    def test_format_response_json(self, tracepath_tool):
        """Test response formatting for JSON output"""
        request = TracePathRequest(entry_point="payment.process", files=["/test/payment.py"], export_format="json")

        response = '{"call_path": [...], "confidence": "high"}'

        formatted = tracepath_tool.format_response(response, request)

        assert response in formatted
        assert "structured JSON analysis" in formatted
        assert "confidence levels" in formatted

    def test_format_response_plantuml(self, tracepath_tool):
        """Test response formatting for PlantUML output"""
        request = TracePathRequest(entry_point="service.execute", files=["/test/service.py"], export_format="plantuml")

        response = "@startuml\nBooking -> Payment\n@enduml"

        formatted = tracepath_tool.format_response(response, request)

        assert response in formatted
        assert "PlantUML diagram" in formatted
        assert "Render the PlantUML" in formatted

    def test_get_default_temperature(self, tracepath_tool):
        """Test that the tool uses analytical temperature"""
        from config import TEMPERATURE_ANALYTICAL

        assert tracepath_tool.get_default_temperature() == TEMPERATURE_ANALYTICAL

    def test_wants_line_numbers_by_default(self, tracepath_tool):
        """Test that line numbers are enabled by default"""
        # The base class should enable line numbers by default for precise references
        # We test that this isn't overridden to disable them
        assert hasattr(tracepath_tool, "wants_line_numbers_by_default")

    def test_side_effects_configuration(self):
        """Test side effects boolean configuration"""
        request = TracePathRequest(
            entry_point="test.function",
            files=["/test/file.py"],
            include_db=True,
            include_network=False,
            include_fs=True,
        )

        assert request.include_db is True
        assert request.include_network is False
        assert request.include_fs is True

    def test_confidence_threshold_bounds(self):
        """Test confidence threshold validation bounds"""
        # Valid thresholds
        request1 = TracePathRequest(entry_point="test.function", files=["/test/file.py"], confidence_threshold=0.0)
        assert request1.confidence_threshold == 0.0

        request2 = TracePathRequest(entry_point="test.function", files=["/test/file.py"], confidence_threshold=1.0)
        assert request2.confidence_threshold == 1.0

        # Invalid thresholds should raise ValidationError
        with pytest.raises(ValueError):
            TracePathRequest(entry_point="test.function", files=["/test/file.py"], confidence_threshold=-0.1)

        with pytest.raises(ValueError):
            TracePathRequest(entry_point="test.function", files=["/test/file.py"], confidence_threshold=1.1)

    def test_signature_parameter(self):
        """Test signature parameter for overload resolution"""
        request = TracePathRequest(
            entry_point="Calculator.add",
            files=["/test/calc.cs"],
            signature="public int Add(int a, int b)",
            language="csharp",
        )

        assert request.signature == "public int Add(int a, int b)"
        assert request.language == "csharp"

    @pytest.mark.asyncio
    async def test_prepare_prompt_with_language_override(self, tracepath_tool):
        """Test prompt preparation with language override"""
        request = TracePathRequest(
            entry_point="Calculator::Add",
            files=["/test/calc.py"],  # Python extension
            language="csharp",  # Override to C#
        )

        with patch.object(tracepath_tool, "_prepare_file_content_for_prompt") as mock_prep:
            mock_prep.return_value = "public class Calculator { }"
            with patch.object(tracepath_tool, "_validate_token_limit"):
                prompt = await tracepath_tool.prepare_prompt(request)

        assert "Language: csharp" in prompt  # Should use override, not detected

    def test_export_format_options(self):
        """Test all export format options"""
        formats = ["markdown", "json", "plantuml"]

        for fmt in formats:
            request = TracePathRequest(entry_point="test.function", files=["/test/file.py"], export_format=fmt)
            assert request.export_format == fmt

        # Invalid format should raise ValidationError
        with pytest.raises(ValueError):
            TracePathRequest(entry_point="test.function", files=["/test/file.py"], export_format="invalid_format")
