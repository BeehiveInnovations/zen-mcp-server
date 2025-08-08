# Zen MCP Server Architecture Notes

These notes are for future contributors and agent integrators. They summarize how the server is structured, how routing works (MCP handlers and tool dispatch), and the most important operational considerations.

## Overview
- The server is an MCP (Model Context Protocol) server that communicates over stdio with MCP-capable clients (e.g., Claude Desktop, Claude Code CLI, Gemini CLI).
- There is no HTTP web server in production. Any Flask or FastAPI files you see in `simulator_tests/` or `test_simulation_files/` are test fixtures only.
- Main entrypoint: `server.py` (console script exposed as `zen-mcp-server` via `pyproject.toml`).

## Entrypoints and Process Model
- Console entrypoint: `zen-mcp-server = "server:run"` (see `pyproject.toml`).
- Runtime: `server.run()` → `asyncio.run(main())` → `stdio_server()` → `server.run(read_stream, write_stream, InitializationOptions(...))`.
- The process is intended to remain resident while the MCP client is running to preserve conversation memory (see Conversation Memory).

## Routing (MCP Handlers)
All MCP routing is implemented with decorators on the global `server` instance in `server.py`.

- `@server.list_tools()` → `handle_list_tools()` returns the list of tools (names, descriptions, input schemas).
- `@server.call_tool()` → `handle_call_tool(name, arguments)` is the central dispatcher. It:
  - Looks up the tool by name in `TOOLS`.
  - Reconstructs conversation context when `continuation_id` is present.
  - Resolves model/provider before delegating to the tool.
  - Performs file-size checks and token budgeting prior to tool execution.
- `@server.list_prompts()` → `handle_list_prompts()` returns named command shortcuts (e.g., `/zen:thinkdeeper`).
- `@server.get_prompt()` → `handle_get_prompt(name, arguments)` resolves the named prompt to a concrete instruction that the client will then use to call a tool.

Source locations:
- MCP server init and handlers: `server.py` (see handlers around `@server.list_tools`, `@server.call_tool`, `@server.list_prompts`, `@server.get_prompt`).

## Tool Registry
- Defined in `server.py` as `TOOLS = { ... }`.
- Tools are instantiated once (stateless by design) and reused across requests.
- Current tool names (keys in `TOOLS`):
  - `chat`, `thinkdeep`, `planner`, `consensus`, `codereview`, `precommit`, `debug`, `secaudit`, `docgen`, `analyze`, `refactor`, `tracer`, `testgen`, `challenge`, `listmodels`, `version`.
- Each tool class lives under `tools/` and implements a common API via `tools/shared/base_tool.py` and workflow mixins where applicable.
- Environment-based tool filtering: set `DISABLED_TOOLS` to a comma-separated list of tool names to disable at startup (essential tools cannot be disabled).

## Prompts and Shortcuts
- The `PROMPT_TEMPLATES` mapping in `server.py` defines human-friendly prompt names and descriptions for each tool.
- `handle_list_prompts()` exposes these as MCP prompts; `handle_get_prompt()` turns them into instructions.
- Notable:
  - The `thinkdeep` tool’s shortcut prompt is named `thinkdeeper` (intentional).
  - Special alias `continue` maps to `chat` to continue a previous thread.

## Provider Architecture and Model Routing
- Providers are registered dynamically based on environment variables in `configure_providers()` (in `server.py`).
- Registration priority:
  1) Native APIs (Google/Gemini, OpenAI, X.AI, DIAL)
  2) Custom provider (local/self-hosted endpoints like Ollama/vLLM via `CUSTOM_API_URL`)
  3) OpenRouter (catch-all unified API)
- Provider registry: `providers/registry.py` (singleton `ModelProviderRegistry`).
  - `get_provider_for_model(model_name)` walks providers in priority order and asks them to validate the model.
  - `get_available_models(respect_restrictions=True)` composes model lists while avoiding double restriction filtering.
