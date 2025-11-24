"""
Zen MCP Server - LangGraph Entry Point.

This server exposes the LangGraph agent as a single MCP tool.
"""

from mcp.server.fastmcp import FastMCP

from agent import create_graph

# Initialize FastMCP
mcp = FastMCP("Zen Agent")


@mcp.tool()
async def ask_zen(task: str, thread_id: str = "default") -> str:
    """
    Ask the Zen Agent to perform a complex task.

    The agent uses a multi-agent architecture (Architect, Coder, Researcher, etc.)
    to solve the problem.

    Args:
        task: The task description.
        thread_id: Optional ID for conversation persistence.
    """
    app = create_graph()

    # Config for persistence
    config = {"configurable": {"thread_id": thread_id}}

    # Initial state
    initial_state = {"messages": [("user", task)], "next": "Supervisor", "errors": [], "context": {}}

    # Run the graph
    # We use ainvoke for async execution
    result = await app.ainvoke(initial_state, config=config)

    # Extract the final response
    # The result is the final state
    messages = result.get("messages", [])
    if messages:
        last_message = messages[-1]
        return last_message.content

    return "No response generated."


if __name__ == "__main__":
    mcp.run()
