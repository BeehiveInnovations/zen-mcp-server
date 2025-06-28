"""
HTTP/SSE Transport Server for Zen MCP

This module provides HTTP/SSE transport capabilities for the Zen MCP Server,
enabling remote hosting and URL-based client connections. It uses Starlette
for the ASGI framework and integrates with the MCP SDK's SSE transport.

The server exposes:
- GET /sse - SSE endpoint for server-to-client streaming
- POST /messages/ - Message endpoint for client-to-server communication
- GET /health - Health check endpoint
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route

from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from mcp.types import ServerCapabilities, ToolsCapability, PromptsCapability

from config import __version__
from server import server, TOOLS, configure_providers

# Configure logging
logger = logging.getLogger(__name__)

# Global SSE transport instance
sse_transport: Optional[SseServerTransport] = None
server_task: Optional[asyncio.Task] = None


class AuthenticationMiddleware:
    """
    API key authentication middleware for protecting MCP endpoints.
    
    Uses x-api-key header for authentication, similar to Claude's remote MCP.
    Can be configured via environment variables.
    """
    
    def __init__(self, app):
        self.app = app
        self.api_key = os.getenv("MCP_API_KEY")
        self.require_auth = os.getenv("MCP_REQUIRE_AUTH", "true").lower() == "true"
    
    async def __call__(self, scope, receive, send):
        if not self.require_auth or scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Skip auth for health check
        if scope["path"] == "/health":
            await self.app(scope, receive, send)
            return
        
        # Check x-api-key header
        headers = dict(scope["headers"])
        api_key_header = headers.get(b"x-api-key", b"").decode()
        
        if not api_key_header:
            response = PlainTextResponse("Missing API key", status_code=401)
            await response(scope, receive, send)
            return
        
        # Validate API key
        if api_key_header != self.api_key:
            response = PlainTextResponse("Invalid API key", status_code=403)
            await response(scope, receive, send)
            return
        
        await self.app(scope, receive, send)


async def handle_sse(request: Request):
    """
    Handle SSE connection requests from MCP clients.
    
    This endpoint establishes a Server-Sent Events connection for
    real-time communication between the MCP client and server.
    """
    global server_task
    
    logger.info(f"SSE connection request from {request.client.host}")
    
    if not sse_transport:
        return PlainTextResponse("SSE transport not initialized", status_code=500)
    
    # Handle the SSE connection
    async with sse_transport.connect_sse(
        request.scope, 
        request.receive, 
        request._send
    ) as (read_stream, write_stream):
        # Initialize server options
        init_options = InitializationOptions(
            server_name="zen",
            server_version=__version__,
            capabilities=ServerCapabilities(
                tools=ToolsCapability(),
                prompts=PromptsCapability(),
            ),
        )
        
        # Run the MCP server for this connection
        try:
            await server.run(read_stream, write_stream, init_options)
        except Exception as e:
            logger.error(f"Error in SSE connection: {e}")
            raise


async def handle_health(request: Request):
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns server status and version information.
    """
    return JSONResponse({
        "status": "healthy",
        "version": __version__,
        "transport": "http/sse",
        "tools": len(TOOLS)
    })


@asynccontextmanager
async def lifespan(app: Starlette):
    """
    Manage server lifecycle - startup and shutdown.
    
    Initializes the MCP server and SSE transport on startup,
    and ensures clean shutdown on exit.
    """
    global sse_transport
    
    # Startup
    logger.info("Starting Zen MCP HTTP/SSE Server...")
    
    # Configure providers (API keys, etc.)
    configure_providers()
    
    # Initialize SSE transport with the messages endpoint
    sse_transport = SseServerTransport("/messages/")
    
    logger.info(f"Server ready - listening for HTTP/SSE connections")
    logger.info(f"Available tools: {list(TOOLS.keys())}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Zen MCP HTTP/SSE Server...")


def create_app() -> Starlette:
    """
    Create and configure the Starlette ASGI application.
    
    Sets up routes, middleware, and server configuration.
    """
    # Configure middleware (authentication only, no CORS)
    middleware = [
        Middleware(AuthenticationMiddleware),
    ]
    
    # Create app with lifespan first
    app = Starlette(
        middleware=middleware,
        lifespan=lifespan,
    )
    
    # Configure routes
    routes = [
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Route("/health", endpoint=handle_health, methods=["GET"]),
    ]
    
    # Mount routes on the app
    for route in routes:
        app.add_route(route.path, route.endpoint, methods=route.methods)
    
    # Add SSE transport message handler
    @app.on_event("startup")
    async def add_message_handler():
        if sse_transport:
            app.mount("/messages/", sse_transport.handle_post_message)
    
    return app


# Create the ASGI app instance
app = create_app()


if __name__ == "__main__":
    """
    Run the server directly with uvicorn.
    
    This is mainly for development - in production, run with:
    uvicorn http_server:app --host 0.0.0.0 --port 8000
    """
    import uvicorn
    
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))
    
    uvicorn.run(
        "http_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )