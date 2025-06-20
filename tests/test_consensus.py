"""
Tests for the Consensus tool
"""

import json
from unittest.mock import patch

import pytest

from tools.consensus import ConsensusTool, ModelConfig


class TestConsensusTool:
    """Test cases for the Consensus tool"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tool = ConsensusTool()

    def test_tool_metadata(self):
        """Test tool metadata is correct"""
        assert self.tool.get_name() == "consensus"
        assert "MULTI-MODEL CONSENSUS" in self.tool.get_description()
        assert self.tool.get_default_temperature() == 0.2

    def test_input_schema(self):
        """Test input schema is properly defined"""
        schema = self.tool.get_input_schema()
        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "models" in schema["properties"]
        assert schema["required"] == ["prompt", "models"]

        # Check that schema includes model configuration information
        models_desc = schema["properties"]["models"]["description"]
        # Check description includes object format
        assert "model configurations" in models_desc
        assert "specific stance and custom instructions" in models_desc
        # Check example shows new format
        assert "'model': 'o3'" in models_desc
        assert "'stance': 'for'" in models_desc
        assert "'stance_prompt'" in models_desc

    def test_normalize_stance_basic(self):
        """Test basic stance normalization"""
        # Test basic stances
        assert self.tool._normalize_stance("for") == "for"
        assert self.tool._normalize_stance("against") == "against"
        assert self.tool._normalize_stance("neutral") == "neutral"
        assert self.tool._normalize_stance(None) == "neutral"

    def test_normalize_stance_synonyms(self):
        """Test stance synonym normalization"""
        # Supportive synonyms
        assert self.tool._normalize_stance("support") == "for"
        assert self.tool._normalize_stance("favor") == "for"

        # Critical synonyms
        assert self.tool._normalize_stance("critical") == "against"
        assert self.tool._normalize_stance("oppose") == "against"

        # Case insensitive
        assert self.tool._normalize_stance("FOR") == "for"
        assert self.tool._normalize_stance("Support") == "for"
        assert self.tool._normalize_stance("AGAINST") == "against"
        assert self.tool._normalize_stance("Critical") == "against"

        # Test unknown stances default to neutral
        assert self.tool._normalize_stance("supportive") == "neutral"
        assert self.tool._normalize_stance("maybe") == "neutral"
        assert self.tool._normalize_stance("contra") == "neutral"
        assert self.tool._normalize_stance("random") == "neutral"

    def test_model_config_validation(self):
        """Test ModelConfig validation"""
        # Valid config
        config = ModelConfig(model="o3", stance="for", stance_prompt="Custom prompt")
        assert config.model == "o3"
        assert config.stance == "for"
        assert config.stance_prompt == "Custom prompt"

        # Default stance
        config = ModelConfig(model="flash")
        assert config.stance == "neutral"
        assert config.stance_prompt is None

        # Test that empty model is handled by validation elsewhere
        # Pydantic allows empty strings by default, but the tool validates it
        config = ModelConfig(model="")
        assert config.model == ""

    def test_validate_model_combinations(self):
        """Test model combination validation with ModelConfig objects"""
        # Valid combinations
        configs = [
            ModelConfig(model="o3", stance="for"),
            ModelConfig(model="pro", stance="against"),
            ModelConfig(model="grok"),  # neutral default
            ModelConfig(model="o3", stance="against"),
        ]
        valid, skipped = self.tool._validate_model_combinations(configs)
        assert len(valid) == 4
        assert len(skipped) == 0

        # Test max instances per combination (2)
        configs = [
            ModelConfig(model="o3", stance="for"),
            ModelConfig(model="o3", stance="for"),
            ModelConfig(model="o3", stance="for"),  # This should be skipped
            ModelConfig(model="pro", stance="against"),
        ]
        valid, skipped = self.tool._validate_model_combinations(configs)
        assert len(valid) == 3
        assert len(skipped) == 1
        assert "max 2 instances" in skipped[0]

        # Test unknown stances get normalized to neutral
        configs = [
            ModelConfig(model="o3", stance="maybe"),  # Unknown stance -> neutral
            ModelConfig(model="pro", stance="kinda"),  # Unknown stance -> neutral
            ModelConfig(model="grok"),  # Already neutral
        ]
        valid, skipped = self.tool._validate_model_combinations(configs)
        assert len(valid) == 3  # All are valid (normalized to neutral)
        assert len(skipped) == 0  # None skipped

        # Verify normalization worked
        assert valid[0].stance == "neutral"  # maybe -> neutral
        assert valid[1].stance == "neutral"  # kinda -> neutral
        assert valid[2].stance == "neutral"  # already neutral

    def test_get_stance_enhanced_prompt(self):
        """Test stance-enhanced prompt generation"""
        # Test that stance prompts are injected correctly
        for_prompt = self.tool._get_stance_enhanced_prompt("for")
        assert "SUPPORTIVE PERSPECTIVE" in for_prompt

        against_prompt = self.tool._get_stance_enhanced_prompt("against")
        assert "CRITICAL PERSPECTIVE" in against_prompt

        neutral_prompt = self.tool._get_stance_enhanced_prompt("neutral")
        assert "BALANCED PERSPECTIVE" in neutral_prompt

        # Test custom stance prompt
        custom_prompt = "Focus on user experience and business value"
        enhanced = self.tool._get_stance_enhanced_prompt("for", custom_prompt)
        assert custom_prompt in enhanced
        assert "SUPPORTIVE PERSPECTIVE" not in enhanced  # Should use custom instead

    def test_format_consensus_output(self):
        """Test consensus output formatting"""
        responses = [
            {"model": "o3", "stance": "for", "status": "success", "verdict": "Good idea"},
            {"model": "pro", "stance": "against", "status": "success", "verdict": "Bad idea"},
            {"model": "grok", "stance": "neutral", "status": "error", "error": "Timeout"},
        ]
        skipped = ["flash:maybe (invalid stance)"]

        output = self.tool._format_consensus_output(responses, skipped)
        output_data = json.loads(output)

        assert output_data["status"] == "consensus_success"
        assert output_data["models_used"] == ["o3:for", "pro:against"]
        assert output_data["models_skipped"] == skipped
        assert output_data["models_errored"] == ["grok"]
        assert "next_steps" in output_data

    @pytest.mark.asyncio
    @patch("tools.consensus.ConsensusTool._get_consensus_responses")
    async def test_execute_with_model_configs(self, mock_get_responses):
        """Test execute with ModelConfig objects"""
        # Mock responses directly at the consensus level
        mock_responses = [
            {
                "model": "o3",
                "stance": "for",  # support normalized to for
                "status": "success",
                "verdict": "This is good for user benefits",
                "metadata": {"provider": "openai", "usage": None, "custom_stance_prompt": True},
            },
            {
                "model": "pro",
                "stance": "against",  # critical normalized to against
                "status": "success",
                "verdict": "There are technical risks to consider",
                "metadata": {"provider": "gemini", "usage": None, "custom_stance_prompt": True},
            },
            {
                "model": "grok",
                "stance": "neutral",
                "status": "success",
                "verdict": "Balanced perspective on the proposal",
                "metadata": {"provider": "xai", "usage": None, "custom_stance_prompt": False},
            },
        ]
        mock_get_responses.return_value = mock_responses

        # Test with ModelConfig objects including custom stance prompts
        models = [
            {"model": "o3", "stance": "support", "stance_prompt": "Focus on user benefits"},  # Test synonym
            {"model": "pro", "stance": "critical", "stance_prompt": "Focus on technical risks"},  # Test synonym
            {"model": "grok", "stance": "neutral"},
        ]

        result = await self.tool.execute({"prompt": "Test prompt", "models": models})

        # Verify the response structure
        response_text = result[0].text
        response_data = json.loads(response_text)
        assert response_data["status"] == "consensus_success"
        assert len(response_data["models_used"]) == 3

        # Verify stance normalization worked in the models_used field
        models_used = response_data["models_used"]
        assert "o3:for" in models_used  # support -> for
        assert "pro:against" in models_used  # critical -> against
        assert "grok" in models_used  # neutral (no stance suffix)


if __name__ == "__main__":
    import unittest

    unittest.main()
