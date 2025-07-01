"""
Zen MCP Server - Main server implementation

This module implements the core MCP (Model Context Protocol) server that provides
AI-powered tools for code analysis, review, and assistance using multiple AI models.

The server follows the MCP specification to expose various AI tools as callable functions
that can be used by MCP clients (like Claude). Each tool provides specialized functionality
such as code review, debugging, deep thinking, and general chat capabilities.

Key Components:
- MCP Server: Handles protocol communication and tool discovery
- Tool Registry: Maps tool names to their implementations
- Request Handler: Processes incoming tool calls and returns formatted responses
- Configuration: Manages API keys and model settings

The server runs on stdio (standard input/output) and communicates using JSON-RPC messages
as defined by the MCP protocol.
"""

import asyncio
import atexit
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Try to load environment variables from .env file if dotenv is available
# This is optional - environment variables can still be passed directly
try:
    from dotenv import load_dotenv

    # Load environment variables from .env file in the script's directory
    # This ensures .env is loaded regardless of the current working directory
    script_dir = Path(__file__).parent
    env_file = script_dir / ".env"
    load_dotenv(dotenv_path=env_file)
except ImportError:
    # dotenv not available - this is fine, environment variables can still be passed directly
    # This commonly happens when running via uvx or in minimal environments
    pass

from mcp.server import Server  # noqa: E402
from mcp.server.models import InitializationOptions  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.types import (  # noqa: E402
    GetPromptResult,
    Prompt,
    PromptMessage,
    PromptsCapability,
    ServerCapabilities,
    TextContent,
    Tool,
    ToolAnnotations,
    ToolsCapability,
)

from config import (  # noqa: E402
    DEFAULT_MODEL,
    __version__,
)
from services import (  # noqa: E402
    ConversationManager,
    FileOperationService,
    ModelValidationService,
    ProviderManager,
)

# Import factory for lazy tool loading instead of individual tools
from tools.factory import get_tool_factory  # noqa: E402
from tools.models import ToolOutput  # noqa: E402

# Configure logging for server operations
# Can be controlled via LOG_LEVEL environment variable (DEBUG, INFO, WARNING, ERROR)
log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()

# Create timezone-aware formatter


class LocalTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        """Override to use local timezone instead of UTC"""
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = f"{t},{record.msecs:03.0f}"
        return s


# Configure both console and file logging
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Clear any existing handlers first
root_logger = logging.getLogger()
root_logger.handlers.clear()

# Create and configure stderr handler explicitly
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(getattr(logging, log_level, logging.INFO))
stderr_handler.setFormatter(LocalTimeFormatter(log_format))
root_logger.addHandler(stderr_handler)

# Note: MCP stdio_server interferes with stderr during tool execution
# All logs are properly written to logs/mcp_server.log for monitoring

# Set root logger level
root_logger.setLevel(getattr(logging, log_level, logging.INFO))

# Add rotating file handler for local log monitoring

try:
    # Create logs directory in project root
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # Main server log with size-based rotation (20MB max per file)
    # This ensures logs don't grow indefinitely and are properly managed
    file_handler = RotatingFileHandler(
        log_dir / "mcp_server.log",
        maxBytes=20 * 1024 * 1024,  # 20MB max file size
        backupCount=5,  # Keep 10 rotated files (100MB total)
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, log_level, logging.INFO))
    file_handler.setFormatter(LocalTimeFormatter(log_format))
    logging.getLogger().addHandler(file_handler)

    # Create a special logger for MCP activity tracking with size-based rotation
    mcp_logger = logging.getLogger("mcp_activity")
    mcp_file_handler = RotatingFileHandler(
        log_dir / "mcp_activity.log",
        maxBytes=10 * 1024 * 1024,  # 20MB max file size
        backupCount=2,  # Keep 5 rotated files (20MB total)
        encoding="utf-8",
    )
    mcp_file_handler.setLevel(logging.INFO)
    mcp_file_handler.setFormatter(LocalTimeFormatter("%(asctime)s - %(message)s"))
    mcp_logger.addHandler(mcp_file_handler)
    mcp_logger.setLevel(logging.INFO)
    # Ensure MCP activity also goes to stderr
    mcp_logger.propagate = True

    # Log setup info directly to root logger since logger isn't defined yet
    logging.info(f"Logging to: {log_dir / 'mcp_server.log'}")
    logging.info(f"Process PID: {os.getpid()}")

except Exception as e:
    print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)

logger = logging.getLogger(__name__)


# Create the MCP server instance with a unique name identifier
# This name is used by MCP clients to identify and connect to this specific server
server: Server = Server("zen-server")


# Constants for tool filtering
ESSENTIAL_TOOLS = {"version", "listmodels"}


def parse_disabled_tools_env() -> set[str]:
    """
    Parse the DISABLED_TOOLS environment variable into a set of tool names.

    Returns:
        Set of lowercase tool names to disable, empty set if none specified
    """
    disabled_tools_env = os.getenv("DISABLED_TOOLS", "").strip()
    if not disabled_tools_env:
        return set()
    return {t.strip().lower() for t in disabled_tools_env.split(",") if t.strip()}


def validate_disabled_tools(disabled_tools: set[str], tools_interface) -> None:
    """
    Validate the disabled tools list and log appropriate warnings.

    Args:
        disabled_tools: Set of tool names requested to be disabled
        tools_interface: Tools interface (dict-like or LazyToolDict)
    """
    essential_disabled = disabled_tools & ESSENTIAL_TOOLS
    if essential_disabled:
        logger.warning(f"Cannot disable essential tools: {sorted(essential_disabled)}")

    # Get available tools from the interface
    if hasattr(tools_interface, "keys"):
        available_tools = set(tools_interface.keys())
    elif hasattr(tools_interface, "_factory"):
        available_tools = set(tools_interface._factory.get_available_tools())
    else:
        available_tools = set(tools_interface.keys())

    unknown_tools = disabled_tools - available_tools
    if unknown_tools:
        logger.warning(f"Unknown tools in DISABLED_TOOLS: {sorted(unknown_tools)}")


