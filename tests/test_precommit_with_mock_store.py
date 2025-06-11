"""
Enhanced tests for precommit tool using mock storage to test real logic
"""

import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

import pytest

from tools.precommit import Precommit, PrecommitRequest


class MockRedisClient:
    """Mock Redis client that uses in-memory dictionary storage"""
    
    def __init__(self):
        self.data: Dict[str, str] = {}
        self.ttl_data: Dict[str, int] = {}
    
    def get(self, key: str) -> Optional[str]:
        return self.data.get(key)
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self.data[key] = value
        if ex:
            self.ttl_data[key] = ex
        return True
    
    def delete(self, key: str) -> int:
        if key in self.data:
            del self.data[key]
            self.ttl_data.pop(key, None)
            return 1
        return 0
    
    def exists(self, key: str) -> int:
        return 1 if key in self.data else 0


class TestPrecommitToolWithMockStore:
    """Test precommit tool with mock storage to validate actual logic"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        return MockRedisClient()
    
    @pytest.fixture
    def tool(self, mock_redis):
        """Create tool instance with mocked Redis"""
        tool = Precommit()
        
        # Mock the Redis client getter to return our mock
        with patch('utils.conversation_memory.get_redis_client', return_value=mock_redis):
            yield tool
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository with test files"""
        import subprocess
        
        temp_dir = tempfile.mkdtemp()
        
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_dir, capture_output=True)
        
        # Create test config file
        config_content = '''"""Test configuration file"""

# Version and metadata
__version__ = "1.0.0"
__author__ = "Test"

# Configuration
MAX_CONTENT_TOKENS = 800_000  # 800K tokens for content
TEMPERATURE_ANALYTICAL = 0.2  # For code review, debugging
'''
        
        config_path = os.path.join(temp_dir, 'config.py')
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Add and commit initial version
        subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_dir, capture_output=True)
        
        # Modify config to create a diff
        modified_content = config_content + '\nNEW_SETTING = "test"  # Added setting\n'
        with open(config_path, 'w') as f:
            f.write(modified_content)
        
        yield temp_dir, config_path
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_no_duplicate_file_content_in_prompt(self, tool, temp_repo, mock_redis):
        """Test that file content doesn't appear twice in the generated prompt"""
        temp_dir, config_path = temp_repo
        
        # Create request with files parameter  
        request = PrecommitRequest(
            path=temp_dir,
            files=[config_path],
            original_request="Test configuration changes"
        )
        
        # Generate the prompt
        prompt = await tool.prepare_prompt(request)
        
        # Test that MAX_CONTENT_TOKENS only appears once in the entire prompt
        max_content_count = prompt.count('MAX_CONTENT_TOKENS = 800_000')
        assert max_content_count == 1, f"MAX_CONTENT_TOKENS appears {max_content_count} times (should be 1)"
        
        # Test that the config file content only appears once
        config_content_count = prompt.count('# Configuration')
        assert config_content_count == 1, f"Config file content appears {config_content_count} times (should be 1)"
        
        # Verify expected sections are present
        assert "## Original Request" in prompt
        assert "Test configuration changes" in prompt
        assert "## Additional Context Files" in prompt
        assert "## Git Diffs" in prompt
    
    @pytest.mark.asyncio
    async def test_conversation_memory_integration(self, tool, temp_repo, mock_redis):
        """Test that conversation memory works with mock storage"""
        temp_dir, config_path = temp_repo
        
        # Mock conversation memory functions to use our mock redis
        with patch('utils.conversation_memory.get_redis_client', return_value=mock_redis):
            # First request - should embed file content
            request1 = PrecommitRequest(
                path=temp_dir,
                files=[config_path],
                original_request="First review"
            )
            
            # Simulate conversation thread creation
            from utils.conversation_memory import create_thread, add_turn
            thread_id = create_thread("precommit", {"files": [config_path]})
            
            # Test that file embedding works
            files_to_embed = tool.filter_new_files([config_path], None)
            assert config_path in files_to_embed, "New conversation should embed all files"
            
            # Add a turn to the conversation
            add_turn(thread_id, "assistant", "First response", files=[config_path], tool_name="precommit")
            
            # Second request with continuation - should skip already embedded files
            request2 = PrecommitRequest(
                path=temp_dir,
                files=[config_path],
                continuation_id=thread_id,
                original_request="Follow-up review"
            )
            
            files_to_embed_2 = tool.filter_new_files([config_path], thread_id)
            assert len(files_to_embed_2) == 0, "Continuation should skip already embedded files"
    
    @pytest.mark.asyncio 
    async def test_prompt_structure_integrity(self, tool, temp_repo, mock_redis):
        """Test that the prompt structure is well-formed and doesn't have content duplication"""
        temp_dir, config_path = temp_repo
        
        request = PrecommitRequest(
            path=temp_dir,
            files=[config_path],
            original_request="Validate prompt structure",
            review_type="full",
            severity_filter="high"
        )
        
        prompt = await tool.prepare_prompt(request)
        
        # Split prompt into sections
        sections = {
            "original_request": "## Original Request",
            "review_parameters": "## Review Parameters", 
            "repo_summary": "## Repository Changes Summary",
            "context_files_summary": "## Context Files Summary",
            "git_diffs": "## Git Diffs",
            "additional_context": "## Additional Context Files",
            "review_instructions": "## Review Instructions"
        }
        
        section_indices = {}
        for name, header in sections.items():
            index = prompt.find(header)
            if index != -1:
                section_indices[name] = index
        
        # Verify sections appear in logical order
        assert section_indices["original_request"] < section_indices["review_parameters"]
        assert section_indices["review_parameters"] < section_indices["repo_summary"]  
        assert section_indices["git_diffs"] < section_indices["additional_context"]
        assert section_indices["additional_context"] < section_indices["review_instructions"]
        
        # Test that file content only appears in Additional Context section
        file_content_start = section_indices["additional_context"]
        file_content_end = section_indices["review_instructions"]
        
        file_section = prompt[file_content_start:file_content_end]
        before_file_section = prompt[:file_content_start]
        after_file_section = prompt[file_content_end:]
        
        # MAX_CONTENT_TOKENS should only appear in the file section
        assert 'MAX_CONTENT_TOKENS' in file_section
        assert 'MAX_CONTENT_TOKENS' not in before_file_section
        assert 'MAX_CONTENT_TOKENS' not in after_file_section
    
    @pytest.mark.asyncio
    async def test_file_content_formatting(self, tool, temp_repo, mock_redis):
        """Test that file content is properly formatted without duplication"""
        temp_dir, config_path = temp_repo
        
        # Test the centralized file preparation method directly
        file_content = tool._prepare_file_content_for_prompt(
            [config_path],
            None,  # No continuation
            "Test files",
            max_tokens=100000,
            reserve_tokens=1000
        )
        
        # Should contain file markers
        assert "--- BEGIN FILE:" in file_content
        assert "--- END FILE:" in file_content
        assert "config.py" in file_content
        
        # Should contain actual file content
        assert "MAX_CONTENT_TOKENS = 800_000" in file_content
        assert "__version__ = \"1.0.0\"" in file_content
        
        # Content should appear only once
        assert file_content.count("MAX_CONTENT_TOKENS = 800_000") == 1
        assert file_content.count("__version__ = \"1.0.0\"") == 1


def test_mock_redis_basic_operations():
    """Test that our mock Redis implementation works correctly"""
    mock_redis = MockRedisClient()
    
    # Test basic operations
    assert mock_redis.get("nonexistent") is None
    assert mock_redis.exists("nonexistent") == 0
    
    mock_redis.set("test_key", "test_value")
    assert mock_redis.get("test_key") == "test_value"
    assert mock_redis.exists("test_key") == 1
    
    assert mock_redis.delete("test_key") == 1
    assert mock_redis.get("test_key") is None
    assert mock_redis.delete("test_key") == 0  # Already deleted