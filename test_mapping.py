#!/usr/bin/env python3
"""
Test OpenRouter model mapping
"""

import sys

sys.path.append("/Users/fahad/Developer/gemini-mcp-server")

from simulator_tests.base_test import BaseSimulatorTest


class MappingTest(BaseSimulatorTest):
    def test_mapping(self):
        """Test model alias mapping"""

        # Test with 'flash' alias - should map to google/gemini-2.5-flash-preview-05-20
        print("\nTesting 'flash' alias mapping...")

        response, continuation_id = self.call_mcp_tool(
            "chat",
            {
                "prompt": "Say 'Hello from Flash model!'",
                "model": "flash",  # Should be mapped to google/gemini-2.5-flash-preview-05-20
                "temperature": 0.1,
            },
        )

        if response:
            print("✅ Flash alias worked!")
            print(f"Response: {response[:200]}...")
            return True
        else:
            print("❌ Flash alias failed")
            return False


if __name__ == "__main__":
    test = MappingTest(verbose=False)
    success = test.test_mapping()
    print(f"\nTest result: {'Success' if success else 'Failed'}")
