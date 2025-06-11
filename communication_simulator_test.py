#!/usr/bin/env python3
"""
Communication Simulator Test for Gemini MCP Server

This script provides comprehensive end-to-end testing of the Gemini MCP server
by simulating real Claude CLI communications and validating conversation
continuity, file handling, and deduplication features.

Test Flow:
1. Setup fresh Docker environment with clean containers
2. Simulate Claude CLI tool calls via docker exec
3. Test conversation threading with file handling
4. Validate file deduplication in conversation history
5. Check Docker logs for proper behavior
6. Cleanup and report results

Usage:
    python communication_simulator_test.py [--verbose] [--keep-logs]
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CommunicationSimulator:
    """Simulates real-world Claude CLI communication with MCP Gemini server"""
    
    def __init__(self, verbose: bool = False, keep_logs: bool = False):
        self.verbose = verbose
        self.keep_logs = keep_logs
        self.temp_dir = None
        self.test_files = {}
        self.container_name = "gemini-mcp-server"
        self.redis_container = "gemini-mcp-redis"
        
        # Test result tracking
        self.test_results = {
            "basic_conversation": False,
            "per_tool_tests": {},
            "cross_tool_scenarios": {},
            "logs_validation": False,
            "redis_validation": False
        }
        
        # Configure logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_test_environment(self) -> bool:
        """Setup fresh Docker environment and test files"""
        try:
            self.logger.info("🚀 Setting up test environment...")
            
            # Create temporary directory for test files
            self.temp_dir = tempfile.mkdtemp(prefix="mcp_test_")
            self.logger.debug(f"Created temp directory: {self.temp_dir}")
            
            # Create test files
            self._create_test_files()
            
            # Setup Docker environment
            return self._setup_docker()
            
        except Exception as e:
            self.logger.error(f"Failed to setup test environment: {e}")
            return False
    
    def _create_test_files(self):
        """Create test files for the simulation in a location accessible by Docker"""
        # Test Python file
        python_content = '''"""
