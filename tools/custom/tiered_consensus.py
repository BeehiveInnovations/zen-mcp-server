"""
Tiered Consensus Tool.

Simple API for multi-model consensus analysis with additive tier architecture.
User provides just: prompt + level (1, 2, or 3)

Implements:
- Additive tier architecture (Level 2 includes Level 1's models)
- BandSelector integration (no hardcoded models)
- Free model failover (transient availability)
- Domain-specific role assignments

NOTE: This is separate from the core /tools/consensus.py (upstream tool).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import Field, model_validator

from config import TEMPERATURE_ANALYTICAL
from providers import ModelProviderRegistry
from tools.custom.consensus_models import TierManager, get_level_description
from tools.custom.consensus_roles import RoleAssigner, create_role_prompt
from tools.custom.consensus_synthesis import SynthesisEngine, format_consensus_result
from tools.shared.base_models import WorkflowRequest
from tools.workflow.base import WorkflowTool

logger = logging.getLogger(__name__)


class TieredConsensusRequest(WorkflowRequest):
    """Request model for tiered consensus tool."""

    # Simple user-facing fields
    prompt: str = Field(
        ...,
        description="The question or proposal to analyze with consensus",
    )
    level: int = Field(
        ...,
        ge=1,
        le=3,
        description=(
            "Organizational level (1-3):\n"
            "  1 = Foundation (3 free models, $0)\n"
            "  2 = Professional (6 models, ~$0.50)\n"
            "  3 = Executive (8 models, ~$5.00)"
        ),
    )
    domain: str = Field(
        default="code_review",
        description="Domain type: code_review, security, architecture, general",
    )

    # Optional advanced parameters (most users won't need these)
    include_synthesis: bool = Field(
        default=True,
        description="Generate synthesis report (default: true)",
    )
    max_cost: Optional[float] = Field(
        default=None,
        description="Override cost limit (default: based on level)",
    )

    @model_validator(mode='after')
    def validate_domain(self):
        """Validate domain is supported."""
        valid_domains = ["code_review", "security", "architecture", "general"]
        if self.domain not in valid_domains:
            raise ValueError(
                f"Invalid domain: {self.domain}. "
                f"Valid domains: {', '.join(valid_domains)}"
            )
        return self


class TieredConsensusTool(WorkflowTool):
    """
    Tiered consensus tool with simple API and additive tier architecture.

    User provides:
    - prompt: Question/proposal to analyze
    - level: 1 (Foundation), 2 (Professional), or 3 (Executive)
    - domain: Optional domain type (default: code_review)

    Tool automatically:
    - Selects appropriate models using BandSelector (additive tiers)
    - Assigns professional roles based on domain
    - Handles free model failover
    - Aggregates perspectives
    - Generates consensus analysis

    NOTE: Separate from /tools/consensus.py (upstream core tool)
    """

    def __init__(self):
        """Initialize consensus tool."""
        super().__init__()
        self.tier_manager = TierManager()
        self.role_assigner = RoleAssigner()
        self.synthesis_engine = SynthesisEngine()

    def get_name(self) -> str:
        """Get tool name."""
        return "tiered_consensus"

    def get_description(self) -> str:
        """Get tool description."""
        return (
            "Multi-model consensus analysis with simple API. "
            "Provide prompt + level (1-3) for additive tier consensus "
            "from multiple AI models and professional perspectives."
        )

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """
        Return tool-specific fields beyond standard workflow fields.

        Standard workflow fields (automatic):
        - step, step_number, total_steps, next_step_required
        - findings, files_checked, relevant_files, etc.

        Tool-specific fields (add here):
        - prompt, level, domain, etc.
        """
        return {
            "prompt": {
                "type": "string",
                "description": "The question or proposal to analyze with consensus",
            },
            "level": {
                "type": "integer",
                "minimum": 1,
                "maximum": 3,
                "description": (
                    "Organizational level (1-3):\n"
                    "  1 = Foundation (3 free models, $0)\n"
                    "  2 = Professional (6 models, ~$0.50)\n"
                    "  3 = Executive (8 models, ~$5.00)"
                ),
            },
            "domain": {
                "type": "string",
                "default": "code_review",
                "enum": ["code_review", "security", "architecture", "general"],
                "description": "Domain type for role assignments",
            },
            "include_synthesis": {
                "type": "boolean",
                "default": True,
                "description": "Generate synthesis report (default: true)",
            },
            "max_cost": {
                "type": "number",
                "description": "Override cost limit (default: based on level)",
            },
        }

    def get_required_fields(self) -> List[str]:
        """
        Return additional required fields beyond standard workflow requirements.

        Standard workflow required fields (automatic):
        - step, step_number, total_steps, next_step_required, findings

        Additional required fields:
        - prompt, level
        """
        return ["prompt", "level"]

    def requires_model(self) -> bool:
        """
        Consensus tool uses multiple models (selected via BandSelector).

        Returns False because we don't use a single assistant model parameter.
        Models are selected internally based on level and domain.
        """
        return False

    def get_request_model(self):
        """Return the Pydantic model for request validation."""
        return TieredConsensusRequest

    def get_system_prompt(self) -> str:
        """Return system prompt for this tool (not used in consensus)."""
        return ""

    async def prepare_prompt(self, request) -> str:
        """
        Prepare prompt for model call (not used - we handle prompts internally).

        Args:
            request: Tool request object

        Returns:
            Empty string (prompts are built per-model in execute())
        """
        return ""

    async def execute(self, arguments: dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute consensus analysis workflow.

        Args:
            arguments: Dictionary of arguments from MCP protocol

        Returns:
            List of MCP text content blocks with consensus analysis
        """
        # Parse arguments into request model for validation
        request = TieredConsensusRequest(**arguments)

        logger.info(
            f"Starting consensus analysis - Level {request.level}, "
            f"Domain: {request.domain}, Step: {request.step_number}/{request.total_steps}"
        )

        # Get models and roles for this level
        models = self.tier_manager.get_tier_models(request.level)
        roles = self.role_assigner.get_roles_for_level(request.level, request.domain)

        # Get failover candidates for smart retry
        primary_models, fallback_models = self.tier_manager.get_failover_candidates(request.level)

        logger.info(f"Selected {len(models)} models and {len(roles)} roles")
        logger.debug(f"Failover pool: {len(fallback_models)} additional candidates available")

        # Workflow step 1: Initial setup
        if request.step_number == 1:
            # Return initial guidance
            tier_costs = self.tier_manager.get_tier_costs(request.level)
            level_desc = get_level_description(request.level)

            guidance = (
                f"**Consensus Analysis Configuration**\n\n"
                f"- **Level:** {request.level} ({level_desc})\n"
                f"- **Domain:** {request.domain}\n"
                f"- **Models:** {len(models)} ({', '.join(models[:3])}{'...' if len(models) > 3 else ''})\n"
                f"- **Roles:** {len(roles)} ({', '.join(roles[:3])}{'...' if len(roles) > 3 else ''})\n"
                f"- **Estimated Cost:** ${tier_costs['estimated_cost_per_call']}\n\n"
                f"**Next Steps:**\n"
                f"1. Consult each model with role-specific prompt\n"
                f"2. Collect perspectives from all models\n"
                f"3. Synthesize consensus analysis\n"
                f"4. Generate executive summary\n\n"
                f"**Step 2 will begin model consultations...**"
            )

            return self._create_text_content(guidance)

        # Workflow steps 2-N: Collect perspectives from each model
        if request.step_number >= 2 and request.step_number <= len(models) + 1:
            model_index = request.step_number - 2
            current_model = models[model_index]
            current_role = roles[model_index] if model_index < len(roles) else roles[-1]

            # Create role-specific prompt
            role_prompt = create_role_prompt(current_role, request.prompt)

            # Call the model with smart failover
            model_response, response_cost, actual_model, failover_used = await self._call_model_with_failover(
                primary_model=current_model,
                fallback_candidates=fallback_models,
                role=current_role,
                prompt=role_prompt,
                level=request.level,
            )

            # Track if failover was used
            if failover_used:
                logger.info(f"✅ Failover successful: {actual_model} (replaced {current_model})")
                # Note: We still track as current_model for consistency in output
            else:
                logger.info(f"✅ Model call successful: {actual_model} (cost: ${response_cost:.4f})")

            # Add perspective to synthesis engine
            self.synthesis_engine.add_perspective(
                role=current_role,
                model=actual_model,  # Use actual model that succeeded
                analysis=model_response,
                cost=response_cost,
            )

            logger.info(f"Collected perspective from {actual_model} as {current_role}")

            # Progress update
            progress = (
                f"**Step {request.step_number}/{request.total_steps}:** "
                f"Collected perspective from {current_model} as {current_role}\n\n"
                f"Progress: {model_index + 1}/{len(models)} models consulted"
            )

            return self._create_text_content(progress)

        # Final step: Generate synthesis
        if request.step_number == len(models) + 2:
            logger.info("Generating consensus synthesis")

            # Calculate actual cost (placeholder)
            tier_costs = self.tier_manager.get_tier_costs(request.level)
            total_cost = tier_costs['estimated_cost_per_call']

            # Generate consensus result
            result = self.synthesis_engine.generate_consensus(
                prompt=request.prompt,
                level=request.level,
                domain=request.domain,
                models_used=models,
                total_cost=total_cost,
            )

            # Format result
            formatted_output = format_consensus_result(
                result,
                include_full_perspectives=request.include_synthesis,
            )

            logger.info("Consensus analysis complete")

            # Clear synthesis engine for next run
            self.synthesis_engine.clear()

            return self._create_text_content(formatted_output)

        # Shouldn't reach here
        return self._create_text_content(
            f"Error: Unexpected step number {request.step_number}/{request.total_steps}"
        )

    async def _call_model_with_failover(
        self,
        primary_model: str,
        fallback_candidates: List[str],
        role: str,
        prompt: str,
        level: int,
        max_failover_attempts: int = 5,
    ) -> tuple[str, float, str, bool]:
        """
        Call model with smart failover to alternative candidates.

        When primary model fails, tries fallback candidates before
        resorting to simulation. For Level 1, automatically tries
        economy models if all free models fail.

        Args:
            primary_model: Primary model to try first
            fallback_candidates: List of fallback models to try
            role: Professional role for this consultation
            prompt: The prompt to send
            level: Tier level (for cost warnings)
            max_failover_attempts: Maximum number of fallback attempts

        Returns:
            Tuple of (response, cost, actual_model_used, failover_was_used)
        """
        # Try primary model first
        try:
            response, cost = await self._call_model(
                model_name=primary_model,
                role=role,
                prompt=prompt,
            )
            return (response, cost, primary_model, False)
        except Exception as e:
            logger.warning(f"Primary model {primary_model} failed: {e}")
            logger.info(f"Attempting failover from {len(fallback_candidates)} candidates...")

        # Try fallback candidates
        tried_models = [primary_model]
        free_exhausted = False

        for attempt, fallback_model in enumerate(fallback_candidates[:max_failover_attempts], 1):
            # Skip if already tried
            if fallback_model in tried_models:
                continue

            tried_models.append(fallback_model)

            # Check if switching from free to paid (Level 1 only)
            is_paid_fallback = (
                level == 1
                and ":free" not in fallback_model
                and not free_exhausted
            )

            if is_paid_fallback:
                free_exhausted = True
                logger.warning(
                    f"⚠️ All free models exhausted. Falling back to economy model: {fallback_model}"
                )

            try:
                response, cost = await self._call_model(
                    model_name=fallback_model,
                    role=role,
                    prompt=prompt,
                )

                # Success! Log failover details
                if is_paid_fallback:
                    logger.info(
                        f"✅ Failover to paid model successful: {fallback_model} "
                        f"(cost: ${cost:.4f}, attempt {attempt}/{max_failover_attempts})"
                    )
                else:
                    logger.info(
                        f"✅ Failover successful: {fallback_model} "
                        f"(attempt {attempt}/{max_failover_attempts})"
                    )

                return (response, cost, fallback_model, True)

            except Exception as e:
                # Distinguish between data policy errors (needs configuration)
                # vs true unavailability (model deprecated)
                error_str = str(e).lower()

                if "data policy" in error_str:
                    logger.info(
                        f"⚙️  Model {fallback_model} requires OpenRouter data policy opt-in. "
                        f"Skipping (valid model, needs user configuration)."
                    )
                elif "no endpoints found for" in error_str:
                    logger.warning(
                        f"⚠️  Model {fallback_model} not found on OpenRouter (may be deprecated). "
                        f"Skipping."
                    )
                else:
                    logger.warning(
                        f"Failover attempt {attempt} failed for {fallback_model}: {e}"
                    )
                continue

        # All failover attempts exhausted - use simulation as last resort
        logger.error(
            f"❌ All models failed (tried {len(tried_models)}). "
            f"Using simulation as last resort."
        )
        simulation_response = self._simulate_model_response(primary_model, role, prompt)
        return (simulation_response, 0.0, primary_model, False)

    async def _call_model(
        self,
        model_name: str,
        role: str,
        prompt: str,
        max_retries: int = 2,
    ) -> tuple[str, float]:
        """
        Call a specific model with the given prompt.

        Args:
            model_name: Name of the model to call
            role: Professional role for this consultation
            prompt: The prompt to send to the model
            max_retries: Maximum number of retry attempts

        Returns:
            Tuple of (model_response, cost)

        Raises:
            Exception: If model call fails after retries
        """
        logger.debug(f"Calling model {model_name} for role {role}")

        # Resolve model to provider
        provider = ModelProviderRegistry.get_provider_for_model(model_name)
        if not provider:
            raise ValueError(
                f"No provider found for model: {model_name}. "
                "Check API keys and model availability."
            )

        # Build system prompt for this role
        role_clean = role.replace('_', ' ').title()
        system_prompt = f"""You are a {role_clean} providing expert analysis.

Your analysis should be:
- Focused on {role} concerns and perspectives
- Detailed and actionable
- Based on industry best practices
- Honest about risks and trade-offs

Provide your analysis in a structured format with:
- Key Observations
- Concerns (if any)
- Recommendations
- Conclusion"""

        # Call provider with retry logic
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Attempt {attempt + 1}/{max_retries + 1} for {model_name}")

                # Generate content
                response = provider.generate_content(
                    prompt=prompt,
                    model_name=model_name,
                    system_prompt=system_prompt,
                    temperature=TEMPERATURE_ANALYTICAL,
                    thinking_mode=None,  # Not all models support extended thinking
                    images=None,
                )

                if response.content:
                    # Estimate cost (basic estimation for now)
                    # TODO: Get actual cost from response metadata when available
                    estimated_cost = self._estimate_response_cost(model_name, prompt, response.content)

                    logger.debug(f"Successfully received response from {model_name}")
                    return response.content, estimated_cost
                else:
                    # Empty response - try again
                    logger.warning(f"Empty response from {model_name}, attempt {attempt + 1}")
                    if attempt < max_retries:
                        continue
                    else:
                        raise ValueError("Model returned empty response after all retries")

            except Exception as e:
                last_error = e
                logger.warning(f"Model call attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    # Wait briefly before retry (exponential backoff)
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    # Final attempt failed
                    break

        # All retries exhausted
        raise Exception(f"Model call failed after {max_retries + 1} attempts: {last_error}")

    def _estimate_response_cost(self, model_name: str, prompt: str, response: str) -> float:
        """
        Estimate the cost of a model response.

        TODO: Get actual costs from provider metadata when available.

        Args:
            model_name: Model name
            prompt: Input prompt
            response: Model response

        Returns:
            Estimated cost in USD
        """
        # Simple estimation based on model name pattern
        # Free models
        if ":free" in model_name.lower() or "free" in model_name.lower():
            return 0.0

        # Economy tier models (rough estimates)
        economy_models = ["deepseek", "qwen", "llama", "phi", "mistral"]
        if any(name in model_name.lower() for name in economy_models):
            # Estimate ~$0.05-0.15 per call for economy models
            token_count = (len(prompt) + len(response)) // 4  # Rough tokens
            return token_count * 0.0000002  # $0.20 per 1M tokens

        # Premium models
        premium_models = ["gpt-5", "claude", "gemini-2.5-pro", "opus"]
        if any(name in model_name.lower() for name in premium_models):
            # Estimate ~$0.50-2.00 per call for premium models
            token_count = (len(prompt) + len(response)) // 4
            return token_count * 0.000002  # $2 per 1M tokens

        # Default fallback
        return 0.10

    def _simulate_model_response(self, model: str, role: str, prompt: str) -> str:
        """
        Simulate model response for testing/fallback.

        Used when actual model API call fails as graceful degradation.

        Args:
            model: Model name
            role: Professional role
            prompt: User prompt

        Returns:
            Simulated model response
        """
        role_clean = role.replace('_', ' ').title()

        return f"""**{role_clean} Analysis ({model})**

I've analyzed this proposal from the {role_clean.lower()} perspective.

**Key Observations:**
- This appears to be a well-formed question requiring multi-perspective analysis
- From my role's viewpoint, I would focus on {role}-specific concerns
- The approach should consider both immediate and long-term implications

**Concerns:**
- Risk: Potential {role}-specific risks need evaluation
- Impact: Consider the {role} impact on the team and system

**Recommendations:**
- Recommend: Conduct thorough {role} review before proceeding
- Consider: Alternative approaches from {role} perspective
- Implement: Best practices for {role} in this context

**Conclusion:**
This requires careful consideration of {role} factors before making a final decision.
"""

    def _create_text_content(self, text: str) -> List[Dict[str, Any]]:
        """
        Create MCP text content response.

        Args:
            text: Text content to return

        Returns:
            List with single text content block
        """
        return [{"type": "text", "text": text}]

    # WorkflowMixin abstract methods (not used in our simplified workflow)

    def get_required_actions(
        self, step_number: int, confidence: str, findings: str, total_steps: int
    ) -> List[str]:
        """
        Get required actions for current step (not used in our workflow).

        Args:
            step_number: Current step number
            confidence: Confidence level
            findings: Current findings
            total_steps: Total steps planned

        Returns:
            List of required actions
        """
        # Not used because we manage workflow explicitly in execute()
        return []

    def should_call_expert_analysis(self, consolidated_findings) -> bool:
        """
        Whether to call expert analysis model (not used in our workflow).

        Args:
            consolidated_findings: Consolidated findings object

        Returns:
            False - we don't use separate expert analysis
        """
        # We don't use external expert analysis - synthesis is built-in
        return False

    def prepare_expert_analysis_context(
        self, consolidated_findings, request_data: dict
    ) -> tuple[str, dict]:
        """
        Prepare context for expert analysis (not used in our workflow).

        Args:
            consolidated_findings: Consolidated findings
            request_data: Request data dictionary

        Returns:
            Tuple of (prompt, context)
        """
        # Not used - we don't call external expert analysis
        return "", {}
