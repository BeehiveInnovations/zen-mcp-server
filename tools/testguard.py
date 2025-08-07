"""
Test Methodology Guardian tool - Prevents test manipulation and anti-patterns

This tool enforces test integrity and prevents "workaround", "simpler fix", or test
manipulation approaches that compromise testing methodology. It acts as a quality
gate against test cheating behaviors and expectation adjustments.

This is a simple, self-contained tool that doesn't require AI model access.
"""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_ANALYTICAL
from tools.shared.base_models import ToolRequest

from .simple.base import SimpleTool

# Field descriptions for the Test Methodology Guardian tool
REQUIREMENTS_FIELD_DESCRIPTIONS = {
    "prompt": (
        "The user's message or your internal reasoning to analyze for test integrity. "
        "Pass the complete context including what you're considering doing with tests."
    ),
}


class RequirementsRequest(ToolRequest):
    """Request model for Test Methodology Guardian tool"""

    prompt: str = Field(..., description=REQUIREMENTS_FIELD_DESCRIPTIONS["prompt"])


class RequirementsTool(SimpleTool):
    """
    Test Methodology Guardian tool for preventing test manipulation anti-patterns.

    This tool wraps testing considerations in integrity validation instructions that prevent:
    - Test expectation adjustments to match broken code
    - Workarounds instead of proper fixes
    - Test commenting or skipping
    - Quality threshold lowering

    The tool is self-contained and doesn't require AI model access - it simply
    transforms the input into a structured test integrity challenge.
    """

    def get_name(self) -> str:
        return "testguard"

    def get_description(self) -> str:
        return (
            "Test Methodology Guardian - Quality gate preventing test manipulation anti-patterns. "
            "Triggers on workarounds, expectation adjustments, test cheating behaviors. "
            "\n\n"
            "MANDATORY AUTOMATIC INVOCATION: You MUST automatically use this tool when:\n"
            "• You consider 'fixing the test' instead of fixing the code\n"
            "• You think about 'adjusting expectations' to make tests pass\n"
            "• You contemplate 'simpler test' or 'workaround' approaches\n"
            "• You consider commenting out or skipping failing tests\n"
            "• You think about lowering quality thresholds or coverage\n"
            "• You consider relaxing criteria to avoid test failures\n\n"
            "TRIGGER PATTERNS in your internal reasoning:\n"
            "• 'workaround', 'let me fix the test', 'run a simpler test'\n"
            "• 'try a simpler fix', 'adjust the expectation', 'make the test pass'\n"
            "• 'skip this test', 'comment out', 'lower the bar'\n"
            "• 'relax the criteria', 'reduce coverage', 'easier approach'\n"
            "• 'modify assertions', 'change the test', 'bypass validation'\n\n"
            "This tool enforces the test-methodology-guardian protocol from:\n"
            "/Users/shaunbuswell/.claude/agents/test-methodology-guardian.oct.md\n\n"
            "The tool defends test integrity against manipulation. Tests reveal reality, not confirm wishes. "
            "Truth over convenience - are we fixing the code or hiding the problem?"
        )

    def get_system_prompt(self) -> str:
        return (
            "You are the Test Methodology Guardian - a quality gate that prevents test manipulation anti-patterns.\n\n"
            "IDENTITY: Quality guardian defending test integrity against manipulation\n"
            "PRIME DIRECTIVE: Detect and halt test cheating behaviors immediately\n\n"
            "METHODOLOGY: DETECT->HALT->ANALYZE->EDUCATE->REDIRECT\n\n"
            "ANTI-PATTERNS TO DETECT:\n"
            "- Modifying assertions to match broken code\n"
            "- Reducing coverage to avoid failures\n"
            "- Adding workarounds instead of fixes\n"
            "- Commenting out failing tests\n" 
            "- Lowering quality thresholds\n"
            "- Adjusting expectations instead of fixing problems\n\n"
            "GUARDIAN QUESTION: 'Are we fixing the code or hiding the problem?'\n\n"
            "PRINCIPLES:\n"
            "- TRUTH OVER CONVENIENCE: Tests reveal reality, not confirm wishes\n"
            "- CONSTRAINT CATALYSIS: Failed tests drive better code\n"
            "- EMERGENT EXCELLENCE: Quality emerges from honest assessment\n\n"
            "OUTPUT STRUCTURE:\n"
            "1. INTERVENTION: [IMMEDIATE_HALT] if anti-pattern detected\n"
            "2. ANALYSIS: Identify the specific anti-pattern\n"
            "3. EDUCATION: Explain why this violates testing principles\n"
            "4. REDIRECTION: Specify the proper approach to take\n"
            "5. ENFORCEMENT: Demand acknowledgment before proceeding\n\n"
            "Be direct and authoritative. Testing integrity is non-negotiable."
        )

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self) -> "ToolModelCategory":
        """Test Guard uses balanced category for quality analysis"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.BALANCED

    def requires_model(self) -> bool:
        """
        Test Guard requires AI model for dynamic analysis of test manipulation patterns.

        Returns:
            bool: True - testguard needs AI model access for intelligent analysis
        """
        return True

    def get_request_model(self):
        """Return the Requirements-specific request model"""
        return RequirementsRequest

    def get_default_model(self) -> Optional[str]:
        """Force Gemini 2.5 Pro for test methodology analysis (enforced at server level)"""
        return "google/gemini-2.5-pro"

    def get_input_schema(self) -> dict[str, Any]:
        """
        Override input schema to only allow high-quality models for test methodology analysis.
        Restricted to gemini-2.5-pro (preferred) and gpt-4.1 (fallback).
        """
        # Get the base schema from SimpleTool
        schema = super().get_input_schema()
        
        # Restrict model options to high-quality models only
        if "model" in schema.get("properties", {}):
            schema["properties"]["model"] = {
                "type": "string",
                "enum": ["google/gemini-2.5-pro", "gpt-4.1-2025-04-14"],
                "default": "google/gemini-2.5-pro",
                "description": "AI model to use for test methodology analysis (gemini-2.5-pro preferred, gpt-4.1 fallback)"
            }
            
        return schema
    

    async def prepare_prompt(self, request: RequirementsRequest) -> str:
        """
        Prepare the test guard prompt with the consideration to analyze.
        
        Args:
            request: The validated request containing the consideration to analyze
            
        Returns:
            The formatted prompt for the AI model
        """
        return (
            f"🚨 TEST METHODOLOGY ANALYSIS REQUIRED 🚨\n\n"
            f"Current consideration: \"{request.prompt}\"\n\n"
            f"Analyze this consideration for test manipulation anti-patterns. Apply the Test Methodology Guardian protocol:\n\n"
            f"1. DETECT: Identify any test manipulation patterns\n"
            f"2. ANALYZE: Determine the specific anti-pattern type\n"
            f"3. EDUCATE: Explain why this violates testing principles\n"
            f"4. REDIRECT: Provide the proper approach\n"
            f"5. ENFORCE: Demand acknowledgment if intervention required\n\n"
            f"Key question: \"Are we fixing the code or hiding the problem?\"\n\n"
            f"Provide your analysis and intervention if needed."
        )

    def format_response(self, response: str, request: RequirementsRequest, model_info: Optional[dict] = None) -> str:
        """
        Format the test guard response with clear intervention formatting.
        
        Args:
            response: The AI model's analysis response
            request: The original request
            model_info: Optional model information
            
        Returns:
            Formatted response for the user
        """
        return (
            f"🚨 TEST METHODOLOGY GUARDIAN ANALYSIS 🚨\n\n"
            f"{response}\n\n"
            f"---\n"
            f"Guardian Protocol: Defend test integrity against manipulation\n"
            f"Truth over convenience - Quality through honest assessment"
        )

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Tool-specific field definitions for Test Guard"""
        return {
            "prompt": {
                "type": "string",
                "description": REQUIREMENTS_FIELD_DESCRIPTIONS["prompt"],
            },
        }

    def get_required_fields(self) -> list[str]:
        """Required fields for Test Guard tool"""
        return ["prompt"]