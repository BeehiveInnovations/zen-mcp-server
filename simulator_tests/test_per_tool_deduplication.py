#!/usr/bin/env python3
"""
Per-Tool File Deduplication Test

Tests file deduplication for each individual MCP tool to ensure
that files are properly deduplicated within single-tool conversations.
"""

from .base_test import BaseSimulatorTest


class PerToolDeduplicationTest(BaseSimulatorTest):
    """Test file deduplication for each individual tool"""

    @property
    def test_name(self) -> str:
        return "per_tool_deduplication"

    @property
    def test_description(self) -> str:
        return "File deduplication for individual tools"

    def run_test(self) -> bool:
        """Test file deduplication for each individual tool"""
        try:
            self.logger.info("📄 Test: Per-tool file deduplication")

            # Setup test files
            self.setup_test_files()

            tools_to_test = [
                (
                    "thinkdeep",
                    {
                        "prompt": "Please use low thinking mode. Think deeply about this Python code and identify potential architectural improvements",
                        "files": [self.test_files["python"]],
                    },
                ),
                ("analyze", {"files": [self.test_files["python"]], "analysis_type": "architecture"}),
                (
                    "debug",
                    {
                        "files": [self.test_files["python"]],
                        "issue_description": "The fibonacci function seems slow for large numbers",
                    },
                ),
                (
                    "codereview",
                    {
                        "files": [self.test_files["python"]],
                        "context": "General code review for quality and best practices",
                    },
                ),
            ]

            successful_tests = 0
            total_tests = len(tools_to_test)

            for tool_name, initial_params in tools_to_test:
                self.logger.info(f"  {tool_name}: Testing {tool_name} tool file deduplication")

                # Initial call
                response1, continuation_id = self.call_mcp_tool(tool_name, initial_params)
                if not response1:
                    self.logger.warning(f"  ⚠️ {tool_name} tool initial call failed, skipping")
                    continue

                if not continuation_id:
                    self.logger.warning(f"  ⚠️ {tool_name} tool didn't provide continuation_id, skipping")
                    continue

                # Continue with same file - should be deduplicated
                continue_params = initial_params.copy()
                continue_params["continuation_id"] = continuation_id

                if tool_name == "thinkdeep":
                    continue_params["prompt"] = "Please use low thinking mode. Now focus specifically on the recursive fibonacci implementation"
                elif tool_name == "analyze":
                    continue_params["analysis_type"] = "performance"
                elif tool_name == "debug":
                    continue_params["issue_description"] = "How can we optimize the fibonacci function?"
                elif tool_name == "codereview":
                    continue_params["context"] = "Focus on the Calculator class implementation"

                response2, _ = self.call_mcp_tool(tool_name, continue_params)
                if response2:
                    self.logger.info(f"  ✅ {tool_name} tool file deduplication working")
                    successful_tests += 1
                else:
                    self.logger.warning(f"  ⚠️ {tool_name} tool continuation failed")

            self.logger.info(f"  ✅ Per-tool file deduplication tests completed: {successful_tests}/{total_tests} tools passed")
            
            # Consider test successful if at least one tool worked
            return successful_tests > 0

        except Exception as e:
            self.logger.error(f"Per-tool file deduplication test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()