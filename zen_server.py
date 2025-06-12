"""
Zen MCP Server - Entry point for backward compatibility
This file exists to maintain compatibility with existing configurations.
The main implementation is now in server.py
"""

import asyncio

from server import main

if __name__ == "__main__":
    asyncio.run(main())
