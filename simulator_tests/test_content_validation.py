#!/usr/bin/env python3
"""
Content Validation Test

Tests that tools don't duplicate file content in their responses.
This test is specifically designed to catch content duplication bugs.
"""

import json
import os

from .base_test import BaseSimulatorTest


class ContentValidationTest(BaseSimulatorTest):
    """Test that tools don't duplicate file content in their responses"""

    @property
    def test_name(self) -> str:
        return "content_validation"

    @property
    def test_description(self) -> str:
        return "Content validation and duplicate detection"

    def run_test(self) -> bool:
        """Test that tools don't duplicate file content in their responses"""
        try:
            self.logger.info("📄 Test: Content validation and duplicate detection")

            # Setup test files first
            self.setup_test_files()

            # Create a test file with distinctive content for validation
            validation_content = '''"""
Configuration file for content validation testing
This content should appear only ONCE in any tool response
"""

# Configuration constants
MAX_CONTENT_TOKENS = 800_000  # This line should appear exactly once
TEMPERATURE_ANALYTICAL = 0.2  # This should also appear exactly once
UNIQUE_VALIDATION_MARKER = "CONTENT_VALIDATION_TEST_12345"

# Database settings
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "name": "validation_test_db"
}
'''

            validation_file = os.path.join(self.test_dir, "validation_config.py")
            with open(validation_file, "w") as f:
                f.write(validation_content)
            
            # Ensure absolute path for MCP server compatibility
            validation_file = os.path.abspath(validation_file)

            # Test 1: Precommit tool with files parameter (where the bug occurred)
            self.logger.info("  1: Testing precommit tool content duplication")

            # Call precommit tool with the validation file
            response1, thread_id = self.call_mcp_tool(
                "precommit",
                {
                    "path": os.getcwd(),
                    "files": [validation_file],
                    "original_request": "Test for content duplication in precommit tool",
                },
            )

            if response1:
                # Parse response and check for content duplication
                try:
                    response_data = json.loads(response1)
                    content = response_data.get("content", "")

                    # Count occurrences of distinctive markers
                    max_content_count = content.count("MAX_CONTENT_TOKENS = 800_000")
                    temp_analytical_count = content.count("TEMPERATURE_ANALYTICAL = 0.2")
                    unique_marker_count = content.count("UNIQUE_VALIDATION_MARKER")

                    # Validate no duplication
                    duplication_detected = False
                    issues = []

                    if max_content_count > 1:
                        issues.append(f"MAX_CONTENT_TOKENS appears {max_content_count} times")
                        duplication_detected = True

                    if temp_analytical_count > 1:
                        issues.append(f"TEMPERATURE_ANALYTICAL appears {temp_analytical_count} times")
                        duplication_detected = True

                    if unique_marker_count > 1:
                        issues.append(f"UNIQUE_VALIDATION_MARKER appears {unique_marker_count} times")
                        duplication_detected = True

                    if duplication_detected:
                        self.logger.error(f"  ❌ Content duplication detected in precommit tool: {'; '.join(issues)}")
                        return False
                    else:
                        self.logger.info("  ✅ No content duplication in precommit tool")

                except json.JSONDecodeError:
                    self.logger.warning("  ⚠️  Could not parse precommit response as JSON")

            else:
                self.logger.warning("  ⚠️  Precommit tool failed to respond")

            # Test 2: Other tools that use files parameter
            tools_to_test = [
                (
                    "chat",
                    {"prompt": "Please use low thinking mode. Analyze this config file", "files": [validation_file]},  # Using absolute path
                ),
                (
                    "codereview",
                    {"files": [validation_file], "context": "Please use low thinking mode. Review this configuration"},  # Using absolute path
                ),
                ("analyze", {"files": [validation_file], "analysis_type": "code_quality"}),  # Using absolute path
            ]

            for tool_name, params in tools_to_test:
                self.logger.info(f"  2.{tool_name}: Testing {tool_name} tool content duplication")

                response, _ = self.call_mcp_tool(tool_name, params)
                if response:
                    try:
                        response_data = json.loads(response)
                        content = response_data.get("content", "")

                        # Check for duplication
                        marker_count = content.count("UNIQUE_VALIDATION_MARKER")
                        if marker_count > 1:
                            self.logger.error(
                                f"  ❌ Content duplication in {tool_name}: marker appears {marker_count} times"
                            )
                            return False
                        else:
                            self.logger.info(f"  ✅ No content duplication in {tool_name}")

                    except json.JSONDecodeError:
                        self.logger.warning(f"  ⚠️  Could not parse {tool_name} response")
                else:
                    self.logger.warning(f"  ⚠️  {tool_name} tool failed to respond")

            # Test 3: Cross-tool content validation with file deduplication
            self.logger.info("  3: Testing cross-tool content consistency")

            if thread_id:
                # Continue conversation with same file - content should be deduplicated in conversation history
                response2, _ = self.call_mcp_tool(
                    "chat",
                    {
                        "prompt": "Please use low thinking mode. Continue analyzing this configuration file",
                        "files": [validation_file],  # Same file should be deduplicated
                        "continuation_id": thread_id,
                    },
                )

                if response2:
                    try:
                        response_data = json.loads(response2)
                        content = response_data.get("content", "")

                        # In continuation, the file content shouldn't be duplicated either
                        marker_count = content.count("UNIQUE_VALIDATION_MARKER")
                        if marker_count > 1:
                            self.logger.error(
                                f"  ❌ Content duplication in cross-tool continuation: marker appears {marker_count} times"
                            )
                            return False
                        else:
                            self.logger.info("  ✅ No content duplication in cross-tool continuation")

                    except json.JSONDecodeError:
                        self.logger.warning("  ⚠️  Could not parse continuation response")

            # Cleanup
            os.remove(validation_file)

            self.logger.info("  ✅ All content validation tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Content validation test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()
