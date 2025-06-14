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

4. **Before submitting PR**:
   - Run all unit tests: `python -m pytest -xvs`
   - Run relevant simulator tests
   - Ensure all linting passes

Remember: Tests are documentation. They show how features are intended to be used and help prevent regressions.