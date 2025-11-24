"""
Agent State Definition for Zen MCP Server.

This module defines the state structure used by the LangGraph execution model.
"""

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """
    The state of the agent execution graph.

    Attributes:
        messages: The conversation history, including user inputs and tool outputs.
                  We use the `add_messages` reducer to append new messages.
        next: The name of the next node/agent to execute.
        errors: A list of errors encountered during execution.
        context: Shared context dictionary for passing data between agents.
    """

    # The 'messages' key will be reduced by adding new messages to the existing list
    messages: Annotated[list[BaseMessage], operator.add]

    # The 'next' key tracks which node should execute next
    next: str

    # Optional error tracking
    errors: list[str]

    # Shared context for multi-turn reasoning
    context: dict[str, Any]
