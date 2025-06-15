# Testing Guide

This project includes comprehensive test coverage through unit tests and integration simulator tests.

## Running Tests

### Prerequisites
- Python virtual environment activated: `source venv/bin/activate`
- All dependencies installed: `pip install -r requirements.txt`
- Docker containers running (for simulator tests): `./run-server.sh`

### Unit Tests

Run all unit tests with pytest:
```bash
# Run all tests with verbose output
python -m pytest -xvs

# Run specific test file
python -m pytest tests/test_providers.py -xvs
```

### Simulator Tests

Simulator tests replicate real-world Claude CLI interactions with the MCP server running in Docker. Unlike unit tests that test isolated functions, simulator tests validate the complete end-to-end flow including:
- Actual MCP protocol communication
- Docker container interactions
- Multi-turn conversations across tools
- Log output validation

**Important**: Simulator tests require `LOG_LEVEL=DEBUG` in your `.env` file to validate detailed execution logs.

#### Monitoring Logs During Tests

**Important**: The MCP stdio protocol interferes with stderr output during tool execution. While server startup logs appear in `docker compose logs`, tool execution logs are only written to file-based logs inside the container. This is a known limitation of the stdio-based MCP protocol and cannot be fixed without changing the MCP implementation.

To monitor logs during test execution:

```bash
# Monitor main server logs (includes all tool execution details)
docker exec zen-mcp-server tail -f -n 500 /tmp/mcp_server.log

# Monitor MCP activity logs (tool calls and completions)  
docker exec zen-mcp-server tail -f /tmp/mcp_activity.log

# Check log file sizes (logs rotate at 20MB)
docker exec zen-mcp-server ls -lh /tmp/mcp_*.log*
```

**Log Rotation**: All log files are configured with automatic rotation at 20MB to prevent disk space issues. The server keeps:
- 10 rotated files for mcp_server.log (200MB total)
- 5 rotated files for mcp_activity.log (100MB total)

**Why logs don't appear in docker compose logs**: The MCP stdio_server captures stderr during tool execution to prevent interference with the JSON-RPC protocol communication. This means that while you'll see startup logs in `docker compose logs`, you won't see tool execution logs there.

#### Running All Simulator Tests
```bash
# Run all simulator tests
python communication_simulator_test.py

# Run with verbose output for debugging
python communication_simulator_test.py --verbose

# Keep Docker logs after tests for inspection
python communication_simulator_test.py --keep-logs
```

#### Running Individual Tests
To run a single simulator test in isolation (useful for debugging or test development):

```bash
# Run a specific test by name
python communication_simulator_test.py --individual basic_conversation

# Examples of available tests:
python communication_simulator_test.py --individual content_validation
python communication_simulator_test.py --individual cross_tool_continuation
python communication_simulator_test.py --individual redis_validation
```

#### Other Options
```bash
# List all available simulator tests with descriptions
python communication_simulator_test.py --list-tests

# Run multiple specific tests (not all)
python communication_simulator_test.py --tests basic_conversation content_validation

# Force Docker environment rebuild before running tests
python communication_simulator_test.py --rebuild
```

### Code Quality Checks

Before committing, ensure all linting passes:
```bash
# Run all linting checks
ruff check .
black --check .
isort --check-only .

# Auto-fix issues
ruff check . --fix
black .
isort .
```

## What Each Test Suite Covers

### Unit Tests
Test isolated components and functions:
- **Provider functionality**: Model initialization, API interactions, capability checks
- **Tool operations**: All MCP tools (chat, analyze, debug, etc.)
- **Conversation memory**: Threading, continuation, history management
- **File handling**: Path validation, token limits, deduplication
- **Auto mode**: Model selection logic and fallback behavior

### Simulator Tests
Validate real-world usage scenarios by simulating actual Claude prompts:
- **Basic conversations**: Multi-turn chat functionality with real prompts
- **Cross-tool continuation**: Context preservation across different tools
- **File deduplication**: Efficient handling of repeated file references
- **Model selection**: Proper routing to configured providers
- **Token allocation**: Context window management in practice
- **Redis validation**: Conversation persistence and retrieval

## Contributing: Test Requirements

When contributing to this project:

1. **New features MUST include tests**:
   - Add unit tests in `tests/` for new functions or classes
   - Test both success and error cases
   
2. **Tool changes require simulator tests**:
   - Add simulator tests in `simulator_tests/` for new or modified tools
   - Use realistic prompts that demonstrate the feature
   - Validate output through Docker logs
   
3. **Test naming conventions**:
   - Unit tests: `test_<feature>_<scenario>.py`
   - Simulator tests: `test_<tool>_<behavior>.py`

4. **Before submitting PR - Complete Validation Checklist**:
   ```bash
   # Activate virtual environment first as needed
   source venv/bin/activate
   
   # Run all linting tools (must pass 100%)
   ruff check .
   black --check .
   isort --check-only .
   
   # Auto-fix issues if needed
   ruff check . --fix
   black .
   isort .
   
   # Run complete unit test suite (must pass 100%)
   python -m pytest -xvs
   
   # Run simulator tests for tool changes
   python communication_simulator_test.py
   ```

5. **GitHub Actions Compliance**:
   - **Every single test must pass** - we have zero tolerance for failing tests in CI
   - All linting must pass cleanly (ruff, black, isort)
   - Import sorting must be correct
   - Virtual environment activation is required for consistent results
   - Tests failing in GitHub Actions will result in PR rejection

6. **Contribution Standards**:
   - Follow the [PR template](../.github/pull_request_template.md) requirements exactly
   - Check every box in the template checklist before submitting
   - Include comprehensive tests for all new functionality
   - Ensure backward compatibility unless explicitly breaking

Remember: Tests are documentation. They show how features are intended to be used and help prevent regressions. **Quality over speed** - take the time to ensure everything passes locally before pushing.