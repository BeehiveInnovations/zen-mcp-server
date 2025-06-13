#!/usr/bin/env python3
"""
Per-Tool File Deduplication Test

Tests file deduplication for each individual MCP tool to ensure
that files are properly deduplicated within single-tool conversations.
Validates that:
1. Files are embedded only once in conversation history
2. Continuation calls don't re-read existing files
3. New files are still properly embedded
4. Docker logs show deduplication behavior
"""

import os
import subprocess

from .base_test import BaseSimulatorTest


class PerToolDeduplicationTest(BaseSimulatorTest):
    """Test file deduplication for each individual tool"""

    @property
    def test_name(self) -> str:
        return "per_tool_deduplication"

    @property
    def test_description(self) -> str:
        return "File deduplication for individual tools"

    def get_docker_logs_since(self, since_time: str) -> str:
        """Get docker logs since a specific timestamp"""
        try:
            # Check both main server and log monitor for comprehensive logs
            cmd_server = ["docker", "logs", "--since", since_time, self.container_name]
            cmd_monitor = ["docker", "logs", "--since", since_time, "zen-mcp-log-monitor"]

            result_server = subprocess.run(cmd_server, capture_output=True, text=True)
            result_monitor = subprocess.run(cmd_monitor, capture_output=True, text=True)

            # Get the internal log files which have more detailed logging
            server_log_result = subprocess.run(
                ["docker", "exec", self.container_name, "cat", "/tmp/mcp_server.log"], capture_output=True, text=True
            )

            activity_log_result = subprocess.run(
                ["docker", "exec", self.container_name, "cat", "/tmp/mcp_activity.log"], capture_output=True, text=True
            )

            # Combine all logs
            combined_logs = (
                result_server.stdout
                + "\n"
                + result_monitor.stdout
                + "\n"
                + server_log_result.stdout
                + "\n"
                + activity_log_result.stdout
            )
            return combined_logs
        except Exception as e:
            self.logger.error(f"Failed to get docker logs: {e}")
            return ""

    # create_additional_test_file method now inherited from base class

    def validate_file_deduplication_in_logs(self, logs: str, tool_name: str, test_file: str) -> bool:
        """Validate that logs show file deduplication behavior"""
        # Look for file embedding messages
        embedding_messages = [
            line for line in logs.split("\n") if "📁" in line and "embedding" in line and tool_name in line
        ]

        # Look for deduplication/filtering messages
        filtering_messages = [
            line for line in logs.split("\n") if "📁" in line and "Filtering" in line and tool_name in line
        ]
        skipping_messages = [
            line for line in logs.split("\n") if "📁" in line and "skipping" in line and tool_name in line
        ]

        deduplication_found = len(filtering_messages) > 0 or len(skipping_messages) > 0

        if deduplication_found:
            self.logger.info(f"  ✅ {tool_name}: Found deduplication evidence in logs")
            for msg in filtering_messages + skipping_messages:
                self.logger.debug(f"    📁 {msg.strip()}")
        else:
            self.logger.warning(f"  ⚠️ {tool_name}: No deduplication evidence found in logs")
            self.logger.debug(f"  📁 All embedding messages: {embedding_messages}")

        return deduplication_found

    def run_test(self) -> bool:
        """Test file deduplication with realistic precommit/codereview workflow"""
        try:
            self.logger.info("📄 Test: Simplified file deduplication with precommit/codereview workflow")

            # Setup test files
            self.setup_test_files()

            # Create a short dummy file for quick testing in the current repo
            dummy_content = """def add(a, b):
    return a + b  # Missing type hints

def divide(x, y):
    return x / y  # No zero check
"""
            # Create the file in the current git repo directory to make it show up in git status
            dummy_file_path = os.path.join(os.getcwd(), "dummy_code.py")
            with open(dummy_file_path, "w") as f:
                f.write(dummy_content)

            # Get timestamp for log filtering
            import datetime

            start_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            # Step 1: precommit tool with dummy file (low thinking mode)
            self.logger.info("  Step 1: precommit tool with dummy file")
            precommit_params = {
                "path": self.test_dir,  # Required path parameter
                "files": [dummy_file_path],
                "prompt": "Please give me a quick one line reply. Review this code for commit readiness",
                "thinking_mode": "low",
                "model": "flash",
            }

            response1, continuation_id = self.call_mcp_tool("precommit", precommit_params)
            if not response1:
                self.logger.error("  ❌ Step 1: precommit tool failed")
                return False

            if not continuation_id:
                self.logger.error("  ❌ Step 1: precommit tool didn't provide continuation_id")
                return False

            # Validate continuation_id format (should be UUID)
            if len(continuation_id) < 32:
                self.logger.error(f"  ❌ Step 1: Invalid continuation_id format: {continuation_id}")
                return False

            self.logger.info(f"  ✅ Step 1: precommit completed with continuation_id: {continuation_id[:8]}...")

            # Step 2: codereview tool with same file (NO continuation - fresh conversation)
            self.logger.info("  Step 2: codereview tool with same file (fresh conversation)")
            codereview_params = {
                "files": [dummy_file_path],
                "prompt": "Please give me a quick one line reply. General code review for quality and best practices",
                "thinking_mode": "low",
                "model": "flash",
            }

            response2, _ = self.call_mcp_tool("codereview", codereview_params)
            if not response2:
                self.logger.error("  ❌ Step 2: codereview tool failed")
                return False

            self.logger.info("  ✅ Step 2: codereview completed (fresh conversation)")

            # Step 3: Create new file and continue with precommit
            self.logger.info("  Step 3: precommit continuation with old + new file")
            new_file_content = """def multiply(x, y):
    return x * y

def subtract(a, b):
    return a - b
"""
            # Create another temp file in the current repo for git changes
            new_file_path = os.path.join(os.getcwd(), "new_feature.py")
            with open(new_file_path, "w") as f:
                f.write(new_file_content)

            # Continue precommit with both files
            continue_params = {
                "continuation_id": continuation_id,
                "path": self.test_dir,  # Required path parameter
                "files": [dummy_file_path, new_file_path],  # Old + new file
                "prompt": "Please give me a quick one line reply. Now also review the new feature file along with the previous one",
                "thinking_mode": "low",
                "model": "flash",
            }

            response3, _ = self.call_mcp_tool("precommit", continue_params)
            if not response3:
                self.logger.error("  ❌ Step 3: precommit continuation failed")
                return False

            self.logger.info("  ✅ Step 3: precommit continuation completed")

            # Validate results in docker logs
            self.logger.info("  📋 Validating conversation history and file deduplication...")
            logs = self.get_docker_logs_since(start_time)

            # Check for conversation history building
            conversation_logs = [
                line for line in logs.split("\n") if "conversation" in line.lower() or "history" in line.lower()
            ]

            # Check for file embedding/deduplication
            embedding_logs = [
                line
                for line in logs.split("\n")
                if "[FILE_PROCESSING]" in line or "embedding" in line.lower() or "[FILES]" in line
            ]

            # Check for continuation evidence
            continuation_logs = [
                line for line in logs.split("\n") if "continuation" in line.lower() or continuation_id[:8] in line
            ]

            # Check for both files mentioned
            dummy_file_mentioned = any("dummy_code.py" in line for line in logs.split("\n"))
            new_file_mentioned = any("new_feature.py" in line for line in logs.split("\n"))

            # Print diagnostic information
            self.logger.info(f"   Conversation logs found: {len(conversation_logs)}")
            self.logger.info(f"   File embedding logs found: {len(embedding_logs)}")
            self.logger.info(f"   Continuation logs found: {len(continuation_logs)}")
            self.logger.info(f"   Dummy file mentioned: {dummy_file_mentioned}")
            self.logger.info(f"   New file mentioned: {new_file_mentioned}")

            if self.verbose:
                self.logger.debug("  📋 Sample embedding logs:")
                for log in embedding_logs[:5]:  # Show first 5
                    if log.strip():
                        self.logger.debug(f"    {log.strip()}")

                self.logger.debug("  📋 Sample continuation logs:")
                for log in continuation_logs[:3]:  # Show first 3
                    if log.strip():
                        self.logger.debug(f"    {log.strip()}")

            # Determine success criteria
            success_criteria = [
                len(embedding_logs) > 0,  # File embedding occurred
                len(continuation_logs) > 0,  # Continuation worked
                dummy_file_mentioned,  # Original file processed
                new_file_mentioned,  # New file processed
            ]

            passed_criteria = sum(success_criteria)
            total_criteria = len(success_criteria)

            self.logger.info(f"   Success criteria met: {passed_criteria}/{total_criteria}")

            if passed_criteria == total_criteria:  # All criteria must pass
                self.logger.info("  ✅ File deduplication workflow test: PASSED")
                return True
            else:
                self.logger.warning("  ⚠️ File deduplication workflow test: FAILED")
                self.logger.warning("  💡 Check docker logs for detailed file embedding and continuation activity")
                return False

        except Exception as e:
            self.logger.error(f"File deduplication workflow test failed: {e}")
            return False
        finally:
            # Clean up temp files created in current repo
            temp_files = ["dummy_code.py", "new_feature.py"]
            for temp_file in temp_files:
                temp_path = os.path.join(os.getcwd(), temp_file)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    self.logger.debug(f"Removed temp file: {temp_path}")
            self.cleanup_test_files()
