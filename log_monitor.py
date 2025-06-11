#!/usr/bin/env python3
"""
Log monitor for MCP server - monitors and displays tool activity
"""

import os
import time
from datetime import datetime
from pathlib import Path


def monitor_mcp_activity():
    """Monitor MCP server activity by watching the log file"""
    log_file = "/tmp/mcp_server.log"
    activity_file = "/tmp/mcp_activity.log"
    debug_file = "/tmp/gemini_debug.log"

    print(f"[{datetime.now().strftime('%H:%M:%S')}] MCP Log Monitor started")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring: {log_file}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Activity file: {activity_file}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Debug file: {debug_file}")
    print("-" * 60)

    # Track file positions
    log_pos = 0
    activity_pos = 0
    debug_pos = 0

    # Ensure files exist
    Path(log_file).touch()
    Path(activity_file).touch()
    Path(debug_file).touch()

    while True:
        try:
            # Check activity file (most important for tool calls)
            if os.path.exists(activity_file):
                with open(activity_file) as f:
                    f.seek(activity_pos)
                    new_lines = f.readlines()
                    activity_pos = f.tell()

                    for line in new_lines:
                        line = line.strip()
                        if line:
                            if "TOOL_CALL:" in line:
                                tool_info = line.split("TOOL_CALL:")[-1].strip()
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Tool called: {tool_info}")
                            elif "TOOL_COMPLETED:" in line:
                                tool_name = line.split("TOOL_COMPLETED:")[-1].strip()
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Tool completed: {tool_name}")
                            elif "CONVERSATION_RESUME:" in line:
                                resume_info = line.split("CONVERSATION_RESUME:")[-1].strip()
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Resume: {resume_info}")
                            elif "CONVERSATION_CONTEXT:" in line:
                                context_info = line.split("CONVERSATION_CONTEXT:")[-1].strip()
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Context: {context_info}")
                            elif "CONVERSATION_ERROR:" in line:
                                error_info = line.split("CONVERSATION_ERROR:")[-1].strip()
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Conversation error: {error_info}")

            # Check main log file for errors and warnings
            if os.path.exists(log_file):
                with open(log_file) as f:
                    f.seek(log_pos)
                    new_lines = f.readlines()
                    log_pos = f.tell()

                    for line in new_lines:
                        line = line.strip()
                        if line:
                            if "ERROR" in line:
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {line}")
                            elif "WARNING" in line:
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  {line}")
                            elif "Gemini API" in line and ("Sending" in line or "Received" in line):
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] API: {line}")

            # Check debug file
            if os.path.exists(debug_file):
                with open(debug_file) as f:
                    f.seek(debug_pos)
                    new_lines = f.readlines()
                    debug_pos = f.tell()

                    for line in new_lines:
                        line = line.strip()
                        if line:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] DEBUG: {line}")

            time.sleep(0.5)  # Check every 500ms

        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Log monitor stopped")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitor error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    monitor_mcp_activity()
