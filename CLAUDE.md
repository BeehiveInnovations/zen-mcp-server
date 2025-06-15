# Claude Development Guide for Zen MCP Server

This file contains essential commands and workflows for developing and maintaining the Zen MCP Server when working with Claude. Use these instructions to efficiently run quality checks, manage the server, check logs, and run tests.

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
- Complete unit test suite (361 tests)
- Verification that all checks pass 100%

### Server Management

#### Start/Restart the Server
```bash
# Start or restart the Docker containers
./run-server.sh
```

This script will:
- Build/rebuild Docker images if needed
- Start the MCP server container (`zen-mcp-server`)
- Start the Redis container (`zen-mcp-redis`)
- Set up proper networking and volumes

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

#### Debug Container Issues
```bash
# Check container logs (Docker level)
docker logs zen-mcp-server

# Execute interactive shell in container
docker exec -it zen-mcp-server /bin/bash

# Check Redis container logs
docker logs zen-mcp-redis
```

### Testing

#### Run All Simulator Tests
```bash
# Run the complete test suite
python communication_simulator_test.py

# Run tests with verbose output
python communication_simulator_test.py --verbose

# Force rebuild environment before testing
python communication_simulator_test.py --rebuild
```

#### Run Individual Simulator Tests (Recommended)
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

Available simulator tests include:
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

**Note**: All simulator tests should be run individually for optimal testing and better error isolation.

#### Run Unit Tests Only
```bash
# Run all unit tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_refactor.py -v

# Run specific test function
python -m pytest tests/test_refactor.py::TestRefactorTool::test_format_response -v

# Run tests with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Development Workflow

#### Before Making Changes
1. Ensure virtual environment is activated: `source venv/bin/activate`
2. Run quality checks: `./code_quality_checks.sh`
3. Check server is running: `./run-server.sh`

#### After Making Changes
1. Run quality checks again: `./code_quality_checks.sh`
2. Run relevant simulator tests: `python communication_simulator_test.py --individual <test_name>`
3. Check logs for any issues: `docker exec zen-mcp-server tail -n 100 /tmp/mcp_server.log`

#### Before Committing/PR
1. Final quality check: `./code_quality_checks.sh`
2. Run full simulator test suite: `python communication_simulator_test.py`
3. Verify all tests pass 100%

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
```

#### Test Failures
```bash
# Run individual failing test with verbose output
python communication_simulator_test.py --individual <test_name> --verbose

# Check server logs during test execution
docker exec zen-mcp-server tail -f /tmp/mcp_server.log

# Run tests while keeping containers running for debugging
python communication_simulator_test.py --keep-logs
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
```

### File Structure Context

- `./code_quality_checks.sh` - Comprehensive quality check script
- `./run-server.sh` - Docker container setup and management
- `communication_simulator_test.py` - End-to-end testing framework
- `simulator_tests/` - Individual test modules
- `tests/` - Unit test suite
- `tools/` - MCP tool implementations
- `providers/` - AI provider implementations
- `systemprompts/` - System prompt definitions

### Environment Requirements

- Python 3.8+ with virtual environment activated
- Docker and Docker Compose installed
- All dependencies from `requirements.txt` installed
- Proper API keys configured in environment or config files

This guide provides everything needed to efficiently work with the Zen MCP Server codebase using Claude. Always run quality checks before and after making changes to ensure code integrity.