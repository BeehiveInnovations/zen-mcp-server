#!/usr/bin/env python3
"""
Test script to verify the zen MCP fixes are working correctly.
"""


def test_mode_consistency():
    """Test that all modes are consistent across files."""
    from tools.mode_selector import MODE_DESCRIPTIONS, MODE_KEYWORDS
    from tools.zen_execute import ZenExecuteTool

    print("=== Testing Mode Name Consistency ===")

    # Expected standardized modes
    expected_modes = {
        "debug",
        "codereview",
        "analyze",
        "chat",
        "consensus",
        "security",
        "refactor",
        "testgen",
        "planner",
        "tracer",
    }

    # Check mode selector
    selector_modes = set(MODE_DESCRIPTIONS.keys())
    print(f"Mode selector modes: {selector_modes}")
    assert (
        selector_modes == expected_modes
    ), f"Mismatch in mode_selector: {selector_modes - expected_modes} extra, {expected_modes - selector_modes} missing"

    # Check keywords
    keyword_modes = set(MODE_KEYWORDS.keys())
    assert (
        keyword_modes == expected_modes
    ), f"Mismatch in keywords: {keyword_modes - expected_modes} extra, {expected_modes - keyword_modes} missing"

    # Check zen_execute enum
    executor = ZenExecuteTool()
    schema = executor.get_input_schema()
    enum_modes = set(schema["properties"]["mode"]["enum"])
    assert (
        enum_modes == expected_modes
    ), f"Mismatch in zen_execute enum: {enum_modes - expected_modes} extra, {expected_modes - enum_modes} missing"

    print("✅ All mode names are consistent")
    return True


def test_request_model_coverage():
    """Test that all mode/complexity combinations have request models."""
    from tools.mode_executor import MODE_REQUEST_MAP

    print("=== Testing Request Model Coverage ===")

    modes = [
        "debug",
        "codereview",
        "analyze",
        "chat",
        "consensus",
        "security",
        "refactor",
        "testgen",
        "planner",
        "tracer",
    ]
    complexities = ["simple", "workflow"]

    missing = []
    for mode in modes:
        for complexity in complexities:
            key = (mode, complexity)
            if key not in MODE_REQUEST_MAP:
                missing.append(key)

    print(f"Request model mappings: {len(MODE_REQUEST_MAP)}")
    if missing:
        print(f"❌ Missing mappings: {missing}")
        return False
    else:
        print("✅ All mode/complexity combinations covered")
        return True


def test_schema_generation():
    """Test that schemas can be generated without errors."""
    from tools.mode_executor import ModeExecutor

    print("=== Testing Schema Generation ===")

    test_cases = [("debug", "simple"), ("codereview", "workflow"), ("testgen", "simple"), ("planner", "workflow")]

    for mode, complexity in test_cases:
        try:
            executor = ModeExecutor(mode, complexity)
            schema = executor.get_input_schema()
            assert "properties" in schema
            assert len(schema["properties"]) > 0
            print(f"✅ {mode}/{complexity}: {len(schema['properties'])} fields")
        except Exception as e:
            print(f"❌ {mode}/{complexity}: {e}")
            return False

    print("✅ Schema generation working")
    return True


def main():
    """Run all tests."""
    print("🧪 TESTING ZEN MCP FIXES")
    print("=" * 50)

    tests = [test_mode_consistency, test_request_model_coverage, test_schema_generation]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append(False)
            print()

    print("=" * 50)
    if all(results):
        print("🎉 ALL TESTS PASSED - Fixes are working!")
        return 0
    else:
        print("❌ Some tests failed - More fixes needed")
        return 1


if __name__ == "__main__":
    exit(main())
