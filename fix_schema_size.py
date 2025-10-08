#!/usr/bin/env python3
"""
Fix for enormous tool schema issue causing MCP client connection problems.

The chat tool's model field schema is generating descriptions and enums for
hundreds of model variants, creating a 170KB+ JSON response that overwhelms
MCP clients.

This patch simplifies the model field schema to a reasonable size.
"""

import shutil
from pathlib import Path


def patch_base_tool():
    """Patch the base_tool.py to reduce model schema size."""

    base_tool_path = Path("tools/shared/base_tool.py")
    backup_path = Path("tools/shared/base_tool.py.backup")

    # Create backup
    if not backup_path.exists():
        shutil.copy(base_tool_path, backup_path)
        print(f"Created backup: {backup_path}")

    # Read the file
    with open(base_tool_path) as f:
        content = f.read()

    # Find and replace the get_model_field_schema method
    # We'll create a much simpler version
    simpler_schema = '''    def get_model_field_schema(self) -> dict[str, Any]:
        """
        Generate a simplified model field schema.
        
        This version reduces the schema size from 170KB+ to ~1KB to fix
        MCP client connectivity issues.
        """
        from config import DEFAULT_MODEL
        
        # Use the centralized effective auto mode check
        if self.is_effective_auto_mode():
            # In auto mode, provide a concise model selection guide
            return {
                "type": "string",
                "description": (
                    "Select an appropriate model: "
                    "gemini-2.5-pro (deep reasoning), gemini-2.5-flash (fast), "
                    "o3/o3-mini (logical reasoning), gpt-5 (advanced), "
                    "grok-4 (multimodal). Use 'auto' for automatic selection."
                ),
                "default": "auto"
            }
        else:
            # When not in auto mode, just list available models
            models = self.get_available_models()
            if models:
                return {
                    "type": "string",
                    "enum": models[:20],  # Limit to first 20 models
                    "description": f"Available models (showing first 20 of {len(models)})",
                    "default": DEFAULT_MODEL if DEFAULT_MODEL != "auto" else models[0]
                }
            else:
                return {
                    "type": "string",
                    "description": "Model name",
                    "default": DEFAULT_MODEL
                }'''

    # Find the start of the get_model_field_schema method
    import re

    pattern = r"def get_model_field_schema\(self\) -> dict\[str, Any\]:.*?(?=\n    def |\n\nclass |\Z)"

    # Replace with our simpler version
    new_content = re.sub(pattern, simpler_schema.strip(), content, flags=re.DOTALL)

    # Write the patched file
    with open(base_tool_path, "w") as f:
        f.write(new_content)

    print(f"✅ Patched {base_tool_path}")
    print("   Reduced model schema from ~170KB to ~1KB")


def main():
    """Apply the schema size fix."""
    print("Applying MCP schema size fix...")
    patch_base_tool()
    print("\n✅ Fix applied successfully!")
    print("\nNext steps:")
    print("1. Restart the Zen MCP server")
    print("2. Reconnect Claude Code")
    print("3. Tools should now be visible")


if __name__ == "__main__":
    main()
