#!/usr/bin/env python3
"""
Zen MCP Server entry point for UV/UVX packaging.

This module provides the main entry point for running the Zen MCP Server
when installed via UV/UVX package management.
"""

import asyncio
import sys
from pathlib import Path


def main():
    """Main entry point for UV/UVX packaging."""
    # Add parent directory to Python path to allow importing server module
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        from server import main as server_main
        asyncio.run(server_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()