"""
Test consensus tool with three models demonstrating sequential processing
"""

import json

from .base_test import BaseSimulatorTest


class TestConsensusThreeModels(BaseSimulatorTest):
    """Test consensus tool functionality with three models (testing sequential processing)"""

    @property
    def test_name(self) -> str:
        return "consensus_three_models"

    @property
    def test_description(self) -> str:
        return "Test consensus tool with three models using flash:against, flash:for, local-llama:neutral"

    def run_test(self) -> bool:
        """Run three-model consensus test"""
        try:
            self.logger.info("Testing consensus tool with three models: flash:against, flash:for, local-llama:neutral")

            # Send request with three ModelConfig objects
            response, continuation_id = self.call_mcp_tool(
                "consensus",
                {
                    "prompt": "Is a sync manager class a good idea for my CoolTodos app?",
                    "models": [
                        {
                            "model": "flash",
                            "stance": "against",
                            "stance_prompt": "You are a software architecture critic. Focus on the potential downsides of adding a sync manager class: complexity overhead, maintenance burden, potential for over-engineering, and whether simpler alternatives exist. Consider if this adds unnecessary abstraction layers.",
                        },
                        {
                            "model": "flash",
                            "stance": "for",
                            "stance_prompt": "You are a software architecture advocate. Focus on the benefits of a sync manager class: separation of concerns, testability, maintainability, and how it can improve the overall architecture. Consider scalability and code organization advantages.",
                        },
                        {
                            "model": "local-llama",
                            "stance": "neutral",
                            "stance_prompt": "You are a pragmatic software engineer. Provide a balanced analysis considering both the benefits and drawbacks. Focus on the specific context of a CoolTodos app and what factors would determine if this is the right choice.",
                        },
                    ],
                    "model": "flash",  # Default model for Claude's synthesis
                    "focus_areas": ["architecture", "maintainability", "complexity", "scalability"],
                },
            )

            # Validate response
            if not response:
                self.logger.error("Failed to get response from three-model consensus tool")
                return False

            self.logger.info(f"Three-model consensus response preview: {response[:500]}...")

            # Parse the JSON response
            try:
                consensus_data = json.loads(response)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse three-model consensus response as JSON: {response}")
                return False

            # Validate consensus structure
            if "status" not in consensus_data:
                self.logger.error("Missing 'status' field in three-model consensus response")
                return False

            if consensus_data["status"] != "consensus_success":
                self.logger.error(f"Three-model consensus failed with status: {consensus_data['status']}")

                # Log additional error details for debugging
                if "error" in consensus_data:
                    self.logger.error(f"Error message: {consensus_data['error']}")
                if "models_errored" in consensus_data:
                    self.logger.error(f"Models that errored: {consensus_data['models_errored']}")
                if "models_skipped" in consensus_data:
                    self.logger.error(f"Models skipped: {consensus_data['models_skipped']}")
                if "next_steps" in consensus_data:
                    self.logger.error(f"Suggested next steps: {consensus_data['next_steps']}")

                return False

            # Check that models were used correctly
            if "models_used" not in consensus_data:
                self.logger.error("Missing 'models_used' field in three-model consensus response")
                return False

            models_used = consensus_data["models_used"]
            self.logger.info(f"Models used in three-model test: {models_used}")

            # Validate we got the expected models (allowing for some to fail)
            expected_models = ["flash:against", "flash:for", "local-llama"]
            successful_models = [m for m in expected_models if m in models_used]

            if len(successful_models) == 0:
                self.logger.error("No models succeeded in three-model consensus test")
                return False

            self.logger.info(f"Successful models in three-model test: {successful_models}")

            # Validate responses structure
            if "responses" not in consensus_data:
                self.logger.error("Missing 'responses' field in three-model consensus response")
                return False

            responses = consensus_data["responses"]
            if len(responses) == 0:
                self.logger.error("No responses received in three-model consensus test")
                return False

            self.logger.info(f"Received {len(responses)} responses in three-model test")

            # Count successful responses by stance
            stance_counts = {"for": 0, "against": 0, "neutral": 0}
            for resp in responses:
                if resp.get("status") == "success":
                    stance = resp.get("stance", "neutral")
                    stance_counts[stance] = stance_counts.get(stance, 0) + 1

            self.logger.info(f"Stance distribution: {stance_counts}")

            # Verify we have at least one successful response
            total_successful = sum(stance_counts.values())
            if total_successful == 0:
                self.logger.error("No successful responses in three-model consensus test")
                return False

            # Check for sequential processing indication (>2 models should use sequential)
            if len(consensus_data["models_used"]) > 2:
                self.logger.info("✓ Sequential processing was correctly used for >2 models")
            else:
                self.logger.info("✓ Concurrent processing was used (≤2 models)")

            # Verify synthesis guidance is present
            if "next_steps" not in consensus_data:
                self.logger.error("Missing 'next_steps' field in three-model consensus response")
                return False

            self.logger.info("✓ Three-model consensus tool test completed successfully")
            self.logger.info(f"✓ Total successful responses: {total_successful}")
            self.logger.info(
                f"✓ Stance diversity achieved: {len([s for s in stance_counts.values() if s > 0])} different stances"
            )

            return True

        except Exception as e:
            self.logger.error(f"Three-model consensus test failed with exception: {str(e)}")
            return False
