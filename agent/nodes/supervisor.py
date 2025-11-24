"""
Supervisor Node.

This node acts as the router, deciding which worker node should handle the next step
based on the conversation history and the current state.
"""

import os
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from agent.llm_factory import get_llm
from agent.state import AgentState

# List of available worker nodes
MEMBERS = ["Architect", "Coder", "Researcher", "Reviewer", "Debugger", "Terminal", "Utilities"]


# Define the routing schema
class Route(BaseModel):
    """The next worker to act."""

    next: Literal["Architect", "Coder", "Researcher", "Reviewer", "Debugger", "Terminal", "Utilities", "FINISH"]


# System prompt for the supervisor
SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor of the Zen MCP Server.
Your goal is to manage the conversation and delegate tasks to the appropriate specialized workers.

Available Workers:
- Architect: High-level system design, refactoring strategies, and planning.
- Coder: Writing, modifying, and implementing code.
- Researcher: Deep research, multi-model consensus, and information gathering.
- Reviewer: Code quality checks, security audits, and pre-commit verification.
- Debugger: Root cause analysis, tracing, and fixing runtime issues.
- Terminal: Executing shell commands and managing the environment.
- Utilities: General helper tools (version, model list, etc.).

1. Analyze the user's request.
2. Decide which worker is best suited to handle the next step.
3. If the task is complete or requires user input, select 'FINISH'.
4. Do not do the work yourself; delegate to the workers.
"""


def _supervisor_llm():
    """Return LLM for supervisor using factory (respects gateway/direct toggle)."""
    # Allow override via SUPERVISOR_MODEL else fall back to LLM_MODEL or default
    override_model = os.getenv("SUPERVISOR_MODEL")
    return get_llm(model=override_model, temperature=0)


def supervisor_node(state: AgentState) -> dict:
    """
    The Supervisor node function.

    Decides the next step in the graph.
    """
    llm = _supervisor_llm()

    # Create the routing chain
    # We use with_structured_output to force the LLM to choose a valid route
    supervisor_chain = ChatPromptTemplate.from_messages(
        [
            ("system", SUPERVISOR_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            ("system", "Given the conversation above, who should act next? Select one of: {members} or FINISH."),
        ]
    ) | llm.with_structured_output(Route)

    # Invoke the chain
    result = supervisor_chain.invoke({"messages": state["messages"], "members": ", ".join(MEMBERS)})

    # Return the decision
    return {"next": result.next}