def apply_tool_filter(tools_interface, disabled_tools: set[str]):
    """
    Apply the disabled tools filter to the tools interface.

    Args:
        tools_interface: Tools interface (dict-like or LazyToolDict)
        disabled_tools: Set of tool names to disable

    Returns:
        Modified tools interface with disabled tools filtered out
    """
    if hasattr(tools_interface, "set_disabled_tools"):
        # LazyToolDict case - delegate filtering to the interface
        effective_disabled = disabled_tools - ESSENTIAL_TOOLS
        tools_interface.set_disabled_tools(effective_disabled)
        for tool_name in effective_disabled:
            logger.debug(f"Tool '{tool_name}' disabled via DISABLED_TOOLS")
        return tools_interface
    else:
        # Regular dict case - filter manually
        enabled_tools = {}
        for tool_name, tool_instance in tools_interface.items():
            if tool_name in ESSENTIAL_TOOLS or tool_name not in disabled_tools:
                enabled_tools[tool_name] = tool_instance
            else:
                logger.debug(f"Tool '{tool_name}' disabled via DISABLED_TOOLS")
        return enabled_tools


def log_tool_configuration(disabled_tools: set[str], tools_interface) -> None:
    """
    Log the final tool configuration for visibility.

    Args:
        disabled_tools: Set of tool names that were requested to be disabled
        tools_interface: Tools interface (dict-like or LazyToolDict)
    """
    if not disabled_tools:
        logger.info("All tools enabled (DISABLED_TOOLS not set)")
        return

    actual_disabled = disabled_tools - ESSENTIAL_TOOLS
    if actual_disabled:
        logger.debug(f"Disabled tools: {sorted(actual_disabled)}")

        # Get active tools from the interface
        if hasattr(tools_interface, "keys"):
            active_tools = sorted(tools_interface.keys())
        else:
            active_tools = sorted(tools_interface.keys())

        logger.info(f"Active tools: {active_tools}")


def filter_disabled_tools(tools_interface):
    """
    Filter tools based on DISABLED_TOOLS environment variable.

    Args:
        tools_interface: Tools interface (dict-like or LazyToolDict)

    Returns:
        Modified tools interface with disabled tools filtered out
    """
    disabled_tools = parse_disabled_tools_env()
    if not disabled_tools:
        log_tool_configuration(disabled_tools, tools_interface)
        return tools_interface
    validate_disabled_tools(disabled_tools, tools_interface)
    filtered_interface = apply_tool_filter(tools_interface, disabled_tools)
    log_tool_configuration(disabled_tools, filtered_interface)
    return filtered_interface


# Initialize the tool factory for lazy loading of AI-powered tools
# Each tool provides specialized functionality for different development tasks
# Tools are loaded on-demand to reduce startup memory usage and initialization time
tool_factory = get_tool_factory()


# Create a wrapper that behaves like the old TOOLS dict but uses lazy loading
class LazyToolDict:
    """
    Dictionary-like wrapper around ToolFactory that maintains backward compatibility
    while enabling lazy loading. This allows existing code to work unchanged.
    """

    def __init__(self, factory):
        self._factory = factory
        self._disabled_tools = set()

    def __getitem__(self, key):
        if key in self._disabled_tools:
            raise KeyError(f"Tool '{key}' is disabled")
        tool = self._factory.get_tool(key)
        if tool is None:
            raise KeyError(f"Tool '{key}' not found")
        return tool

    def __contains__(self, key):
        return key not in self._disabled_tools and key in self._factory

    def __iter__(self):
        for tool_name in self._factory.get_available_tools():
            if tool_name not in self._disabled_tools:
                yield tool_name

    def keys(self):
        return [name for name in self._factory.get_available_tools() if name not in self._disabled_tools]

    def values(self):
        for tool_name in self.keys():
            tool = self._factory.get_tool(tool_name)
            if tool:
                yield tool

    def items(self):
        for tool_name in self.keys():
            tool = self._factory.get_tool(tool_name)
            if tool:
                yield (tool_name, tool)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def set_disabled_tools(self, disabled_tools):
        """Set the list of disabled tools."""
        self._disabled_tools = set(disabled_tools)


# Create the lazy TOOLS interface with backward compatibility
TOOLS = LazyToolDict(tool_factory)

# Apply tool filtering (maintain existing functionality)
TOOLS = filter_disabled_tools(TOOLS)

# Initialize service instances for request handler decomposition
provider_manager = ProviderManager()
conversation_manager = ConversationManager()
file_operation_service = FileOperationService()
model_validation_service = ModelValidationService(provider_manager)

