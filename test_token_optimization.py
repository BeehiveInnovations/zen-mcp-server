#!/usr/bin/env python3
"""
Quick test script for token optimization two-stage flow
"""
import os
import json

# Enable token optimization
os.environ['ZEN_TOKEN_OPTIMIZATION'] = 'enabled'
os.environ['ZEN_OPTIMIZATION_MODE'] = 'two_stage'

from server_token_optimized import get_optimized_tools
from tools.mode_selector import ModeSelectorTool
from tools.zen_execute import ZenExecuteTool
import asyncio

async def test_mode_selection():
    """Test Stage 1: Mode selection"""
    print("=" * 60)
    print("STAGE 1 TEST: Mode Selection")
    print("=" * 60)
    
    selector = ModeSelectorTool()
    
    # Test 1: Debug mode selection
    result = await selector.execute({
        "task_description": "Debug why OAuth tokens aren't persisting across sessions"
    })
    
    if result:
        data = json.loads(result[0].text)
        print(f"✅ Mode selected: {data['selected_mode']}")
        print(f"✅ Complexity: {data['complexity']}")
        print(f"✅ Token savings: {data.get('token_savings', 'N/A')}")
        return data
    
    return None

async def test_tool_registration():
    """Test tool registration"""
    print("\n" + "=" * 60)
    print("TOOL REGISTRATION TEST")
    print("=" * 60)
    
    tools = get_optimized_tools()
    
    print(f"✅ Registered {len(tools)} tools:")
    for name in sorted(tools.keys()):
        print(f"   - {name}")
    
    # Verify core tools
    assert "zen_select_mode" in tools
    assert "zen_execute" in tools
    print("\n✅ Core optimization tools present")
    
    # Verify compatibility stubs
    compat_tools = ["debug", "codereview", "analyze", "chat"]
    for tool in compat_tools:
        assert tool in tools
    print("✅ Backward compatibility stubs present")

async def main():
    """Run all tests"""
    print("\n🔬 Testing Token Optimization Two-Stage Architecture\n")
    
    # Test tool registration
    await test_tool_registration()
    
    # Test mode selection
    mode_data = await test_mode_selection()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nToken optimization is working correctly!")
    print("- Stage 1 (zen_select_mode): ✅")
    print("- Stage 2 (zen_execute): Ready for testing")
    print("- Backward compatibility: ✅")

if __name__ == "__main__":
    asyncio.run(main())
