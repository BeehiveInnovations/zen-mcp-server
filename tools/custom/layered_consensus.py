"""Layered Consensus Custom Tool.

This tool provides sophisticated multi-model consensus analysis with layered
model distribution and role-based assignments for comprehensive decision making.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.simple.base import SimpleTool

logger = logging.getLogger(__name__)


class LayeredConsensusRequest(ToolRequest):
    """Request model for layered consensus analysis."""

    question: str = Field(description="The question or proposal to analyze with layered consensus")
    org_level: str = Field(
        default="startup", description="Organization level (startup, scaleup, enterprise) for model distribution",
    )
    model_count: int = Field(default=5, description="Total number of models to use across all layers")
    layers: list[str] = Field(
        default=["strategic", "analytical", "practical"],
        description="Consensus layers to analyze (strategic, analytical, practical, technical)",
    )
    cost_threshold: str = Field(
        default="balanced", description="Cost preference (cost-optimized, balanced, performance)",
    )


class LayeredConsensusTool(SimpleTool):
    """Tool for multi-layered consensus analysis with model distribution."""

    def get_name(self) -> str:
        """Get the name of the tool."""
        return "layered_consensus"

    def get_description(self) -> str:
        """Get the description of the tool."""
        return "Performs sophisticated multi-model consensus analysis with layered model distribution and role-based assignments."

    def get_tool_fields(self) -> dict[str, Any]:
        """Return tool-specific field definitions for schema generation."""
        return {
            "question": {"type": "string", "description": "The question or proposal to analyze with layered consensus"},
            "org_level": {
                "type": "string",
                "default": "startup",
                "enum": ["startup", "scaleup", "enterprise"],
                "description": "Organization level (startup, scaleup, enterprise) for model distribution",
            },
            "model_count": {
                "type": "integer",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
                "description": "Total number of models to use across all layers",
            },
            "layers": {
                "type": "array",
                "items": {"type": "string", "enum": ["strategic", "analytical", "practical", "technical"]},
                "default": ["strategic", "analytical", "practical"],
                "description": "Consensus layers to analyze (strategic, analytical, practical, technical)",
            },
            "cost_threshold": {
                "type": "string",
                "default": "balanced",
                "enum": ["cost-optimized", "balanced", "performance"],
                "description": "Cost preference (cost-optimized, balanced, performance)",
            },
        }

    def get_required_fields(self) -> list[str]:
        """Return list of required field names."""
        return ["question"]

    def get_system_prompt(self) -> str:
        """Get the system prompt for the tool."""
        return """You are a professional role-based consensus analysis assistant.

Your role is to coordinate analysis across specific professional roles within organizational hierarchies.

CRITICAL REQUIREMENTS:
- You MUST use only the specific professional roles provided in each request
- DO NOT default to generic "strategic/analytical/practical" layers
- Each role has specific expertise and concerns that must be reflected
- Follow the additive organizational structure (startup → scaleup → enterprise)

Your responsibilities:
1. Provide analysis from each assigned professional role's perspective
2. Reflect role-specific expertise, concerns, and priorities
3. Show how higher organizational levels build upon lower levels
4. Synthesize perspectives across all professional roles
5. Identify consensus points and disagreements between roles
6. Provide balanced recommendations considering all role perspectives

Professional roles include: Code Reviewer, Security Checker, Technical Validator, Senior Developer, System Architect, DevOps Engineer, Lead Architect, Technical Director.

Each role has distinct expertise - ensure your analysis reflects this specialization."""

    def get_request_model(self) -> LayeredConsensusRequest:
        """Get the request model for the tool."""
        return LayeredConsensusRequest

    async def prepare_prompt(self, request: LayeredConsensusRequest) -> str:
        """Prepare the role-based consensus prompt."""
        # Create role-specific analysis structure
        role_assignments = self._create_layer_assignments(request)

        # Create structured role breakdown
        role_structure = self._create_role_structure(role_assignments, request.org_level)

        # Map professional roles to the layers the model expects
        mapped_roles = self._map_roles_to_expected_format(role_assignments, request.org_level)

        return f"""Conduct a layered consensus analysis on the following:

QUESTION/PROPOSAL: {request.question}

