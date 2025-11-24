"""
LangGraph Construction Module.

This module assembles the StateGraph, defining nodes, edges, and persistence.
"""

import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes.researcher import researcher_node
from agent.nodes.supervisor import MEMBERS, supervisor_node
from agent.state import AgentState

# Import other nodes as they are implemented
# from agent.nodes.architect import architect_node
# ...


def create_graph():
    """Create and compile the agent graph."""

    # Initialize the graph
    workflow = StateGraph(AgentState)

    # Add the Supervisor node
    workflow.add_node("Supervisor", supervisor_node)

    # Add Worker nodes
    # For now, we only have Researcher implemented
    workflow.add_node("Researcher", researcher_node)

    # Add placeholders for other workers (using a dummy function for now)
    def dummy_node(state: AgentState) -> dict:
        return {"messages": [{"role": "assistant", "content": "This worker is not yet implemented."}]}

    for member in MEMBERS:
        if member != "Researcher":
            workflow.add_node(member, dummy_node)

    # Define the entry point
    workflow.add_edge(START, "Supervisor")

    # Define the conditional edges from Supervisor
    # The Supervisor outputs a "next" key in the state (or returns it)
    # Wait, my supervisor_node returns {"next": ...}, which updates the state.
    # So we can read state["next"] in the conditional edge.

    def get_next_node(state: AgentState) -> str:
        return state["next"]

    # Create the mapping for the conditional edge
    # Maps the output of get_next_node to the actual node name
    conditional_map: dict[str, str] = {member: member for member in MEMBERS}
    conditional_map["FINISH"] = END

    workflow.add_conditional_edges("Supervisor", get_next_node, conditional_map)

    # Add edges from workers back to Supervisor
    for member in MEMBERS:
        workflow.add_edge(member, "Supervisor")

    # Set up persistence
    redis_url = os.getenv("REDIS_URL")
    checkpointer = None

    if redis_url:
        try:
            from langgraph.checkpoint.redis import RedisSaver

            # from redis import Redis  # Not used, commented out to avoid lint error
            # Create Redis client
            # We need to parse the URL or pass it directly if supported
            # RedisSaver.from_conn_string is available in newer versions
            checkpointer = RedisSaver.from_conn_string(redis_url)
            print(f"Using Redis persistence at {redis_url}")
        except ImportError:
            print("Redis dependencies not found, falling back to MemorySaver.")
            checkpointer = MemorySaver()
        except Exception as e:
            print(f"Failed to connect to Redis: {e}. Falling back to MemorySaver.")
            checkpointer = MemorySaver()
    else:
        print("REDIS_URL not set, using in-memory persistence.")
        checkpointer = MemorySaver()

    # Compile the graph
    app = workflow.compile(checkpointer=checkpointer)

    return app
