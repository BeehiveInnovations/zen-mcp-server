"""Schema-related tests for ConsensusTool."""

from types import MethodType

from tools.consensus import ConsensusTool


def test_consensus_models_field_includes_available_models(monkeypatch):
    """Consensus schema should surface available model guidance like single-model tools."""

    tool = ConsensusTool()

    monkeypatch.setattr(
        tool,
        "_get_ranked_model_summaries",
        MethodType(lambda self, limit=5: (["gemini-2.5-pro (score 100, 1.0M ctx, thinking)"], 1, False), tool),
    )
    monkeypatch.setattr(tool, "_get_restriction_note", MethodType(lambda self: None, tool))

    schema = tool.get_input_schema()
    models_field_description = schema["properties"]["models"]["description"]

    assert "listmodels" in models_field_description
    assert "Top models" in models_field_description
