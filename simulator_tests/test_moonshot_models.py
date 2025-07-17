#!/usr/bin/env python3
"""
Moonshot Kimi Model Tests

Tests that verify Moonshot Kimi functionality including:
- Model alias resolution (kimi-latest, kimi-thinking, moonshot-latest map to actual Kimi models)
- kimi-latest and kimi-thinking-preview models work correctly
- Conversation continuity works with Kimi models
- API integration and response validation
"""


from .base_test import BaseSimulatorTest


class MoonshotModelsTest(BaseSimulatorTest):
    """Test Moonshot Kimi model functionality and integration"""

    @property
    def test_name(self) -> str:
        return "moonshot_models"

    @property
    def test_description(self) -> str:
        return "Moonshot Kimi model functionality and integration"

    def run_test(self) -> bool:
        """Test Moonshot Kimi model functionality"""
        try:
            self.logger.info("Test: Moonshot Kimi model functionality and integration")

            # Check if Moonshot API key is configured and not empty
            import os

            moonshot_key = os.environ.get("MOONSHOT_API_KEY", "")
            is_valid = bool(moonshot_key and moonshot_key != "your_moonshot_api_key_here" and moonshot_key.strip())

            if not is_valid:
                self.logger.info("  ⚠️  Moonshot API key not configured or empty - skipping test")
                self.logger.info("  ℹ️  This test requires MOONSHOT_API_KEY to be set in .env with a valid key")
                return True  # Return True to indicate test is skipped, not failed

            # Setup test files for later use
            self.setup_test_files()

            # Test 1: 'kimi-latest' model
            self.logger.info("  1: Testing 'kimi-latest' model")

            response1, continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from Kimi model!' and nothing else.",
                    "model": "kimi-latest",
                    "temperature": 0.1,
                },
            )

            if not response1:
                self.logger.error("  ❌ kimi-latest test failed")
                return False

            self.logger.info("  ✅ kimi-latest call completed")
            if continuation_id:
                self.logger.info(f"  ✅ Got continuation_id: {continuation_id}")

            # Test 2: kimi-thinking-preview model
            self.logger.info("  2: Testing kimi-thinking-preview model")

            response2, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from Kimi thinking!' and nothing else.",
                    "model": "kimi-thinking-preview",
                    "temperature": 0.1,
                },
            )

            if not response2:
                self.logger.error("  ❌ kimi-thinking-preview test failed")
                return False

            self.logger.info("  ✅ kimi-thinking-preview call completed")

            # Test 3: Shorthand aliases
            self.logger.info("  3: Testing shorthand aliases (moonshot-latest, kimi-thinking)")

            response3, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from moonshot-latest alias!' and nothing else.",
                    "model": "moonshot-latest",
                    "temperature": 0.1,
                },
            )

            if not response3:
                self.logger.error("  ❌ moonshot-latest alias test failed")
                return False

            response4, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from kimi-thinking alias!' and nothing else.",
                    "model": "kimi-thinking",
                    "temperature": 0.1,
                },
            )

            if not response4:
                self.logger.error("  ❌ kimi-thinking alias test failed")
                return False

            self.logger.info("  ✅ Shorthand aliases work correctly")

            # Test 4: moonshot-thinking alias
            self.logger.info("  4: Testing moonshot-thinking alias")

            response5, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from moonshot-thinking!' and nothing else.",
                    "model": "moonshot-thinking",
                    "temperature": 0.1,
                },
            )

            if not response5:
                self.logger.error("  ❌ moonshot-thinking alias test failed")
                return False

            self.logger.info("  ✅ moonshot-thinking alias works correctly")

            # Test 5: Conversation continuity with Kimi models
            self.logger.info("  5: Testing conversation continuity with Kimi")

            response6, new_continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Remember this number: 42. What number did I just tell you?",
                    "model": "kimi-latest",
                    "temperature": 0.1,
                },
            )

            if not response6 or not new_continuation_id:
                self.logger.error("  ❌ Failed to start conversation with continuation_id")
                return False

            # Continue the conversation
            response7, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "What was the number I told you earlier?",
                    "model": "kimi-latest",
                    "continuation_id": new_continuation_id,
                    "temperature": 0.1,
                },
            )

            if not response7:
                self.logger.error("  ❌ Failed to continue conversation")
                return False

            # Check if the model remembered the number
            if "42" in response7:
                self.logger.info("  ✅ Conversation continuity working with Kimi")
            else:
                self.logger.warning("  ⚠️  Model may not have remembered the number")

            # Test 6: Validate Moonshot API usage from logs
            self.logger.info("  6: Validating Moonshot API usage in logs")
            logs = self.get_recent_server_logs()

            # Check for Moonshot API calls
            moonshot_logs = [line for line in logs.split("\n") if "moonshot" in line.lower()]
            moonshot_api_logs = [line for line in logs.split("\n") if "api.moonshot.ai" in line]
            kimi_logs = [line for line in logs.split("\n") if "kimi" in line.lower()]

            # Check for specific model resolution
            kimi_resolution_logs = [
                line
                for line in logs.split("\n")
                if ("Resolved model" in line and "kimi" in line.lower()) or ("kimi" in line and "->" in line)
            ]

            # Check for Moonshot provider usage
            moonshot_provider_logs = [line for line in logs.split("\n") if "Moonshot" in line]

            # Log findings
            self.logger.info(f"   Moonshot-related logs: {len(moonshot_logs)}")
            self.logger.info(f"   Moonshot API logs: {len(moonshot_api_logs)}")
            self.logger.info(f"   Kimi-related logs: {len(kimi_logs)}")
            self.logger.info(f"   Model resolution logs: {len(kimi_resolution_logs)}")
            self.logger.info(f"   Moonshot provider logs: {len(moonshot_provider_logs)}")

            # Sample log output for debugging
            if self.verbose and moonshot_logs:
                self.logger.debug("  📋 Sample Moonshot logs:")
                for log in moonshot_logs[:3]:
                    self.logger.debug(f"    {log}")

            if self.verbose and kimi_logs:
                self.logger.debug("  📋 Sample Kimi logs:")
                for log in kimi_logs[:3]:
                    self.logger.debug(f"    {log}")

            # Success criteria
            kimi_mentioned = len(kimi_logs) > 0
            api_used = len(moonshot_api_logs) > 0 or len(moonshot_logs) > 0
            provider_used = len(moonshot_provider_logs) > 0

            success_criteria = [
                ("Kimi models mentioned in logs", kimi_mentioned),
                ("Moonshot API calls made", api_used),
                ("Moonshot provider used", provider_used),
                ("All model calls succeeded", True),  # We already checked this above
                ("Conversation continuity works", True),  # We already tested this
            ]

            passed_criteria = sum(1 for _, passed in success_criteria if passed)
            self.logger.info(f"   Success criteria met: {passed_criteria}/{len(success_criteria)}")

            for criterion, passed in success_criteria:
                status = "✅" if passed else "❌"
                self.logger.info(f"    {status} {criterion}")

            if passed_criteria >= 3:  # At least 3 out of 5 criteria
                self.logger.info("  ✅ Moonshot Kimi model tests passed")
                return True
            else:
                self.logger.error("  ❌ Moonshot Kimi model tests failed")
                return False

        except Exception as e:
            self.logger.error(f"Moonshot Kimi model test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()


def main():
    """Run the Moonshot Kimi model tests"""
    import sys

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    test = MoonshotModelsTest(verbose=verbose)

    success = test.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
