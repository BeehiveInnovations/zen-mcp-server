# Gateway / Bifrost Playbook

This playbook packages the snippets, commands, and verification steps needed to run the LangGraph entry point through an external Bifrost (or any OpenAI-compatible) router. It complements the high-level context in `docs/MIGRATION_GUIDE.md` with copy-pastable examples.

## 1. LangChain Factory Usage

```python
from agent.llm_factory import get_llm

llm = get_llm(
    provider="openai",           # defaults to LLM_PROVIDER when omitted
    model="gpt-4o-mini",         # falls back to LLM_MODEL / DEFAULT_MODELS
    temperature=0.2,              # forwarded directly to the LangChain ctor
)
# Honors USE_GATEWAY, GATEWAY_URL, UNIFIED_LLM_API_KEY, etc.
```

- When `USE_GATEWAY=true`, every provider funnels through the gateway URL, wrapping Anthropic/Google/Azure calls with OpenAI-compatible shims where needed.
- When `USE_GATEWAY=false`, the same helper instantiates provider-specific SDKs and expects the native API keys (`OPENAI_API_KEY`, `GEMINI_API_KEY`, ...).

## 2. Environment Toggles

```dotenv
UNIFIED_LLM_GATEWAY=http://localhost:8080      # Router root (Bifrost/LiteLLM)
UNIFIED_LLM_API_KEY=sk-gateway-key-if-required
USE_GATEWAY=true
GATEWAY_URL=http://localhost:8080/langchain    # OpenAI-compatible path
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
SUPERVISOR_MODEL=gpt-4o-mini                   # Optional override for Supervisor node
REDIS_URL=redis://localhost:6379/0             # LangGraph checkpoint store
```

Flip to direct-provider mode by setting `USE_GATEWAY=false` and supplying whichever native keys the workflow requires.

## 3. Docker Compose Stack

`docker/docker-compose.gateway.yml` builds the LangGraph server, a Bifrost gateway, and Redis on a shared bridge network:

```bash
docker compose -f docker/docker-compose.gateway.yml up --build
```

- `mcp-server` runs `python server_graph.py` with gateway/Redis env overrides.
- `gateway` pulls `maximhq/bifrost:latest` and forwards requests using whichever provider keys are passed through (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`).
- `redis` exposes checkpoint storage at `redis://redis:6379/0`.

## 4. Local (Non-Docker) Workflow

```bash
cp .env.example .env
# update the gateway + Redis variables as shown above
./run-server.sh                # legacy architecture
python server_graph.py         # LangGraph entry point
```

Use Claude Desktop (or any MCP client) to point at whichever process you want to exercise.

## 5. Test & Simulator Commands

| Command | Purpose |
| --- | --- |
| `python -m pytest` | Run the full suite (unit + integration). |
| `python -m pytest tests/test_prompt_regression.py -m integration` | Hit the Ollama-backed prompt regression flow (requires `CUSTOM_API_URL`). |
| `python communication_simulator_test.py --quick` | Execute the six essential simulator scenarios end-to-end. |
| `python communication_simulator_test.py --tests basic_conversation content_validation` | Targeted simulator coverage for conversational flows. |

> **Heads-up:** No suite currently toggles `USE_GATEWAY=true`. See `docs/dev/test/review1123.md` for a grade-by-grade breakdown of the existing suites and the missing contract doubles. Adding gateway-aware tests (unit, integration, simulator) is the next high-impact gap.

## 6. Operator Checklist

1. **Credentials:** Either place upstream provider keys on the gateway container/environment variables or configure LiteLLM/Bifrost to pull from your secret store.
2. **Redis:** Confirm `REDIS_URL` resolves and persistence is enabled (volume mount in Docker or managed Redis in cloud).
3. **Routing Toggle:** Keep `USE_GATEWAY=true` for centralized policy enforcement; flip only when diagnosing direct-provider issues.
4. **Monitoring Hooks:** Enable HTTP request logging on the gateway and set `LOG_LEVEL=INFO` (or `DEBUG`) on the MCP server while validating new routes.
5. **Simulator Backstop:** Before rolling changes to production, run the simulator quick suite plus any gateway-specific tests you add per the review.

Refer to this playbook from the README or migration guide whenever you need the concrete commands.
