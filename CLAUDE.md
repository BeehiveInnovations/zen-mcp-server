# Claude Development Guide for Zen MCP Server

This file contains essential commands and workflows for developing and maintaining the Zen MCP Server when working with Claude. Use these instructions to efficiently run quality checks, manage the server, check logs, and run tests.

## Project Overview

**Zen MCP Server v4.8.3** - A Model Context Protocol server that enables Claude to orchestrate multiple AI models (Gemini, O3, GROK, OpenRouter, Ollama, custom endpoints) for collaborative development.

**Current Status**:
- ✅ Production-ready with 491 unit tests + 21 simulator tests
- ✅ 100% test pass requirement enforced via CI/CD
- ✅ Docker-based deployment with Redis for conversation threading
- ✅ Comprehensive documentation (9 guides in docs/)
- ✅ Multi-provider support (Gemini, OpenAI, X.AI, OpenRouter, Custom APIs)

**Key Features**:
- **AI-to-AI Conversation Threading** - Multi-turn conversations between Claude and other models
- **Cross-Tool Continuation** - Context persists across different tools (analyze → codereview)
- **Context Revival** - Resume conversations even after Claude's memory resets
- **Auto Mode** - Claude intelligently selects best model for each task
- **Vision Support** - Image analysis across all tools
- **10 Specialized Tools** - chat, thinkdeep, codereview, precommit, debug, analyze, refactor, tracer, testgen, listmodels

## Quick Reference Commands

### Code Quality Checks

Before making any changes or submitting PRs, always run the comprehensive quality checks:

```bash
# Activate virtual environment first
source venv/bin/activate

# Run all quality checks (linting, formatting, tests)
./code_quality_checks.sh
```

This script automatically runs:
- Ruff linting with auto-fix
- Black code formatting
- Import sorting with isort
- Complete unit test suite (491 tests)
- Verification that all checks pass 100%

### Server Management

#### Start/Restart the Server
```bash
# Start or restart the Docker containers
./run-server.sh

# Start server and follow logs automatically
./run-server.sh -f
```

This script will:
- Build/rebuild Docker images if needed
- Start the MCP server container (`zen-mcp-server`)
- Start the Redis container (`zen-mcp-redis`)
- Set up proper networking and volumes
- Display configuration for Claude Code/Desktop

#### Check Server Status
```bash
# Check if containers are running
docker ps

# Look for these containers:
# - zen-mcp-server
# - zen-mcp-redis
```

### Log Management

#### View Server Logs
```bash
# View last 500 lines of server logs
docker exec zen-mcp-server tail -n 500 /tmp/mcp_server.log

# Follow logs in real-time
docker exec zen-mcp-server tail -f /tmp/mcp_server.log

# View specific number of lines (replace 100 with desired count)
docker exec zen-mcp-server tail -n 100 /tmp/mcp_server.log

# Search logs for specific patterns
docker exec zen-mcp-server grep "ERROR" /tmp/mcp_server.log
docker exec zen-mcp-server grep "tool_name" /tmp/mcp_server.log
```

#### Monitor Tool Executions Only
```bash
# View tool activity log (focused on tool calls and completions)
docker exec zen-mcp-server tail -n 100 /tmp/mcp_activity.log

# Follow tool activity in real-time
docker exec zen-mcp-server tail -f /tmp/mcp_activity.log

# Use the dedicated log monitor (shows tool calls, completions, errors)
python log_monitor.py
```

The `log_monitor.py` script provides a real-time view of:
- Tool calls and completions
- Conversation resumptions and context
- Errors and warnings from all log files
- File rotation handling

#### All Available Log Files
```bash
# Main server log (all activity)
docker exec zen-mcp-server tail -f /tmp/mcp_server.log

# Tool activity only (TOOL_CALL, TOOL_COMPLETED, etc.)
docker exec zen-mcp-server tail -f /tmp/mcp_activity.log

# Debug information
docker exec zen-mcp-server tail -f /tmp/gemini_debug.log

# Overflow logs (when main log gets too large)
docker exec zen-mcp-server tail -f /tmp/mcp_server_overflow.log
```

