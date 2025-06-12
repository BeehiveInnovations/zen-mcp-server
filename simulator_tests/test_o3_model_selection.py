#!/usr/bin/env python3
"""
O3 Model Selection Test

Tests that O3 models are properly selected and used when explicitly specified,
regardless of the default model configuration (even when set to auto).
Validates model selection via Docker logs.
"""

import datetime
import subprocess

from .base_test import BaseSimulatorTest


class O3ModelSelectionTest(BaseSimulatorTest):
    """Test O3 model selection and usage"""

    @property
    def test_name(self) -> str:
        return "o3_model_selection"

    @property
    def test_description(self) -> str:
        return "O3 model selection and usage validation"

    def get_recent_server_logs(self) -> str:
        """Get recent server logs from the log file directly"""
        try:
            # Read logs directly from the log file - more reliable than docker logs --since
            cmd = ["docker", "exec", self.container_name, "tail", "-n", "200", "/tmp/mcp_server.log"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout
            else:
                self.logger.warning(f"Failed to read server logs: {result.stderr}")
                return ""
        except Exception as e:
            self.logger.error(f"Failed to get server logs: {e}")
            return ""

    def run_test(self) -> bool:
        """Test O3 model selection and usage"""
        try:
            self.logger.info("🔥 Test: O3 model selection and usage validation")

            # Setup test files for later use
            self.setup_test_files()

            # Get timestamp for log filtering
            start_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            # Test 1: Explicit O3 model selection
            self.logger.info("  1: Testing explicit O3 model selection")

            response1, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Simple test: What is 2 + 2? Just give a brief answer.",
                    "model": "o3",
                    "temperature": 1.0,  # O3 only supports default temperature of 1.0
                },
            )

            if not response1:
                self.logger.error("  ❌ O3 model test failed")
                return False

            self.logger.info("  ✅ O3 model call completed")

            # Test 2: Explicit O3-mini model selection
            self.logger.info("  2: Testing explicit O3-mini model selection")

            response2, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Simple test: What is 3 + 3? Just give a brief answer.",
                    "model": "o3-mini",
                    "temperature": 1.0,  # O3-mini only supports default temperature of 1.0
                },
            )

            if not response2:
                self.logger.error("  ❌ O3-mini model test failed")
                return False

            self.logger.info("  ✅ O3-mini model call completed")

            # Test 3: Another tool with O3 to ensure it works across tools
            self.logger.info("  3: Testing O3 with different tool (codereview)")

            # Create a simple test file
            test_code = """def add(a, b):
    return a + b

def multiply(x, y):
    return x * y
"""
            test_file = self.create_additional_test_file("simple_math.py", test_code)

            response3, _ = self.call_mcp_tool(
                "codereview",
                {
                    "files": [test_file],
                    "prompt": "Quick review of this simple code",
                    "model": "o3",
                    "temperature": 1.0,  # O3 only supports default temperature of 1.0
                },
            )

            if not response3:
                self.logger.error("  ❌ O3 with codereview tool failed")
                return False

            self.logger.info("  ✅ O3 with codereview tool completed")

            # Validate model usage from server logs  
            self.logger.info("  4: Validating model usage in logs")
            logs = self.get_recent_server_logs()

            # Check for OpenAI API calls (this proves O3 models are being used)
            openai_api_logs = [
                line for line in logs.split("\n")
                if "Sending request to openai API" in line
            ]

            # Check for OpenAI HTTP responses (confirms successful O3 calls)
            openai_http_logs = [
                line for line in logs.split("\n")
                if "HTTP Request: POST https://api.openai.com" in line
            ]

            # Check for received responses from OpenAI
            openai_response_logs = [
                line for line in logs.split("\n")
                if "Received response from openai API" in line
            ]

            # Check that we have both chat and codereview tool calls to OpenAI
            chat_openai_logs = [
                line for line in logs.split("\n")
                if "Sending request to openai API for chat" in line
            ]

            codereview_openai_logs = [
                line for line in logs.split("\n")
                if "Sending request to openai API for codereview" in line
            ]

            # Validation criteria - we expect 3 OpenAI calls (2 chat + 1 codereview)
            openai_api_called = len(openai_api_logs) >= 3  # Should see 3 OpenAI API calls
            openai_http_success = len(openai_http_logs) >= 3  # Should see 3 HTTP requests
            openai_responses_received = len(openai_response_logs) >= 3  # Should see 3 responses
            chat_calls_to_openai = len(chat_openai_logs) >= 2  # Should see 2 chat calls (o3 + o3-mini)
            codereview_calls_to_openai = len(codereview_openai_logs) >= 1  # Should see 1 codereview call

            self.logger.info(f"  📊 OpenAI API call logs: {len(openai_api_logs)}")
            self.logger.info(f"  📊 OpenAI HTTP request logs: {len(openai_http_logs)}")
            self.logger.info(f"  📊 OpenAI response logs: {len(openai_response_logs)}")
            self.logger.info(f"  📊 Chat calls to OpenAI: {len(chat_openai_logs)}")
            self.logger.info(f"  📊 Codereview calls to OpenAI: {len(codereview_openai_logs)}")

            # Log sample evidence for debugging
            if self.verbose and openai_api_logs:
                self.logger.debug("  📋 Sample OpenAI API logs:")
                for log in openai_api_logs[:5]:
                    self.logger.debug(f"    {log}")

            if self.verbose and chat_openai_logs:
                self.logger.debug("  📋 Sample chat OpenAI logs:")
                for log in chat_openai_logs[:3]:
                    self.logger.debug(f"    {log}")

            # Success criteria
            success_criteria = [
                ("OpenAI API calls made", openai_api_called),
                ("OpenAI HTTP requests successful", openai_http_success),
                ("OpenAI responses received", openai_responses_received),
                ("Chat tool used OpenAI", chat_calls_to_openai),
                ("Codereview tool used OpenAI", codereview_calls_to_openai)
            ]

            passed_criteria = sum(1 for _, passed in success_criteria if passed)
            self.logger.info(f"  📊 Success criteria met: {passed_criteria}/{len(success_criteria)}")

            for criterion, passed in success_criteria:
                status = "✅" if passed else "❌"
                self.logger.info(f"    {status} {criterion}")

            if passed_criteria >= 3:  # At least 3 out of 4 criteria
                self.logger.info("  ✅ O3 model selection validation passed")
                return True
            else:
                self.logger.error("  ❌ O3 model selection validation failed")
                return False

        except Exception as e:
            self.logger.error(f"O3 model selection test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()


def main():
    """Run the O3 model selection tests"""
    import sys

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    test = O3ModelSelectionTest(verbose=verbose)

    success = test.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()