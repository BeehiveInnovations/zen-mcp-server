#!/usr/bin/env python3
"""
PlannerWorkflow Tool Validation Test

Tests the planner tool's capabilities using the new workflow architecture.
This validates that the new workflow-based implementation maintains all the
functionality of the original planner tool while using the workflow pattern
like the debug tool.
"""

import json
from typing import Optional

from .conversation_base_test import ConversationBaseTest


class PlannerValidationTest(ConversationBaseTest):
    """Test planner tool with new workflow architecture"""

    @property
    def test_name(self) -> str:
        return "planner_validation"

    @property
    def test_description(self) -> str:
        return "PlannerWorkflow tool validation with new workflow architecture"

    def run_test(self) -> bool:
        """Test planner tool capabilities"""
        # Set up the test environment
        self.setUp()

        try:
            self.logger.info("Test: PlannerWorkflow tool validation (new architecture)")

            # Test 1: Single planning session with workflow architecture
            if not self._test_single_planning_session():
                return False

            # Test 2: Planning with continuation using workflow
            if not self._test_planning_with_continuation():
                return False

            # Test 3: Complex plan with deep thinking pauses
            if not self._test_complex_plan_deep_thinking():
                return False

            # Test 4: Self-contained completion (no expert analysis)
            if not self._test_self_contained_completion():
                return False

            # Test 5: Branching and revision with workflow
            if not self._test_branching_and_revision():
                return False

            # Test 6: Workflow file context behavior
            if not self._test_workflow_file_context():
                return False

            self.logger.info("  ✅ All planner validation tests passed")
            return True

        except Exception as e:
            self.logger.error(f"PlannerWorkflow validation test failed: {e}")
            return False

    def _test_single_planning_session(self) -> bool:
        """Test a complete planning session with workflow architecture"""
        try:
            self.logger.info("  1.1: Testing single planning session with workflow")

            # Step 1: Start planning
            self.logger.info("    1.1.1: Step 1 - Initial planning step")
            response1, continuation_id = self.call_mcp_tool(
                "planner",
                {
                    "step": "I need to plan a comprehensive API redesign for our legacy system. Let me start by analyzing the current state and identifying key requirements for the new API architecture.",
                    "step_number": 1,
                    "total_steps": 4,
                    "next_step_required": True,
                    "model": "flash",
                },
            )

            if not response1 or not continuation_id:
                self.logger.error("Failed to get initial planning response")
                return False

            # Parse and validate JSON response
            response1_data = self._parse_planner_response(response1)
            if not response1_data:
                return False

            # Validate step 1 response structure - expect pause_for_planner for next_step_required=True
            if not self._validate_step_response(response1_data, 1, 4, True, "pause_for_planner"):
                return False

            # Debug: Log the actual response structure to see what we're getting
            self.logger.debug(f"Response structure: {list(response1_data.keys())}")

            # Check workflow-specific response structure (more flexible)
            status_key = None
            for key in response1_data.keys():
                if key.endswith("_status"):
                    status_key = key
                    break

            if not status_key:
                self.logger.error(f"Missing workflow status field in response: {list(response1_data.keys())}")
                return False

            self.logger.debug(f"Found status field: {status_key}")

            # Check required_actions for workflow guidance
            if not response1_data.get("required_actions"):
                self.logger.error("Missing required_actions in workflow response")
                return False

            self.logger.info(f"    ✅ Step 1 successful with workflow, continuation_id: {continuation_id}")

            # Step 2: Continue planning
            self.logger.info("    1.1.2: Step 2 - API domain analysis")
            response2, _ = self.call_mcp_tool(
                "planner",
                {
                    "step": "After analyzing the current API, I can identify three main domains: User Management, Content Management, and Analytics. Let me design the new API structure with RESTful endpoints and proper versioning.",
                    "step_number": 2,
                    "total_steps": 4,
                    "next_step_required": True,
                    "continuation_id": continuation_id,
                    "model": "flash",
                },
            )

            if not response2:
                self.logger.error("Failed to continue planning to step 2")
                return False

            response2_data = self._parse_planner_response(response2)
            if not self._validate_step_response(response2_data, 2, 4, True, "pause_for_planner"):
                return False

            # Check step history tracking in workflow (more flexible)
            status_key = None
            for key in response2_data.keys():
                if key.endswith("_status"):
                    status_key = key
                    break

            if status_key:
                workflow_status = response2_data.get(status_key, {})
                step_history_length = workflow_status.get("step_history_length", 0)
                if step_history_length < 2:
                    self.logger.error(f"Step history not properly tracked in workflow: {step_history_length}")
                    return False
                self.logger.debug(f"Step history length: {step_history_length}")
            else:
                self.logger.warning("No workflow status found, skipping step history check")

            self.logger.info("    ✅ Step 2 successful with workflow tracking")

            # Step 3: Final step - should trigger completion
            self.logger.info("    1.1.3: Step 3 - Final planning step")
            response3, _ = self.call_mcp_tool(
                "planner",
                {
                    "step": "API redesign plan complete: Phase 1 - User Management API, Phase 2 - Content Management API, Phase 3 - Analytics API. Each phase includes proper authentication, rate limiting, and comprehensive documentation.",
                    "step_number": 3,
                    "total_steps": 3,  # Adjusted total
                    "next_step_required": False,  # Final step - should complete without expert analysis
                    "continuation_id": continuation_id,
                    "model": "flash",
                },
            )

            if not response3:
                self.logger.error("Failed to complete planning session")
                return False

            response3_data = self._parse_planner_response(response3)
            if not response3_data:
                return False

            # Validate final response structure - should be self-contained completion
            if response3_data.get("status") != "planner_complete":
                self.logger.error(f"Expected status 'planner_complete', got '{response3_data.get('status')}'")
                return False

            if not response3_data.get("planning_complete"):
                self.logger.error("Expected planning_complete=true for final step")
                return False

            # Should NOT have expert_analysis (self-contained)
            if "expert_analysis" in response3_data:
                self.logger.error("PlannerWorkflow should be self-contained without expert analysis")
                return False

            # Check plan_summary exists
            if not response3_data.get("plan_summary"):
                self.logger.error("Missing plan_summary in final step")
                return False

            self.logger.info("    ✅ Planning session completed successfully with workflow architecture")

            # Store continuation_id for next test
            self.api_continuation_id = continuation_id
            return True

        except Exception as e:
            self.logger.error(f"Single planning session test failed: {e}")
            return False

    def _test_planning_with_continuation(self) -> bool:
        """Test planning continuation with workflow architecture"""
        try:
            self.logger.info("  1.2: Testing planning continuation with workflow")

            # Use continuation from previous test if available
            continuation_id = getattr(self, "api_continuation_id", None)
            if not continuation_id:
                # Start fresh if no continuation available
                self.logger.info("    1.2.0: Starting fresh planning session")
                response0, continuation_id = self.call_mcp_tool(
                    "planner",
                    {
                        "step": "Planning API security strategy",
                        "step_number": 1,
                        "total_steps": 2,
                        "next_step_required": True,
                        "model": "flash",
                    },
                )
                if not response0 or not continuation_id:
                    self.logger.error("Failed to start fresh planning session")
                    return False

            # Test continuation step
            self.logger.info("    1.2.1: Continue planning session")
            response1, _ = self.call_mcp_tool(
                "planner",
                {
                    "step": "Building on the API redesign, let me now plan the security implementation with OAuth 2.0, API keys, and rate limiting strategies.",
                    "step_number": 2,
                    "total_steps": 2,
                    "next_step_required": True,
                    "continuation_id": continuation_id,
                    "model": "flash",
                },
            )

            if not response1:
                self.logger.error("Failed to continue planning")
                return False

            response1_data = self._parse_planner_response(response1)
            if not response1_data:
                return False

            # Validate continuation behavior
            if not self._validate_step_response(response1_data, 2, 2, True, "pause_for_planner"):
                return False

            # Check that continuation_id is preserved
            if response1_data.get("continuation_id") != continuation_id:
                self.logger.error("Continuation ID not preserved in workflow")
                return False

            self.logger.info("    ✅ Planning continuation working with workflow")
            return True

        except Exception as e:
            self.logger.error(f"Planning continuation test failed: {e}")
            return False

    def _test_complex_plan_deep_thinking(self) -> bool:
        """Test complex plan with deep thinking pauses"""
        try:
            self.logger.info("  1.3: Testing complex plan with deep thinking pauses")

            # Start complex plan (≥5 steps) - should trigger deep thinking
            self.logger.info("    1.3.1: Step 1 of complex plan (should trigger deep thinking)")
            response1, continuation_id = self.call_mcp_tool(
                "planner",
                {
                    "step": "I need to plan a complete digital transformation for our enterprise organization, including cloud migration, process automation, and cultural change management.",
                    "step_number": 1,
                    "total_steps": 8,  # Complex plan ≥5 steps
                    "next_step_required": True,
                    "model": "flash",
                },
            )

            if not response1 or not continuation_id:
                self.logger.error("Failed to start complex planning")
                return False

            response1_data = self._parse_planner_response(response1)
            if not response1_data:
                return False

            # Should trigger deep thinking pause for complex plan
            if response1_data.get("status") != "pause_for_deep_thinking":
                self.logger.error("Expected deep thinking pause for complex plan step 1")
                return False

            if not response1_data.get("thinking_required"):
                self.logger.error("Expected thinking_required=true for complex plan")
                return False

            # Check required thinking actions
            required_thinking = response1_data.get("required_thinking", [])
            if len(required_thinking) < 4:
                self.logger.error("Expected comprehensive thinking requirements for complex plan")
                return False

            # Check for deep thinking guidance in next_steps
            next_steps = response1_data.get("next_steps", "")
            if "MANDATORY" not in next_steps or "deep thinking" not in next_steps.lower():
                self.logger.error("Expected mandatory deep thinking guidance")
                return False

            self.logger.info("    ✅ Complex plan step 1 correctly triggered deep thinking pause")

            # Step 2 of complex plan - should also trigger deep thinking
            self.logger.info("    1.3.2: Step 2 of complex plan (should trigger deep thinking)")
            response2, _ = self.call_mcp_tool(
                "planner",
                {
                    "step": "After deep analysis, I can see this transformation requires three parallel tracks: Technical Infrastructure, Business Process, and Human Capital. Let me design the coordination strategy.",
                    "step_number": 2,
                    "total_steps": 8,
                    "next_step_required": True,
                    "continuation_id": continuation_id,
                    "model": "flash",
                },
            )

            if not response2:
                self.logger.error("Failed to continue complex planning")
                return False

            response2_data = self._parse_planner_response(response2)
            if not response2_data:
                return False

            # Step 2 should also trigger deep thinking for complex plans
            if response2_data.get("status") != "pause_for_deep_thinking":
                self.logger.error("Expected deep thinking pause for complex plan step 2")
                return False

            self.logger.info("    ✅ Complex plan step 2 correctly triggered deep thinking pause")

            # Step 4 of complex plan - should use normal flow (after step 3)
            self.logger.info("    1.3.3: Step 4 of complex plan (should use normal flow)")
            response4, _ = self.call_mcp_tool(
                "planner",
                {
                    "step": "Now moving to tactical planning: Phase 1 execution details with specific timelines and resource allocation for the technical infrastructure track.",
                    "step_number": 4,
                    "total_steps": 8,
                    "next_step_required": True,
                    "continuation_id": continuation_id,
                    "model": "flash",
                },
            )

            if not response4:
                self.logger.error("Failed to continue to step 4")
                return False

            response4_data = self._parse_planner_response(response4)
            if not response4_data:
                return False

            # Step 4 should use normal flow (no more deep thinking pauses)
            if response4_data.get("status") != "pause_for_planner":
                self.logger.error("Expected normal planning flow for step 4")
                return False

            if response4_data.get("thinking_required"):
                self.logger.error("Step 4 should not require special thinking pause")
                return False

            self.logger.info("    ✅ Complex plan transitions to normal flow after step 3")
            return True

        except Exception as e:
            self.logger.error(f"Complex plan deep thinking test failed: {e}")
            return False

    def _test_self_contained_completion(self) -> bool:
        """Test self-contained completion without expert analysis"""
        try:
            self.logger.info("  1.4: Testing self-contained completion")

            # Simple planning session that should complete without expert analysis
            self.logger.info("    1.4.1: Simple planning session")
            response1, continuation_id = self.call_mcp_tool(
                "planner",
                {
                    "step": "Planning a simple website redesign with new color scheme and improved navigation.",
                    "step_number": 1,
                    "total_steps": 2,
                    "next_step_required": True,
                    "model": "flash",
                },
            )

            if not response1 or not continuation_id:
                self.logger.error("Failed to start simple planning")
                return False

            # Final step - should complete without expert analysis
            self.logger.info("    1.4.2: Final step - self-contained completion")
            response2, _ = self.call_mcp_tool(
                "planner",
                {
                    "step": "Website redesign plan complete: Phase 1 - Update color palette and typography, Phase 2 - Redesign navigation structure and user flows.",
                    "step_number": 2,
                    "total_steps": 2,
                    "next_step_required": False,  # Final step
                    "continuation_id": continuation_id,
                    "model": "flash",
                },
            )

            if not response2:
                self.logger.error("Failed to complete simple planning")
                return False

            response2_data = self._parse_planner_response(response2)
            if not response2_data:
                return False

            # Validate self-contained completion
            if response2_data.get("status") != "planner_complete":
                self.logger.error("Expected self-contained completion status")
                return False

            # Should NOT call expert analysis
            if "expert_analysis" in response2_data:
                self.logger.error("PlannerWorkflow should not call expert analysis")
                return False

            # Should have planning_complete flag
            if not response2_data.get("planning_complete"):
                self.logger.error("Expected planning_complete=true")
                return False

            # Should have plan_summary
            if not response2_data.get("plan_summary"):
                self.logger.error("Expected plan_summary in completion")
                return False

            # Check completion instructions
            output = response2_data.get("output", {})
            if not output.get("instructions"):
                self.logger.error("Missing output instructions for plan presentation")
                return False

            self.logger.info("    ✅ Self-contained completion working correctly")
            return True

        except Exception as e:
            self.logger.error(f"Self-contained completion test failed: {e}")
            return False

    def _test_branching_and_revision(self) -> bool:
        """Test branching and revision with workflow architecture"""
        try:
            self.logger.info("  1.5: Testing branching and revision with workflow")

            # Start planning session for branching test
            self.logger.info("    1.5.1: Start planning for branching test")
            response1, continuation_id = self.call_mcp_tool(
                "planner",
                {
                    "step": "Planning mobile app development strategy with different technology options to evaluate.",
                    "step_number": 1,
                    "total_steps": 4,
                    "next_step_required": True,
                    "model": "flash",
                },
            )

            if not response1 or not continuation_id:
                self.logger.error("Failed to start branching test")
                return False

            # Create branch
            self.logger.info("    1.5.2: Create branch for React Native approach")
            response2, _ = self.call_mcp_tool(
                "planner",
                {
                    "step": "Branch A: React Native approach - cross-platform development with shared codebase, faster development cycle, and consistent UI across platforms.",
                    "step_number": 2,
                    "total_steps": 4,
                    "next_step_required": True,
                    "is_branch_point": True,
                    "branch_from_step": 1,
                    "branch_id": "react-native",
                    "continuation_id": continuation_id,
                    "model": "flash",
                },
            )

            if not response2:
                self.logger.error("Failed to create branch")
                return False

            response2_data = self._parse_planner_response(response2)
            if not response2_data:
                return False

            # Validate branching in workflow
            metadata = response2_data.get("metadata", {})
            if not metadata.get("is_branch_point"):
                self.logger.error("Branch point not recorded in workflow")
                return False

            if metadata.get("branch_id") != "react-native":
                self.logger.error("Branch ID not properly recorded")
                return False

            if "react-native" not in metadata.get("branches", []):
                self.logger.error("Branch not added to branches list")
                return False

            self.logger.info("    ✅ Branching working with workflow architecture")

            # Test revision
            self.logger.info("    1.5.3: Test revision capability")
            response3, _ = self.call_mcp_tool(
                "planner",
                {
                    "step": "Revision of step 2: After consideration, let me revise the React Native approach to include performance optimizations and native module integration for critical features.",
                    "step_number": 3,
                    "total_steps": 4,
                    "next_step_required": True,
                    "is_step_revision": True,
                    "revises_step_number": 2,
                    "continuation_id": continuation_id,
                    "model": "flash",
                },
            )

            if not response3:
                self.logger.error("Failed to create revision")
                return False

            response3_data = self._parse_planner_response(response3)
            if not response3_data:
                return False

            # Validate revision in workflow
            metadata = response3_data.get("metadata", {})
            if not metadata.get("is_step_revision"):
                self.logger.error("Step revision not recorded in workflow")
                return False

            if metadata.get("revises_step_number") != 2:
                self.logger.error("Revised step number not properly recorded")
                return False

            self.logger.info("    ✅ Revision working with workflow architecture")
            return True

        except Exception as e:
            self.logger.error(f"Branching and revision test failed: {e}")
            return False

    def _test_workflow_file_context(self) -> bool:
        """Test workflow file context behavior (should be minimal for planner)"""
        try:
            self.logger.info("  1.6: Testing workflow file context behavior")

            # Planner typically doesn't use files, but test the workflow handles this correctly
            self.logger.info("    1.6.1: Planning step with no files (normal case)")
            response1, continuation_id = self.call_mcp_tool(
                "planner",
                {
                    "step": "Planning data architecture for analytics platform.",
                    "step_number": 1,
                    "total_steps": 2,
                    "next_step_required": True,
                    "model": "flash",
                },
            )

            if not response1 or not continuation_id:
                self.logger.error("Failed to start workflow file context test")
                return False

            response1_data = self._parse_planner_response(response1)
            if not response1_data:
                return False

            # Planner workflow should not have file_context since it doesn't use files
            if "file_context" in response1_data:
                self.logger.info("    ℹ️ Workflow file context present but should be minimal for planner")

            # Final step
            self.logger.info("    1.6.2: Final step (should complete without file embedding)")
            response2, _ = self.call_mcp_tool(
                "planner",
                {
                    "step": "Data architecture plan complete with data lakes, processing pipelines, and analytics layers.",
                    "step_number": 2,
                    "total_steps": 2,
                    "next_step_required": False,
                    "continuation_id": continuation_id,
                    "model": "flash",
                },
            )

            if not response2:
                self.logger.error("Failed to complete workflow file context test")
                return False

            response2_data = self._parse_planner_response(response2)
            if not response2_data:
                return False

            # Final step should complete self-contained
            if response2_data.get("status") != "planner_complete":
                self.logger.error("Expected self-contained completion for planner workflow")
                return False

            self.logger.info("    ✅ Workflow file context behavior appropriate for planner")
            return True

        except Exception as e:
            self.logger.error(f"Workflow file context test failed: {e}")
            return False

    def call_mcp_tool(self, tool_name: str, params: dict) -> tuple[Optional[str], Optional[str]]:
        """Call an MCP tool in-process - override for planner-specific response handling"""
        # Use in-process implementation to maintain conversation memory
        response_text, _ = self.call_mcp_tool_direct(tool_name, params)

        if not response_text:
            return None, None

        # Extract continuation_id from planner response specifically
        continuation_id = self._extract_planner_continuation_id(response_text)

        return response_text, continuation_id

    def _extract_planner_continuation_id(self, response_text: str) -> Optional[str]:
        """Extract continuation_id from planner response"""
        try:
            # Parse the response
            response_data = json.loads(response_text)
            return response_data.get("continuation_id")

        except json.JSONDecodeError as e:
            self.logger.debug(f"Failed to parse response for planner continuation_id: {e}")
            return None

    def _parse_planner_response(self, response_text: str) -> dict:
        """Parse planner tool JSON response"""
        try:
            # Parse the response - it should be direct JSON
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse planner response as JSON: {e}")
            self.logger.error(f"Response text: {response_text[:500]}...")
            return {}

    def _validate_step_response(
        self,
        response_data: dict,
        expected_step: int,
        expected_total: int,
        expected_next_required: bool,
        expected_status: str,
    ) -> bool:
        """Validate a planner step response structure"""
        try:
            # Check status
            if response_data.get("status") != expected_status:
                self.logger.error(f"Expected status '{expected_status}', got '{response_data.get('status')}'")
                return False

            # Check step number
            if response_data.get("step_number") != expected_step:
                self.logger.error(f"Expected step_number {expected_step}, got {response_data.get('step_number')}")
                return False

            # Check total steps
            if response_data.get("total_steps") != expected_total:
                self.logger.error(f"Expected total_steps {expected_total}, got {response_data.get('total_steps')}")
                return False

            # Check next_step_required
            if response_data.get("next_step_required") != expected_next_required:
                self.logger.error(
                    f"Expected next_step_required {expected_next_required}, got {response_data.get('next_step_required')}"
                )
                return False

            # Check step_content exists
            if not response_data.get("step_content"):
                self.logger.error("Missing step_content in response")
                return False

            # Check next_steps guidance
            if not response_data.get("next_steps"):
                self.logger.error("Missing next_steps guidance in response")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating step response: {e}")
            return False
