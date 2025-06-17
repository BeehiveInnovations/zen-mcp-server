#!/usr/bin/env python3
"""
Test script for the enhanced consensus tool with ModelConfig objects
"""

import asyncio
import json
import sys

from tools.consensus import ConsensusTool


async def test_enhanced_consensus():
    """Test the enhanced consensus tool with custom stance prompts"""

    print("🧪 Testing Enhanced Consensus Tool")
    print("=" * 50)

    # Test all stance synonyms work
    print("📝 Testing stance synonym normalization...")
    tool = ConsensusTool()

    test_synonyms = [
        ("support", "for"),
        ("favor", "for"),
        ("oppose", "against"),
        ("critical", "against"),
        ("neutral", "neutral"),
        ("for", "for"),
        ("against", "against"),
        # Test unknown stances default to neutral
        ("maybe", "neutral"),
        ("supportive", "neutral"),
        ("random", "neutral"),
    ]

    for input_stance, expected in test_synonyms:
        normalized = tool._normalize_stance(input_stance)
        status = "✅" if normalized == expected else "❌"
        print(f"{status} '{input_stance}' → '{normalized}' (expected: '{expected}')")

    print()

    # Create consensus tool instance
    tool = ConsensusTool()

    # Test arguments with new ModelConfig format
    test_arguments = {
        "prompt": "Should we add a pizza ordering button to our enterprise software?",
        "models": [
            {
                "model": "flash",
                "stance": "support",  # Test synonym
                "stance_prompt": "You are a user experience advocate. Focus on how this feature could improve user engagement and satisfaction. Consider the human elements - how might this bring joy to users' workday? Think about unexpected benefits and creative use cases.",
            },
            {
                "model": "flash",
                "stance": "oppose",  # Test synonym
                "stance_prompt": "You are a software architecture specialist. Focus on technical concerns: code maintainability, security implications, scope creep, and system complexity. Consider long-term costs and potential maintenance burden.",
            },
        ],
        "focus_areas": ["user experience", "technical complexity", "business value"],
        "temperature": 0.3,
    }

    try:
        print("📝 Test Arguments:")
        print(json.dumps(test_arguments, indent=2))
        print()

        print("🚀 Executing consensus tool...")

        # Execute the tool
        result = await tool.execute(test_arguments)

        print("✅ Consensus tool execution completed!")
        print()

        # Parse and display results
        if result and len(result) > 0:
            response_text = result[0].text
            try:
                response_data = json.loads(response_text)
                print("📊 Consensus Results:")
                print(f"Status: {response_data.get('status', 'unknown')}")

                if response_data.get("status") == "consensus_success":
                    models_used = response_data.get("models_used", [])
                    print(f"Models used: {', '.join(models_used)}")

                    responses = response_data.get("responses", [])
                    print(f"\n🎭 Individual Model Responses ({len(responses)} total):")

                    for i, resp in enumerate(responses, 1):
                        model = resp.get("model", "unknown")
                        stance = resp.get("stance", "neutral")
                        status = resp.get("status", "unknown")

                        print(f"\n{i}. {model.upper()} ({stance} stance) - {status}")

                        if status == "success":
                            verdict = resp.get("verdict", "No verdict")
                            custom_prompt = resp.get("metadata", {}).get("custom_stance_prompt", False)
                            print(f"   Custom prompt used: {'Yes' if custom_prompt else 'No'}")
                            print(f"   Verdict preview: {verdict[:200]}...")

                            # Show stance normalization worked
                            if stance in ["support", "oppose"]:
                                expected = "for" if stance == "support" else "against"
                                print(f"   ✅ Stance '{stance}' normalized correctly")
                        else:
                            error = resp.get("error", "Unknown error")
                            print(f"   Error: {error}")

                else:
                    print(f"❌ Consensus failed: {response_data.get('error', 'Unknown error')}")

            except json.JSONDecodeError:
                print("📄 Raw response (not JSON):")
                print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
        else:
            print("❌ No response received from consensus tool")

    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    print("\n🎉 Enhanced consensus tool test completed!")
    return True


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_enhanced_consensus())
    sys.exit(0 if success else 1)
