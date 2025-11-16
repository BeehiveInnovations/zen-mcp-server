"""
Tests for cassette semantic matching to prevent breaks from prompt changes.

This validates that o3 model cassettes match on semantic content (model + user question)
rather than exact request bodies, preventing cassette breaks when system prompts change.
"""

import hashlib
import json

import pytest

from tests.http_transport_recorder import ReplayTransport


class TestCassetteSemanticMatching:
    """Test that cassette matching is resilient to prompt changes."""

    @pytest.fixture
    def dummy_cassette(self, tmp_path):
        """Create a minimal dummy cassette file."""
        cassette_file = tmp_path / "dummy.json"
        cassette_file.write_text(json.dumps({"interactions": []}))
        return cassette_file

    def test_o3_model_semantic_matching(self, dummy_cassette):
        """Test that o3 models use semantic matching."""
        transport = ReplayTransport(str(dummy_cassette))

        # Two requests with same user question but different system prompts
        request1_body = {
            "model": "o3-pro",
            "reasoning": {"effort": "medium"},
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "System prompt v1...\n\n=== USER REQUEST ===\nWhat is 2 + 2?\n=== END REQUEST ===\n\nMore instructions...",
                        }
                    ],
                }
            ],
        }

        request2_body = {
            "model": "o3-pro",
            "reasoning": {"effort": "medium"},
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "System prompt v2 (DIFFERENT)...\n\n=== USER REQUEST ===\nWhat is 2 + 2?\n=== END REQUEST ===\n\nDifferent instructions...",
                        }
                    ],
                }
            ],
        }

        # Extract semantic fields - should be identical
        semantic1 = transport._extract_semantic_fields(request1_body)
        semantic2 = transport._extract_semantic_fields(request2_body)

        assert semantic1 == semantic2, "Semantic fields should match despite different prompts"
        assert semantic1["user_question"] == "What is 2 + 2?"
        assert semantic1["model"] == "o3-pro"
        assert semantic1["reasoning"] == {"effort": "medium"}

        # Generate signatures - should be identical
        content1 = json.dumps(semantic1, sort_keys=True)
        content2 = json.dumps(semantic2, sort_keys=True)
        hash1 = hashlib.md5(content1.encode()).hexdigest()
        hash2 = hashlib.md5(content2.encode()).hexdigest()

        assert hash1 == hash2, "Hashes should match for same semantic content"

    def test_non_o3_model_exact_matching(self, dummy_cassette):
        """Test that non-o3 models still use exact matching."""
        transport = ReplayTransport(str(dummy_cassette))

        request_body = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "test"}],
        }

        # Should not use semantic matching
        assert not transport._is_o3_model_request(request_body)

    def test_o3_mini_semantic_matching(self, dummy_cassette):
        """Test that o3-mini also uses semantic matching."""
        transport = ReplayTransport(str(dummy_cassette))

        request_body = {
            "model": "o3-mini",
            "reasoning": {"effort": "low"},
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "System...\n\n=== USER REQUEST ===\nTest\n=== END REQUEST ==="}
                    ],
                }
            ],
        }

        assert transport._is_o3_model_request(request_body)
        semantic = transport._extract_semantic_fields(request_body)
        assert semantic["model"] == "o3-mini"
        assert semantic["user_question"] == "Test"

    def test_o3_without_request_markers(self, dummy_cassette):
        """Test o3 requests without REQUEST markers fall back to full text."""
        transport = ReplayTransport(str(dummy_cassette))

        request_body = {
            "model": "o3-pro",
            "reasoning": {"effort": "medium"},
            "input": [{"role": "user", "content": [{"type": "input_text", "text": "Just a simple question"}]}],
        }

        semantic = transport._extract_semantic_fields(request_body)
        assert semantic["user_question"] == "Just a simple question"