**Note**: Log files rotate automatically at 20MB to prevent disk space issues:
- mcp_server.log: 10 backup files (200MB total)
- mcp_activity.log: 5 backup files (100MB total)

#### Debug Container Issues
```bash
# Check container logs (Docker level)
docker logs zen-mcp-server

# Execute interactive shell in container
docker exec -it zen-mcp-server /bin/bash

# Check Redis container logs
docker logs zen-mcp-redis

# Check Redis connection
docker exec zen-mcp-redis redis-cli ping
```

### Testing

Zen MCP Server has comprehensive test coverage with two test suites:

#### Unit Tests (491 tests)
Test isolated components and functions:
```bash
# Run all unit tests with pytest
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_refactor.py -v

# Run specific test function
python -m pytest tests/test_refactor.py::TestRefactorTool::test_format_response -v

# Run tests with coverage report
python -m pytest tests/ --cov=. --cov-report=html
```

**Unit test coverage includes**:
- Provider functionality and API interactions
- Tool operations and parameter validation
- Conversation memory and threading
- File handling and deduplication
- Auto mode logic and fallback behavior
- Model restrictions and configurations

#### Simulator Tests (21 tests)

Simulator tests validate real-world usage by simulating actual Claude CLI interactions with the MCP server running in Docker. These tests verify the complete end-to-end flow including MCP protocol communication, Docker container interactions, multi-turn conversations, and log output.

**IMPORTANT**:
- Simulator tests require your actual API keys to be configured in `.env`
- Tests use real AI models and may incur API costs
- Requires `LOG_LEVEL=DEBUG` in `.env` for log validation
- Any time code is changed, you MUST restart the server with `./run-server.sh` OR pass `--rebuild` to the simulator test script

**Run All Simulator Tests:**
```bash
# Run the complete test suite
python communication_simulator_test.py

# Run tests with verbose output
python communication_simulator_test.py --verbose

# Force rebuild environment before testing
python communication_simulator_test.py --rebuild
```

**Run Individual Simulator Tests (Recommended):**
```bash
# List all available tests
python communication_simulator_test.py --list-tests

# RECOMMENDED: Run tests individually for better isolation and debugging
python communication_simulator_test.py --individual basic_conversation
python communication_simulator_test.py --individual content_validation
python communication_simulator_test.py --individual cross_tool_continuation
python communication_simulator_test.py --individual logs_validation
python communication_simulator_test.py --individual redis_validation

# Run multiple specific tests (alternative approach)
python communication_simulator_test.py --tests basic_conversation content_validation

# Run individual test with verbose output for debugging
python communication_simulator_test.py --individual logs_validation --verbose

# Individual tests provide full Docker setup and teardown per test
# This ensures clean state and better error isolation
```

**Available Simulator Tests:**
- `basic_conversation` - Basic conversation flow with chat tool
- `content_validation` - Content validation and duplicate detection
- `per_tool_deduplication` - File deduplication for individual tools
- `cross_tool_continuation` - Cross-tool conversation continuation scenarios
- `cross_tool_comprehensive` - Comprehensive cross-tool file deduplication and continuation
- `line_number_validation` - Line number handling validation across tools
- `logs_validation` - Docker logs validation
- `redis_validation` - Redis conversation memory validation
- `model_thinking_config` - Model-specific thinking configuration behavior
- `o3_model_selection` - O3 model selection and usage validation
- `ollama_custom_url` - Ollama custom URL endpoint functionality
- `openrouter_fallback` - OpenRouter fallback behavior when only provider
- `openrouter_models` - OpenRouter model functionality and alias mapping
- `token_allocation_validation` - Token allocation and conversation history validation
- `testgen_validation` - TestGen tool validation with specific test function
- `refactor_validation` - Refactor tool validation with codesmells
- `conversation_chain_validation` - Conversation chain and threading validation
- `vision_capability` - Image/vision support validation
- `xai_models` - X.AI GROK model functionality

