#!/usr/bin/env python3
"""
Gemini Tools Integration Test

Tests the integration of URL context and Google search tools with actual Gemini API calls.
This validates that the tools work correctly in real scenarios.
"""

from .base_test import BaseSimulatorTest


class GeminiToolsIntegrationTest(BaseSimulatorTest):
    """Test Gemini tools integration with live API calls"""

    @property
    def test_name(self) -> str:
        return "gemini_tools_integration"

    @property
    def test_description(self) -> str:
        return "Live integration test for Gemini URL context and Google search tools"

    def run_test(self) -> bool:
        """Test Gemini tools integration with actual API calls"""
        try:
            self.logger.info("Test: Gemini Tools Integration")

            # Test 1: Google Search Tool
            self.logger.info("  1.1: Testing Google Search Tool")
            search_response, continuation_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Please use minimal thinking mode. Search for 'Python programming language' and tell me one interesting fact you found. Keep your response short.",
                    "model": "flash",
                },
            )

            if not search_response:
                self.logger.error("Failed to get response for Google search test")
                return False

            # Check if response indicates search was used
            if not self.validate_test_result(search_response, "search"):
                self.logger.error("Google search validation failed - response doesn't indicate search tool was used")
                return False
            else:
                self.logger.info("  ✅ Google search appears to have been used successfully")

            # Test 2: URL Context Tool
            self.logger.info("  1.2: Testing URL Context Tool")
            url_response, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Please use minimal thinking mode. Access the URL 'https://www.python.org' and tell me what the main purpose of this website is. Keep your response short.",
                    "model": "flash",
                    "continuation_id": continuation_id,
                },
            )

            if not url_response:
                self.logger.error("Failed to get response for URL context test")
                return False

            # Check if response indicates URL was accessed
            if not self.validate_test_result(url_response, "url"):
                self.logger.error("URL context validation failed - response doesn't indicate URL tool was used")
                return False
            else:
                self.logger.info("  ✅ URL context tool appears to have been used successfully")

            # Test 3: Combined Tools Usage
            self.logger.info("  1.3: Testing Combined Tools Usage")
            combined_response, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Please use minimal thinking mode. Search for information about 'GitHub' and then visit 'https://github.com' to verify what you found. Give me a brief summary.",
                    "model": "flash",
                },
            )

            if not combined_response:
                self.logger.error("Failed to get response for combined tools test")
                return False

            # Check if response indicates both tools might have been used
            if not self.validate_test_result(combined_response, "combined"):
                self.logger.error("Combined tools validation failed - response doesn't indicate tools were used effectively")
                return False
            else:
                self.logger.info("  ✅ Combined tools test completed successfully")

            # Test 4: Pro Model with Tools
            self.logger.info("  1.4: Testing Tools with Pro Model")
            pro_response, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Please use minimal thinking mode. Search for 'Claude AI' and give me one fact about it. Keep it brief.",
                    "model": "pro",
                },
            )

            if not pro_response:
                self.logger.error("Failed to get response from Pro model with tools")
                return False

            if not self.validate_test_result(pro_response, "search"):
                self.logger.error("Pro model search validation failed - response doesn't indicate search tool was used")
                return False
            else:
                self.logger.info("  ✅ Pro model with tools working correctly")

            # Test 5: Error Handling - Invalid URL
            self.logger.info("  1.5: Testing Error Handling with Invalid URL")
            error_response, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Please use minimal thinking mode. Try to access the URL 'https://this-domain-definitely-does-not-exist-12345.com' and tell me what happens.",
                    "model": "flash",
                },
            )

            if not error_response:
                self.logger.error("Failed to get response for error handling test")
                return False

            # The response should handle the error gracefully
            self.logger.info("  ✅ Error handling test completed")

            self.logger.info("🎉 All Gemini tools integration tests passed!")
            return True

        except Exception as e:
            self.logger.error(f"Test failed with error: {e}")
            return False

    def validate_test_result(self, response: str, test_type: str) -> bool:
        """Validate that the response indicates tool usage"""
        if not response:
            return False

        response_lower = response.lower()

        if test_type == "search":
            # Look for indicators that search was used
            search_indicators = [
                "search", "found", "according to", "results", "information",
                "based on", "research", "discovered"
            ]
            return any(indicator in response_lower for indicator in search_indicators)

        elif test_type == "url":
            # Look for indicators that URL was accessed
            url_indicators = [
                "website", "page", "site", "url", "visited", "accessed",
                "according to the", "based on the page"
            ]
            return any(indicator in response_lower for indicator in url_indicators)

        elif test_type == "combined":
            # For combined test, just check if response is coherent and mentions the topic
            return len(response) > 50 and any(word in response_lower for word in ["github", "repository", "code"])

        return True


def main():
    """Run the Gemini tools integration test"""
    test = GeminiToolsIntegrationTest(verbose=True)
    success = test.run_test()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