# Rich prompt templates for all tools
PROMPT_TEMPLATES = {
    "chat": {
        "name": "chat",
        "description": "Chat and brainstorm ideas",
        "template": "Chat with {model} about this",
    },
    "thinkdeep": {
        "name": "thinkdeeper",
        "description": "Step-by-step deep thinking workflow with expert analysis",
        "template": "Start comprehensive deep thinking workflow with {model} using {thinking_mode} thinking mode",
    },
    "planner": {
        "name": "planner",
        "description": "Break down complex ideas, problems, or projects into multiple manageable steps",
        "template": "Create a detailed plan with {model}",
    },
    "consensus": {
        "name": "consensus",
        "description": "Step-by-step consensus workflow with multi-model analysis",
        "template": "Start comprehensive consensus workflow with {model}",
    },
    "codereview": {
        "name": "review",
        "description": "Perform a comprehensive code review",
        "template": "Perform a comprehensive code review with {model}",
    },
    "precommit": {
        "name": "precommit",
        "description": "Step-by-step pre-commit validation workflow",
        "template": "Start comprehensive pre-commit validation workflow with {model}",
    },
    "debug": {
        "name": "debug",
        "description": "Debug an issue or error",
        "template": "Help debug this issue with {model}",
    },
    "secaudit": {
        "name": "secaudit",
        "description": "Comprehensive security audit with OWASP Top 10 coverage",
        "template": "Perform comprehensive security audit with {model}",
    },
    "docgen": {
        "name": "docgen",
        "description": "Generate comprehensive code documentation with complexity analysis",
        "template": "Generate comprehensive documentation with {model}",
    },
    "analyze": {
        "name": "analyze",
        "description": "Analyze files and code structure",
        "template": "Analyze these files with {model}",
    },
    "refactor": {
        "name": "refactor",
        "description": "Refactor and improve code structure",
        "template": "Refactor this code with {model}",
    },
    "tracer": {
        "name": "tracer",
        "description": "Trace code execution paths",
        "template": "Generate tracer analysis with {model}",
    },
    "testgen": {
        "name": "testgen",
        "description": "Generate comprehensive tests",
        "template": "Generate comprehensive tests with {model}",
    },
    "challenge": {
        "name": "challenge",
        "description": "Challenge a statement critically without automatic agreement",
        "template": "Challenge this statement critically",
    },
    "cache_monitor": {
        "name": "cache_monitor",
        "description": "Monitor and manage cache system",
        "template": "Check cache performance and health",
    },
    "listmodels": {
        "name": "listmodels",
        "description": "List available AI models",
        "template": "List all available models",
    },
    "version": {
        "name": "version",
        "description": "Show server version and system information",
        "template": "Show Zen MCP Server version",
    },
}