**Note**: All simulator tests should be run individually for optimal testing and better error isolation.

### Development Workflow

#### Before Making Changes
1. Ensure virtual environment is activated: `source venv/bin/activate`
2. Run quality checks: `./code_quality_checks.sh`
3. Check server is running: `./run-server.sh`
4. Review relevant documentation in `docs/`

#### After Making Changes
1. Run quality checks again: `./code_quality_checks.sh`
2. Run relevant simulator tests: `python communication_simulator_test.py --individual <test_name>`
3. Check logs for any issues: `docker exec zen-mcp-server tail -n 100 /tmp/mcp_server.log`
4. Test manually with Claude Code: `claude` command in project directory

#### Before Committing/PR
1. **REQUIRED**: Run final quality check: `./code_quality_checks.sh`
2. **REQUIRED**: All 491 unit tests must pass 100%
3. **REQUIRED**: Run relevant simulator tests: `python communication_simulator_test.py`
4. **REQUIRED**: All linting must pass (ruff, black, isort)
5. Update documentation if adding features or changing behavior
6. Follow PR title format: `feat:`, `fix:`, or `breaking:` for version bumps

### Common Troubleshooting

#### Container Issues
```bash
# Restart containers if they're not responding
docker stop zen-mcp-server zen-mcp-redis
./run-server.sh

# Check container resource usage
docker stats zen-mcp-server

# Remove containers and rebuild from scratch
docker rm -f zen-mcp-server zen-mcp-redis
./run-server.sh

# Check Docker Compose status
docker compose ps
```

#### Test Failures
```bash
# Run individual failing test with verbose output
python communication_simulator_test.py --individual <test_name> --verbose

# Check server logs during test execution
docker exec zen-mcp-server tail -f /tmp/mcp_server.log

# Run tests while keeping containers running for debugging
python communication_simulator_test.py --keep-logs

# For unit test failures, run specific test with verbose output
python -m pytest tests/test_<name>.py::test_<function> -xvs
```

#### Linting Issues
```bash
# Auto-fix most linting issues
ruff check . --fix
black .
isort .

# Check what would be changed without applying
ruff check .
black --check .
isort --check-only .

# View specific linting errors
ruff check . --output-format=full
```

#### API Key Issues
```bash
# Verify .env file exists and has correct format
cat .env

# Restart server after updating .env
./run-server.sh

# Test API connectivity with listmodels tool
# (requires Claude Code session)
```

#### Redis Issues
```bash
# Check Redis is running
docker exec zen-mcp-redis redis-cli ping

# View conversation keys in Redis
docker exec zen-mcp-redis redis-cli KEYS "conversation:*"

# Clear all conversation data (for testing)
docker exec zen-mcp-redis redis-cli FLUSHDB

# Check Redis memory usage
docker exec zen-mcp-redis redis-cli INFO memory
```

### File Structure Context

**Core Server Files**:
- `server.py` - Main MCP server implementation (47K LOC)
- `config.py` - Configuration and constants
- `run-server.sh` - Docker container setup and management script

**Test Suites**:
- `tests/` - Unit test suite (491 tests, ~14,600 LOC)
- `simulator_tests/` - Integration test modules (21 tests)
- `communication_simulator_test.py` - Test runner for simulator tests
- `code_quality_checks.sh` - Comprehensive quality check automation

**Tool Implementations**:
- `tools/analyze.py` - Smart file analysis
- `tools/chat.py` - Collaborative thinking
- `tools/codereview.py` - Professional code review
- `tools/debug.py` - Expert debugging assistant
- `tools/listmodels.py` - List available models
- `tools/precommit.py` - Pre-commit validation
- `tools/refactor.py` - Intelligent code refactoring
- `tools/testgen.py` - Comprehensive test generation
- `tools/thinkdeep.py` - Extended reasoning partner
- `tools/tracer.py` - Static code analysis prompt generator
- `tools/base.py` - Base tool class and utilities
- `tools/models.py` - Tool data models

