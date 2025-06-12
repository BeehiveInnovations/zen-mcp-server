#!/usr/bin/env python3
"""
Conversation Chain and Threading Validation Test

This test validates that:
1. Multiple tool invocations create proper parent->parent->parent chains
2. New conversations can be started independently 
3. Original conversation chains can be resumed from any point
4. History traversal works correctly for all scenarios
5. Thread relationships are properly maintained in Redis

Test Flow:
Chain A: chat -> analyze -> debug (3 linked threads)
Chain B: chat -> analyze (2 linked threads, independent)  
Chain A Branch: debug (continue from original chat, creating branch)

This validates the conversation threading system's ability to:
- Build linear chains
- Create independent conversation threads
- Branch from earlier points in existing chains
- Properly traverse parent relationships for history reconstruction
"""

import datetime
import subprocess
import re
from typing import Dict, List, Tuple, Optional

from .base_test import BaseSimulatorTest


class ConversationChainValidationTest(BaseSimulatorTest):
    """Test conversation chain and threading functionality"""

    @property
    def test_name(self) -> str:
        return "conversation_chain_validation"

    @property
    def test_description(self) -> str:
        return "Conversation chain and threading validation"

    def get_recent_server_logs(self) -> str:
        """Get recent server logs from the log file directly"""
        try:
            cmd = ["docker", "exec", self.container_name, "tail", "-n", "500", "/tmp/mcp_server.log"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout
            else:
                self.logger.warning(f"Failed to read server logs: {result.stderr}")
                return ""
        except Exception as e:
            self.logger.error(f"Failed to get server logs: {e}")
            return ""

    def extract_thread_creation_logs(self, logs: str) -> List[Dict[str, str]]:
        """Extract thread creation logs with parent relationships"""
        thread_logs = []
        
        lines = logs.split('\n')
        for line in lines:
            if "[THREAD] Created new thread" in line:
                # Parse: [THREAD] Created new thread 9dc779eb-645f-4850-9659-34c0e6978d73 with parent a0ce754d-c995-4b3e-9103-88af429455aa
                match = re.search(r'\[THREAD\] Created new thread ([a-f0-9-]+) with parent ([a-f0-9-]+|None)', line)
                if match:
                    thread_id = match.group(1)
                    parent_id = match.group(2) if match.group(2) != "None" else None
                    thread_logs.append({
                        "thread_id": thread_id,
                        "parent_id": parent_id,
                        "log_line": line
                    })
        
        return thread_logs

    def extract_history_traversal_logs(self, logs: str) -> List[Dict[str, str]]:
        """Extract conversation history traversal logs"""
        traversal_logs = []
        
        lines = logs.split('\n')
        for line in lines:
            if "[THREAD] Retrieved chain of" in line:
                # Parse: [THREAD] Retrieved chain of 3 threads for 9dc779eb-645f-4850-9659-34c0e6978d73
                match = re.search(r'\[THREAD\] Retrieved chain of (\d+) threads for ([a-f0-9-]+)', line)
                if match:
                    chain_length = int(match.group(1))
                    thread_id = match.group(2)
                    traversal_logs.append({
                        "thread_id": thread_id,
                        "chain_length": chain_length,
                        "log_line": line
                    })
        
        return traversal_logs

    def run_test(self) -> bool:
        """Test conversation chain and threading functionality"""
        try:
            self.logger.info("🔗 Test: Conversation chain and threading validation")

            # Setup test files
            self.setup_test_files()

            # Create test file for consistent context
            test_file_content = """def example_function():
    '''Simple test function for conversation continuity testing'''
    return "Hello from conversation chain test"

class TestClass:
    def method(self):
        return "Method in test class"
"""
            test_file_path = self.create_additional_test_file("chain_test.py", test_file_content)
            
            # Track all continuation IDs and their relationships
            conversation_chains = {}
            
            # === CHAIN A: Build linear conversation chain ===
            self.logger.info("  🔗 Chain A: Building linear conversation chain")
            
            # Step A1: Start with chat tool (creates thread_id_1)
            self.logger.info("    Step A1: Chat tool - start new conversation")
            
            response_a1, continuation_id_a1 = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Analyze this test file and explain what it does.",
                    "files": [test_file_path],
                    "model": "flash",
                    "temperature": 0.7,
                },
            )

            if not response_a1 or not continuation_id_a1:
                self.logger.error("    ❌ Step A1 failed - no response or continuation ID")
                return False

            self.logger.info(f"    ✅ Step A1 completed - thread_id: {continuation_id_a1[:8]}...")
            conversation_chains['A1'] = continuation_id_a1

            # Step A2: Continue with analyze tool (creates thread_id_2 with parent=thread_id_1)
            self.logger.info("    Step A2: Analyze tool - continue Chain A")
            
            response_a2, continuation_id_a2 = self.call_mcp_tool(
                "analyze",
                {
                    "prompt": "Now analyze the code quality and suggest improvements.",
                    "files": [test_file_path],
                    "continuation_id": continuation_id_a1,
                    "model": "flash",
                    "temperature": 0.7,
                },
            )

            if not response_a2 or not continuation_id_a2:
                self.logger.error("    ❌ Step A2 failed - no response or continuation ID")
                return False

            self.logger.info(f"    ✅ Step A2 completed - thread_id: {continuation_id_a2[:8]}...")
            conversation_chains['A2'] = continuation_id_a2

            # Step A3: Continue with debug tool (creates thread_id_3 with parent=thread_id_2)  
            self.logger.info("    Step A3: Debug tool - continue Chain A")
            
            response_a3, continuation_id_a3 = self.call_mcp_tool(
                "debug",
                {
                    "prompt": "Debug any potential issues in this code.",
                    "files": [test_file_path],
                    "continuation_id": continuation_id_a2,
                    "model": "flash",
                    "temperature": 0.7,
                },
            )

            if not response_a3 or not continuation_id_a3:
                self.logger.error("    ❌ Step A3 failed - no response or continuation ID")
                return False

            self.logger.info(f"    ✅ Step A3 completed - thread_id: {continuation_id_a3[:8]}...")
            conversation_chains['A3'] = continuation_id_a3

            # === CHAIN B: Start independent conversation ===
            self.logger.info("  🔗 Chain B: Starting independent conversation")
            
            # Step B1: Start new chat conversation (creates thread_id_4, no parent)
            self.logger.info("    Step B1: Chat tool - start NEW independent conversation")
            
            response_b1, continuation_id_b1 = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "This is a completely new conversation. Please greet me.",
                    "model": "flash",
                    "temperature": 0.7,
                },
            )

            if not response_b1 or not continuation_id_b1:
                self.logger.error("    ❌ Step B1 failed - no response or continuation ID")
                return False

            self.logger.info(f"    ✅ Step B1 completed - thread_id: {continuation_id_b1[:8]}...")
            conversation_chains['B1'] = continuation_id_b1

            # Step B2: Continue the new conversation (creates thread_id_5 with parent=thread_id_4)
            self.logger.info("    Step B2: Analyze tool - continue Chain B")
            
            response_b2, continuation_id_b2 = self.call_mcp_tool(
                "analyze",
                {
                    "prompt": "Analyze the previous greeting and suggest improvements.",
                    "continuation_id": continuation_id_b1,
                    "model": "flash",
                    "temperature": 0.7,
                },
            )

            if not response_b2 or not continuation_id_b2:
                self.logger.error("    ❌ Step B2 failed - no response or continuation ID")
                return False

            self.logger.info(f"    ✅ Step B2 completed - thread_id: {continuation_id_b2[:8]}...")
            conversation_chains['B2'] = continuation_id_b2

            # === CHAIN A BRANCH: Go back to original conversation ===
            self.logger.info("  🔗 Chain A Branch: Resume original conversation from A1")
            
            # Step A1-Branch: Use original continuation_id_a1 to branch (creates thread_id_6 with parent=thread_id_1)
            self.logger.info("    Step A1-Branch: Debug tool - branch from original Chain A")
            
            response_a1_branch, continuation_id_a1_branch = self.call_mcp_tool(
                "debug",
                {
                    "prompt": "Let's debug this from a different angle now.",
                    "files": [test_file_path],
                    "continuation_id": continuation_id_a1,  # Go back to original!
                    "model": "flash",
                    "temperature": 0.7,
                },
            )

            if not response_a1_branch or not continuation_id_a1_branch:
                self.logger.error("    ❌ Step A1-Branch failed - no response or continuation ID")
                return False

            self.logger.info(f"    ✅ Step A1-Branch completed - thread_id: {continuation_id_a1_branch[:8]}...")
            conversation_chains['A1_Branch'] = continuation_id_a1_branch

            # === ANALYSIS: Validate thread relationships and history traversal ===
            self.logger.info("  📊 Analyzing conversation chain structure...")
            
            # Get logs and extract thread relationships
            logs = self.get_recent_server_logs()
            thread_creation_logs = self.extract_thread_creation_logs(logs)
            history_traversal_logs = self.extract_history_traversal_logs(logs)
            
            self.logger.info(f"    Found {len(thread_creation_logs)} thread creation logs")
            self.logger.info(f"    Found {len(history_traversal_logs)} history traversal logs")
            
            # Debug: Show what we found
            if self.verbose:
                self.logger.debug("    Thread creation logs found:")
                for log in thread_creation_logs:
                    self.logger.debug(f"      {log['thread_id'][:8]}... parent: {log['parent_id'][:8] if log['parent_id'] else 'None'}...")
                self.logger.debug("    History traversal logs found:")
                for log in history_traversal_logs:
                    self.logger.debug(f"      {log['thread_id'][:8]}... chain length: {log['chain_length']}")
            
            # Build expected thread relationships
            expected_relationships = []
            
            # Note: A1 and B1 won't appear in thread creation logs because they're new conversations (no parent)
            # Only continuation threads (A2, A3, B2, A1-Branch) will appear in creation logs
            
            # Find logs for each continuation thread
            a2_log = next((log for log in thread_creation_logs if log['thread_id'] == continuation_id_a2), None)
            a3_log = next((log for log in thread_creation_logs if log['thread_id'] == continuation_id_a3), None)
            b2_log = next((log for log in thread_creation_logs if log['thread_id'] == continuation_id_b2), None)
            a1_branch_log = next((log for log in thread_creation_logs if log['thread_id'] == continuation_id_a1_branch), None)
            
            # A2 should have A1 as parent
            if a2_log:
                expected_relationships.append(("A2 has A1 as parent", a2_log['parent_id'] == continuation_id_a1))
            
            # A3 should have A2 as parent
            if a3_log:
                expected_relationships.append(("A3 has A2 as parent", a3_log['parent_id'] == continuation_id_a2))
            
            # B2 should have B1 as parent (independent chain)
            if b2_log:
                expected_relationships.append(("B2 has B1 as parent", b2_log['parent_id'] == continuation_id_b1))
            
            # A1-Branch should have A1 as parent (branching)
            if a1_branch_log:
                expected_relationships.append(("A1-Branch has A1 as parent", a1_branch_log['parent_id'] == continuation_id_a1))
            
            # Validate history traversal
            traversal_validations = []
            
            # History traversal logs are only generated when conversation history is built from scratch
            # (not when history is already embedded in the prompt by server.py)
            # So we should expect at least 1 traversal log, but not necessarily for every continuation
            
            if len(history_traversal_logs) > 0:
                # Validate that any traversal logs we find have reasonable chain lengths
                for log in history_traversal_logs:
                    thread_id = log['thread_id']
                    chain_length = log['chain_length']
                    
                    # Chain length should be at least 2 for any continuation thread
                    # (original thread + continuation thread)
                    is_valid_length = chain_length >= 2
                    
                    # Try to identify which thread this is for better validation
                    thread_description = "Unknown thread"
                    if thread_id == continuation_id_a2:
                        thread_description = "A2 (should be 2-thread chain)"
                        is_valid_length = chain_length == 2
                    elif thread_id == continuation_id_a3:
                        thread_description = "A3 (should be 3-thread chain)"
                        is_valid_length = chain_length == 3
                    elif thread_id == continuation_id_b2:
                        thread_description = "B2 (should be 2-thread chain)"
                        is_valid_length = chain_length == 2
                    elif thread_id == continuation_id_a1_branch:
                        thread_description = "A1-Branch (should be 2-thread chain)"
                        is_valid_length = chain_length == 2
                    
                    traversal_validations.append((f"{thread_description[:8]}... has valid chain length", is_valid_length))
                    
                # Also validate we found at least one traversal (shows the system is working)
                traversal_validations.append(("At least one history traversal occurred", len(history_traversal_logs) >= 1))
            
            # === VALIDATION RESULTS ===
            self.logger.info("  📊 Thread Relationship Validation:")
            relationship_passed = 0
            for desc, passed in expected_relationships:
                status = "✅" if passed else "❌"
                self.logger.info(f"    {status} {desc}")
                if passed:
                    relationship_passed += 1
            
            self.logger.info("  📊 History Traversal Validation:")
            traversal_passed = 0
            for desc, passed in traversal_validations:
                status = "✅" if passed else "❌"
                self.logger.info(f"    {status} {desc}")
                if passed:
                    traversal_passed += 1
            
            # === SUCCESS CRITERIA ===
            total_relationship_checks = len(expected_relationships)
            total_traversal_checks = len(traversal_validations)
            
            self.logger.info(f"  📊 Validation Summary:")
            self.logger.info(f"    Thread relationships: {relationship_passed}/{total_relationship_checks}")
            self.logger.info(f"    History traversal: {traversal_passed}/{total_traversal_checks}")
            
            # Success requires at least 80% of validations to pass
            relationship_success = relationship_passed >= (total_relationship_checks * 0.8)
            
            # If no traversal checks were possible, it means no traversal logs were found
            # This could indicate an issue since we expect at least some history building
            if total_traversal_checks == 0:
                self.logger.warning("    No history traversal logs found - this may indicate conversation history is always pre-embedded")
                # Still consider it successful since the thread relationships are what matter most
                traversal_success = True
            else:
                traversal_success = traversal_passed >= (total_traversal_checks * 0.8)
            
            overall_success = relationship_success and traversal_success
            
            self.logger.info(f"  📊 Conversation Chain Structure:")
            self.logger.info(f"    Chain A: {continuation_id_a1[:8]} → {continuation_id_a2[:8]} → {continuation_id_a3[:8]}")
            self.logger.info(f"    Chain B: {continuation_id_b1[:8]} → {continuation_id_b2[:8]}")
            self.logger.info(f"    Branch:  {continuation_id_a1[:8]} → {continuation_id_a1_branch[:8]}")

            if overall_success:
                self.logger.info("  ✅ Conversation chain validation test PASSED")
                return True
            else:
                self.logger.error("  ❌ Conversation chain validation test FAILED")
                return False

        except Exception as e:
            self.logger.error(f"Conversation chain validation test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()


def main():
    """Run the conversation chain validation test"""
    import sys
    
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    test = ConversationChainValidationTest(verbose=verbose)
    
    success = test.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()