"""
Researcher Node.

Responsible for deep research, multi-model consensus, and information gathering.
"""

from agent.nodes.supervisor import get_llm
from agent.state import AgentState


def researcher_node(state: AgentState) -> dict:
    """
    The Researcher node function.
    """
    llm = get_llm()

    # Simple implementation for now: just call the LLM with the last message
    # In the future, this will use the consensus tool logic
    messages = state["messages"]
    response = llm.invoke(messages)

    return {"messages": [response]}