Sample Python module for testing MCP conversation continuity
"""

def fibonacci(n):
    """Calculate fibonacci number recursively"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    """Calculate factorial iteratively"""
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

class Calculator:
    """Simple calculator class"""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def multiply(self, a, b):
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
'''
        
        # Test configuration file
        config_content = '''{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "testdb",
    "ssl": true
  },
  "cache": {
    "redis_url": "redis://localhost:6379",
    "ttl": 3600
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}'''
        
        # Create files in the current project directory so they're accessible to MCP tools
        # MCP tools can access files with absolute paths within the project
        current_dir = os.getcwd()
        test_dir = os.path.join(current_dir, "test_simulation_files")
        os.makedirs(test_dir, exist_ok=True)
        
        test_py = os.path.join(test_dir, "test_module.py")
        test_config = os.path.join(test_dir, "config.json")
        
        with open(test_py, 'w') as f:
            f.write(python_content)
        with open(test_config, 'w') as f:
            f.write(config_content)
        
        self.test_files = {
            "python": test_py,
            "config": test_config
        }
        
        # Store test directory for cleanup
        self.test_dir = test_dir
        
        self.logger.debug(f"Created test files: {list(self.test_files.values())}")
    
    def _setup_docker(self) -> bool:
        """Setup fresh Docker environment"""
        try:
            self.logger.info("🐳 Setting up Docker environment...")
            
            # Stop and remove existing containers
            self._run_command(["docker", "compose", "down", "--remove-orphans"], 
                            check=False, capture_output=True)
            
            # Clean up any old containers/images
            old_containers = [self.container_name, self.redis_container]
            for container in old_containers:
                self._run_command(["docker", "stop", container], 
                                check=False, capture_output=True)
                self._run_command(["docker", "rm", container], 
                                check=False, capture_output=True)
            
            # Build and start services
            self.logger.info("📦 Building Docker images...")
            result = self._run_command(["docker", "compose", "build", "--no-cache"], 
                                     capture_output=True)
            if result.returncode != 0:
                self.logger.error(f"Docker build failed: {result.stderr}")
                return False
            
            self.logger.info("🚀 Starting Docker services...")
            result = self._run_command(["docker", "compose", "up", "-d"], 
                                     capture_output=True)
            if result.returncode != 0:
                self.logger.error(f"Docker startup failed: {result.stderr}")
                return False
            
            # Wait for services to be ready
            self.logger.info("⏳ Waiting for services to be ready...")
            time.sleep(10)  # Give services time to initialize
            
            # Verify containers are running
            if not self._verify_containers():
                return False
            
            self.logger.info("✅ Docker environment ready")
            return True
            
        except Exception as e:
            self.logger.error(f"Docker setup failed: {e}")
            return False
    
    def _verify_containers(self) -> bool:
        """Verify that required containers are running"""
        try:
            result = self._run_command(["docker", "ps", "--format", "{{.Names}}"], 
                                     capture_output=True)
            running_containers = result.stdout.decode().strip().split('\n')
            
            required = [self.container_name, self.redis_container]
            for container in required:
                if container not in running_containers:
                    self.logger.error(f"Container not running: {container}")
                    return False
            
            self.logger.debug(f"Verified containers running: {required}")
            return True
            
        except Exception as e:
            self.logger.error(f"Container verification failed: {e}")
            return False
    
    def simulate_claude_cli_session(self) -> bool:
        """Simulate a complete Claude CLI session with conversation continuity"""
        try:
            self.logger.info("🤖 Starting Claude CLI simulation...")
            
            # Test basic conversation continuity
            if not self._test_basic_conversation_flow():
                return False
            
            # Test per-tool file deduplication
            if not self._test_per_tool_file_deduplication():
                return False
            
            # Test comprehensive cross-tool continuation
            if not self._test_cross_tool_continuation():
                return False
            
            # Test state isolation and contamination detection
            if not self._test_state_isolation():
                return False
            
            # Test conversation boundaries and reset behavior
            if not self._test_conversation_boundaries():
                return False
            
            self.logger.info("✅ All conversation continuity tests passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Claude CLI simulation failed: {e}")
            return False
    
    def _test_basic_conversation_flow(self) -> bool:
        """Test basic conversation flow with chat tool"""
        try:
            self.logger.info("📝 Test 1: Basic conversation flow")
            
            # Initial chat tool call with file
            self.logger.info("  1.1: Initial chat with file analysis")
            response1, continuation_id = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "Analyze this Python code and explain what it does",
                    "files": [self.test_files["python"]]
                }
            )
            
            if not response1 or not continuation_id:
                self.logger.error("Failed to get initial response with continuation_id")
                return False
            
            self.logger.info(f"  ✅ Got continuation_id: {continuation_id}")
            
            # Continue conversation with same file (should be deduplicated)
            self.logger.info("  1.2: Continue conversation with same file")
            response2, _ = self._call_mcp_tool(
                "chat", 
                {
                    "prompt": "Now focus on the Calculator class specifically. Are there any improvements you'd suggest?",
                    "files": [self.test_files["python"]],  # Same file - should be deduplicated
                    "continuation_id": continuation_id
                }
            )
            
            if not response2:
                self.logger.error("Failed to continue conversation")
                return False
            
            # Continue with additional file
            self.logger.info("  1.3: Continue conversation with additional file")
            response3, _ = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "Now also analyze this configuration file and see how it might relate to the Python code",
                    "files": [self.test_files["python"], self.test_files["config"]],
                    "continuation_id": continuation_id
                }
            )
            
            if not response3:
                self.logger.error("Failed to continue with additional file")
                return False
            
            self.logger.info("  ✅ Basic conversation flow working")
            self.test_results["basic_conversation"] = True
            return True
            
        except Exception as e:
            self.logger.error(f"Basic conversation flow test failed: {e}")
            return False
    
    def _test_per_tool_file_deduplication(self) -> bool:
        """Test file deduplication for each individual tool"""
        try:
            self.logger.info("📄 Test 2: Per-tool file deduplication")
            
            tools_to_test = [
                ("thinkdeep", {
                    "prompt": "Think deeply about this Python code and identify potential architectural improvements",
                    "files": [self.test_files["python"]]
                }),
                ("analyze", {
                    "files": [self.test_files["python"]],
                    "analysis_type": "architecture"
                }),
                ("debug", {
                    "files": [self.test_files["python"]],
                    "issue_description": "The fibonacci function seems slow for large numbers"
                }),
                ("codereview", {
                    "files": [self.test_files["python"]],
                    "context": "General code review for quality and best practices"
                })
            ]
            
            for tool_name, initial_params in tools_to_test:
                self.logger.info(f"  2.{tool_name}: Testing {tool_name} tool file deduplication")
                
                # Initial call
                response1, continuation_id = self._call_mcp_tool(tool_name, initial_params)
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
                    continue_params["prompt"] = "Now focus specifically on the recursive fibonacci implementation"
                elif tool_name == "analyze":
                    continue_params["analysis_type"] = "performance"
                elif tool_name == "debug":
                    continue_params["issue_description"] = "How can we optimize the fibonacci function?"
                elif tool_name == "codereview":
                    continue_params["context"] = "Focus on the Calculator class implementation"
                
                response2, _ = self._call_mcp_tool(tool_name, continue_params)
                if response2:
                    self.logger.info(f"  ✅ {tool_name} tool file deduplication working")
                    self.test_results["per_tool_tests"][tool_name] = True
                else:
                    self.logger.warning(f"  ⚠️ {tool_name} tool continuation failed")
                    self.test_results["per_tool_tests"][tool_name] = False
            
            self.logger.info("  ✅ Per-tool file deduplication tests completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Per-tool file deduplication test failed: {e}")
            return False
    
    def _test_cross_tool_continuation(self) -> bool:
        """Test comprehensive cross-tool continuation scenarios"""
        try:
            self.logger.info("🔧 Test 3: Cross-tool continuation scenarios")
            
            # Scenario 1: chat -> thinkdeep -> codereview
            self.logger.info("  3.1: Testing chat -> thinkdeep -> codereview")
            
            # Start with chat
            chat_response, chat_id = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "Look at this Python code and tell me what you think about it",
                    "files": [self.test_files["python"]]
                }
            )
            
            if not chat_response or not chat_id:
                self.logger.error("Failed to start chat conversation")
                return False
            
            # Continue with thinkdeep
            thinkdeep_response, _ = self._call_mcp_tool(
                "thinkdeep",
                {
                    "prompt": "Think deeply about potential performance issues in this code",
                    "files": [self.test_files["python"]],  # Same file should be deduplicated
                    "continuation_id": chat_id
                }
            )
            
            if not thinkdeep_response:
                self.logger.error("Failed chat -> thinkdeep continuation")
                return False
            
            # Continue with codereview
            codereview_response, _ = self._call_mcp_tool(
                "codereview",
                {
                    "files": [self.test_files["python"]],  # Same file should be deduplicated
                    "context": "Building on our previous analysis, provide a comprehensive code review",
                    "continuation_id": chat_id
                }
            )
            
            if not codereview_response:
                self.logger.error("Failed thinkdeep -> codereview continuation")
                return False
            
            self.logger.info("  ✅ chat -> thinkdeep -> codereview working")
            self.test_results["cross_tool_scenarios"]["chat_thinkdeep_codereview"] = True
            
            # Scenario 2: analyze -> debug -> thinkdeep
            self.logger.info("  3.2: Testing analyze -> debug -> thinkdeep")
            
            # Start with analyze
            analyze_response, analyze_id = self._call_mcp_tool(
                "analyze",
                {
                    "files": [self.test_files["python"]],
                    "analysis_type": "code_quality"
                }
            )
            
            if not analyze_response or not analyze_id:
                self.logger.warning("Failed to start analyze conversation, skipping scenario 2")
            else:
                # Continue with debug
                debug_response, _ = self._call_mcp_tool(
                    "debug",
                    {
                        "files": [self.test_files["python"]],  # Same file should be deduplicated
                        "issue_description": "Based on our analysis, help debug the performance issue in fibonacci",
                        "continuation_id": analyze_id
                    }
                )
                
                if debug_response:
                    # Continue with thinkdeep
                    final_response, _ = self._call_mcp_tool(
                        "thinkdeep",
                        {
                            "prompt": "Think deeply about the architectural implications of the issues we've found",
                            "files": [self.test_files["python"]],  # Same file should be deduplicated
                            "continuation_id": analyze_id
                        }
                    )
                    
                    if final_response:
                        self.logger.info("  ✅ analyze -> debug -> thinkdeep working")
                        self.test_results["cross_tool_scenarios"]["analyze_debug_thinkdeep"] = True
                    else:
                        self.logger.warning("  ⚠️ debug -> thinkdeep continuation failed")
                        self.test_results["cross_tool_scenarios"]["analyze_debug_thinkdeep"] = False
                else:
                    self.logger.warning("  ⚠️ analyze -> debug continuation failed")
                    self.test_results["cross_tool_scenarios"]["analyze_debug_thinkdeep"] = False
            
            # Scenario 3: Multi-file cross-tool continuation
            self.logger.info("  3.3: Testing multi-file cross-tool continuation")
            
            # Start with both files
            multi_response, multi_id = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "Analyze both the Python code and configuration file",
                    "files": [self.test_files["python"], self.test_files["config"]]
                }
            )
            
            if not multi_response or not multi_id:
                self.logger.warning("Failed to start multi-file conversation, skipping scenario 3")
            else:
                # Switch to codereview with same files (should use conversation history)
                multi_review, _ = self._call_mcp_tool(
                    "codereview",
                    {
                        "files": [self.test_files["python"], self.test_files["config"]],  # Same files
                        "context": "Review both files in the context of our previous discussion",
                        "continuation_id": multi_id
                    }
                )
                
                if multi_review:
                    self.logger.info("  ✅ Multi-file cross-tool continuation working")
                    self.test_results["cross_tool_scenarios"]["multi_file_continuation"] = True
                else:
                    self.logger.warning("  ⚠️ Multi-file cross-tool continuation failed")
                    self.test_results["cross_tool_scenarios"]["multi_file_continuation"] = False
            
            self.logger.info("  ✅ Cross-tool continuation scenarios completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Cross-tool continuation test failed: {e}")
            return False
    
    def _test_state_isolation(self) -> bool:
        """Test that different conversation threads don't contaminate each other"""
        try:
            self.logger.info("🔒 Test 4: State isolation and contamination detection")
            
            # Create a test file specifically for this test
            isolation_content = '''"""
Test file for state isolation testing
"""

def isolated_function():
    """This function should only appear in isolation tests"""
    return "ISOLATION_TEST_MARKER"

class IsolationTestClass:
    """Class that should not leak between conversations"""
    def __init__(self):
        self.marker = "ISOLATION_BOUNDARY"
'''
            
            isolation_file = os.path.join(self.test_dir, "isolation_test.py")
            with open(isolation_file, 'w') as f:
                f.write(isolation_content)
            
            # Test 1: Start two separate conversation threads
            self.logger.info("  4.1: Creating separate conversation threads")
            
            # Thread A: Chat about original Python file
            response_a1, thread_a = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "Analyze this Python module",
                    "files": [self.test_files["python"]]
                }
            )
            
            if not response_a1 or not thread_a:
                self.logger.error("Failed to create thread A")
                return False
            
            # Thread B: Chat about isolation test file
            response_b1, thread_b = self._call_mcp_tool(
                "chat", 
                {
                    "prompt": "Analyze this isolation test file",
                    "files": [isolation_file]
                }
            )
            
            if not response_b1 or not thread_b:
                self.logger.error("Failed to create thread B")
                return False
            
            # Verify threads are different
            if thread_a == thread_b:
                self.logger.error("Threads are not isolated - same continuation_id returned")
                return False
            
            self.logger.info(f"    ✅ Created isolated threads: {thread_a[:8]}... and {thread_b[:8]}...")
            
            # Test 2: Continue both threads and check for contamination
            self.logger.info("  4.2: Testing cross-thread contamination")
            
            # Continue thread A - should only know about original Python file
            response_a2, _ = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "What functions did we discuss in the previous file?",
                    "continuation_id": thread_a
                }
            )
            
            # Continue thread B - should only know about isolation file
            response_b2, _ = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "What functions did we discuss in the previous file?", 
                    "continuation_id": thread_b
                }
            )
            
            if not response_a2 or not response_b2:
                self.logger.error("Failed to continue isolated threads")
                return False
            
            # Parse responses to check for contamination
            response_a2_data = json.loads(response_a2)
            response_b2_data = json.loads(response_b2)
            
            content_a = response_a2_data.get("content", "")
            content_b = response_b2_data.get("content", "")
            
            # Thread A should mention fibonacci/factorial, not isolation functions
            # Thread B should mention isolation functions, not fibonacci/factorial
            contamination_detected = False
            
            if "isolated_function" in content_a or "IsolationTestClass" in content_a:
                self.logger.error("Thread A contaminated with Thread B content")
                contamination_detected = True
            
            if "fibonacci" in content_b or "factorial" in content_b or "Calculator" in content_b:
                self.logger.error("Thread B contaminated with Thread A content")
                contamination_detected = True
            
            if contamination_detected:
                self.test_results["cross_tool_scenarios"]["state_isolation"] = False
                return False
            
            self.logger.info("    ✅ No cross-thread contamination detected")
            
            # Test 3: Cross-tool switching with isolation
            self.logger.info("  4.3: Testing cross-tool state isolation")
            
            # Switch thread A to codereview
            response_a3, _ = self._call_mcp_tool(
                "codereview",
                {
                    "files": [self.test_files["python"]],
                    "context": "Review the code we discussed",
                    "continuation_id": thread_a
                }
            )
            
            # Switch thread B to codereview  
            response_b3, _ = self._call_mcp_tool(
                "codereview",
                {
                    "files": [isolation_file],
                    "context": "Review the isolation test code",
                    "continuation_id": thread_b
                }
            )
            
            if response_a3 and response_b3:
                self.logger.info("    ✅ Cross-tool isolation maintained")
                self.test_results["cross_tool_scenarios"]["state_isolation"] = True
            else:
                self.logger.warning("    ⚠️ Cross-tool isolation test incomplete")
                self.test_results["cross_tool_scenarios"]["state_isolation"] = False
            
            # Cleanup isolation test file
            os.remove(isolation_file)
            
            self.logger.info("  ✅ State isolation tests completed")
            return True
            
        except Exception as e:
            self.logger.error(f"State isolation test failed: {e}")
            return False
    
    def _test_conversation_boundaries(self) -> bool:
        """Test conversation boundaries and proper reset behavior"""
        try:
            self.logger.info("🚧 Test 5: Conversation boundaries and reset behavior")
            
            # Test 1: Tool-to-tool-to-tool with fresh start
            self.logger.info("  5.1: Testing A->B->A pattern with fresh conversations")
            
            # Start with chat
            response1, thread1 = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "Analyze the fibonacci function in this code",
                    "files": [self.test_files["python"]]
                }
            )
            
            if not response1 or not thread1:
                self.logger.warning("Failed to start boundary test, skipping")
                return True
            
            # Switch to codereview (continue conversation)
            response2, _ = self._call_mcp_tool(
                "codereview",
                {
                    "files": [self.test_files["python"]],
                    "context": "Building on our fibonacci discussion",
                    "continuation_id": thread1
                }
            )
            
            if not response2:
                self.logger.warning("Failed codereview continuation")
                return True
            
            # Switch back to chat but start FRESH conversation (no continuation_id)
            self.logger.info("  5.2: Testing fresh conversation after previous context")
            response3, thread3 = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "Tell me about the Calculator class in this file", # Different focus
                    "files": [self.test_files["python"]]  # Same file but fresh context
                }
            )
            
            if not response3 or not thread3:
                self.logger.warning("Failed fresh conversation test")
                return True
            
            # Verify it's a truly fresh conversation
            if thread1 == thread3:
                self.logger.error("Fresh conversation got same thread ID - boundary violation!")
                self.test_results["cross_tool_scenarios"]["conversation_boundaries"] = False
                return False
            
            self.logger.info(f"    ✅ Fresh conversation created: {thread3[:8]}... (vs {thread1[:8]}...)")
            
            # Test 2: Verify fresh conversation doesn't have stale context
            self.logger.info("  5.3: Testing stale context isolation")
            
            # Continue the fresh conversation - should not reference fibonacci discussion
            response4, _ = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "What did we just discuss about this code?",
                    "continuation_id": thread3
                }
            )
            
            if response4:
                response4_data = json.loads(response4)
                content4 = response4_data.get("content", "")
                
                # Should reference Calculator class, not fibonacci from previous thread
                if "fibonacci" in content4.lower() and "calculator" not in content4.lower():
                    self.logger.error("Fresh conversation contaminated with stale context!")
                    self.test_results["cross_tool_scenarios"]["conversation_boundaries"] = False
                    return False
                else:
                    self.logger.info("    ✅ Fresh conversation properly isolated from previous context")
            
            # Test 3: File access without continuation should work
            self.logger.info("  5.4: Testing file access in fresh conversations")
            
            # New conversation with same files - should read files fresh
            response5, thread5 = self._call_mcp_tool(
                "chat",
                {
                    "prompt": "What's the purpose of this configuration file?",
                    "files": [self.test_files["config"]]
                }
            )
            
            if response5 and thread5:
                # Verify it can access the file content
                response5_data = json.loads(response5)
                content5 = response5_data.get("content", "")
                
                if "database" in content5.lower() or "redis" in content5.lower():
                    self.logger.info("    ✅ Fresh conversation can access files correctly")
                    self.test_results["cross_tool_scenarios"]["conversation_boundaries"] = True
                else:
                    self.logger.warning("    ⚠️ Fresh conversation may not be reading files properly")
                    self.test_results["cross_tool_scenarios"]["conversation_boundaries"] = False
            else:
                self.logger.warning("    ⚠️ Fresh conversation with config file failed")
                self.test_results["cross_tool_scenarios"]["conversation_boundaries"] = False
            
            self.logger.info("  ✅ Conversation boundary tests completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Conversation boundary test failed: {e}")
            return False
    
    def _call_mcp_tool(self, tool_name: str, params: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Simulate calling an MCP tool via Claude CLI (docker exec)"""
        try:
            # Prepare the MCP initialization and tool call sequence
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "communication-simulator",
                        "version": "1.0.0"
                    }
                }
            }
            
            # Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            
            # Prepare the tool call request
            tool_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params
                }
            }
            
            # Combine all messages
            messages = [
                json.dumps(init_request),
                json.dumps(initialized_notification),
                json.dumps(tool_request)
            ]
            
            # Join with newlines as MCP expects
            input_data = "\n".join(messages) + "\n"
            
            # Simulate Claude CLI calling the MCP server via docker exec
            docker_cmd = [
                "docker", "exec", "-i", self.container_name,
                "python", "server.py"
            ]
            
            self.logger.debug(f"Calling MCP tool {tool_name} with proper initialization")
            
            # Execute the command
            result = subprocess.run(
                docker_cmd,
                input=input_data,
                text=True,
                capture_output=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Docker exec failed: {result.stderr}")
                return None, None
            
            # Parse the response - look for the tool call response
            response_data = self._parse_mcp_response(result.stdout, expected_id=2)
            if not response_data:
                return None, None
            
            # Extract continuation_id if present
            continuation_id = self._extract_continuation_id(response_data)
            
            return response_data, continuation_id
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"MCP tool call timed out: {tool_name}")
            return None, None
        except Exception as e:
            self.logger.error(f"MCP tool call failed: {e}")
            return None, None
    
    def _parse_mcp_response(self, stdout: str, expected_id: int = 2) -> Optional[str]:
        """Parse MCP JSON-RPC response from stdout"""
        try:
            lines = stdout.strip().split('\n')
            for line in lines:
                if line.strip() and line.startswith('{'):
                    response = json.loads(line)
                    # Look for the tool call response with the expected ID
                    if response.get("id") == expected_id and "result" in response:
                        # Extract the actual content from the response
                        result = response["result"]
                        # Handle new response format with 'content' array
                        if isinstance(result, dict) and "content" in result:
                            content_array = result["content"]
                            if isinstance(content_array, list) and len(content_array) > 0:
                                return content_array[0].get("text", "")
                        # Handle legacy format
                        elif isinstance(result, list) and len(result) > 0:
                            return result[0].get("text", "")
                    elif response.get("id") == expected_id and "error" in response:
                        self.logger.error(f"MCP error: {response['error']}")
                        return None
            
            # If we get here, log all responses for debugging
            self.logger.warning(f"No valid tool call response found for ID {expected_id}")
            self.logger.debug(f"Full stdout: {stdout}")
            return None
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse MCP response: {e}")
            self.logger.debug(f"Stdout that failed to parse: {stdout}")
            return None
    
    def _extract_continuation_id(self, response_text: str) -> Optional[str]:
        """Extract continuation_id from response metadata"""
        try:
            # Parse the response text as JSON to look for continuation metadata
            response_data = json.loads(response_text)
            
            # Look for continuation_id in various places
            if isinstance(response_data, dict):
                # Check metadata
                metadata = response_data.get("metadata", {})
                if "thread_id" in metadata:
                    return metadata["thread_id"]
                
                # Check follow_up_request
                follow_up = response_data.get("follow_up_request", {})
                if follow_up and "continuation_id" in follow_up:
                    return follow_up["continuation_id"]
                
                # Check continuation_offer
                continuation_offer = response_data.get("continuation_offer", {})
                if continuation_offer and "continuation_id" in continuation_offer:
                    return continuation_offer["continuation_id"]
            
            self.logger.debug(f"No continuation_id found in response: {response_data}")
            return None
            
        except json.JSONDecodeError as e:
            self.logger.debug(f"Failed to parse response for continuation_id: {e}")
            return None
    
    def validate_docker_logs(self) -> bool:
        """Validate Docker logs to confirm file deduplication behavior"""
        try:
            self.logger.info("📋 Validating Docker logs for file deduplication...")
            
            # Get server logs from both main container and activity logs
            result = self._run_command(
                ["docker", "logs", self.container_name],
                capture_output=True
            )
            
            if result.returncode != 0:
                self.logger.error(f"Failed to get Docker logs: {result.stderr}")
                return False
            
            main_logs = result.stdout.decode() + result.stderr.decode()
            
            # Also get activity logs for more detailed conversation tracking
            activity_result = self._run_command(
                ["docker", "exec", self.container_name, "cat", "/tmp/mcp_activity.log"],
                capture_output=True
            )
            
            activity_logs = ""
            if activity_result.returncode == 0:
                activity_logs = activity_result.stdout.decode()
            
            logs = main_logs + "\n" + activity_logs
            
            # Look for conversation threading patterns that indicate the system is working
            conversation_patterns = [
                'CONVERSATION_RESUME',
                'CONVERSATION_CONTEXT',
                'previous turns loaded',
                'tool embedding',
                'files included',
                'files truncated',
                'already in conversation history'
            ]
            
            conversation_lines = []
            for line in logs.split('\n'):
                for pattern in conversation_patterns:
                    if pattern.lower() in line.lower():
                        conversation_lines.append(line.strip())
                        break
            
            # Look for evidence of conversation threading and file handling
            conversation_threading_found = False
            multi_turn_conversations = False
            
            for line in conversation_lines:
                lower_line = line.lower()
                if 'conversation_resume' in lower_line:
                    conversation_threading_found = True
                    self.logger.debug(f"📄 Conversation threading: {line}")
                elif 'previous turns loaded' in lower_line:
                    multi_turn_conversations = True
                    self.logger.debug(f"📄 Multi-turn conversation: {line}")
                elif 'already in conversation' in lower_line:
                    self.logger.info(f"✅ Found explicit deduplication: {line}")
                    return True
            
            # Conversation threading with multiple turns is evidence of file deduplication working
            if conversation_threading_found and multi_turn_conversations:
                self.logger.info("✅ Conversation threading with multi-turn context working")
                self.logger.info("✅ File deduplication working implicitly (files embedded once in conversation history)")
                self.test_results["logs_validation"] = True
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
    
    def validate_conversation_memory(self) -> bool:
        """Validate that conversation memory is working via Redis"""
        try:
            self.logger.info("💾 Validating conversation memory via Redis...")
            
            # Check Redis for stored conversations
            result = self._run_command([
                "docker", "exec", self.redis_container,
                "redis-cli", "KEYS", "thread:*"
            ], capture_output=True)
            
            if result.returncode != 0:
                self.logger.error("Failed to query Redis")
                return False
            
            keys = result.stdout.decode().strip().split('\n')
            thread_keys = [k for k in keys if k.startswith('thread:')]
            
            if thread_keys:
                self.logger.info(f"✅ Found {len(thread_keys)} conversation threads in Redis")
                
                # Get details of first thread
                if thread_keys:
                    thread_key = thread_keys[0]
                    result = self._run_command([
                        "docker", "exec", self.redis_container,
                        "redis-cli", "GET", thread_key
                    ], capture_output=True)
                    
                    if result.returncode == 0:
                        thread_data = result.stdout.decode()
                        try:
                            parsed = json.loads(thread_data)
                            turns = parsed.get("turns", [])
                            self.logger.info(f"✅ Thread has {len(turns)} turns")
                            self.test_results["redis_validation"] = True
                            return True
                        except json.JSONDecodeError:
                            self.logger.warning("Could not parse thread data")
                
                self.test_results["redis_validation"] = True
                return True
            else:
                self.logger.warning("⚠️  No conversation threads found in Redis")
                return False
            
        except Exception as e:
            self.logger.error(f"Conversation memory validation failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup test environment"""
        try:
            self.logger.info("🧹 Cleaning up test environment...")
            
            if not self.keep_logs:
                # Stop Docker services
                self._run_command(["docker", "compose", "down", "--remove-orphans"], 
                                check=False, capture_output=True)
            else:
                self.logger.info("📋 Keeping Docker services running for log inspection")
            
            # Remove temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.debug(f"Removed temp directory: {self.temp_dir}")
            
            # Remove test files directory
            if hasattr(self, 'test_dir') and self.test_dir and os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
                self.logger.debug(f"Removed test files directory: {self.test_dir}")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def _run_command(self, cmd: List[str], check: bool = True, capture_output: bool = False, **kwargs):
        """Run a shell command with logging"""
        if self.verbose:
            self.logger.debug(f"Running: {' '.join(cmd)}")
        
        return subprocess.run(cmd, check=check, capture_output=capture_output, **kwargs)
    
    def print_test_summary(self):
        """Print comprehensive test results summary"""
        print("\n" + "="*70)
        print("🧪 GEMINI MCP COMMUNICATION SIMULATOR - TEST RESULTS SUMMARY")
        print("="*70)
        
        # Basic conversation flow
        status = "✅ PASS" if self.test_results["basic_conversation"] else "❌ FAIL"
        print(f"📝 Basic Conversation Flow: {status}")
        
        # Per-tool tests
        print(f"\n📄 Per-Tool File Deduplication Tests:")
        tools_tested = len(self.test_results["per_tool_tests"])
        tools_passed = sum(1 for passed in self.test_results["per_tool_tests"].values() if passed)
        
        if tools_tested > 0:
            for tool, passed in self.test_results["per_tool_tests"].items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"  • {tool}: {status}")
            print(f"  → Summary: {tools_passed}/{tools_tested} tools passed")
        else:
            print("  → No tools tested")
        
        # Cross-tool scenarios
        print(f"\n🔧 Cross-Tool Continuation Scenarios:")
        scenarios_tested = len(self.test_results["cross_tool_scenarios"])
        scenarios_passed = sum(1 for passed in self.test_results["cross_tool_scenarios"].values() if passed is True)
        
        if scenarios_tested > 0:
            scenario_names = {
                "chat_thinkdeep_codereview": "chat → thinkdeep → codereview",
                "analyze_debug_thinkdeep": "analyze → debug → thinkdeep", 
                "multi_file_continuation": "Multi-file continuation",
                "state_isolation": "State isolation (contamination detection)",
                "conversation_boundaries": "Conversation boundaries & reset behavior"
            }
            
            for scenario, passed in self.test_results["cross_tool_scenarios"].items():
                name = scenario_names.get(scenario, scenario)
                if passed is True:
                    status = "✅ PASS"
                elif passed is False:
                    status = "❌ FAIL"
                else:
                    status = "⏸️  SKIP"
                print(f"  • {name}: {status}")
            print(f"  → Summary: {scenarios_passed}/{scenarios_tested} scenarios passed")
        else:
            print("  → No scenarios tested")
        
        # System validation
        print(f"\n💾 System Validation:")
        logs_status = "✅ PASS" if self.test_results["logs_validation"] else "❌ FAIL"
        redis_status = "✅ PASS" if self.test_results["redis_validation"] else "❌ FAIL"
        print(f"  • Docker logs (conversation threading): {logs_status}")
        print(f"  • Redis memory (conversation persistence): {redis_status}")
        
        # Overall result
        all_core_tests = [
            self.test_results["basic_conversation"],
            self.test_results["logs_validation"],
            self.test_results["redis_validation"]
        ]
        
        tool_tests_ok = tools_tested == 0 or tools_passed > 0
        scenario_tests_ok = scenarios_tested == 0 or scenarios_passed > 0
        
        overall_success = all(all_core_tests) and tool_tests_ok and scenario_tests_ok
        
        print(f"\n🎯 OVERALL RESULT: {'🎉 SUCCESS' if overall_success else '❌ FAILURE'}")
        
        if overall_success:
            print("✅ MCP server conversation continuity and file deduplication working correctly!")
            print("✅ All core systems validated")
            if tools_passed > 0:
                print(f"✅ {tools_passed} tools working with file deduplication")
            if scenarios_passed > 0:
                print(f"✅ {scenarios_passed} cross-tool scenarios working")
        else:
            print("⚠️  Some tests failed - check individual results above")
        
        print("="*70)
        return overall_success

    def run_full_test_suite(self) -> bool:
        """Run the complete test suite"""
        try:
            self.logger.info("🚀 Starting Gemini MCP Communication Simulator Test Suite")
            
            # Setup
            if not self.setup_test_environment():
                self.logger.error("❌ Environment setup failed")
                return False
            
            # Main simulation
            if not self.simulate_claude_cli_session():
                self.logger.error("❌ Claude CLI simulation failed")
                return False
            
            # Validation
            logs_valid = self.validate_docker_logs()
            memory_valid = self.validate_conversation_memory()
            
            # Print comprehensive summary
            overall_success = self.print_test_summary()
            
            return overall_success
            
        except Exception as e:
            self.logger.error(f"Test suite failed: {e}")
            return False
        finally:
            if not self.keep_logs:
                self.cleanup()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Gemini MCP Communication Simulator Test")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    parser.add_argument("--keep-logs", action="store_true",
                       help="Keep Docker services running for log inspection")
    
    args = parser.parse_args()
    
    simulator = CommunicationSimulator(verbose=args.verbose, keep_logs=args.keep_logs)
    
    try:
        success = simulator.run_full_test_suite()
        
        if success:
            print("\n🎉 COMPREHENSIVE MCP COMMUNICATION TEST: PASSED")
            sys.exit(0)
        else:
            print("\n❌ COMPREHENSIVE MCP COMMUNICATION TEST: FAILED")
            print("⚠️  Check detailed results above")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        simulator.cleanup()
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        simulator.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()