ORGANIZATIONAL STRUCTURE: {request.org_level.title()} Level Analysis
{role_structure}

ROLE ASSIGNMENTS AND RESPONSIBILITIES:
{mapped_roles}

INSTRUCTIONS:
1. For each assigned professional role, provide analysis from that role's specific expertise
2. Show the additive organizational structure where {request.org_level} builds upon previous tiers
3. Focus on role-specific concerns rather than generic strategic/analytical/practical categories
4. Identify consensus points and disagreements across professional roles
5. Synthesize findings into coherent recommendation
6. Include confidence levels and uncertainties

The response should reflect the specific expertise and concerns of each professional role assigned."""

    def _create_layer_assignments(self, request: LayeredConsensusRequest) -> dict[str, list[str]]:
        """Create professional role assignments using data-driven model selection."""
        try:
            return self._create_org_level_assignments(request)
        except Exception as e:
            logger.error(f"Failed to create data-driven assignments: {e}")
            # Fallback to simple assignment
            return self._create_fallback_assignments(request)

    def _create_org_level_assignments(self, request: LayeredConsensusRequest) -> dict[str, list[str]]:
        """Create additive organizational assignments using routing system."""
        if request.org_level == "startup":
            return self._create_startup_assignment()
        elif request.org_level == "scaleup":
            return self._create_scaleup_assignment()  # Additive
        else:  # enterprise
            return self._create_enterprise_assignment()  # Additive

    def _create_startup_assignment(self) -> dict[str, list[str]]:
        """Startup: 3 free models with best performance scores using band selection."""
        from .band_selector import BandSelector

        selector = BandSelector()

        # Get role-specific models using band selection
        return {
            "code_reviewer": selector.get_models_by_role("code_reviewer", "startup", 1),
            "security_checker": selector.get_models_by_role("security_checker", "startup", 1),
            "technical_validator": selector.get_models_by_role("technical_validator", "startup", 1)
        }

    def _create_scaleup_assignment(self) -> dict[str, list[str]]:
        """Scaleup: Startup + 3 professional-tier models using band selection."""
        from .band_selector import BandSelector

        selector = BandSelector()
        startup_roles = self._create_startup_assignment()

        # Add professional roles using band-based selection
        startup_roles.update({
            "senior_developer": selector.get_models_by_role("senior_developer", "scaleup", 1),
            "system_architect": selector.get_models_by_role("system_architect", "scaleup", 1),
            "devops_engineer": selector.get_models_by_role("devops_engineer", "scaleup", 1)
        })
        return startup_roles

    def _create_enterprise_assignment(self) -> dict[str, list[str]]:
        """Enterprise: Scaleup + 2 premium models using band selection."""
        from .band_selector import BandSelector

        selector = BandSelector()
        scaleup_roles = self._create_scaleup_assignment()

        # Add executive roles using band-based selection
        scaleup_roles.update({
            "lead_architect": selector.get_models_by_role("lead_architect", "enterprise", 1),
            "technical_director": selector.get_models_by_role("technical_director", "enterprise", 1)
        })
        return scaleup_roles

    def _get_models_by_criteria(self, cost_max: float = None, cost_min: float = None,
                               org_level: str = None, limit: int = 5) -> list[str]:
        """Get models using band-based selection (legacy method maintained for compatibility)."""
        try:
            from .band_selector import BandSelector

            selector = BandSelector()

            # Map legacy parameters to band-based selection
            if cost_max == 0.0:
                return selector.get_models_by_cost_tier("free", limit)
            elif cost_max and cost_max <= 1.0:
                return selector.get_models_by_cost_tier("economy", limit)
            elif cost_max and cost_max <= 10.0:
                return selector.get_models_by_cost_tier("value", limit)
            elif cost_min and cost_min >= 10.0:
                return selector.get_models_by_cost_tier("premium", limit)
            elif org_level:
                return selector.get_models_by_org_level(org_level, limit)
            else:
                return selector.get_models_by_org_level("scaleup", limit)

        except Exception as e:
            logger.warning(f"Failed to get models from band selector: {e}")
            return self._get_fallback_models(limit)

    def _get_fallback_models(self, limit: int) -> list[str]:
        """Fallback model selection using band selector's fallback system."""
        try:
            from .band_selector import BandSelector
            selector = BandSelector()
            return selector._get_fallback_models("scaleup", limit)
        except Exception:
            # Ultimate fallback
            fallback_models = [
                "deepseek/deepseek-chat:free",
                "meta-llama/llama-3.3-70b-instruct:free",
                "qwen/qwen-2.5-coder-32b-instruct:free",
                "google/gemini-2.5-flash",
                "openai/gpt-5-mini",
                "anthropic/claude-sonnet-4",
                "anthropic/claude-opus-4.1",
                "openai/gpt-5"
            ]
            return fallback_models[:limit]

    def _create_fallback_assignments(self, request: LayeredConsensusRequest) -> dict[str, list[str]]:
        """Fallback assignments using band selector's fallback system."""
        try:
            from .band_selector import BandSelector
            selector = BandSelector()

            if request.org_level == "startup":
                fallback_models = selector._get_fallback_models("startup", 3)
                return {
                    "code_reviewer": [fallback_models[0]] if len(fallback_models) > 0 else ["deepseek/deepseek-chat:free"],
                    "security_checker": [fallback_models[1]] if len(fallback_models) > 1 else ["meta-llama/llama-3.3-70b-instruct:free"],
                    "technical_validator": [fallback_models[2]] if len(fallback_models) > 2 else ["qwen/qwen-2.5-coder-32b-instruct:free"]
                }
            elif request.org_level == "scaleup":
                fallback_models = selector._get_fallback_models("scaleup", 6)
                return {
                    "code_reviewer": [fallback_models[0]] if len(fallback_models) > 0 else ["deepseek/deepseek-chat:free"],
                    "security_checker": [fallback_models[1]] if len(fallback_models) > 1 else ["meta-llama/llama-3.3-70b-instruct:free"],
                    "technical_validator": [fallback_models[2]] if len(fallback_models) > 2 else ["qwen/qwen-2.5-coder-32b-instruct:free"],
                    "senior_developer": [fallback_models[3]] if len(fallback_models) > 3 else ["google/gemini-2.5-flash"],
                    "system_architect": [fallback_models[4]] if len(fallback_models) > 4 else ["openai/gpt-5-mini"],
                    "devops_engineer": [fallback_models[5]] if len(fallback_models) > 5 else ["anthropic/claude-sonnet-4"]
                }
            else:  # enterprise
                fallback_models = selector._get_fallback_models("enterprise", 8)
                return {
                    "code_reviewer": [fallback_models[0]] if len(fallback_models) > 0 else ["deepseek/deepseek-chat:free"],
                    "security_checker": [fallback_models[1]] if len(fallback_models) > 1 else ["meta-llama/llama-3.3-70b-instruct:free"],
                    "technical_validator": [fallback_models[2]] if len(fallback_models) > 2 else ["qwen/qwen-2.5-coder-32b-instruct:free"],
                    "senior_developer": [fallback_models[3]] if len(fallback_models) > 3 else ["google/gemini-2.5-flash"],
                    "system_architect": [fallback_models[4]] if len(fallback_models) > 4 else ["anthropic/claude-sonnet-4"],
                    "devops_engineer": [fallback_models[5]] if len(fallback_models) > 5 else ["openai/gpt-5-mini"],
                    "lead_architect": [fallback_models[6]] if len(fallback_models) > 6 else ["anthropic/claude-opus-4.1"],
                    "technical_director": [fallback_models[7]] if len(fallback_models) > 7 else ["openai/gpt-5"]
                }
        except Exception as e:
            logger.error(f"Fallback assignment failed: {e}")
            # Ultimate fallback with hardcoded assignments
            fallback_models = ["deepseek/deepseek-chat:free", "meta-llama/llama-3.3-70b-instruct:free",
                              "google/gemini-2.5-flash", "anthropic/claude-sonnet-4",
                              "anthropic/claude-opus-4.1", "openai/gpt-5"]

            if request.org_level == "startup":
                return {"code_reviewer": [fallback_models[0]], "security_checker": [fallback_models[1]], "technical_validator": [fallback_models[2]]}
            elif request.org_level == "scaleup":
                return {"code_reviewer": [fallback_models[0]], "security_checker": [fallback_models[1]], "technical_validator": [fallback_models[2]], "senior_developer": [fallback_models[3]], "system_architect": [fallback_models[4]], "devops_engineer": [fallback_models[5]]}
            else:
                return {"code_reviewer": [fallback_models[0]], "security_checker": [fallback_models[1]], "technical_validator": [fallback_models[2]], "senior_developer": [fallback_models[3]], "system_architect": [fallback_models[4]], "devops_engineer": [fallback_models[5]], "lead_architect": [fallback_models[6]], "technical_director": [fallback_models[7]]}


    def _format_layer_assignments(self, assignments: dict[str, list[str]]) -> str:
        """Format professional role assignments for display."""
        formatted = []
        role_descriptions = {
            "code_reviewer": "Code quality and syntax validation",
            "security_checker": "Security vulnerabilities and compliance",
            "technical_validator": "Technical feasibility assessment",
            "senior_developer": "Advanced implementation strategies",
            "system_architect": "System design and scalability",
            "devops_engineer": "Infrastructure and deployment",
            "lead_architect": "Enterprise architecture strategy",
            "technical_director": "Strategic technology decisions",
            # Legacy layer support
            "strategic": "High-level strategic thinking, long-term implications",
            "analytical": "Detailed analysis, data-driven insights",
            "practical": "Implementation feasibility, operational considerations",
            "technical": "Technical implementation, system architecture",
        }

        for role, models in assignments.items():
            description = role_descriptions.get(role, "Professional analysis")
            formatted.append(f"• {role.upper().replace('_', ' ')}: {', '.join(models)} - {description}")

        return "\n".join(formatted)

    def _create_role_structure(self, assignments: dict[str, list[str]], org_level: str) -> str:
        """Create organizational structure breakdown showing additive tiers."""
        if org_level == "startup":
            return """
STARTUP TIER (3 roles - Free models, basic analysis):
• Code Reviewer: Code quality and syntax validation
• Security Checker: Security vulnerabilities and compliance
• Technical Validator: Technical feasibility assessment
"""
        elif org_level == "scaleup":
            return """
STARTUP TIER (3 roles - Free models, basic analysis):
• Code Reviewer: Code quality and syntax validation
• Security Checker: Security vulnerabilities and compliance
• Technical Validator: Technical feasibility assessment

PROFESSIONAL TIER (3 additional roles - Value models, production analysis):
• Senior Developer: Advanced implementation strategies
• System Architect: System design and scalability
• DevOps Engineer: Infrastructure and deployment
"""
        else:  # enterprise
            return """
STARTUP TIER (3 roles - Free models, basic analysis):
• Code Reviewer: Code quality and syntax validation
• Security Checker: Security vulnerabilities and compliance
• Technical Validator: Technical feasibility assessment

PROFESSIONAL TIER (3 roles - Value models, production analysis):
• Senior Developer: Advanced implementation strategies
• System Architect: System design and scalability
• DevOps Engineer: Infrastructure and deployment

EXECUTIVE TIER (2 additional roles - Premium models, strategic analysis):
• Lead Architect: Enterprise architecture strategy
• Technical Director: Strategic technology decisions
"""

    def _create_role_prompts(self, assignments: dict[str, list[str]]) -> str:
        """Create individual prompts for each professional role."""
        role_prompts = []

        role_contexts = {
            "code_reviewer": "Focus on code quality, maintainability, and development practices. Consider technical debt and implementation complexity.",
            "security_checker": "Analyze security implications, compliance requirements, and vulnerability risks. Consider data protection and access control.",
            "technical_validator": "Assess technical feasibility, resource requirements, and implementation challenges. Consider team capabilities and timeline.",
            "senior_developer": "Provide advanced technical perspective on implementation strategies, performance optimization, and best practices.",
            "system_architect": "Focus on system design, scalability, integration patterns, and architectural trade-offs.",
            "devops_engineer": "Consider infrastructure, deployment, monitoring, and operational aspects. Focus on reliability and maintenance.",
            "lead_architect": "Provide enterprise-level architectural vision, long-term strategy, and organizational impact assessment.",
            "technical_director": "Focus on strategic technology decisions, business alignment, and long-term technical direction."
        }

        for role, models in assignments.items():
            context = role_contexts.get(role, "Provide professional analysis from this role's perspective.")
            role_prompts.append(f"""
### {role.upper().replace('_', ' ')} ({', '.join(models)})
{context}
Provide your analysis focusing on this role's specific expertise and concerns.
""")

        return "\n".join(role_prompts)

    def _create_response_template(self, assignments: dict[str, list[str]]) -> str:
        """Create the mandatory response template structure."""
        template_sections = []

        for role, models in assignments.items():
            role_title = role.upper().replace('_', ' ')
            template_sections.append(f"""
### {role_title}
**Model:** {', '.join(models)}
**Expertise:** [Role-specific analysis from {role.replace('_', ' ')} perspective]
**Recommendation:** [Role-specific recommendation]
""")

        return "\n".join(template_sections)

    def _map_roles_to_expected_format(self, assignments: dict[str, list[str]], org_level: str) -> str:
        """Map professional roles to format that works with model expectations."""
        role_mapping = []

        for role, models in assignments.items():
            role_contexts = {
                "code_reviewer": "Technical implementation expert focused on code quality, syntax, maintainability, and development best practices. Acts as technical validator for implementation decisions.",
                "security_checker": "Security and compliance specialist analyzing vulnerability risks, data protection, access control, and regulatory requirements. Provides security-first perspective.",
                "technical_validator": "Technical feasibility expert assessing resource requirements, implementation challenges, team capabilities, and timeline constraints. Evaluates practical implementation aspects.",
                "senior_developer": "Advanced technical strategist providing sophisticated implementation approaches, performance optimization, architectural patterns, and advanced development practices.",
                "system_architect": "System design expert focusing on scalability, integration patterns, architectural trade-offs, and long-term technical strategy. Provides architectural oversight.",
                "devops_engineer": "Infrastructure and operations specialist considering deployment, monitoring, reliability, maintenance, and operational aspects. Ensures operational excellence.",
                "lead_architect": "Enterprise architecture strategist providing high-level technical vision, organizational impact assessment, and strategic architectural direction.",
                "technical_director": "Executive technical leader focusing on strategic technology decisions, business alignment, long-term technical direction, and organizational impact."
            }

            context = role_contexts.get(role, "Professional analysis specialist")
            role_mapping.append(f"• **{role.upper().replace('_', ' ')}** ({', '.join(models)}): {context}")

        return "\n".join(role_mapping)