- Restrictions and environment knobs are described in `docs/configuration.md` (e.g., `OPENAI_ALLOWED_MODELS`, `GOOGLE_ALLOWED_MODELS`, etc.).

## Conversation Memory
- Implemented in `utils/conversation_memory.py`.
- In-memory, process-local storage of conversation threads (UUID).
- Dual prioritization strategy:
  - Files: newest-first throughout collection and budgeting.
  - Conversation turns: collect newest-first but present chronological order to the model.
- Critical constraints:
  - Requires a persistent MCP server process. If tools are invoked as separate subprocesses, memory is lost.
  - Defaults (env-overridable): `MAX_CONVERSATION_TURNS` (20), `CONVERSATION_TIMEOUT_HOURS` (3).
- `handle_call_tool()` uses `reconstruct_thread_context()` to merge prior context, files, and budgeting into the current request.

## Configuration Essentials
- Defaults and constants live in `config.py`.
- Important environment variables:
  - `DEFAULT_MODEL` (e.g., `auto`, `pro`, `flash`, `o3`, etc.).
  - `LOCALE` for response language hints.
  - `DISABLED_TOOLS` to disable non-essential tools at startup.
  - Provider keys: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `XAI_API_KEY`, `DIAL_API_KEY`.
  - Custom endpoints: `CUSTOM_API_URL`, `CUSTOM_API_KEY`, `CUSTOM_MODEL_NAME`.
  - Thinking modes (Gemini): `DEFAULT_THINKING_MODE_THINKDEEP`.
  - MCP transport sizing: derives prompt size limit from `MAX_MCP_OUTPUT_TOKENS`.
  - Logging level: `LOG_LEVEL` (DEBUG by default in code; change via env).
- Full configuration reference: `docs/configuration.md` and `docs/advanced-usage.md`.

## Logging
- Logs directory: `logs/` created on startup by `server.py`.
- Files and rotation (aligned with docs):
  - `logs/mcp_server.log`: rotates at 20MB, keeps 10 backups (≈200MB total).
  - `logs/mcp_activity.log`: rotates at 20MB, keeps 5 backups (≈100MB total).
- Why file logs: MCP stdio transport interferes with stderr during tool execution; details go to files. See `docs/logging.md` and `docs/testing.md`.

## Running Locally
- Preferred: use `run-server.sh` which:
  - Creates a venv (uv-first if available), installs deps, validates env, and can register with Claude automatically.
  - Offers `-f` to follow logs.
- Alternative (quick usage via uvx): see `README.md` quickstart; `pyproject.toml` exposes `zen-mcp-server` entrypoint.
- Tests: see `docs/testing.md` (unit vs. simulator tests; log observation during simulator runs).

## Extending the System
- Adding a tool: follow `docs/tools/*.md` and base classes in `tools/shared/base_tool.py` and `tools/workflow/`.
- Adding a provider: see `docs/adding_providers.md` and provider interfaces in `providers/base.py`.
- System prompts live in `systemprompts/` and are imported via `systemprompts/__init__.py`.

## Security and Operational Notes
- Avoid configuring overlapping provider sources for the same model names (prefer native API where possible). If using both native and OpenRouter, name/alias models to avoid ambiguity.
- Use model restrictions to control costs and capabilities in production.
- Conversation memory is process-local; ensure you run the server in a persistent process, not per-call subprocesses.
- Always prefer absolute file paths in tool requests.

## Quick Routing Map (Reference)
- Handlers (in `server.py`):
  - `@server.list_tools()` → Discover tool list.
  - `@server.call_tool(name, arguments)` → Execute a tool (with context reconstruction and model routing).
  - `@server.list_prompts()` → Discover named command shortcuts.
  - `@server.get_prompt(name, arguments)` → Resolve a prompt to instructions.
- Dispatch to tools via `TOOLS[...]` by tool name. Prompt shortcuts map 1:1 to tools via `PROMPT_TEMPLATES`, with special cases noted above.