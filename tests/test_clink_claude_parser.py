"""Tests for the Claude CLI JSON parser."""

import pytest

from clink.parsers.base import ParserError
from clink.parsers.claude import ClaudeJSONParser


def _build_success_payload() -> str:
    return (
        '{"type":"result","subtype":"success","is_error":false,"duration_ms":1234,'
        '"duration_api_ms":1200,"num_turns":1,"result":"42","session_id":"abc","total_cost_usd":0.12,'
        '"usage":{"input_tokens":10,"output_tokens":5},'
        '"modelUsage":{"claude-sonnet-4-5-20250929":{"inputTokens":10,"outputTokens":5}}}'
    )


def test_claude_parser_extracts_result_and_metadata():
    parser = ClaudeJSONParser()
    stdout = _build_success_payload()

    parsed = parser.parse(stdout=stdout, stderr="")

    assert parsed.content == "42"
    assert parsed.metadata["model_used"] == "claude-sonnet-4-5-20250929"
    assert parsed.metadata["usage"]["output_tokens"] == 5
    assert parsed.metadata["is_error"] is False


def test_claude_parser_falls_back_to_message():
    parser = ClaudeJSONParser()
    stdout = '{"type":"result","is_error":true,"message":"API error message"}'

    parsed = parser.parse(stdout=stdout, stderr="warning")

    assert parsed.content == "API error message"
    assert parsed.metadata["is_error"] is True
    assert parsed.metadata["stderr"] == "warning"


def test_claude_parser_requires_output():
    parser = ClaudeJSONParser()

    with pytest.raises(ParserError):
        parser.parse(stdout="", stderr="")