def configure_providers():
    """
    Configure and validate AI providers based on available API keys.

    This function checks for API keys and registers the appropriate providers.
    At least one valid API key (Gemini or OpenAI) is required.

    Raises:
        ValueError: If no valid API keys are found or conflicting configurations detected
    """
    # Log environment variable status for debugging
    logger.debug("Checking environment variables for API keys...")
    api_keys_to_check = ["OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY", "CUSTOM_API_URL"]
    for key in api_keys_to_check:
        value = os.getenv(key)
        logger.debug(f"  {key}: {'[PRESENT]' if value else '[MISSING]'}")
    from providers import ModelProviderRegistry
    from providers.base import ProviderType
    from providers.custom import CustomProvider
    from providers.dial import DIALModelProvider
    from providers.gemini import GeminiModelProvider
    from providers.openai_provider import OpenAIModelProvider
    from providers.openrouter import OpenRouterProvider
    from providers.xai import XAIModelProvider
    from utils.model_restrictions import get_restriction_service

    valid_providers = []
    has_native_apis = False
    has_openrouter = False
    has_custom = False

    # Check for Gemini API key
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        valid_providers.append("Gemini")
        has_native_apis = True
        logger.info("Gemini API key found - Gemini models available")

    # Check for OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    logger.debug(f"OpenAI key check: key={'[PRESENT]' if openai_key else '[MISSING]'}")
    if openai_key and openai_key != "your_openai_api_key_here":
        valid_providers.append("OpenAI (o3)")
        has_native_apis = True
        logger.info("OpenAI API key found - o3 model available")
    else:
        if not openai_key:
            logger.debug("OpenAI API key not found in environment")
        else:
            logger.debug("OpenAI API key is placeholder value")

    # Check for X.AI API key
    xai_key = os.getenv("XAI_API_KEY")
    if xai_key and xai_key != "your_xai_api_key_here":
        valid_providers.append("X.AI (GROK)")
        has_native_apis = True
        logger.info("X.AI API key found - GROK models available")

    # Check for DIAL API key
    dial_key = os.getenv("DIAL_API_KEY")
    if dial_key and dial_key != "your_dial_api_key_here":
        valid_providers.append("DIAL")
        has_native_apis = True
        logger.info("DIAL API key found - DIAL models available")

    # Check for OpenRouter API key
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    logger.debug(f"OpenRouter key check: key={'[PRESENT]' if openrouter_key else '[MISSING]'}")
    if openrouter_key and openrouter_key != "your_openrouter_api_key_here":
        valid_providers.append("OpenRouter")
        has_openrouter = True
        logger.info("OpenRouter API key found - Multiple models available via OpenRouter")
    else:
        if not openrouter_key:
            logger.debug("OpenRouter API key not found in environment")
        else:
            logger.debug("OpenRouter API key is placeholder value")

    # Check for custom API endpoint (Ollama, vLLM, etc.)
    custom_url = os.getenv("CUSTOM_API_URL")
    if custom_url:
        # IMPORTANT: Always read CUSTOM_API_KEY even if empty
        # - Some providers (vLLM, LM Studio, enterprise APIs) require authentication
        # - Others (Ollama) work without authentication (empty key)
        # - DO NOT remove this variable - it's needed for provider factory function
        custom_key = os.getenv("CUSTOM_API_KEY", "")  # Default to empty (Ollama doesn't need auth)
        custom_model = os.getenv("CUSTOM_MODEL_NAME", "llama3.2")
        valid_providers.append(f"Custom API ({custom_url})")
        has_custom = True
        logger.info(f"Custom API endpoint found: {custom_url} with model {custom_model}")
        if custom_key:
            logger.debug("Custom API key provided for authentication")
        else:
            logger.debug("No custom API key provided (using unauthenticated access)")

    # Register providers in priority order:
    # 1. Native APIs first (most direct and efficient)
    if has_native_apis:
        if gemini_key and gemini_key != "your_gemini_api_key_here":
            ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)
        if openai_key and openai_key != "your_openai_api_key_here":
            ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)
        if xai_key and xai_key != "your_xai_api_key_here":
            ModelProviderRegistry.register_provider(ProviderType.XAI, XAIModelProvider)
        if dial_key and dial_key != "your_dial_api_key_here":
            ModelProviderRegistry.register_provider(ProviderType.DIAL, DIALModelProvider)

    # 2. Custom provider second (for local/private models)
    if has_custom:
        # Factory function that creates CustomProvider with proper parameters
        def custom_provider_factory(api_key=None):
            # api_key is CUSTOM_API_KEY (can be empty for Ollama), base_url from CUSTOM_API_URL
            base_url = os.getenv("CUSTOM_API_URL", "")
            return CustomProvider(api_key=api_key or "", base_url=base_url)  # Use provided API key or empty string

        ModelProviderRegistry.register_provider(ProviderType.CUSTOM, custom_provider_factory)

    # 3. OpenRouter last (catch-all for everything else)
    if has_openrouter:
        ModelProviderRegistry.register_provider(ProviderType.OPENROUTER, OpenRouterProvider)

    # Require at least one valid provider
    if not valid_providers:
        raise ValueError(
            "At least one API configuration is required. Please set either:\n"
            "- GEMINI_API_KEY for Gemini models\n"
            "- OPENAI_API_KEY for OpenAI o3 model\n"
            "- XAI_API_KEY for X.AI GROK models\n"
            "- DIAL_API_KEY for DIAL models\n"
            "- OPENROUTER_API_KEY for OpenRouter (multiple models)\n"
            "- CUSTOM_API_URL for local models (Ollama, vLLM, etc.)"
        )

    logger.info(f"Available providers: {', '.join(valid_providers)}")

    # Log provider priority
    priority_info = []
    if has_native_apis:
        priority_info.append("Native APIs (Gemini, OpenAI)")
    if has_custom:
        priority_info.append("Custom endpoints")
    if has_openrouter:
        priority_info.append("OpenRouter (catch-all)")

    if len(priority_info) > 1:
        logger.info(f"Provider priority: {' → '.join(priority_info)}")

    # Register cleanup function for providers
    def cleanup_providers():
        """Clean up all registered providers on shutdown."""
        try:
            registry = ModelProviderRegistry()
            if hasattr(registry, "_initialized_providers"):
                for provider in list(registry._initialized_providers.items()):
                    try:
                        if provider and hasattr(provider, "close"):
                            provider.close()
                    except Exception:
                        # Logger might be closed during shutdown
                        pass
        except Exception:
            # Silently ignore any errors during cleanup
            pass

    atexit.register(cleanup_providers)

    # Check and log model restrictions
    restriction_service = get_restriction_service()
    restrictions = restriction_service.get_restriction_summary()

    if restrictions:
        logger.info("Model restrictions configured:")
        for provider_name, allowed_models in restrictions.items():
            if isinstance(allowed_models, list):
                logger.info(f"  {provider_name}: {', '.join(allowed_models)}")
            else:
                logger.info(f"  {provider_name}: {allowed_models}")

        # Validate restrictions against known models
        provider_instances = {}
        provider_types_to_validate = [ProviderType.GOOGLE, ProviderType.OPENAI, ProviderType.XAI, ProviderType.DIAL]
        for provider_type in provider_types_to_validate:
            provider = ModelProviderRegistry.get_provider(provider_type)
            if provider:
                provider_instances[provider_type] = provider

        if provider_instances:
            restriction_service.validate_against_known_models(provider_instances)
    else:
        logger.info("No model restrictions configured - all models allowed")

    # Check if auto mode has any models available after restrictions
    from config import IS_AUTO_MODE

    if IS_AUTO_MODE:
        available_models = ModelProviderRegistry.get_available_models(respect_restrictions=True)
        if not available_models:
            logger.error(
                "Auto mode is enabled but no models are available after applying restrictions. "
                "Please check your OPENAI_ALLOWED_MODELS and GOOGLE_ALLOWED_MODELS settings."
            )
            raise ValueError(
                "No models available for auto mode due to restrictions. "
                "Please adjust your allowed model settings or disable auto mode."
            )


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    List all available tools with their descriptions and input schemas.

    This handler is called by MCP clients during initialization to discover
    what tools are available. Each tool provides:
    - name: Unique identifier for the tool
    - description: Detailed explanation of what the tool does
    - inputSchema: JSON Schema defining the expected parameters

    Returns:
        List of Tool objects representing all available tools
    """
    logger.debug("MCP client requested tool list")

    # Try to log client info if available (this happens early in the handshake)
    try:
        from utils.client_info import format_client_info, get_client_info_from_context

        client_info = get_client_info_from_context(server)
        if client_info:
            formatted = format_client_info(client_info)
            logger.info(f"MCP Client Connected: {formatted}")

            # Log to activity file as well
            try:
                mcp_activity_logger = logging.getLogger("mcp_activity")
                friendly_name = client_info.get("friendly_name", "Claude")
                raw_name = client_info.get("name", "Unknown")
                version = client_info.get("version", "Unknown")
                mcp_activity_logger.info(f"MCP_CLIENT_INFO: {friendly_name} (raw={raw_name} v{version})")
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Could not log client info during list_tools: {e}")
    tools = []

    # Add all registered AI-powered tools from the TOOLS registry
    for tool in TOOLS.values():
        # Get optional annotations from the tool
        annotations = tool.get_annotations()
        tool_annotations = ToolAnnotations(**annotations) if annotations else None

        tools.append(
            Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.get_input_schema(),
                annotations=tool_annotations,
            )
        )

    # Log cache efficiency info
    if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY") != "your_openrouter_api_key_here":
        logger.debug("OpenRouter registry cache used efficiently across all tool schemas")

    logger.debug(f"Returning {len(tools)} tools to MCP client")
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle incoming tool execution requests with service delegation.

    This refactored handler uses focused service classes for better maintainability,
    testability, and separation of concerns. The original complex logic has been
    decomposed into specialized services:
    - ConversationManager: Handles conversation context reconstruction
    - ModelValidationService: Handles model resolution and validation
    - FileOperationService: Handles file validation and operations
    - ProviderManager: Handles provider resolution and caching
    """
    # Basic logging and activity tracking
    logger.info(f"MCP tool call: {name}")
    logger.debug(f"MCP tool arguments: {list(arguments.keys())}")

    try:
        mcp_activity_logger = logging.getLogger("mcp_activity")
        mcp_activity_logger.info(f"TOOL_CALL: {name} with {len(arguments)} arguments")
    except Exception:
        pass

    # Perform periodic cache maintenance (non-blocking)
    try:
        from utils.cache_manager import get_cache_manager

        cache_manager = get_cache_manager()
        if cache_manager.should_cleanup():
            # Run maintenance in background to avoid blocking tool execution
            import asyncio

            asyncio.create_task(_perform_cache_maintenance())
    except Exception as e:
        logger.debug(f"Cache maintenance check failed (non-critical): {e}")

    # Handle conversation continuation using ConversationManager
    arguments = await conversation_manager.handle_continuation(arguments)

    # Route to AI-powered tools
    if name in TOOLS:
        logger.info(f"Executing tool '{name}' with {len(arguments)} parameter(s)")
        tool = TOOLS[name]

        # Model validation and resolution using ModelValidationService
        validation_error, resolved_model, model_option = await model_validation_service.resolve_and_validate_model(
            arguments, name, tool, DEFAULT_MODEL
        )

        if validation_error:
            return [TextContent(type="text", text=ToolOutput(**validation_error).model_dump_json())]

        # Skip further processing for tools that don't require models
        if not model_validation_service.requires_model_validation(tool):
            return await tool.execute(arguments)

        # File validation using FileOperationService
        file_validation_error = await file_operation_service.prepare_files_for_tool(arguments, resolved_model)
        if file_validation_error:
            logger.warning(f"File validation failed for {name} with model {resolved_model}")
            return [TextContent(type="text", text=ToolOutput(**file_validation_error).model_dump_json())]

        # Execute tool with validated context
        result = await tool.execute(arguments)
        logger.info(f"Tool '{name}' execution completed")

        # Log completion
        try:
            mcp_activity_logger = logging.getLogger("mcp_activity")
            mcp_activity_logger.info(f"TOOL_COMPLETED: {name}")
        except Exception:
            pass

        return result

    # Handle unknown tools
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _perform_cache_maintenance():
    """
    Perform cache maintenance in background to avoid blocking tool execution.
    """
    try:
        from utils.cache_manager import get_cache_manager

        cache_manager = get_cache_manager()
        cache_manager.perform_maintenance()
        logger.debug("Cache maintenance completed successfully")
    except Exception as e:
        logger.warning(f"Cache maintenance failed: {e}")


