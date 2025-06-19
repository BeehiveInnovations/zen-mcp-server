"""
Zen MCP Server - Entry point
The main implementation is in server.py
"""

import asyncio

from server import main

if __name__ == "__main__":
    asyncio.run(main())
