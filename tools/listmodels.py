"""
List Models Tool - Display all available models organized by provider

This tool provides a comprehensive view of all AI models available in the system,
organized by their provider (Gemini, OpenAI, X.AI, OpenRouter, Custom).
It shows which providers are configured and what models can be used.
"""

import os
from typing import Any, Optional

from mcp.types import TextContent

from tools.base import BaseTool, ToolRequest
from tools.models import ToolModelCategory, ToolOutput


class ListModelsTool(BaseTool):
    """
    Tool for listing all available AI models organized by provider.

    This tool helps users understand:
    - Which providers are configured (have API keys)
    - What models are available from each provider
    - Model aliases and their full names
    - Context window sizes and capabilities
    """

    def get_name(self) -> str:
        return "listmodels"

    def get_description(self) -> str:
        return (
            "LIST AVAILABLE MODELS - Display all AI models organized by provider. "
            "Shows which providers are configured, available models, their aliases, "
            "context windows, and capabilities. Useful for understanding what models "
            "can be used and their characteristics."
        )

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {"type": "object", "properties": {}, "required": []}

    def get_system_prompt(self) -> str:
        """No AI model needed for this tool"""
        return ""

    def get_request_model(self):
        """Return the Pydantic model for request validation."""
        return ToolRequest

    async def prepare_prompt(self, request: ToolRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: ToolRequest, model_info: Optional[dict] = None) -> str:
        """Not used for this utility tool"""
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        List all available models organized by provider.

        This overrides the base class execute to provide direct output without AI model calls.

        Args:
            arguments: Standard tool arguments (none required)

        Returns:
            Formatted list of models by provider
        """
        from config import MODEL_CAPABILITIES_DESC
        from providers.openrouter_registry import OpenRouterModelRegistry

        output_lines = ["# Available AI Models\n"]

        # Check native providers
        native_providers = {
            "gemini": {
                "name": "Google Gemini",
                "env_key": "GEMINI_API_KEY",
                "models": {
                    "flash": "gemini-2.5-flash",
                    "pro": "gemini-2.5-pro",
                },
            },
            "openai": {
                "name": "OpenAI",
                "env_key": "OPENAI_API_KEY",
                "models": {
                    "o3": "o3",
                    "o3-mini": "o3-mini",
                    "o3-pro": "o3-pro",
                    "o4-mini": "o4-mini",
                    "o4-mini-high": "o4-mini-high",
                },
            },
            "xai": {
                "name": "X.AI (Grok)",
                "env_key": "XAI_API_KEY",
                "models": {
                    "grok": "grok-3",
                    "grok-3": "grok-3",
                    "grok-3-fast": "grok-3-fast",
                    "grok3": "grok-3",
                    "grokfast": "grok-3-fast",
                },
            },
        }

        # Check each native provider
        for provider_key, provider_info in native_providers.items():
            api_key = os.getenv(provider_info["env_key"])
            is_configured = api_key and api_key != f"your_{provider_key}_api_key_here"

            output_lines.append(f"## {provider_info['name']} {'✅' if is_configured else '❌'}")

            if is_configured:
                output_lines.append("**Status**: Configured and available")
                output_lines.append("\n**Models**:")

                for alias, full_name in provider_info["models"].items():
                    # Get description from MODEL_CAPABILITIES_DESC
                    desc = MODEL_CAPABILITIES_DESC.get(alias, "")
                    if isinstance(desc, str):
                        # Extract context window from description
                        import re

                        context_match = re.search(r"\(([^)]+context)\)", desc)
                        context_info = context_match.group(1) if context_match else ""

                        output_lines.append(f"- `{alias}` → `{full_name}` - {context_info}")

                        # Extract key capability
                        if "Ultra-fast" in desc:
                            output_lines.append("  - Fast processing, quick iterations")
                        elif "Deep reasoning" in desc:
                            output_lines.append("  - Extended reasoning with thinking mode")
                        elif "Strong reasoning" in desc:
                            output_lines.append("  - Logical problems, systematic analysis")
                        elif "EXTREMELY EXPENSIVE" in desc:
                            output_lines.append("  - ⚠️ Professional grade (very expensive)")
            else:
                output_lines.append(f"**Status**: Not configured (set {provider_info['env_key']})")

            output_lines.append("")

        # Check OpenRouter
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        is_openrouter_configured = openrouter_key and openrouter_key != "your_openrouter_api_key_here"

        output_lines.append(f"## OpenRouter {'✅' if is_openrouter_configured else '❌'}")

        if is_openrouter_configured:
            output_lines.append("**Status**: Configured and available")
            output_lines.append("**Description**: Access to multiple cloud AI providers via unified API")

            try:
                registry = OpenRouterModelRegistry()
                aliases = registry.list_aliases()

                # Group by provider for better organization
                providers_models = {}
                for alias in aliases[:20]:  # Limit to first 20 to avoid overwhelming output
                    config = registry.resolve(alias)
                    if config and not (hasattr(config, "is_custom") and config.is_custom):
                        # Extract provider from model_name
                        provider = config.model_name.split("/")[0] if "/" in config.model_name else "other"
                        if provider not in providers_models:
                            providers_models[provider] = []
                        providers_models[provider].append((alias, config))

                output_lines.append("\n**Available Models** (showing top 20):")
                for provider, models in sorted(providers_models.items()):
                    output_lines.append(f"\n*{provider.title()}:*")
                    for alias, config in models[:5]:  # Limit each provider to 5 models
                        context_str = f"{config.context_window // 1000}K" if config.context_window else "?"
                        output_lines.append(f"- `{alias}` → `{config.model_name}` ({context_str} context)")

                total_models = len(aliases)
                output_lines.append(f"\n...and {total_models - 20} more models available")

            except Exception as e:
                output_lines.append(f"**Error loading models**: {str(e)}")
        else:
            output_lines.append("**Status**: Not configured (set OPENROUTER_API_KEY)")
            output_lines.append("**Note**: Provides access to GPT-4, Claude, Mistral, and many more")

        output_lines.append("")

        # Check Custom API
        custom_url = os.getenv("CUSTOM_API_URL")

        output_lines.append(f"## Custom/Local API {'✅' if custom_url else '❌'}")

        if custom_url:
            output_lines.append("**Status**: Configured and available")
            output_lines.append(f"**Endpoint**: {custom_url}")
            output_lines.append("**Description**: Local models via Ollama, vLLM, LM Studio, etc.")

            try:
                registry = OpenRouterModelRegistry()
                custom_models = []

                for alias in registry.list_aliases():
                    config = registry.resolve(alias)
                    if config and hasattr(config, "is_custom") and config.is_custom:
                        custom_models.append((alias, config))

                if custom_models:
                    output_lines.append("\n**Custom Models**:")
                    for alias, config in custom_models:
                        context_str = f"{config.context_window // 1000}K" if config.context_window else "?"
                        output_lines.append(f"- `{alias}` → `{config.model_name}` ({context_str} context)")
                        if config.description:
                            output_lines.append(f"  - {config.description}")

            except Exception as e:
                output_lines.append(f"**Error loading custom models**: {str(e)}")
        else:
            output_lines.append("**Status**: Not configured (set CUSTOM_API_URL)")
            output_lines.append("**Example**: CUSTOM_API_URL=http://localhost:11434 (for Ollama)")

        output_lines.append("")

        # Add summary
        output_lines.append("## Summary")

        # Count configured providers
        configured_count = sum(
            [
                1
                for p in native_providers.values()
                if os.getenv(p["env_key"])
                and os.getenv(p["env_key"]) != f"your_{p['env_key'].lower().replace('_api_key', '')}_api_key_here"
            ]
        )
        if is_openrouter_configured:
            configured_count += 1
        if custom_url:
            configured_count += 1

        output_lines.append(f"**Configured Providers**: {configured_count}")

        # Get total available models
        try:
            from tools.analyze import AnalyzeTool

            tool = AnalyzeTool()
            total_models = len(tool._get_available_models())
            output_lines.append(f"**Total Available Models**: {total_models}")
        except Exception:
            pass

        # Add usage tips
        output_lines.append("\n**Usage Tips**:")
        output_lines.append("- Use model aliases (e.g., 'flash', 'o3', 'opus') for convenience")
        output_lines.append("- In auto mode, Claude will select the best model for each task")
        output_lines.append("- Custom models are only available when CUSTOM_API_URL is set")
        output_lines.append("- OpenRouter provides access to many cloud models with one API key")

        # Format output
        content = "\n".join(output_lines)

        tool_output = ToolOutput(
            status="success",
            content=content,
            content_type="text",
            metadata={
                "tool_name": self.name,
                "configured_providers": configured_count,
            },
        )

        return [TextContent(type="text", text=tool_output.model_dump_json())]

    def get_model_category(self) -> ToolModelCategory:
        """Return the model category for this tool."""
        return ToolModelCategory.FAST_RESPONSE  # Simple listing, no AI needed
