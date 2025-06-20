"""
Unit tests for workflow file embedding behavior

Tests the critical file embedding logic for workflow tools:
- Intermediate steps: Only reference file names (save Claude's context)
- Final steps: Embed full file content for expert analysis
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from tools.workflow.workflow_mixin import BaseWorkflowMixin


class TestWorkflowFileEmbedding:
    """Test workflow file embedding behavior"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create a mock workflow tool
        self.mock_tool = Mock(spec=BaseWorkflowMixin)
        self.mock_tool.get_name.return_value = "test_workflow"
        
        # Initialize the mixin methods
        BaseWorkflowMixin.__init__(self.mock_tool)
        
        # Bind the methods we want to test
        self.mock_tool._should_embed_files_in_workflow_step = BaseWorkflowMixin._should_embed_files_in_workflow_step.__get__(self.mock_tool)
        
        # Create test files
        self.test_files = []
        for i in range(2):
            fd, path = tempfile.mkstemp(suffix=f'_test_{i}.py')
            with os.fdopen(fd, 'w') as f:
                f.write(f"# Test file {i}\nprint('hello world {i}')\n")
            self.test_files.append(path)

    def teardown_method(self):
        """Clean up test files"""
        for file_path in self.test_files:
            try:
                os.unlink(file_path)
            except OSError:
                pass

    def test_intermediate_step_no_embedding(self):
        """Test that intermediate steps only reference files, don't embed"""
        # Intermediate step: step_number=1, next_step_required=True
        step_number = 1
        continuation_id = None  # New conversation
        is_final_step = False  # next_step_required=True
        
        should_embed = self.mock_tool._should_embed_files_in_workflow_step(
            step_number, continuation_id, is_final_step
        )
        
        assert should_embed is False, "Intermediate steps should NOT embed files"

    def test_intermediate_step_with_continuation_no_embedding(self):
        """Test that intermediate steps with continuation only reference files"""
        # Intermediate step with continuation: step_number=2, next_step_required=True
        step_number = 2
        continuation_id = "test-thread-123"  # Continuing conversation
        is_final_step = False  # next_step_required=True
        
        should_embed = self.mock_tool._should_embed_files_in_workflow_step(
            step_number, continuation_id, is_final_step
        )
        
        assert should_embed is False, "Intermediate steps with continuation should NOT embed files"

    def test_final_step_embeds_files(self):
        """Test that final steps embed full file content for expert analysis"""
        # Final step: any step_number, next_step_required=False
        step_number = 3
        continuation_id = "test-thread-123"
        is_final_step = True  # next_step_required=False
        
        should_embed = self.mock_tool._should_embed_files_in_workflow_step(
            step_number, continuation_id, is_final_step
        )
        
        assert should_embed is True, "Final steps SHOULD embed files for expert analysis"

    def test_final_step_new_conversation_embeds_files(self):
        """Test that final steps in new conversations embed files"""
        # Final step in new conversation (rare but possible): step_number=1, next_step_required=False
        step_number = 1
        continuation_id = None  # New conversation
        is_final_step = True  # next_step_required=False (one-step workflow)
        
        should_embed = self.mock_tool._should_embed_files_in_workflow_step(
            step_number, continuation_id, is_final_step
        )
        
        assert should_embed is True, "Final steps in new conversations SHOULD embed files"

    @patch('utils.file_utils.read_files')
    @patch('utils.file_utils.expand_paths')
    def test_force_embed_bypasses_conversation_history(self, mock_expand_paths, mock_read_files):
        """Test that _force_embed_files_for_expert_analysis bypasses conversation filtering"""
        # Setup mocks
        mock_expand_paths.return_value = self.test_files
        mock_read_files.return_value = "# File content\nprint('test')"
        
        # Mock model context for token allocation
        mock_model_context = Mock()
        mock_token_allocation = Mock()
        mock_token_allocation.file_tokens = 100000
        mock_model_context.calculate_token_allocation.return_value = mock_token_allocation
        
        # Bind the method and set up the tool
        self.mock_tool._force_embed_files_for_expert_analysis = BaseWorkflowMixin._force_embed_files_for_expert_analysis.__get__(self.mock_tool)
        self.mock_tool.get_current_model_context.return_value = mock_model_context
        self.mock_tool.wants_line_numbers_by_default.return_value = True
        
        # Call the method
        file_content, processed_files = self.mock_tool._force_embed_files_for_expert_analysis(self.test_files)
        
        # Verify it called read_files directly (bypassing conversation history filtering)
        mock_read_files.assert_called_once_with(
            self.test_files,
            max_tokens=100000,
            reserve_tokens=1000,
            include_line_numbers=True,
        )
        
        # Verify it expanded paths to get individual files
        mock_expand_paths.assert_called_once_with(self.test_files)
        
        # Verify return values
        assert file_content == "# File content\nprint('test')"
        assert processed_files == self.test_files

    def test_embedding_decision_logic_comprehensive(self):
        """Comprehensive test of the embedding decision logic"""
        test_cases = [
            # (step_number, continuation_id, is_final_step, expected_embed, description)
            (1, None, False, False, "Step 1 new conversation, intermediate"),
            (1, None, True, True, "Step 1 new conversation, final (one-step workflow)"),
            (2, "thread-123", False, False, "Step 2 with continuation, intermediate"),
            (2, "thread-123", True, True, "Step 2 with continuation, final"),
            (5, "thread-456", False, False, "Step 5 with continuation, intermediate"),
            (5, "thread-456", True, True, "Step 5 with continuation, final"),
        ]
        
        for step_number, continuation_id, is_final_step, expected_embed, description in test_cases:
            should_embed = self.mock_tool._should_embed_files_in_workflow_step(
                step_number, continuation_id, is_final_step
            )
            
            assert should_embed == expected_embed, f"Failed for: {description}"


if __name__ == "__main__":
    pytest.main([__file__])