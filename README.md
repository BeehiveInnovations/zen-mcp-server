# Zen MCP Server – Coldaine Augmented Fork

This repository provides **16 sophisticated AI-powered tools** with workflow capabilities, conversation memory, and multi-provider support. A **LangGraph multi-agent architecture** is in development for future migration.

## Current Architecture: Tool/Registry System ✅ PRODUCTION READY

The server provides 16 specialized tools that handle complex development workflows through AI-powered analysis and multi-step processes.

### Core Capabilities
- **16 Production Tools**: Chat, analysis, debugging, code review, security auditing, and more
- **Conversation Memory**: Multi-turn AI-to-AI conversations with context preservation
- **Multi-Provider Support**: OpenAI, Gemini, OpenRouter, XAI, DIAL, and custom endpoints
- **Workflow Automation**: Step-by-step analysis with expert validation
- **Model Selection**: Auto mode or manual model selection per task
- **File Analysis**: Comprehensive codebase analysis with intelligent context management

## Future Architecture: LangGraph Multi-Agent 🔄 IN DEVELOPMENT

A multi-agent system with Supervisor routing to specialized workers (Architect, Coder, Researcher, etc.) is being developed. See [`docs/MIGRATION_GUIDE.md`](docs/MIGRATION_GUIDE.md) for migration details.

### Gateway vs Direct Provider Mode

The experimental LangGraph layer supports **dynamic routing through a unified gateway** (Bifrost/LiteLLM) or **direct provider SDKs**. Control this via environment variables:

```bash
# Gateway mode (centralized credential + policy management)
USE_GATEWAY=true
GATEWAY_URL=http://localhost:8080/langchain
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# Direct mode (talk to providers individually)
USE_GATEWAY=false
OPENAI_API_KEY=sk-openai...
GEMINI_API_KEY=...            # Optional if switching provider
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
```

The Supervisor and worker nodes resolve models through `agent/llm_factory.py`, keeping graph code provider‑agnostic. Override the Supervisor’s specific model with `SUPERVISOR_MODEL` if needed.

Docker Compose example with gateway + Redis: `docker/docker-compose.gateway.yml`.

## Quick Start

### 1. Installation
```bash
git clone https://github.com/Coldaine/zen-mcp-server.git && cd zen-mcp-server
python -m pip install -e .
```

### 2. Configuration
```bash
cp .env.example .env
# Edit .env with your API keys (at least one required)
```

### 3. Run Server
```bash
./run-server.sh
```

### 4. Use with Claude Desktop
Add to your Claude Desktop configuration:
```json
{
  "mcpServers": {
    "zen": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/zen-mcp-server"
    }
  }
}
```

## Setup Requirements

- **Python**: 3.10+ recommended
- **API Keys**: At least one provider (OpenAI, Gemini, OpenRouter, XAI, DIAL, or custom)
- **Optional**: uv for faster installs (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Available Tools

| Tool | Purpose | Key Features |
|------|---------|-------------|
| **chat** | Interactive development | Conversation memory, multi-turn dialogue |
| **thinkdeep** | Deep analysis | Expert validation, step-by-step reasoning |
| **planner** | Project planning | Sequential workflow, task breakdown |
| **consensus** | Multi-model analysis | Parallel model consultation, consensus building |
| **codereview** | Code quality | Step-by-step review, expert analysis |
| **debug** | Issue resolution | Root cause analysis, investigation workflow |
| **secaudit** | Security analysis | OWASP Top 10, compliance checks |
| **analyze** | File analysis | Comprehensive codebase investigation |
| **refactor** | Code improvement | Refactoring strategies, validation |
| **testgen** | Test creation | Automated test generation |
| **docgen** | Documentation | Auto-generated documentation |
| **tracer** | Execution analysis | Call path tracing, control flow |
| **precommit** | Validation | Pre-commit checks, compliance |
| **challenge** | Critical thinking | Avoid automatic agreement |
| **listmodels** | Model info | Available models by provider |
| **version** | Server info | Version and system information |

## Configuration

### Required API Keys
Configure at least one provider in `.env`:

```bash
# OpenAI (recommended for GPT models)
OPENAI_API_KEY=your_openai_key_here

# Google Gemini (recommended for Flash/Pro models)
GEMINI_API_KEY=your_gemini_key_here

# OpenRouter (access to multiple models)
OPENROUTER_API_KEY=your_openrouter_key_here

# X.AI (GROK models)
XAI_API_KEY=your_xai_key_here

# DIAL (enterprise unified access)
DIAL_API_KEY=your_dial_key_here

# Custom endpoints (Ollama, vLLM, etc.)
CUSTOM_API_URL=http://localhost:11434/v1
CUSTOM_API_KEY=  # Leave empty for Ollama
```

### Optional Settings
```bash
# Default model (auto lets Claude choose best model)
DEFAULT_MODEL=auto

# Tool selection (disable non-essential tools)
DISABLED_TOOLS=analyze,refactor,testgen,secaudit,docgen,tracer

# Conversation settings
CONVERSATION_TIMEOUT_HOURS=3
MAX_CONVERSATION_TURNS=20

# Logging level
LOG_LEVEL=INFO
```

## Documentation

- **[Project Status](docs/PROJECT_STATUS.md)**: Current implementation status
- **[Migration Guide](docs/MIGRATION_GUIDE.md)**: LangGraph migration path
- **[Architecture Alignment](docs/ARCHITECTURE_ALIGNMENT.md)**: Technical decisions
- **[Migration Master Plan](docs/MIGRATION_MASTER_PLAN.md)**: Detailed LangGraph roadmap

## Development

### Running Tests
```bash
# Full test suite
python -m pytest

# Specific tool tests
python -m pytest tests/test_consensus.py -v

# Integration tests
./run_integration_tests.sh
```

### Development Setup
```bash
# Install development dependencies
python -m pip install -r requirements-dev.txt

# Code formatting
black .
isort .
ruff check .
```

## Fork Scope

This fork enhances the original with:
- **Advanced Workflow Tools**: Sophisticated multi-step analysis with expert validation
- **Conversation Memory**: Persistent AI-to-AI conversations across tool interactions
- **Multi-Provider Support**: Unified access to all major AI providers
- **Custom Model Registry**: Tailored model configurations and defaults
- **Cross-Platform Scripts**: PowerShell variants and Docker support
- **Comprehensive Testing**: Extensive test coverage with integration scenarios

## Project Status & Migration

### Current System: Tool/Registry Architecture ✅ PRODUCTION READY
- **16 sophisticated tools** with workflow capabilities and conversation memory
- **Multi-provider support** for all major AI providers
- **Comprehensive testing** with integration scenarios
- **Production stability** with extensive real-world usage

### Future System: LangGraph Multi-Agent 🔄 IN DEVELOPMENT
- **2/7 nodes implemented** (Supervisor, Researcher)
- **Dynamic LLM factory** (`agent/llm_factory.py`) enabling gateway toggle
- **State persistence** with Redis checkpointing
- **Agent orchestration** for complex workflows
- **Migration path** documented in [`docs/MIGRATION_GUIDE.md`](docs/MIGRATION_GUIDE.md)

### Quick Status Reference
- **For immediate use**: Current tool/registry system is fully functional
- **For development**: LangGraph system available for testing
- **For planning**: See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for detailed progress

---

**License**: Apache 2.0

**Note**: Use the current tool/registry system for production work. The LangGraph system is experimental and intended for development and testing.