def get_follow_up_instructions(current_turn_count: int, max_turns: int = None) -> str:
    """
    Generate dynamic follow-up instructions based on conversation turn count.

    Args:
        current_turn_count: Current number of turns in the conversation
        max_turns: Maximum allowed turns before conversation ends (defaults to MAX_CONVERSATION_TURNS)

    Returns:
        Follow-up instructions to append to the tool prompt
    """
    if max_turns is None:
        from utils.conversation_memory import MAX_CONVERSATION_TURNS

        max_turns = MAX_CONVERSATION_TURNS

    if current_turn_count >= max_turns - 1:
        # We're at or approaching the turn limit - no more follow-ups
        return """
IMPORTANT: This is approaching the final exchange in this conversation thread.
Do NOT include any follow-up questions in your response. Provide your complete
final analysis and recommendations."""
    else:
        # Normal follow-up instructions
        remaining_turns = max_turns - current_turn_count - 1
        return f"""

CONVERSATION CONTINUATION: You can continue this discussion with Claude! ({remaining_turns} exchanges remaining)

Feel free to ask clarifying questions or suggest areas for deeper exploration naturally within your response.
If something needs clarification or you'd benefit from additional context, simply mention it conversationally.

IMPORTANT: When you suggest follow-ups or ask questions, you MUST explicitly instruct Claude to use the continuation_id
to respond. Use clear, direct language based on urgency:

For optional follow-ups: "Please continue this conversation using the continuation_id from this response if you'd "
"like to explore this further."

For needed responses: "Please respond using the continuation_id from this response - your input is needed to proceed."

For essential/critical responses: "RESPONSE REQUIRED: Please immediately continue using the continuation_id from "
"this response. Cannot proceed without your clarification/input."

This ensures Claude knows both HOW to maintain the conversation thread AND whether a response is optional, "
"needed, or essential.

The tool will automatically provide a continuation_id in the structured response that Claude can use in subsequent
tool calls to maintain full conversation context across multiple exchanges.

Remember: Only suggest follow-ups when they would genuinely add value to the discussion, and always instruct "
"Claude to use the continuation_id when you do."""