class LayeredConfigV2:
    """Compatibility class for configuration."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the configuration."""
        self.config = kwargs


class OrgLevel:
    """Organizational levels for model selection."""

    STARTUP = "startup"
    SCALEUP = "scaleup"
    ENTERPRISE = "enterprise"


class CostThreshold:
    """Cost thresholds for model selection."""

    LOW = "cost-optimized"
    MEDIUM = "balanced"
    HIGH = "performance"


class DefaultModel:
    """Default model configurations."""

    FAST = "gpt-4o-mini"
    BALANCED = "claude-3.5-sonnet"
    PREMIUM = "gpt-4o"


class LayeredConsensusError(Exception):
    """Base exception for layered consensus operations."""


class ModelSelectionError(LayeredConsensusError):
    """Error in model selection process."""


class FormatConversionError(LayeredConsensusError):
    """Error in format conversion."""


class ConsensusExecutionError(LayeredConsensusError):
    """Error during consensus execution."""


class ConfigurationError(LayeredConsensusError):
    """Configuration validation error."""


class ValidationError(LayeredConsensusError):
    """Input validation error."""

def create_layered_consensus_tool(config: Any = None, model_selector: Any = None) -> LayeredConsensusTool:
    """Create a layered consensus tool."""
    return LayeredConsensusTool()


def create_layered_consensus_v2(config: Any = None, model_selector: Any = None) -> LayeredConsensusTool:
    """Create a v2 layered consensus tool."""
    return LayeredConsensusTool()


def create_custom_layered_consensus_v2(config: Any = None, model_selector: Any = None) -> LayeredConsensusTool:
    """Create a custom v2 layered consensus tool."""
    return LayeredConsensusTool()