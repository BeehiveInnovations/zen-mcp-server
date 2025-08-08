# Zen MCP Server Roadmap

## Vision
Deliver a reliable MCP server that orchestrates multiple AI providers with clear workflows, robust conversation memory, and excellent documentation for contributors and agents.

## Short-Term Objectives (next 1–2 sprints)
- Documentation consistency
  - Keep `docs/configuration.md` and `.env.example` in sync
  - Ensure all “large prompt” docs reference `MCP_PROMPT_SIZE_LIMIT`
  - Maintain provider priority docs aligned with runtime (native → custom → OpenRouter)
- Developer experience
  - Add/maintain architecture indices (`docs/README_ARCH.md`)
  - Expand troubleshooting for simulator tests
- Quality and stability
  - Periodically validate that `server.py` logging rotation matches `docs/logging.md`
  - Verify tool registry and prompt templates consistency

## Mid-Term Objectives (next quarter)
- Provider enhancements
  - Expand model aliasing documentation and validation
  - Deeper examples for custom/local providers (Ollama/vLLM) in `custom_models.md`
- Testing
  - CI job for simulator tests with optional local provider
  - Clear guidance for flaky/environment-sensitive tests
- Observability
  - Optional JSON log output mode for log parsing tools

## Long-Term Objectives (6–12 months)
- Modularization
  - Extract provider modules to separate packages where practical
  - Formal plugin API for tools and prompts
- Scale & performance
  - Token budgeting improvements and configurable policies per model
  - Performance profiling guide and benchmarks
- Security & compliance
  - Hardening recommendations for production deployments (container/user namespaces, secrets mgmt)
  - Best practices for network egress and provider API usage

## Dependencies and Risks
- External provider API changes (rate limits, auth headers, model lists)
- MCP protocol or client changes affecting transport and prompt limits
- Local provider variability (Ollama/vLLM) across environments

## Links
- Architecture: `docs/architecture.md`
- Configuration: `docs/configuration.md`
- Docker Deployment: `docs/docker-deployment.md`
- Index: `docs/README_ARCH.md`