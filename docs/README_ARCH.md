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

## Docs Map
- Core
  - `docs/architecture.md` (deep dive)
  - `docs/README_ARCH.md` (this index)
  - `docs/advanced-usage.md`
  - `docs/configuration.md`
  - `docs/testing.md`
  - `docs/troubleshooting.md`
  - `docs/logging.md`
  - `docs/locale-configuration.md`
  - `ROADMAP.md`
- Providers & Models
  - `docs/adding_providers.md`
  - `docs/custom_models.md`
  - `docs/gemini-setup.md`
- Deployment
  - `docs/docker-deployment.md`
  - `README.md` (Quickstart)
- Tools Reference (`docs/tools/`)
  - analyze, chat, challenge, planner, consensus, codereview, precommit, debug, docgen, refactor, tracer, testgen, thinkdeep, listmodels, secaudit, version

## Planning & Roadmap (Initial)
- Short term
  - Keep docs aligned with runtime (provider priority, MCP prompt limits)
  - Ensure `.env.example` stays in sync with configuration docs
- Long term
  - Add a public ROADMAP.md detailing milestones and deprecations
  - Expand simulator tests documentation with troubleshooting for common failures

See `docs/architecture.md` for a full deep-dive.