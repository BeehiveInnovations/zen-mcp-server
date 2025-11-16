import pytest

from clink.parsers.base import ParserError
from clink.parsers.codex import CodexJSONLParser


def test_codex_parser_success():
    parser = CodexJSONLParser()
    stdout = """
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"Hello"}}
{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":5}}
"""
    parsed = parser.parse(stdout=stdout, stderr="")
    assert parsed.content == "Hello"
    assert parsed.metadata["usage"]["output_tokens"] == 5


def test_codex_parser_requires_agent_message():
    parser = CodexJSONLParser()
    stdout = '{"type":"turn.completed"}'
    with pytest.raises(ParserError):
        parser.parse(stdout=stdout, stderr="")