async def reconstruct_thread_context(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Reconstruct conversation context for stateless-to-stateful thread continuation.

    This is a critical function that transforms the inherently stateless MCP protocol into
    stateful multi-turn conversations. It loads persistent conversation state from in-memory
    storage and rebuilds complete conversation context using the sophisticated dual prioritization
    strategy implemented in the conversation memory system.

    CONTEXT RECONSTRUCTION PROCESS:

    1. THREAD RETRIEVAL: Loads complete ThreadContext from storage using continuation_id
       - Includes all conversation turns with tool attribution
       - Preserves file references and cross-tool context
       - Handles conversation chains across multiple linked threads

    2. CONVERSATION HISTORY BUILDING: Uses build_conversation_history() to create
       comprehensive context with intelligent prioritization:

       FILE PRIORITIZATION (Newest-First Throughout):
       - When same file appears in multiple turns, newest reference wins
       - File embedding prioritizes recent versions, excludes older duplicates
       - Token budget management ensures most relevant files are preserved

       CONVERSATION TURN PRIORITIZATION (Dual Strategy):
       - Collection Phase: Processes turns newest-to-oldest for token efficiency
       - Presentation Phase: Presents turns chronologically for LLM understanding
       - Ensures recent context is preserved when token budget is constrained

    3. CONTEXT INJECTION: Embeds reconstructed history into tool request arguments
       - Conversation history becomes part of the tool's prompt context
       - Files referenced in previous turns are accessible to current tool
       - Cross-tool knowledge transfer is seamless and comprehensive

    4. TOKEN BUDGET MANAGEMENT: Applies model-specific token allocation
       - Balances conversation history vs. file content vs. response space
       - Gracefully handles token limits with intelligent exclusion strategies
       - Preserves most contextually relevant information within constraints

    CROSS-TOOL CONTINUATION SUPPORT:
    This function enables seamless handoffs between different tools:
    - Analyze tool → Debug tool: Full file context and analysis preserved
    - Chat tool → CodeReview tool: Conversation context maintained
    - Any tool → Any tool: Complete cross-tool knowledge transfer

    ERROR HANDLING & RECOVERY:
    - Thread expiration: Provides clear instructions for conversation restart
    - Storage unavailability: Graceful degradation with error messaging
    - Invalid continuation_id: Security validation and user-friendly errors

    Args:
        arguments: Original request arguments dictionary containing:
                  - continuation_id (required): UUID of conversation thread to resume
                  - Other tool-specific arguments that will be preserved

    Returns:
        dict[str, Any]: Enhanced arguments dictionary with conversation context:
        - Original arguments preserved
        - Conversation history embedded in appropriate format for tool consumption
        - File context from previous turns made accessible
        - Cross-tool knowledge transfer enabled

    Raises:
        ValueError: When continuation_id is invalid, thread not found, or expired
                   Includes user-friendly recovery instructions

    Performance Characteristics:
        - O(1) thread lookup in memory
        - O(n) conversation history reconstruction where n = number of turns
        - Intelligent token budgeting prevents context window overflow
        - Optimized file deduplication minimizes redundant content

    Example Usage Flow:
        1. Claude: "Continue analyzing the security issues" + continuation_id
        2. reconstruct_thread_context() loads previous analyze conversation
        3. Debug tool receives full context including previous file analysis
        4. Debug tool can reference specific findings from analyze tool
        5. Natural cross-tool collaboration without context loss
    """
    from utils.conversation_memory import add_turn, build_conversation_history, get_thread

    continuation_id = arguments["continuation_id"]

    # Get thread context from storage
    logger.debug(f"[CONVERSATION_DEBUG] Looking up thread {continuation_id} in storage")
    context = get_thread(continuation_id)
    if not context:
        logger.warning(f"Thread not found: {continuation_id}")
        logger.debug(f"[CONVERSATION_DEBUG] Thread {continuation_id} not found in storage or expired")

        # Log to activity file for monitoring
        try:
            mcp_activity_logger = logging.getLogger("mcp_activity")
            mcp_activity_logger.info(f"CONVERSATION_ERROR: Thread {continuation_id} not found or expired")
        except Exception:
            pass

        # Return error asking Claude to restart conversation with full context
        raise ValueError(
            f"Conversation thread '{continuation_id}' was not found or has expired. "
            f"This may happen if the conversation was created more than 3 hours ago or if the "
            f"server was restarted. "
            f"Please restart the conversation by providing your full question/prompt without the "
            f"continuation_id parameter. "
            f"This will create a new conversation thread that can continue with follow-up exchanges."
        )

    # Add user's new input to the conversation
    user_prompt = arguments.get("prompt", "")
    if user_prompt:
        # Capture files referenced in this turn
        user_files = arguments.get("files", [])
        logger.debug(f"[CONVERSATION_DEBUG] Adding user turn to thread {continuation_id}")
        from utils.token_utils import estimate_tokens

        user_prompt_tokens = estimate_tokens(user_prompt)
        logger.debug(
            f"[CONVERSATION_DEBUG] User prompt length: {len(user_prompt)} chars (~{user_prompt_tokens:,} tokens)"
        )
        logger.debug(f"[CONVERSATION_DEBUG] User files: {user_files}")
        success = add_turn(continuation_id, "user", user_prompt, files=user_files)
        if not success:
            logger.warning(f"Failed to add user turn to thread {continuation_id}")
            logger.debug("[CONVERSATION_DEBUG] Failed to add user turn - thread may be at turn limit or expired")
        else:
            logger.debug(f"[CONVERSATION_DEBUG] Successfully added user turn to thread {continuation_id}")

    # Create model context early to use for history building
    from utils.model_context import ModelContext

    # Check if we should use the model from the previous conversation turn
    model_from_args = arguments.get("model")
    if not model_from_args and context.turns:
        # Find the last assistant turn to get the model used
        for turn in reversed(context.turns):
            if turn.role == "assistant" and turn.model_name:
                arguments["model"] = turn.model_name
                logger.debug(f"[CONVERSATION_DEBUG] Using model from previous turn: {turn.model_name}")
                break

    model_context = ModelContext.from_arguments(arguments)

    # Build conversation history with model-specific limits
    logger.debug(f"[CONVERSATION_DEBUG] Building conversation history for thread {continuation_id}")
    logger.debug(f"[CONVERSATION_DEBUG] Thread has {len(context.turns)} turns, tool: {context.tool_name}")
    logger.debug(f"[CONVERSATION_DEBUG] Using model: {model_context.model_name}")
    conversation_history, conversation_tokens = build_conversation_history(context, model_context)
    logger.debug(f"[CONVERSATION_DEBUG] Conversation history built: {conversation_tokens:,} tokens")
    logger.debug(
        f"[CONVERSATION_DEBUG] Conversation history length: {len(conversation_history)} chars (~{conversation_tokens:,} tokens)"
    )

    # Add dynamic follow-up instructions based on turn count
    follow_up_instructions = get_follow_up_instructions(len(context.turns))
    logger.debug(f"[CONVERSATION_DEBUG] Follow-up instructions added for turn {len(context.turns)}")

    # All tools now use standardized 'prompt' field
    original_prompt = arguments.get("prompt", "")
    logger.debug("[CONVERSATION_DEBUG] Extracting user input from 'prompt' field")
    original_prompt_tokens = estimate_tokens(original_prompt) if original_prompt else 0
    logger.debug(
        f"[CONVERSATION_DEBUG] User input length: {len(original_prompt)} chars (~{original_prompt_tokens:,} tokens)"
    )

    # Merge original context with new prompt and follow-up instructions
    if conversation_history:
        enhanced_prompt = (
            f"{conversation_history}\n\n=== NEW USER INPUT ===\n{original_prompt}\n\n{follow_up_instructions}"
        )
    else:
        enhanced_prompt = f"{original_prompt}\n\n{follow_up_instructions}"

    # Update arguments with enhanced context and remaining token budget
    enhanced_arguments = arguments.copy()

    # Store the enhanced prompt in the prompt field
    enhanced_arguments["prompt"] = enhanced_prompt
    # Store the original user prompt separately for size validation
    enhanced_arguments["_original_user_prompt"] = original_prompt
    logger.debug("[CONVERSATION_DEBUG] Storing enhanced prompt in 'prompt' field")
    logger.debug("[CONVERSATION_DEBUG] Storing original user prompt in '_original_user_prompt' field")

    # Calculate remaining token budget based on current model
    # (model_context was already created above for history building)
    token_allocation = model_context.calculate_token_allocation()

    # Calculate remaining tokens for files/new content
    # History has already consumed some of the content budget
    remaining_tokens = token_allocation.content_tokens - conversation_tokens
    enhanced_arguments["_remaining_tokens"] = max(0, remaining_tokens)  # Ensure non-negative
    enhanced_arguments["_model_context"] = model_context  # Pass context for use in tools

    logger.debug("[CONVERSATION_DEBUG] Token budget calculation:")
    logger.debug(f"[CONVERSATION_DEBUG]   Model: {model_context.model_name}")
    logger.debug(f"[CONVERSATION_DEBUG]   Total capacity: {token_allocation.total_tokens:,}")
    logger.debug(f"[CONVERSATION_DEBUG]   Content allocation: {token_allocation.content_tokens:,}")
    logger.debug(f"[CONVERSATION_DEBUG]   Conversation tokens: {conversation_tokens:,}")
    logger.debug(f"[CONVERSATION_DEBUG]   Remaining tokens: {remaining_tokens:,}")

    # Merge original context parameters (files, etc.) with new request
    if context.initial_context:
        logger.debug(f"[CONVERSATION_DEBUG] Merging initial context with {len(context.initial_context)} parameters")
        for key, value in context.initial_context.items():
            if key not in enhanced_arguments and key not in ["temperature", "thinking_mode", "model"]:
                enhanced_arguments[key] = value
                logger.debug(f"[CONVERSATION_DEBUG] Merged initial context param: {key}")

    logger.info(f"Reconstructed context for thread {continuation_id} (turn {len(context.turns)})")
    logger.debug(f"[CONVERSATION_DEBUG] Final enhanced arguments keys: {list(enhanced_arguments.keys())}")

    # Debug log files in the enhanced arguments for file tracking
    if "files" in enhanced_arguments:
        logger.debug(f"[CONVERSATION_DEBUG] Final files in enhanced arguments: {enhanced_arguments['files']}")

    # Log to activity file for monitoring
    try:
        mcp_activity_logger = logging.getLogger("mcp_activity")
        mcp_activity_logger.info(
            f"CONVERSATION_CONTINUATION: Thread {continuation_id} turn {len(context.turns)} - "
            f"{len(context.turns)} previous turns loaded"
        )
    except Exception:
        pass

    return enhanced_arguments


@server.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    """
    List all available prompts for Claude Code shortcuts.

    This handler returns prompts that enable shortcuts like /zen:thinkdeeper.
    We automatically generate prompts from all tools (1:1 mapping) plus add
    a few marketing aliases with richer templates for commonly used tools.

    Returns:
        List of Prompt objects representing all available prompts
    """
    logger.debug("MCP client requested prompt list")
    prompts = []

    # Add a prompt for each tool with rich templates
    for tool_name, tool in TOOLS.items():
        if tool_name in PROMPT_TEMPLATES:
            # Use the rich template
            template_info = PROMPT_TEMPLATES[tool_name]
            prompts.append(
                Prompt(
                    name=template_info["name"],
                    description=template_info["description"],
                    arguments=[],  # MVP: no structured args
                )
            )
        else:
            # Fallback for any tools without templates (shouldn't happen)
            prompts.append(
                Prompt(
                    name=tool_name,
                    description=f"Use {tool.name} tool",
                    arguments=[],
                )
            )

    # Add special "continue" prompt
    prompts.append(
        Prompt(
            name="continue",
            description="Continue the previous conversation using the chat tool",
            arguments=[],
        )
    )

    logger.debug(f"Returning {len(prompts)} prompts to MCP client")
    return prompts


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, Any] = None) -> GetPromptResult:
    """
    Get prompt details and generate the actual prompt text.

    This handler is called when a user invokes a prompt (e.g., /zen:thinkdeeper or /zen:chat:o3).
    It generates the appropriate text that Claude will then use to call the
    underlying tool.

    Supports structured prompt names like "chat:o3" where:
    - "chat" is the tool name
    - "o3" is the model to use

    Args:
        name: The name of the prompt to execute (can include model like "chat:o3")
        arguments: Optional arguments for the prompt (e.g., model, thinking_mode)

    Returns:
        GetPromptResult with the prompt details and generated message

    Raises:
        ValueError: If the prompt name is unknown
    """
    logger.debug(f"MCP client requested prompt: {name} with args: {arguments}")

    # Handle special "continue" case
    if name.lower() == "continue":
        # This is "/zen:continue" - use chat tool as default for continuation
        tool_name = "chat"
        template_info = {
            "name": "continue",
            "description": "Continue the previous conversation",
            "template": "Continue the conversation",
        }
        logger.debug("Using /zen:continue - defaulting to chat tool")
    else:
        # Find the corresponding tool by checking prompt names
        tool_name = None
        template_info = None

        # Check if it's a known prompt name
        for t_name, t_info in PROMPT_TEMPLATES.items():
            if t_info["name"] == name:
                tool_name = t_name
                template_info = t_info
                break

        # If not found, check if it's a direct tool name
        if not tool_name and name in TOOLS:
            tool_name = name
            template_info = {
                "name": name,
                "description": f"Use {name} tool",
                "template": f"Use {name}",
            }

        if not tool_name:
            logger.error(f"Unknown prompt requested: {name}")
            raise ValueError(f"Unknown prompt: {name}")

    # Get the template
    template = template_info.get("template", f"Use {tool_name}")

    # Safe template expansion with defaults
    final_model = arguments.get("model", "auto") if arguments else "auto"

    prompt_args = {
        "model": final_model,
        "thinking_mode": arguments.get("thinking_mode", "medium") if arguments else "medium",
    }

    logger.debug(f"Using model '{final_model}' for prompt '{name}'")

    # Safely format the template
    try:
        prompt_text = template.format(**prompt_args)
    except KeyError as e:
        logger.warning(f"Missing template argument {e} for prompt {name}, using raw template")
        prompt_text = template  # Fallback to raw template

    # Generate tool call instruction
    if name.lower() == "continue":
        # "/zen:continue" case
        tool_instruction = f"Continue the previous conversation using the {tool_name} tool"
    else:
        # Simple prompt case
        tool_instruction = prompt_text

    return GetPromptResult(
        prompt=Prompt(
            name=name,
            description=template_info["description"],
            arguments=[],
        ),
        messages=[
            PromptMessage(
                role="user",
                content={"type": "text", "text": tool_instruction},
            )
        ],
    )


async def main():
    """
    Main entry point for the MCP server.

    Initializes the Gemini API configuration and starts the server using
    stdio transport. The server will continue running until the client
    disconnects or an error occurs.

    The server communicates via standard input/output streams using the
    MCP protocol's JSON-RPC message format.
    """
    # Validate and configure providers based on available API keys
    configure_providers()

    # Initialize caching infrastructure
    try:
        from utils.cache_manager import get_cache_manager

        cache_manager = get_cache_manager()

        # Warm caches with common data
        cache_manager.warm_all_caches()

        # Get initial cache stats
        cache_stats = cache_manager.get_global_stats()
        logger.info(f"Cache system initialized - Memory limit: {cache_stats['memory_limit_mb']}MB")

    except Exception as e:
        logger.warning(f"Cache initialization failed (non-critical): {e}")

    # Log startup message
    logger.info("Zen MCP Server starting up...")
    logger.info(f"Log level: {log_level}")

    # Note: MCP client info will be logged during the protocol handshake
    # (when handle_list_tools is called)

    # Log current model mode
    from config import IS_AUTO_MODE

    if IS_AUTO_MODE:
        logger.info("Model mode: AUTO (Claude will select the best model for each task)")
    else:
        logger.info(f"Model mode: Fixed model '{DEFAULT_MODEL}'")

    # Import here to avoid circular imports
    from config import DEFAULT_THINKING_MODE_THINKDEEP

    logger.info(f"Default thinking mode (ThinkDeep): {DEFAULT_THINKING_MODE_THINKDEEP}")

    logger.info(f"Available tools: {list(TOOLS.keys())}")
    logger.info("Server ready - waiting for tool requests...")

    # Run the server using stdio transport (standard input/output)
    # This allows the server to be launched by MCP clients as a subprocess
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="zen",
                server_version=__version__,
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(),  # Advertise tool support capability
                    prompts=PromptsCapability(),  # Advertise prompt support capability
                ),
            ),
        )


def run():
    """Console script entry point for zen-mcp-server."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle graceful shutdown
        pass


if __name__ == "__main__":
    run()
