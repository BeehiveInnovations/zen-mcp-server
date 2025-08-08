# Architecture Index (Quick Reference)

- Entrypoint: `server.py` → `run()` → `main()` → MCP `stdio_server()`.
- MCP Routing Handlers (in `server.py`):
  - `@server.list_tools()` → returns tool list from `TOOLS`.
  - `@server.call_tool(name, arguments)` → dispatches to `TOOLS[name]` with context reconstruction and model resolution.
  - `@server.list_prompts()` → exposes `PROMPT_TEMPLATES` as named prompts.
  - `@server.get_prompt(name, arguments)` → renders prompt to instruction.
- Tool Registry: defined in `server.py` (`TOOLS = {...}`), implementations in `tools/`.
- Providers: dynamic registration in `configure_providers()`; registry in `providers/registry.py`.
- Conversation Memory: `utils/conversation_memory.py`.
- Configuration: `config.py`, docs in `docs/configuration.md`.
- Logs: `logs/mcp_server.log`, `logs/mcp_activity.log`.

See `docs/architecture.md` for a full deep-dive.