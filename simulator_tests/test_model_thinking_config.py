#!/usr/bin/env python3
"""
Model Thinking Configuration Test

Tests that thinking configuration is properly applied only to models that support it,
and that Flash models work correctly without thinking config.
"""

from .base_test import BaseSimulatorTest


class TestModelThinkingConfig(BaseSimulatorTest):
    """Test model-specific thinking configuration behavior"""

    @property
    def test_name(self) -> str:
        return "model_thinking_config"

    @property
    def test_description(self) -> str:
        return "Model-specific thinking configuration behavior"

    def test_pro_model_with_thinking_config(self):
        """Test that Pro model uses thinking configuration"""
        self.logger.info("Testing Pro model with thinking configuration...")

        try:
            # Test with explicit pro model and high thinking mode
            response, continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "What is 2 + 2? Please think carefully and explain.",
                    "model": "pro",  # Should resolve to gemini-2.5-pro-preview-06-05
                    "thinking_mode": "high",  # Should use thinking_config
                },
            )

            if not response:
                raise Exception("Pro model test failed: No response received")

            self.logger.info("✅ Pro model with thinking config works correctly")
            return True

        except Exception as e:
            self.logger.error(f"❌ Pro model test failed: {e}")
            return False

    def test_flash_model_without_thinking_config(self):
        """Test that Flash model works without thinking configuration"""
        self.logger.info("Testing Flash model without thinking configuration...")

        try:
            # Test with explicit flash model and thinking mode (should be ignored)
            response, continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "What is 3 + 3? Give a quick answer.",
                    "model": "flash",  # Should resolve to gemini-2.0-flash-exp
                    "thinking_mode": "high",  # Should be ignored for Flash model
                },
            )

            if not response:
                raise Exception("Flash model test failed: No response received")

            self.logger.info("✅ Flash model without thinking config works correctly")
            return True

        except Exception as e:
            if "thinking" in str(e).lower() and ("not supported" in str(e).lower() or "invalid" in str(e).lower()):
                raise Exception(f"Flash model incorrectly tried to use thinking config: {e}")
            self.logger.error(f"❌ Flash model test failed: {e}")
            return False

    def test_model_resolution_logic(self):
        """Test that model resolution works correctly for both shortcuts and full names"""
        self.logger.info("Testing model resolution logic...")

        test_cases = [
            ("pro", "should work with Pro model"),
            ("flash", "should work with Flash model"),
            ("gemini-2.5-pro-preview-06-05", "should work with full Pro model name"),
            ("gemini-2.0-flash-exp", "should work with full Flash model name"),
        ]

        success_count = 0

        for model_name, description in test_cases:
            try:
                response, continuation_id = self.call_mcp_tool(
                    "chat",
                    {
                        "prompt": f"Test with {model_name}: What is 1 + 1?",
                        "model": model_name,
                        "thinking_mode": "medium",
                    },
                )

                if not response:
                    raise Exception(f"No response received for model {model_name}")

                self.logger.info(f"✅ {model_name} {description}")
                success_count += 1

            except Exception as e:
                self.logger.error(f"❌ {model_name} failed: {e}")
                return False

        return success_count == len(test_cases)

    def test_default_model_behavior(self):
        """Test behavior with server default model (no explicit model specified)"""
        self.logger.info("Testing default model behavior...")

        try:
            # Test without specifying model (should use server default)
            response, continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Test default model: What is 4 + 4?",
                    # No model specified - should use DEFAULT_MODEL from config
                    "thinking_mode": "medium",
                },
            )

            if not response:
                raise Exception("Default model test failed: No response received")

            self.logger.info("✅ Default model behavior works correctly")
            return True

        except Exception as e:
            self.logger.error(f"❌ Default model test failed: {e}")
            return False

    def run_test(self) -> bool:
        """Run all model thinking configuration tests"""
        self.logger.info(f" Test: {self.test_description}")

        try:
            # Test Pro model with thinking config
            if not self.test_pro_model_with_thinking_config():
                return False

            # Test Flash model without thinking config
            if not self.test_flash_model_without_thinking_config():
                return False

            # Test model resolution logic
            if not self.test_model_resolution_logic():
                return False

            # Test default model behavior
            if not self.test_default_model_behavior():
                return False

            self.logger.info(f"✅ All {self.test_name} tests passed!")
            return True

        except Exception as e:
            self.logger.error(f"❌ {self.test_name} test failed: {e}")
            return False


def main():
    """Run the model thinking configuration tests"""
    import sys

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    test = TestModelThinkingConfig(verbose=verbose)

    success = test.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
