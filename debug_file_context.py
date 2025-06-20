#!/usr/bin/env python3
"""
Debug file context attributes.
"""

import asyncio
import json
import os
import tempfile

from tools.debug import DebugIssueTool


async def debug_file_context():
    """Debug what happens to file context attributes."""

    # Initialize providers
    from server import configure_providers
    configure_providers()

    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Test file\ndef test_function():\n    pass\n")
        test_file = f.name

    try:
        # Create the tool
        tool = DebugIssueTool()

        print("Testing intermediate step with continuation...")

        arguments = {
            "step": "Continuing investigation",
            "step_number": 2,
            "total_steps": 3,
            "next_step_required": True,  # Intermediate step
            "continuation_id": "test-123",  # Fake continuation ID
            "findings": "Some findings",
            "files_checked": [test_file],
            "relevant_files": [test_file],
            "relevant_methods": ["test_function"],
            "hypothesis": "Test hypothesis",
            "confidence": "medium",
            "model": "flash",
        }

        # Check attributes before execution
        print("Before execution:")
        print(f"  _file_reference_note: {hasattr(tool, '_file_reference_note')}")
        print(f"  _embedded_file_content: {hasattr(tool, '_embedded_file_content')}")

        result = await tool.execute_workflow(arguments)

        # Check attributes after execution
        print("After execution:")
        print(f"  _file_reference_note: {hasattr(tool, '_file_reference_note')}")
        if hasattr(tool, '_file_reference_note'):
            print(f"  _file_reference_note value: {tool._file_reference_note}")
        print(f"  _embedded_file_content: {hasattr(tool, '_embedded_file_content')}")
        if hasattr(tool, '_embedded_file_content'):
            print(f"  _embedded_file_content length: {len(tool._embedded_file_content)}")

        # Check response
        response = json.loads(result[0].text)
        print(f"Response has file_context: {'file_context' in response}")
        if 'file_context' in response:
            print(f"  file_context: {response['file_context']}")

        # Print full response for debugging
        print("\nFull response:")
        print(json.dumps(response, indent=2))

    finally:
        try:
            os.unlink(test_file)
        except:
            pass


if __name__ == "__main__":
    asyncio.run(debug_file_context())
