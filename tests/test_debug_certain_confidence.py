"""
Integration tests for the debug tool's 'certain' confidence feature.

Tests the complete workflow where Claude identifies obvious bugs with absolute certainty
and can skip expensive expert analysis for minimal fixes.
"""

import json
from unittest.mock import patch

import pytest

from tools.debug import DebugIssueTool


class TestDebugCertainConfidence:
    """Integration tests for certain confidence optimization."""

    def setup_method(self):
        """Set up test tool instance."""
        self.tool = DebugIssueTool()

    @pytest.mark.asyncio
    async def test_certain_confidence_skips_expert_analysis(self):
        """Test that certain confidence with valid minimal fix skips expert analysis."""
        # Simulate a multi-step investigation ending with certain confidence

        # Step 1: Initial investigation
        with patch("utils.conversation_memory.create_thread", return_value="debug-certain-uuid"):
            with patch("utils.conversation_memory.add_turn"):
                result1 = await self.tool.execute(
                    {
                        "step": "Investigating Python ImportError in user authentication module",
                        "step_number": 1,
                        "total_steps": 2,
                        "next_step_required": True,
                        "findings": "Users cannot log in, getting 'ModuleNotFoundError: No module named hashlib'",
                        "files_checked": ["/auth/user_auth.py"],
                        "relevant_files": ["/auth/user_auth.py"],
                        "hypothesis": "Missing import statement",
                        "confidence": "medium",
                        "continuation_id": None,
                    }
                )

        # Verify step 1 response
        response1 = json.loads(result1[0].text)
        assert response1["status"] == "pause_for_investigation"
        assert response1["step_number"] == 1
        assert response1["investigation_required"] is True
        assert "required_actions" in response1
        continuation_id = response1["continuation_id"]

        # Step 2: Final step with certain confidence (simple import fix)
        with patch("utils.conversation_memory.add_turn"):
            result2 = await self.tool.execute(
                {
                    "step": "Found the exact issue and fix",
                    "step_number": 2,
                    "total_steps": 2,
                    "next_step_required": False,  # Final step
                    "findings": "Missing 'import hashlib' statement at top of user_auth.py file, line 3. Simple one-line fix required.",
                    "files_checked": ["/auth/user_auth.py"],
                    "relevant_files": ["/auth/user_auth.py"],
                    "relevant_methods": ["UserAuth.hash_password"],
                    "hypothesis": "Missing import hashlib statement causes ModuleNotFoundError when hash_password method is called",
                    "confidence": "certain",  # NAILEDIT confidence - should skip expert analysis
                    "continuation_id": continuation_id,
                }
            )

        # Verify final response skipped expert analysis
        response2 = json.loads(result2[0].text)

        # Should indicate certain confidence was used
        assert response2["status"] == "certain_confidence_proceed_with_fix"
        assert response2["investigation_complete"] is True
        assert response2["skip_expert_analysis"] is True

        # Expert analysis should be marked as skipped
        assert response2["expert_analysis"]["status"] == "skipped_due_to_certain_confidence"
        assert (
            response2["expert_analysis"]["reason"] == "Claude identified exact root cause with minimal fix requirement"
        )

        # Should have complete investigation summary
        assert "complete_investigation" in response2
        assert response2["complete_investigation"]["confidence_level"] == "certain"
        assert response2["complete_investigation"]["steps_taken"] == 2

        # Next steps should guide Claude to implement the fix directly
        assert "CERTAIN confidence" in response2["next_steps"]
        assert "minimal fix" in response2["next_steps"]
        assert "without requiring further consultation" in response2["next_steps"]

    @pytest.mark.asyncio
    async def test_certain_confidence_always_trusted(self):
        """Test that certain confidence is always trusted, even for complex issues."""

        # Set up investigation state
        self.tool.initial_issue = "Any kind of issue"
        self.tool.investigation_history = [
            {
                "step_number": 1,
                "step": "Initial investigation",
                "findings": "Some findings",
                "files_checked": [],
                "relevant_files": [],
                "relevant_methods": [],
                "hypothesis": None,
                "confidence": "low",
            }
        ]
        self.tool.consolidated_findings = {
            "files_checked": set(),
            "relevant_files": set(),
            "relevant_methods": set(),
            "findings": ["Step 1: Some findings"],
            "hypotheses": [],
            "images": [],
        }

        # Final step with certain confidence - should ALWAYS be trusted
        with patch("utils.conversation_memory.add_turn"):
            result = await self.tool.execute(
                {
                    "step": "Found the issue and fix",
                    "step_number": 2,
                    "total_steps": 2,
                    "next_step_required": False,  # Final step
                    "findings": "Complex or simple, doesn't matter - Claude says certain",
                    "files_checked": ["/any/file.py"],
                    "relevant_files": ["/any/file.py"],
                    "relevant_methods": ["any_method"],
                    "hypothesis": "Claude has decided this is certain - trust the judgment",
                    "confidence": "certain",  # Should always be trusted
                    "continuation_id": "debug-trust-uuid",
                }
            )

        # Verify certain is always trusted
        response = json.loads(result[0].text)

        # Should proceed with certain confidence
        assert response["status"] == "certain_confidence_proceed_with_fix"
        assert response["investigation_complete"] is True
        assert response["skip_expert_analysis"] is True

        # Expert analysis should be skipped
        assert response["expert_analysis"]["status"] == "skipped_due_to_certain_confidence"

        # Next steps should guide Claude to implement fix directly
        assert "CERTAIN confidence" in response["next_steps"]

    @pytest.mark.asyncio
    async def test_regular_high_confidence_still_uses_expert_analysis(self):
        """Test that regular 'high' confidence still triggers expert analysis."""

        # Set up investigation state
        self.tool.initial_issue = "Session validation issue"
        self.tool.investigation_history = [
            {
                "step_number": 1,
                "step": "Initial investigation",
                "findings": "Found session issue",
                "files_checked": [],
                "relevant_files": [],
                "relevant_methods": [],
                "hypothesis": None,
                "confidence": "low",
            }
        ]
        self.tool.consolidated_findings = {
            "files_checked": set(),
            "relevant_files": {"/api/sessions.py"},
            "relevant_methods": {"SessionManager.validate"},
            "findings": ["Step 1: Found session issue"],
            "hypotheses": [],
            "images": [],
        }

        # Mock expert analysis
        mock_expert_response = {
            "status": "analysis_complete",
            "summary": "Expert analysis of session validation",
            "hypotheses": [
                {
                    "name": "SESSION_VALIDATION_BUG",
                    "confidence": "High",
                    "root_cause": "Session timeout not properly handled",
                }
            ],
        }

        # Final step with regular 'high' confidence (should trigger expert analysis)
        with patch("utils.conversation_memory.add_turn"):
            with patch.object(self.tool, "_call_expert_analysis", return_value=mock_expert_response):
                with patch.object(self.tool, "_prepare_file_content_for_prompt", return_value=("file content", 100)):
                    result = await self.tool.execute(
                        {
                            "step": "Identified likely root cause",
                            "step_number": 2,
                            "total_steps": 2,
                            "next_step_required": False,  # Final step
                            "findings": "Session validation fails when timeout occurs during user activity",
                            "files_checked": ["/api/sessions.py"],
                            "relevant_files": ["/api/sessions.py"],
                            "relevant_methods": ["SessionManager.validate", "SessionManager.cleanup"],
                            "hypothesis": "Session timeout handling bug causes validation failures",
                            "confidence": "high",  # Regular high confidence, NOT certain
                            "continuation_id": "debug-regular-uuid",
                        }
                    )

        # Verify expert analysis was called (not skipped)
        response = json.loads(result[0].text)

        # Should call expert analysis normally
        assert response["status"] == "calling_expert_analysis"
        assert response["investigation_complete"] is True
        assert "skip_expert_analysis" not in response  # Should not be present

        # Expert analysis should be present with real results
        assert response["expert_analysis"]["status"] == "analysis_complete"
        assert response["expert_analysis"]["summary"] == "Expert analysis of session validation"

        # Next steps should indicate normal investigation completion (not certain confidence)
        assert "INVESTIGATION IS COMPLETE" in response["next_steps"]
        assert "certain" not in response["next_steps"].lower()

    def test_certain_confidence_schema_requirements(self):
        """Test that certain confidence is properly described in schema for Claude's guidance."""

        # The schema description should guide Claude on proper certain usage
        schema = self.tool.get_input_schema()
        confidence_description = schema["properties"]["confidence"]["description"]

        # Should emphasize it's only when root cause and fix are confirmed
        assert "root cause" in confidence_description.lower()
        assert "minimal fix" in confidence_description.lower()
        assert "confirmed" in confidence_description.lower()

        # Should emphasize trust in Claude's judgment
        assert "absolutely" in confidence_description.lower() or "certain" in confidence_description.lower()

        # Should mention no thought-partner assistance needed
        assert "thought-partner" in confidence_description.lower() or "assistance" in confidence_description.lower()

    @pytest.mark.asyncio
    async def test_confidence_enum_validation(self):
        """Test that certain is properly included in confidence enum validation."""

        # Valid confidence values should not raise errors
        valid_confidences = ["low", "medium", "high", "certain"]

        for confidence in valid_confidences:
            # This should not raise validation errors
            with patch("utils.conversation_memory.create_thread", return_value="test-uuid"):
                with patch("utils.conversation_memory.add_turn"):
                    result = await self.tool.execute(
                        {
                            "step": f"Test step with {confidence} confidence",
                            "step_number": 1,
                            "total_steps": 1,
                            "next_step_required": False,
                            "findings": "Test findings",
                            "confidence": confidence,
                        }
                    )

            # Should get valid response
            response = json.loads(result[0].text)
            assert "error" not in response or response.get("status") != "investigation_failed"

    def test_tool_schema_includes_certain(self):
        """Test that the tool schema properly includes certain in confidence enum."""
        schema = self.tool.get_input_schema()

        confidence_property = schema["properties"]["confidence"]
        assert confidence_property["type"] == "string"
        assert "certain" in confidence_property["enum"]
        assert confidence_property["enum"] == ["exploring", "low", "medium", "high", "certain"]

        # Check that description explains certain usage
        description = confidence_property["description"]
        assert "certain" in description.lower()
        assert "root cause" in description.lower()
        assert "minimal fix" in description.lower()
        assert "thought-partner" in description.lower()

    @pytest.mark.asyncio
    async def test_certain_confidence_preserves_investigation_data(self):
        """Test that certain confidence path preserves all investigation data properly."""

        # Multi-step investigation leading to certain
        with patch("utils.conversation_memory.create_thread", return_value="preserve-data-uuid"):
            with patch("utils.conversation_memory.add_turn"):
                # Step 1
                await self.tool.execute(
                    {
                        "step": "Initial investigation of login failure",
                        "step_number": 1,
                        "total_steps": 3,
                        "next_step_required": True,
                        "findings": "Users can't log in after password reset",
                        "files_checked": ["/auth/password.py"],
                        "relevant_files": ["/auth/password.py"],
                        "confidence": "low",
                    }
                )

                # Step 2
                await self.tool.execute(
                    {
                        "step": "Examining password validation logic",
                        "step_number": 2,
                        "total_steps": 3,
                        "next_step_required": True,
                        "findings": "Password hash function not imported correctly",
                        "files_checked": ["/auth/password.py", "/utils/crypto.py"],
                        "relevant_files": ["/auth/password.py"],
                        "relevant_methods": ["PasswordManager.validate_password"],
                        "hypothesis": "Import statement issue",
                        "confidence": "medium",
                        "continuation_id": "preserve-data-uuid",
                    }
                )

                # Step 3: Final with certain
                result = await self.tool.execute(
                    {
                        "step": "Found exact issue and fix",
                        "step_number": 3,
                        "total_steps": 3,
                        "next_step_required": False,
                        "findings": "Missing 'from utils.crypto import hash_password' at line 5",
                        "files_checked": ["/auth/password.py", "/utils/crypto.py"],
                        "relevant_files": ["/auth/password.py"],
                        "relevant_methods": ["PasswordManager.validate_password", "hash_password"],
                        "hypothesis": "Missing import statement for hash_password function",
                        "confidence": "certain",
                        "continuation_id": "preserve-data-uuid",
                    }
                )

        # Verify all investigation data is preserved
        response = json.loads(result[0].text)

        assert response["status"] == "certain_confidence_proceed_with_fix"

        investigation = response["complete_investigation"]
        assert investigation["steps_taken"] == 3
        assert len(investigation["files_examined"]) == 2  # Both files from all steps
        assert "/auth/password.py" in investigation["files_examined"]
        assert "/utils/crypto.py" in investigation["files_examined"]
        assert len(investigation["relevant_files"]) == 1
        assert len(investigation["relevant_methods"]) == 2
        assert investigation["confidence_level"] == "certain"

        # Should have complete investigation summary
        assert "SYSTEMATIC INVESTIGATION SUMMARY" in investigation["investigation_summary"]
        assert (
            "Steps taken: 3" in investigation["investigation_summary"]
            or "Total steps: 3" in investigation["investigation_summary"]
        )
