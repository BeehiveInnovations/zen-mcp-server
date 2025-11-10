"""
Integration tests for tiered_consensus tool.

Tests the full consensus workflow including:
- Multi-step workflow orchestration
- Model selection via TierManager
- Role assignment via RoleAssigner
- Perspective aggregation via SynthesisEngine
- Final consensus generation

NOTE: Currently uses simulated model responses.
      Phase 2 will replace with real API calls.
"""

import pytest
from typing import Dict, Any, List

from tools.custom.tiered_consensus import TieredConsensusTool, TieredConsensusRequest


class TestTieredConsensusWorkflow:
    """Test the complete consensus workflow."""

    @pytest.fixture
    def tool(self):
        """Create a tiered_consensus tool instance."""
        return TieredConsensusTool()

    @pytest.fixture
    def sample_prompt(self):
        """Sample consensus prompt."""
        return "Should we migrate from PostgreSQL to MongoDB for our e-commerce platform?"

    # === Level 1: Foundation Tier (3 free models) ===

    @pytest.mark.asyncio
    async def test_level_1_foundation_tier(self, tool, sample_prompt):
        """Test Level 1 consensus with 3 free models."""
        # Step 1: Initial setup
        request = TieredConsensusRequest(
            prompt=sample_prompt,
            level=1,
            domain="code_review",
            step=sample_prompt,
            step_number=1,
            total_steps=5,  # 1 setup + 3 models + 1 synthesis
            next_step_required=True,
            findings="Initial consensus request",
        )

        result = await tool.execute(request)

        # Verify setup response
        assert len(result) > 0
        assert any("Configuration" in str(r) for r in result)
        assert any("Level: 1" in str(r) for r in result)
        assert any("Foundation" in str(r) for r in result)

    @pytest.mark.asyncio
    async def test_level_1_model_consultations(self, tool, sample_prompt):
        """Test Level 1 model consultation steps."""
        # Simulate steps 2-4 (3 model consultations)
        for step_num in range(2, 5):
            request = TieredConsensusRequest(
                prompt=sample_prompt,
                level=1,
                domain="code_review",
                step=f"Step {step_num} consultation",
                step_number=step_num,
                total_steps=5,
                next_step_required=(step_num < 4),
                findings=f"Consulting model {step_num - 1}",
            )

            result = await tool.execute(request)

            # Verify model consultation response
            assert len(result) > 0
            assert any(f"Step {step_num}" in str(r) for r in result)

    @pytest.mark.asyncio
    async def test_level_1_synthesis(self, tool, sample_prompt):
        """Test Level 1 final synthesis."""
        # First run setup and consultations
        for step_num in range(1, 5):
            request = TieredConsensusRequest(
                prompt=sample_prompt,
                level=1,
                domain="code_review",
                step=sample_prompt if step_num == 1 else f"Step {step_num}",
                step_number=step_num,
                total_steps=5,
                next_step_required=(step_num < 4),
                findings=f"Step {step_num} findings",
            )
            await tool.execute(request)

        # Final synthesis step
        synthesis_request = TieredConsensusRequest(
            prompt=sample_prompt,
            level=1,
            domain="code_review",
            step="Generate synthesis",
            step_number=5,
            total_steps=5,
            next_step_required=False,
            findings="All perspectives collected",
        )

        result = await tool.execute(synthesis_request)

        # Verify synthesis contains expected sections
        result_text = str(result)
        assert "Consensus Analysis" in result_text or "synthesis" in result_text.lower()

    # === Level 2: Professional Tier (6 models) ===

    @pytest.mark.asyncio
    async def test_level_2_professional_tier(self, tool, sample_prompt):
        """Test Level 2 consensus with 6 models (additive)."""
        # Step 1: Initial setup
        request = TieredConsensusRequest(
            prompt=sample_prompt,
            level=2,
            domain="architecture",
            step=sample_prompt,
            step_number=1,
            total_steps=8,  # 1 setup + 6 models + 1 synthesis
            next_step_required=True,
            findings="Level 2 consensus request",
        )

        result = await tool.execute(request)

        # Verify setup includes Level 2 details
        result_text = str(result)
        assert "Level: 2" in result_text
        assert "Professional" in result_text
        assert "6" in result_text  # Should mention 6 models

    @pytest.mark.asyncio
    async def test_level_2_additive_architecture(self, tool, sample_prompt):
        """Verify Level 2 includes Level 1's models (additive)."""
        # Get models for Level 1 and Level 2
        level1_models = tool.tier_manager.get_tier_models(1)
        level2_models = tool.tier_manager.get_tier_models(2)

        # Level 2 should include all of Level 1's models
        assert len(level2_models) == 6
        assert len(level1_models) == 3

        # First 3 models of Level 2 should match Level 1
        for i, model in enumerate(level1_models):
            assert level2_models[i] == model, \
                f"Level 2 model {i} ({level2_models[i]}) != Level 1 model {i} ({model})"

    # === Level 3: Executive Tier (8 models) ===

    @pytest.mark.asyncio
    async def test_level_3_executive_tier(self, tool, sample_prompt):
        """Test Level 3 consensus with 8 models (additive)."""
        request = TieredConsensusRequest(
            prompt=sample_prompt,
            level=3,
            domain="security",
            step=sample_prompt,
            step_number=1,
            total_steps=10,  # 1 setup + 8 models + 1 synthesis
            next_step_required=True,
            findings="Level 3 consensus request",
        )

        result = await tool.execute(request)

        result_text = str(result)
        assert "Level: 3" in result_text
        assert "Executive" in result_text
        assert "8" in result_text  # Should mention 8 models

    @pytest.mark.asyncio
    async def test_level_3_additive_architecture(self, tool, sample_prompt):
        """Verify Level 3 includes Level 2's models (additive)."""
        level2_models = tool.tier_manager.get_tier_models(2)
        level3_models = tool.tier_manager.get_tier_models(3)

        # Level 3 should include all of Level 2's models
        assert len(level3_models) == 8
        assert len(level2_models) == 6

        # First 6 models of Level 3 should match Level 2
        for i, model in enumerate(level2_models):
            assert level3_models[i] == model, \
                f"Level 3 model {i} ({level3_models[i]}) != Level 2 model {i} ({model})"