**Provider Implementations**:
- `providers/gemini.py` - Google Gemini provider
- `providers/openai.py` - OpenAI provider
- `providers/xai.py` - X.AI GROK provider
- `providers/openrouter.py` - OpenRouter provider
- `providers/custom.py` - Custom API provider (Ollama, vLLM, etc.)
- `providers/base.py` - Base provider interface
- `providers/registry.py` - Provider registry and management

**System Prompts**:
- `systemprompts/analyze_prompt.py` - Analyze tool system prompt
- `systemprompts/chat_prompt.py` - Chat tool system prompt
- `systemprompts/codereview_prompt.py` - Code review system prompt
- `systemprompts/debug_prompt.py` - Debug tool system prompt
- `systemprompts/precommit_prompt.py` - Precommit system prompt
- `systemprompts/refactor_prompt.py` - Refactor system prompt (19K LOC)
- `systemprompts/testgen_prompt.py` - Test generation system prompt
- `systemprompts/thinkdeep_prompt.py` - Think deep system prompt

**Documentation**:
- `README.md` - Main project documentation (44K LOC)
- `docs/advanced-usage.md` - Model configuration, thinking modes, workflows
- `docs/adding_tools.md` - Step-by-step tool development guide
- `docs/adding_providers.md` - Provider integration guide
- `docs/context-revival.md` - Technical deep-dive on conversation persistence
- `docs/custom_models.md` - Local model setup (Ollama, vLLM, LM Studio)
- `docs/testing.md` - Test suite documentation
- `docs/troubleshooting.md` - Common issues and debugging
- `docs/contributions.md` - PR process and code standards
- `docs/logging.md` - Log monitoring and debugging

**Configuration Files**:
- `.env.example` - Example environment configuration
- `docker-compose.yml` - Docker services configuration
- `Dockerfile` - Docker image definition
- `pyproject.toml` - Python project configuration (linting, formatting)
- `requirements.txt` - Python dependencies
- `conf/custom_models.json` - Custom model aliases and configurations

**Monitoring & Debugging**:
- `log_monitor.py` - Real-time log viewer script

### Environment Requirements

- Python 3.9+ with virtual environment activated
- Docker and Docker Compose installed
- All dependencies from `requirements.txt` installed
- At least one API key configured (GEMINI_API_KEY, OPENAI_API_KEY, XAI_API_KEY, OPENROUTER_API_KEY, or CUSTOM_API_URL)
- Redis (automatically managed by Docker Compose)

### Version Information

- **Current Version**: 4.8.3
- **Last Updated**: 2025-06-16
- **Author**: Fahad Gilani
- **License**: Apache 2.0

### Key Technical Achievements

1. **Conversation Threading** - Stateful AI-to-AI conversations in stateless MCP environment
2. **Cross-Tool Continuation** - Context persists when switching between tools
3. **Auto Mode** - Intelligent model selection based on task requirements
4. **Large Context Handling** - Bypass MCP's 25K token limit via incremental updates
5. **Context Revival** - Resume conversations even after Claude's memory resets
6. **Multi-Provider Support** - Unified interface for 6 different AI provider types
7. **Vision Integration** - Image analysis across all tools
8. **Prompt Shortcuts** - Structured prompt format (`/zen:chat:o3 hello`)

### Contributing

For detailed contribution guidelines, see `docs/contributions.md`. Quick summary:

1. Fork and clone the repository
2. Create feature branch: `git checkout -b feat/your-feature-name`
3. Make changes and ensure quality checks pass: `./code_quality_checks.sh`
4. Add tests for new features (unit tests + simulator tests if applicable)
5. Follow PR title format: `feat:`, `fix:`, or `breaking:`
6. Submit PR with clear description

**Zero-tolerance policy**: All tests must pass 100%, all linting must pass cleanly.

---

This guide provides everything needed to efficiently work with the Zen MCP Server codebase using Claude. Always run quality checks before and after making changes to ensure code integrity. For detailed technical information, refer to the documentation in the `docs/` directory.
