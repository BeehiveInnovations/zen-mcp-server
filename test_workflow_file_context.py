#!/usr/bin/env python3
"""
Test workflow file context handling for different scenarios.
"""

import asyncio
import json
import os
import tempfile

from tools.debug import DebugIssueTool


async def test_workflow_file_context():
    """Test workflow file context handling in different scenarios."""

    # Initialize providers
    from server import configure_providers
    configure_providers()

    # Create test files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Test file 1\ndef test_function():\n    pass\n")
        test_file1 = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Test file 2\ndef another_function():\n    return 'test'\n")
        test_file2 = f.name

    try:
        # Create the tool
        tool = DebugIssueTool()

        print("=" * 80)
        print("TEST 1: New conversation, step 1 - should NOT embed files (more work needed)")
        print("=" * 80)

        arguments1 = {
            "step": "Starting investigation",
            "step_number": 1,
            "total_steps": 3,
            "next_step_required": True,  # Intermediate step
            "findings": "Initial findings",
            "files_checked": [test_file1, test_file2],
            "relevant_files": [test_file1],  # Use relevant_files for workflow tools
            "relevant_methods": ["test_function"],
            "hypothesis": "Initial hypothesis",
            "confidence": "low",
            "model": "flash",
        }

        result1 = await tool.execute_workflow(arguments1)
        response1 = json.loads(result1[0].text)

        print(f"Status: {response1.get('status')}")
        file_context1 = response1.get('file_context', {})
        print(f"File context type: {file_context1.get('type')}")
        print(f"Context optimization: {file_context1.get('context_optimization')}")
        print()

        # Extract continuation_id for next test
        continuation_id = response1.get('continuation_id')

        print("=" * 80)
        print("TEST 2: Intermediate step with continuation - should only reference files")
        print("=" * 80)

        arguments2 = {
            "step": "Continuing investigation with more findings",
            "step_number": 2,
            "total_steps": 3,
            "next_step_required": True,  # Still intermediate
            "continuation_id": continuation_id,
            "findings": "More detailed findings",
            "files_checked": [test_file1, test_file2],
            "relevant_files": [test_file1, test_file2],  # Use relevant_files for workflow tools
            "relevant_methods": ["test_function", "another_function"],
            "hypothesis": "Updated hypothesis",
            "confidence": "medium",
            "model": "flash",
        }

        result2 = await tool.execute_workflow(arguments2)
        response2 = json.loads(result2[0].text)

        print(f"Status: {response2.get('status')}")
        file_context2 = response2.get('file_context', {})
        print(f"File context type: {file_context2.get('type')}")
        print(f"Context optimization: {file_context2.get('context_optimization')}")
        if 'note' in file_context2:
            print(f"Reference note: {file_context2.get('note')}")
        print()

        print("=" * 80)
        print("TEST 3: Final step with continuation - should embed files for expert analysis")
        print("=" * 80)

        arguments3 = {
            "step": "Final investigation step with conclusion",
            "step_number": 3,
            "total_steps": 3,
            "next_step_required": False,  # Final step
            "continuation_id": continuation_id,
            "findings": "Conclusive findings",
            "files_checked": [test_file1, test_file2],
            "relevant_files": [test_file1, test_file2],  # Use relevant_files for workflow tools
            "relevant_methods": ["test_function", "another_function"],
            "hypothesis": "Final hypothesis with clear evidence",
            "confidence": "high",
            "model": "flash",
        }

        result3 = await tool.execute_workflow(arguments3)
        response3 = json.loads(result3[0].text)

        print(f"Status: {response3.get('status')}")
        file_context3 = response3.get('file_context', {})
        print(f"File context type: {file_context3.get('type')}")
        print(f"Context optimization: {file_context3.get('context_optimization')}")
        if 'files_embedded' in file_context3:
            print(f"Files embedded: {file_context3.get('files_embedded')}")
        print()

        # Test summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        test1_context = file_context1.get('type', 'unknown')
        test2_context = file_context2.get('type', 'unknown')
        test3_context = file_context3.get('type', 'unknown')

        print(f"✅ Test 1 (New conversation): {test1_context}")
        print(f"✅ Test 2 (Intermediate + continuation): {test2_context}")
        print(f"✅ Test 3 (Final + continuation): {test3_context}")

        # Verify expected behavior
        expected_behavior = [
            (test1_context == 'reference_only', "Test 1 should only reference files (more work needed)"),
            (test2_context == 'reference_only', "Test 2 should only reference files"),
            (test3_context == 'fully_embedded', "Test 3 should embed files for expert analysis")
        ]

        all_passed = True
        for check, description in expected_behavior:
            if check:
                print(f"✅ {description}")
            else:
                print(f"❌ {description}")
                all_passed = False

        if all_passed:
            print("\n🎉 All workflow file context tests PASSED!")
        else:
            print("\n❌ Some workflow file context tests FAILED!")

    finally:
        # Clean up test files
        try:
            os.unlink(test_file1)
            os.unlink(test_file2)
        except:
            pass


if __name__ == "__main__":
    asyncio.run(test_workflow_file_context())