class TestDomainSpecificRoles:
    """Test domain-specific role assignments."""

    @pytest.fixture
    def tool(self):
        return TieredConsensusTool()

    def test_code_review_domain_roles(self, tool):
        """Test code_review domain assigns correct roles."""
        roles = tool.role_assigner.get_roles_for_level(1, "code_review")

        # Level 1 should have core code review roles
        assert "code_reviewer" in roles
        assert "security_checker" in roles
        assert "technical_validator" in roles

    def test_security_domain_roles(self, tool):
        """Test security domain assigns security-focused roles."""
        roles = tool.role_assigner.get_roles_for_level(1, "security")

        # Security domain should have security-specific roles
        assert any("security" in role for role in roles)

    def test_architecture_domain_roles(self, tool):
        """Test architecture domain assigns architecture-focused roles."""
        roles = tool.role_assigner.get_roles_for_level(2, "architecture")

        # Architecture domain should include architect roles
        assert any("architect" in role for role in roles)

    def test_general_domain_roles(self, tool):
        """Test general domain assigns balanced roles."""
        roles = tool.role_assigner.get_roles_for_level(1, "general")

        # General domain should have diverse roles
        assert len(roles) >= 3


class TestCostEstimation:
    """Test cost estimation and tracking."""

    @pytest.fixture
    def tool(self):
        return TieredConsensusTool()

    def test_level_1_cost_estimation(self, tool):
        """Test Level 1 cost estimation (should be $0)."""
        costs = tool.tier_manager.get_tier_costs(1)

        assert costs['estimated_cost_per_call'] == 0.0
        assert costs['cost_tier'] == 'free'

    def test_level_2_cost_estimation(self, tool):
        """Test Level 2 cost estimation (~$0.50)."""
        costs = tool.tier_manager.get_tier_costs(2)

        # Level 2 includes economy models
        assert 0.30 <= costs['estimated_cost_per_call'] <= 0.70
        assert costs['cost_tier'] == 'economy'

    def test_level_3_cost_estimation(self, tool):
        """Test Level 3 cost estimation (~$5.00)."""
        costs = tool.tier_manager.get_tier_costs(3)

        # Level 3 includes premium models
        assert 3.0 <= costs['estimated_cost_per_call'] <= 7.0
        assert costs['cost_tier'] == 'premium'


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def tool(self):
        return TieredConsensusTool()

    def test_invalid_level_rejected(self, tool):
        """Test invalid level values are rejected."""
        with pytest.raises(Exception):  # Pydantic validation error
            TieredConsensusRequest(
                prompt="Test",
                level=0,  # Invalid: must be 1-3
                domain="code_review",
                step="Test",
                step_number=1,
                total_steps=1,
                next_step_required=False,
                findings="Test",
            )

        with pytest.raises(Exception):
            TieredConsensusRequest(
                prompt="Test",
                level=4,  # Invalid: must be 1-3
                domain="code_review",
                step="Test",
                step_number=1,
                total_steps=1,
                next_step_required=False,
                findings="Test",
            )

    def test_invalid_domain_rejected(self, tool):
        """Test invalid domain values are rejected."""
        with pytest.raises(ValueError, match="Invalid domain"):
            TieredConsensusRequest(
                prompt="Test",
                level=1,
                domain="invalid_domain",  # Invalid domain
                step="Test",
                step_number=1,
                total_steps=1,
                next_step_required=False,
                findings="Test",
            )

    def test_missing_prompt_rejected(self, tool):
        """Test missing required prompt field."""
        with pytest.raises(Exception):  # Pydantic validation error
            TieredConsensusRequest(
                level=1,
                domain="code_review",
                step="Test",
                step_number=1,
                total_steps=1,
                next_step_required=False,
                findings="Test",
                # Missing prompt - required field
            )


