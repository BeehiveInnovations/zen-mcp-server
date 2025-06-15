#!/usr/bin/env python3
"""
Azure OpenAI Model Tests

Tests that verify Azure OpenAI functionality including:
- Model alias resolution (o3, o4-mini, etc. work through Azure)
- Azure-specific deployment name handling
- Conversation continuity with Azure OpenAI models
- Azure endpoint and authentication
"""

from .base_test import BaseSimulatorTest


class AzureOpenAIModelsTest(BaseSimulatorTest):
    """Test Azure OpenAI model functionality"""

    @property
    def test_name(self) -> str:
        return "azure_openai_models"

    @property
    def test_description(self) -> str:
        return "Azure OpenAI model functionality and integration"

    def run_test(self) -> bool:
        """Test Azure OpenAI model functionality"""
        try:
            self.logger.info("Test: Azure OpenAI model functionality")

            # Check if Azure OpenAI API key and endpoint are configured
            azure_key_result = self.check_env_var("AZURE_OPENAI_API_KEY")
            azure_endpoint_result = self.check_env_var("AZURE_OPENAI_ENDPOINT")

            if not azure_key_result or not azure_endpoint_result:
                self.logger.info("  ⚠️  Azure OpenAI not fully configured - skipping test")
                self.logger.info("  ℹ️  This test requires AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")
                return True  # Skip, not fail

            # Test 1: O3 alias mapping
            self.logger.info("  1: Testing 'o3' alias through Azure OpenAI")

            response1, continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from Azure O3 model!' and nothing else.",
                    "model": "o3",
                    "temperature": 0.1,
                },
            )

            if not response1:
                self.logger.error("  ❌ O3 alias test failed")
                return False

            self.logger.info("  ✅ O3 alias call completed")

            # Test 2: O4-mini model
            self.logger.info("  2: Testing 'o4-mini' model through Azure")

            response2, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from Azure O4-mini!' and nothing else.",
                    "model": "o4-mini",
                    "temperature": 0.1,
                },
            )

            if not response2:
                self.logger.error("  ❌ O4-mini test failed")
                return False

            self.logger.info("  ✅ O4-mini call completed")

            # Test 3: Conversation continuity
            self.logger.info("  3: Testing conversation continuity with Azure OpenAI")

            response3, new_continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Remember this number: 42. What number did I just tell you?",
                    "model": "o4-mini",
                    "temperature": 0.1,
                },
            )

            if not response3 or not new_continuation_id:
                self.logger.error("  ❌ Failed to start conversation")
                return False

            # Continue conversation
            response4, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "What was the number I told you earlier?",
                    "model": "o4-mini",
                    "continuation_id": new_continuation_id,
                    "temperature": 0.1,
                },
            )

            if not response4:
                self.logger.error("  ❌ Failed to continue conversation")
                return False

            if "42" in response4:
                self.logger.info("  ✅ Conversation continuity working")
            else:
                self.logger.warning("  ⚠️  Model may not have remembered the number")

            # Test 4: Check logs for Azure provider usage
            self.logger.info("  4: Validating Azure OpenAI provider usage in logs")
            logs = self.get_recent_server_logs()

            # Look for evidence of Azure OpenAI provider usage
            azure_logs = [line for line in logs.split("\\n") if "azure" in line.lower()]
            deployment_logs = [
                line for line in logs.split("\\n") if "deployment" in line.lower() or "azure" in line.lower()
            ]

            self.logger.info(f"   Azure-related logs: {len(azure_logs)}")
            self.logger.info(f"   Deployment-related logs: {len(deployment_logs)}")

            # Success criteria
            azure_provider_used = len(azure_logs) > 0

            if azure_provider_used:
                self.logger.info("  ✅ Azure OpenAI provider tests passed")
                return True
            else:
                self.logger.error("  ❌ No evidence of Azure OpenAI provider usage in logs")
                return False

        except Exception as e:
            self.logger.error(f"Azure OpenAI provider test failed: {e}")
            return False


def main():
    """Run the Azure OpenAI provider tests"""
    import sys

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    test = AzureOpenAIModelsTest(verbose=verbose)

    success = test.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
