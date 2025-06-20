#!/usr/bin/env python3
"""
Debug the certain confidence behavior.
"""

import asyncio
import json

from tools.debugworkflow import DebugWorkflowTool


async def test_certain_confidence():
    """Test certain confidence behavior."""

    # Initialize providers (just like the test does)
    from server import configure_providers
    configure_providers()

    # Create the tool
    tool = DebugWorkflowTool()

    # Create a request with certain confidence
    arguments = {
        "step": "I have confirmed the exact root cause with 100% certainty: dictionary modification during iteration.",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,  # Final step
        "findings": "The bug is on line 44-47: for loop iterates over dict.items() while del modifies the dict inside the loop.",
        "files_checked": ["/tmp/test.py"],
        "relevant_files": ["/tmp/test.py"],
        "relevant_methods": ["SessionManager.cleanup_expired_sessions"],
        "hypothesis": "Dictionary modification during iteration causes RuntimeError - fix is straightforward",
        "confidence": "certain",  # This should skip expert analysis
        "model": "flash",
    }

    print("Testing certain confidence behavior...")
    print(f"Arguments: confidence={arguments['confidence']}, next_step_required={arguments['next_step_required']}")

    # Create request to test should_skip_expert_analysis
    request = tool.get_workflow_request_model()(**arguments)
    print(f"Request created: confidence={request.confidence}, next_step_required={request.next_step_required}")

    # Test the skip logic
    should_skip = tool.should_skip_expert_analysis(request, tool.consolidated_findings)
    print(f"should_skip_expert_analysis returned: {should_skip}")

    # Execute the tool
    print("\nExecuting tool...")
    result = await tool.execute_workflow(arguments)
    response_text = result[0].text
    response_data = json.loads(response_text)

    print(f"\nResponse status: {response_data.get('status')}")
    print(f"Skip expert analysis: {response_data.get('skip_expert_analysis')}")

    expert_analysis = response_data.get('expert_analysis', {})
    print(f"Expert analysis status: {expert_analysis.get('status')}")
    print(f"Expert analysis reason: {expert_analysis.get('reason')}")

    # Check if this matches what the test expects
    expected_status = "skipped_due_to_certain_confidence"
    actual_status = expert_analysis.get('status')

    if actual_status == expected_status:
        print(f"\n✅ SUCCESS: Expert analysis status matches expected '{expected_status}'")
    else:
        print(f"\n❌ FAIL: Expected '{expected_status}', got '{actual_status}'")
        print("Full response:")
        print(json.dumps(response_data, indent=2))


if __name__ == "__main__":
    asyncio.run(test_certain_confidence())
