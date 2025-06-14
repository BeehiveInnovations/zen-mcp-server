#!/usr/bin/env python3
"""
O3-Pro Expensive Model Test

⚠️  WARNING: This test uses o3-pro which is EXTREMELY EXPENSIVE! ⚠️

This test is intentionally NOT added to TEST_REGISTRY to prevent accidental execution.
It can only be run manually using:
    python communication_simulator_test.py --individual o3_pro_expensive

Tests that o3-pro model works with one simple chat call. That's it.
"""

from .base_test import BaseSimulatorTest


class O3ProExpensiveTest(BaseSimulatorTest):
    """Test o3-pro model basic functionality - EXPENSIVE, manual only"""

    @property
    def test_name(self) -> str:
        return "o3_pro_expensive"

    @property
    def test_description(self) -> str:
        return "⚠️ EXPENSIVE O3-Pro basic validation (manual only)"

    def run_test(self) -> bool:
        """Test o3-pro model with one simple chat call - EXPENSIVE!"""
        try:
            self.logger.warning("⚠️ ⚠️ ⚠️  EXPENSIVE TEST - O3-PRO COSTS ~$15-60 PER 1K TOKENS! ⚠️ ⚠️ ⚠️")
            self.logger.info("Test: O3-Pro basic chat test")

            # One simple chat call
            response, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "What is 2 + 2?",
                    "model": "o3-pro",
                    "temperature": 1.0,
                },
            )

            if response:
                self.logger.info("✅ O3-Pro chat call succeeded")
                self.logger.warning("💰 Test completed - check your billing!")
                return True
            else:
                self.logger.error("❌ O3-Pro chat call failed")
                return False

        except Exception as e:
            self.logger.error(f"O3-Pro test failed: {e}")
            return False


def main():
    """Run the O3-Pro expensive test"""
    import sys

    print("⚠️ ⚠️ ⚠️  WARNING: This test uses O3-PRO which is EXTREMELY EXPENSIVE! ⚠️ ⚠️ ⚠️")
    print("O3-Pro can cost $15-60 per 1K tokens!")
    print("This is a MINIMAL test but may still cost $5-15!")
    print()

    response = input("Are you absolutely sure you want to run this expensive test? Type 'YES_I_UNDERSTAND_THE_COST': ")
    if response != "YES_I_UNDERSTAND_THE_COST":
        print("❌ Test cancelled")
        sys.exit(1)

    print("💰 Running minimal O3-Pro test...")

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    test = O3ProExpensiveTest(verbose=verbose)

    success = test.run_test()

    if success:
        print("✅ O3-Pro test completed successfully")
        print("💰 Don't forget to check your billing!")
    else:
        print("❌ O3-Pro test failed")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
