#!/usr/bin/env python3
"""
Log monitor for MCP server - monitors and displays tool activity

This module provides a simplified log monitoring interface using the
centralized LogTailer class from utils.file_utils.
"""

from datetime import datetime

from utils.file_utils import LogTailer


def monitor_mcp_activity():
    """Monitor MCP server activity by watching multiple log files"""
    log_files = {
        "/tmp/mcp_server.log": "main",
        "/tmp/mcp_activity.log": "activity",
        "/tmp/gemini_debug.log": "debug",
        "/tmp/mcp_server_overflow.log": "overflow",
    }

    print(f"[{datetime.now().strftime('%H:%M:%S')}] MCP Log Monitor started")
    for file_path, name in log_files.items():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring {name}: {file_path}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Note: Logs rotate daily at midnight, keeping 7 days of history")
    print("-" * 60)

    # Create tailers for each log file
    tailers = {}

    # Activity log - most important for tool calls
    def activity_filter(line: str) -> bool:
        return any(
            keyword in line
            for keyword in [
                "TOOL_CALL:",
                "TOOL_COMPLETED:",
                "CONVERSATION_RESUME:",
                "CONVERSATION_CONTEXT:",
                "CONVERSATION_ERROR:",
            ]
        )

    def activity_formatter(line: str) -> str:
        if "TOOL_CALL:" in line:
            tool_info = line.split("TOOL_CALL:")[-1].strip()
            return f"Tool called: {tool_info}"
        elif "TOOL_COMPLETED:" in line:
            tool_name = line.split("TOOL_COMPLETED:")[-1].strip()
            return f"✓ Tool completed: {tool_name}"
        elif "CONVERSATION_RESUME:" in line:
            resume_info = line.split("CONVERSATION_RESUME:")[-1].strip()
            return f"Resume: {resume_info}"
        elif "CONVERSATION_CONTEXT:" in line:
            context_info = line.split("CONVERSATION_CONTEXT:")[-1].strip()
            return f"Context: {context_info}"
        elif "CONVERSATION_ERROR:" in line:
            error_info = line.split("CONVERSATION_ERROR:")[-1].strip()
            return f"❌ Conversation error: {error_info}"
        return line

    tailers["activity"] = LogTailer("/tmp/mcp_activity.log")

    # Main log - errors and warnings
    def main_filter(line: str) -> bool:
        return any(keyword in line for keyword in ["ERROR", "WARNING", "DEBUG", "Gemini API"])

    def main_formatter(line: str) -> str:
        if "ERROR" in line:
            return f"❌ {line}"
        elif "WARNING" in line:
            return f"⚠️  {line}"
        elif "DEBUG" in line:
            if "📄" in line or "📁" in line:
                return f"📂 FILE: {line}"
            else:
                return f"🔍 {line}"
        elif "Gemini API" in line and ("Sending" in line or "Received" in line):
            return f"API: {line}"
        elif "INFO" in line and any(keyword in line for keyword in ["Gemini API", "Tool", "Conversation"]):
            return f"ℹ️  {line}"
        return line

    tailers["main"] = LogTailer("/tmp/mcp_server.log")

    # Debug log
    def debug_formatter(line: str) -> str:
        return f"DEBUG: {line}"

    tailers["debug"] = LogTailer("/tmp/gemini_debug.log")

    # Overflow log
    def overflow_filter(line: str) -> bool:
        return "ERROR" in line or "WARNING" in line

    def overflow_formatter(line: str) -> str:
        if "ERROR" in line:
            return f"🚨 OVERFLOW: {line}"
        elif "WARNING" in line:
            return f"⚠️  OVERFLOW: {line}"
        return line

    tailers["overflow"] = LogTailer("/tmp/mcp_server_overflow.log")

    # Monitor all files in a simple loop
    try:
        while True:
            # Check activity log
            activity_lines = tailers["activity"].read_new_lines()
            for line in activity_lines:
                if activity_filter(line):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    formatted = activity_formatter(line)
                    print(f"[{timestamp}] {formatted}")

            # Check main log
            main_lines = tailers["main"].read_new_lines()
            for line in main_lines:
                if main_filter(line):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    formatted = main_formatter(line)
                    print(f"[{timestamp}] {formatted}")

            # Check debug log
            debug_lines = tailers["debug"].read_new_lines()
            for line in debug_lines:
                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted = debug_formatter(line)
                print(f"[{timestamp}] {formatted}")

            # Check overflow log
            overflow_lines = tailers["overflow"].read_new_lines()
            for line in overflow_lines:
                if overflow_filter(line):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    formatted = overflow_formatter(line)
                    print(f"[{timestamp}] {formatted}")

            # Wait before next check
            import time

            time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Log monitor stopped")


if __name__ == "__main__":
    monitor_mcp_activity()
