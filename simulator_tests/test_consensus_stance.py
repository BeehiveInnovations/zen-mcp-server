"""
Test consensus tool with explicit stance arguments
"""

import json

from .base_test import BaseSimulatorTest


class TestConsensusStance(BaseSimulatorTest):
    """Test consensus tool functionality with stance steering"""

    @property
    def test_name(self) -> str:
        return "consensus_stance"

    @property
    def test_description(self) -> str:
        return "Test consensus tool with stance steering (for/against/neutral)"

    def run_test(self) -> bool:
        """Run consensus stance test"""
        try:
            self.logger.info("Testing consensus tool with ModelConfig objects and custom stance prompts")

            # Send request with full two-model consensus
            response, continuation_id = self.call_mcp_tool(
                "consensus",
                {
                    "prompt": "Add pizza button: good idea?",
                    "models": [
                        {
                            "model": "flash",
                            "stance": "for",
                            "stance_prompt": "Focus on user engagement benefits.",
                        },
                        {
                            "model": "flash",
                            "stance": "against",
                            "stance_prompt": "Focus on technical complexity issues.",
                        },
                    ],
                    "model": "flash",
                },
            )

            # Validate response
            if not response:
                self.logger.error("Failed to get response from consensus tool")
                return False

            self.logger.info(f"Consensus response preview: {response[:500]}...")

            # Parse the JSON response
            try:
                consensus_data = json.loads(response)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse consensus response as JSON: {response}")
                return False

            # Validate consensus structure
            if "status" not in consensus_data:
                self.logger.error("Missing 'status' field in consensus response")
                return False

            if consensus_data["status"] != "consensus_success":
                self.logger.error(f"Consensus failed with status: {consensus_data['status']}")

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

            # Check that both models were used with their stances
            if "models_used" not in consensus_data:
                self.logger.error("Missing 'models_used' field in consensus response")
                return False

            models_used = consensus_data["models_used"]
            if len(models_used) != 2:
                self.logger.error(f"Expected 2 models, got {len(models_used)}")
                return False

            if "flash:for" not in models_used:
                self.logger.error("Missing 'flash:for' in models_used")
                return False

            if "flash:against" not in models_used:
                self.logger.error("Missing 'flash:against' in models_used")
                return False

            # Validate responses structure
            if "responses" not in consensus_data:
                self.logger.error("Missing 'responses' field in consensus response")
                return False

            responses = consensus_data["responses"]
            if len(responses) != 2:
                self.logger.error(f"Expected 2 responses, got {len(responses)}")
                return False

            # Check each response has the correct stance
            for_response = None
            against_response = None

            for resp in responses:
                if "stance" not in resp:
                    self.logger.error("Missing 'stance' field in response")
                    return False

                if resp["stance"] == "for":
                    for_response = resp
                elif resp["stance"] == "against":
                    against_response = resp

            # Verify we got both stances
            if not for_response:
                self.logger.error("Missing 'for' stance response")
                return False

            if not against_response:
                self.logger.error("Missing 'against' stance response")
                return False

            # Check that successful responses have verdicts
            if for_response.get("status") == "success":
                if "verdict" not in for_response:
                    self.logger.error("Missing 'verdict' in for_response")
                    return False
                self.logger.info(f"FOR stance verdict preview: {for_response['verdict'][:200]}...")

            if against_response.get("status") == "success":
                if "verdict" not in against_response:
                    self.logger.error("Missing 'verdict' in against_response")
                    return False
                self.logger.info(f"AGAINST stance verdict preview: {against_response['verdict'][:200]}...")

            # Verify synthesis guidance is present
            if "next_steps" not in consensus_data:
                self.logger.error("Missing 'next_steps' field in consensus response")
                return False

            self.logger.info("✓ Consensus tool successfully processed two-model consensus with stance steering")

            return True

        except Exception as e:
            self.logger.error(f"Test failed with exception: {str(e)}")
            return False