class TestWorkflowProgression:
    """Test workflow step progression."""

    @pytest.fixture
    def tool(self):
        return TieredConsensusTool()

    @pytest.mark.asyncio
    async def test_workflow_step_sequence(self, tool):
        """Test proper workflow step progression."""
        prompt = "Test consensus question"
        total_steps = 5  # Level 1: setup + 3 models + synthesis

        for step_num in range(1, total_steps + 1):
            request = TieredConsensusRequest(
                prompt=prompt,
                level=1,
                domain="code_review",
                step=prompt if step_num == 1 else f"Step {step_num}",
                step_number=step_num,
                total_steps=total_steps,
                next_step_required=(step_num < total_steps),
                findings=f"Step {step_num} findings",
            )

            result = await tool.execute(request)

            # Each step should return content
            assert len(result) > 0
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_synthesis_requires_all_perspectives(self, tool):
        """Test synthesis step has access to all collected perspectives."""
        prompt = "Test consensus"

        # Collect perspectives (steps 1-4)
        for step_num in range(1, 5):
            request = TieredConsensusRequest(
                prompt=prompt,
                level=1,
                domain="code_review",
                step=prompt if step_num == 1 else f"Step {step_num}",
                step_number=step_num,
                total_steps=5,
                next_step_required=(step_num < 4),
                findings=f"Step {step_num} findings",
            )
            await tool.execute(request)

        # Verify synthesis engine has perspectives
        assert len(tool.synthesis_engine.perspectives) == 3  # 3 model consultations


class TestOptionalParameters:
    """Test optional parameters."""

    @pytest.fixture
    def tool(self):
        return TieredConsensusTool()

    @pytest.mark.asyncio
    async def test_include_synthesis_parameter(self, tool):
        """Test include_synthesis parameter."""
        request = TieredConsensusRequest(
            prompt="Test",
            level=1,
            domain="code_review",
            include_synthesis=False,  # Disable detailed synthesis
            step="Test",
            step_number=1,
            total_steps=1,
            next_step_required=False,
            findings="Test",
        )

        # Should still execute without errors
        result = await tool.execute(request)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_max_cost_parameter(self, tool):
        """Test max_cost override parameter."""
        request = TieredConsensusRequest(
            prompt="Test",
            level=3,  # Normally expensive
            domain="code_review",
            max_cost=1.0,  # Override cost limit
            step="Test",
            step_number=1,
            total_steps=1,
            next_step_required=False,
            findings="Test",
        )

        # Should execute with cost override
        result = await tool.execute(request)
        assert len(result) > 0


# === Test Utilities ===

class TestToolMetadata:
    """Test tool metadata and discovery."""

    def test_tool_name(self):
        """Test tool has correct name."""
        tool = TieredConsensusTool()
        assert tool.get_name() == "tiered_consensus"

    def test_tool_description(self):
        """Test tool has descriptive text."""
        tool = TieredConsensusTool()
        description = tool.get_description()

        assert len(description) > 0
        assert "consensus" in description.lower()
        assert "multi-model" in description.lower()

    def test_tool_requires_no_single_model(self):
        """Test tool doesn't require single model parameter."""
        tool = TieredConsensusTool()
        # Consensus uses multiple models internally
        assert tool.requires_model() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
