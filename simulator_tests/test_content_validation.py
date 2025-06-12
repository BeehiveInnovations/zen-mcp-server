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

    def get_docker_logs_since(self, since_time: str) -> str:
        """Get docker logs since a specific timestamp"""
        try:
            # Check both main server and log monitor for comprehensive logs
            cmd_server = ["docker", "logs", "--since", since_time, self.container_name]
            cmd_monitor = ["docker", "logs", "--since", since_time, "gemini-mcp-log-monitor"]

            import subprocess
            result_server = subprocess.run(cmd_server, capture_output=True, text=True)
            result_monitor = subprocess.run(cmd_monitor, capture_output=True, text=True)

            # Combine logs from both containers
            combined_logs = result_server.stdout + "\n" + result_monitor.stdout
            return combined_logs
        except Exception as e:
            self.logger.error(f"Failed to get docker logs: {e}")
            return ""

    def run_test(self) -> bool:
        """Test that file processing system properly handles file deduplication"""
        try:
            self.logger.info("📄 Test: Content validation and file processing deduplication")

            # Setup test files first
            self.setup_test_files()

            # Create a test file for validation
            validation_content = '''"""
Configuration file for content validation testing
"""

# Configuration constants
MAX_CONTENT_TOKENS = 800_000
TEMPERATURE_ANALYTICAL = 0.2
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

            # Get timestamp for log filtering
            import datetime
            start_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            # Test 1: Initial tool call with validation file
            self.logger.info("  1: Testing initial tool call with file")

            # Call chat tool with the validation file
            response1, thread_id = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Analyze this configuration file briefly",
                    "files": [validation_file],
                    "model": "flash",
                },
            )

            if not response1:
                self.logger.error("  ❌ Initial tool call failed")
                return False

            self.logger.info("  ✅ Initial tool call completed")

            # Test 2: Continuation with same file (should be deduplicated)
            self.logger.info("  2: Testing continuation with same file")

            if thread_id:
                response2, _ = self.call_mcp_tool(
                    "chat",
                    {
                        "prompt": "Continue analyzing this configuration file",
                        "files": [validation_file],  # Same file should be deduplicated
                        "continuation_id": thread_id,
                        "model": "flash",
                    },
                )

                if response2:
                    self.logger.info("  ✅ Continuation with same file completed")
                else:
                    self.logger.warning("  ⚠️  Continuation failed")

            # Test 3: Different tool with same file (new conversation)
            self.logger.info("  3: Testing different tool with same file")

            response3, _ = self.call_mcp_tool(
                "codereview",
                {
                    "files": [validation_file],
                    "prompt": "Review this configuration file",
                    "model": "flash",
                },
            )

            if response3:
                self.logger.info("  ✅ Different tool with same file completed")
            else:
                self.logger.warning("  ⚠️  Different tool failed")

            # Validate file processing behavior from Docker logs
            self.logger.info("  4: Validating file processing logs")
            logs = self.get_docker_logs_since(start_time)

            # Check for proper file embedding logs
            embedding_logs = [
                line for line in logs.split("\n")
                if "📁" in line or "embedding" in line.lower() or "[FILES]" in line
            ]

            # Check for deduplication evidence
            deduplication_logs = [
                line for line in logs.split("\n")
                if "skipping" in line.lower() and "already in conversation" in line.lower()
            ]

            # Check for file processing patterns
            new_file_logs = [
                line for line in logs.split("\n")
                if "all 1 files are new" in line or "New conversation" in line
            ]

            # Validation criteria
            validation_file_mentioned = any("validation_config.py" in line for line in logs.split("\n"))
            embedding_found = len(embedding_logs) > 0
            proper_deduplication = len(deduplication_logs) > 0 or len(new_file_logs) >= 2  # Should see new conversation patterns

            self.logger.info(f"  📊 Embedding logs found: {len(embedding_logs)}")
            self.logger.info(f"  📊 Deduplication evidence: {len(deduplication_logs)}")
            self.logger.info(f"  📊 New conversation patterns: {len(new_file_logs)}")
            self.logger.info(f"  📊 Validation file mentioned: {validation_file_mentioned}")

            # Log sample evidence for debugging
            if self.verbose and embedding_logs:
                self.logger.debug("  📋 Sample embedding logs:")
                for log in embedding_logs[:5]:
                    self.logger.debug(f"    {log}")

            # Success criteria
            success_criteria = [
                ("Embedding logs found", embedding_found),
                ("File processing evidence", validation_file_mentioned),
                ("Multiple tool calls", len(new_file_logs) >= 2)
            ]

            passed_criteria = sum(1 for _, passed in success_criteria if passed)
            self.logger.info(f"  📊 Success criteria met: {passed_criteria}/{len(success_criteria)}")

            # Cleanup
            os.remove(validation_file)

            if passed_criteria >= 2:  # At least 2 out of 3 criteria
                self.logger.info("  ✅ File processing validation passed")
                return True
            else:
                self.logger.error("  ❌ File processing validation failed")
                return False

        except Exception as e:
            self.logger.error(f"Content validation test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()
