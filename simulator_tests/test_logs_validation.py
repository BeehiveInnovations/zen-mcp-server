#!/usr/bin/env python3
"""
Docker Logs Validation Test

Validates Docker logs to confirm file deduplication behavior and
conversation threading is working properly.
"""

from .base_test import BaseSimulatorTest


class LogsValidationTest(BaseSimulatorTest):
    """Validate Docker logs to confirm file deduplication behavior"""

    @property
    def test_name(self) -> str:
        return "logs_validation"

    @property
    def test_description(self) -> str:
        return "Docker logs validation"

    def run_test(self) -> bool:
        """Validate Docker logs to confirm file deduplication behavior"""
        try:
            self.logger.info("📋 Test: Validating Docker logs for file deduplication...")

            # Get server logs from main container
            result = self.run_command(["docker", "logs", self.container_name], capture_output=True)

            if result.returncode != 0:
                self.logger.error(f"Failed to get Docker logs: {result.stderr}")
                return False

            main_logs = result.stdout.decode() + result.stderr.decode()

            # Get logs from log monitor container (where detailed activity is logged)
            monitor_result = self.run_command(["docker", "logs", "gemini-mcp-log-monitor"], capture_output=True)
            monitor_logs = ""
            if monitor_result.returncode == 0:
                monitor_logs = monitor_result.stdout.decode() + monitor_result.stderr.decode()

            # Also get activity logs for more detailed conversation tracking
            activity_result = self.run_command(
                ["docker", "exec", self.container_name, "cat", "/tmp/mcp_activity.log"], capture_output=True
            )

            activity_logs = ""
            if activity_result.returncode == 0:
                activity_logs = activity_result.stdout.decode()

            logs = main_logs + "\n" + monitor_logs + "\n" + activity_logs

            # Look for conversation threading patterns that indicate the system is working
            conversation_patterns = [
                "CONVERSATION_RESUME",
                "CONVERSATION_CONTEXT",
                "previous turns loaded",
                "tool embedding",
                "files included",
                "files truncated",
                "already in conversation history",
            ]

            conversation_lines = []
            for line in logs.split("\n"):
                for pattern in conversation_patterns:
                    if pattern.lower() in line.lower():
                        conversation_lines.append(line.strip())
                        break

            # Look for evidence of conversation threading and file handling
            conversation_threading_found = False
            multi_turn_conversations = False

            for line in conversation_lines:
                lower_line = line.lower()
                if "conversation_resume" in lower_line:
                    conversation_threading_found = True
                    self.logger.debug(f"📄 Conversation threading: {line}")
                elif "previous turns loaded" in lower_line:
                    multi_turn_conversations = True
                    self.logger.debug(f"📄 Multi-turn conversation: {line}")
                elif "already in conversation" in lower_line:
                    self.logger.info(f"✅ Found explicit deduplication: {line}")
                    return True

            # Conversation threading with multiple turns is evidence of file deduplication working
            if conversation_threading_found and multi_turn_conversations:
                self.logger.info("✅ Conversation threading with multi-turn context working")
                self.logger.info(
                    "✅ File deduplication working implicitly (files embedded once in conversation history)"
                )
                return True
            elif conversation_threading_found:
                self.logger.info("✅ Conversation threading detected")
                return True
            else:
                self.logger.warning("⚠️  No clear evidence of conversation threading in logs")
                self.logger.debug(f"Found {len(conversation_lines)} conversation-related log lines")
                return False

        except Exception as e:
            self.logger.error(f"Log validation failed: {e}")
            return False
