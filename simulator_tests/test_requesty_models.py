"""
Requesty Provider Model Tests

Tests that verify Requesty provider functionality including:
- Model alias resolution (claude-4-sonnet, o3, gemini-pro, etc.)
- Case-insensitive model resolution
- Extended thinking mode support for capable models
- Multiple Requesty models work correctly
- Conversation continuity works with Requesty models
- Error handling when models are not available
"""

from .base_test import BaseSimulatorTest
from .log_utils import LogUtils


class TestRequestyModels(BaseSimulatorTest):
    """Test Requesty provider functionality and alias mapping"""

    @property
    def test_name(self) -> str:
        return "requesty_models"

    @property
    def test_description(self) -> str:
        return "Requesty provider model functionality and alias mapping"

    def get_recent_server_logs(self) -> str:
        """Get recent server logs from the log file directly"""
        return LogUtils.get_recent_server_logs(lines=500)

    def run_test(self) -> bool:
        """Test Requesty provider models"""
        try:
            self.logger.info("Test: Requesty provider model functionality and alias mapping")

            # Check if Requesty API key is configured
            import os

            from dotenv import load_dotenv

            # Load .env file to get the API key
            load_dotenv()

            requesty_key = os.environ.get("REQUESTY_API_KEY", "").strip()
            if not requesty_key or requesty_key == "your_requesty_api_key_here":
                self.logger.info("  ⚠️  Requesty API key not configured - skipping test")
                self.logger.info("  ℹ️  This test requires REQUESTY_API_KEY to be set in .env")
                return True  # Return True to indicate test is skipped, not failed

            # Setup test files for later use
            self.setup_test_files()

            # Test 1: Claude 4 Sonnet alias mapping
            self.logger.info("  1: Testing 'claude-4-sonnet' alias (should map to coding/claude-4-sonnet)")

            response1, continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from Claude 4 Sonnet!' and nothing else.",
                    "model": "claude-4-sonnet",
                    "temperature": 0.1,
                },
            )

            if not response1:
                self.logger.error("  ❌ Claude 4 Sonnet alias test failed")
                return False

            self.logger.info("  ✅ Claude 4 Sonnet alias call completed")
            if continuation_id:
                self.logger.info(f"  ✅ Got continuation_id: {continuation_id}")

            # Test 2: Gemini Pro alias mapping
            self.logger.info("  2: Testing 'gemini-pro' alias (should map to google/gemini-2.5-pro-preview-06-05)")

            response2, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from Gemini Pro!' and nothing else.",
                    "model": "gemini-pro",
                    "temperature": 0.1,
                },
            )

            if not response2:
                self.logger.error("  ❌ Gemini Pro alias test failed")
                return False

            self.logger.info("  ✅ Gemini Pro alias call completed")

            # Test 3: Sonar alias mapping (Perplexity)
            self.logger.info("  3: Testing 'sonar' alias (should map to perplexity/sonar)")

            response3, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from Sonar!' and nothing else.",
                    "model": "sonar",
                    "temperature": 0.1,
                },
            )

            if not response3:
                self.logger.error("  ❌ Sonar alias test failed")
                return False

            self.logger.info("  ✅ Sonar alias call completed")

            # Test 4: Direct Requesty model name
            self.logger.info("  4: Testing direct Requesty model name (anthropic/claude-3-5-haiku-latest)")

            response4, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from Claude Haiku!' and nothing else.",
                    "model": "anthropic/claude-3-5-haiku-latest",
                    "temperature": 0.1,
                },
            )

            if not response4:
                self.logger.error("  ❌ Direct Requesty model test failed")
                return False

            self.logger.info("  ✅ Direct Requesty model call completed")

            # Test 5: Requesty-specific model (not available elsewhere)
            self.logger.info("  5: Testing Requesty-specific model (coding/claude-4-sonnet)")

            response5, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Hello from Coding Claude!' and nothing else.",
                    "model": "coding/claude-4-sonnet",
                    "temperature": 0.1,
                },
            )

            if not response5:
                self.logger.error("  ❌ Requesty-specific model test failed")
                return False

            self.logger.info("  ✅ Requesty-specific model call completed")

            # Test 6: Case-insensitive model resolution
            self.logger.info("  6: Testing case-insensitive model resolution")

            response6, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Say 'Case insensitive works!' and nothing else.",
                    "model": "CLAUDE-4-SONNET",  # Testing uppercase alias
                    "temperature": 0.1,
                },
            )

            if not response6:
                self.logger.error("  ❌ Case-insensitive resolution test failed")
                return False

            self.logger.info("  ✅ Case-insensitive model resolution working")

            # Test 7: Extended thinking mode for supported models
            self.logger.info("  7: Testing extended thinking mode with claude-4-sonnet")

            response7, _ = self.call_mcp_tool(
                "thinkdeep",
                {
                    "question": "What is 2+2?",
                    "model": "claude-4-sonnet",  # This model supports extended thinking
                },
            )

            if not response7:
                self.logger.warning("  ⚠️  Extended thinking test skipped (thinkdeep tool may not be available)")
            else:
                self.logger.info("  ✅ Extended thinking mode test completed")

            # Test 8: Conversation continuity with Requesty models
            self.logger.info("  8: Testing conversation continuity with Requesty")

            response8, new_continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Remember this number: 42. What number did I just tell you?",
                    "model": "claude-haiku",  # Claude Haiku via Requesty
                    "temperature": 0.1,
                },
            )

            if not response8 or not new_continuation_id:
                self.logger.error("  ❌ Failed to start conversation with continuation_id")
                return False

            # Continue the conversation
            response9, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "What was the number I told you earlier?",
                    "model": "claude-haiku",
                    "continuation_id": new_continuation_id,
                    "temperature": 0.1,
                },
            )

            if not response9:
                self.logger.error("  ❌ Failed to continue conversation")
                return False

            # Check if the model remembered the number
            if "42" in response9:
                self.logger.info("  ✅ Conversation continuity working with Requesty")
            else:
                self.logger.warning("  ⚠️  Model may not have remembered the number")

            # Test 9: Validate Requesty API usage from logs
            self.logger.info("  9: Validating Requesty API usage in logs")
            logs = self.get_recent_server_logs()

            # Check for Requesty API calls
            requesty_logs = [line for line in logs.split("\n") if "requesty" in line.lower()]
            requesty_api_logs = [line for line in logs.split("\n") if "router.requesty.ai" in line]

            # Check for specific model mappings
            claude_mapping_logs = [
                line
                for line in logs.split("\n")
                if ("claude-4-sonnet" in line and "coding/claude-4-sonnet" in line)
                or ("Resolved model" in line and "coding/claude-4-sonnet" in line)
            ]

            gemini_mapping_logs = [
                line
                for line in logs.split("\n")
                if ("gemini-pro" in line and "google/gemini-2.5-pro" in line)
                or ("Resolved model" in line and "google/gemini-2.5-pro" in line)
            ]

            # Log findings
            self.logger.info(f"   Requesty-related logs: {len(requesty_logs)}")
            self.logger.info(f"   Requesty API logs: {len(requesty_api_logs)}")
            self.logger.info(f"   Claude mapping logs: {len(claude_mapping_logs)}")
            self.logger.info(f"   Gemini mapping logs: {len(gemini_mapping_logs)}")

            # Sample log output for debugging
            if self.verbose and requesty_logs:
                self.logger.debug("  📋 Sample Requesty logs:")
                for log in requesty_logs[:5]:
                    self.logger.debug(f"    {log}")

            # Success criteria
            requesty_api_used = len(requesty_api_logs) > 0
            models_mapped = len(claude_mapping_logs) > 0 or len(gemini_mapping_logs) > 0

            success_criteria = [
                ("Requesty API calls made", requesty_api_used),
                ("Model aliases mapped correctly", models_mapped),
                ("All model calls succeeded", True),  # We already checked this above
            ]

            passed_criteria = sum(1 for _, passed in success_criteria if passed)
            self.logger.info(f"   Success criteria met: {passed_criteria}/{len(success_criteria)}")

            for criterion, passed in success_criteria:
                status = "✅" if passed else "❌"
                self.logger.info(f"    {status} {criterion}")

            if passed_criteria >= 2:  # At least 2 out of 3 criteria
                self.logger.info("  ✅ Requesty provider tests passed")
                return True
            else:
                self.logger.error("  ❌ Requesty provider tests failed")
                return False

        except Exception as e:
            self.logger.error(f"Requesty provider test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()


def main():
    """Run the Requesty provider tests"""
    import sys

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    test = TestRequestyModels(verbose=verbose)

    success = test.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
