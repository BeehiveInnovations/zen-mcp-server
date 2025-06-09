# Contributing to Gemini MCP Server

Thank you for your interest in contributing! This guide explains how to set up the development environment and contribute to the project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/BeehiveInnovations/gemini-mcp-server.git
   cd gemini-mcp-server
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Testing Strategy

### Two Types of Tests

#### 1. Unit Tests (Mandatory - No API Key Required)
- **Location**: `tests/test_*.py` (except `test_live_integration.py`)
- **Purpose**: Test logic, mocking, and functionality without API calls
- **Run with**: `python -m pytest tests/ --ignore=tests/test_live_integration.py -v`
- **GitHub Actions**: ✅ Always runs
- **Coverage**: Measures code coverage

#### 2. Live Integration Tests (Optional - API Key Required)
- **Location**: `tests/test_live_integration.py` 
- **Purpose**: Verify actual API integration works
- **Run with**: `python tests/test_live_integration.py` (requires `GEMINI_API_KEY`)
- **GitHub Actions**: 🔒 Only runs if `GEMINI_API_KEY` secret is set

### Running Tests

```bash
# Run all unit tests (CI-friendly, no API key needed)
python -m pytest tests/ --ignore=tests/test_live_integration.py -v

# Run with coverage
python -m pytest tests/ --ignore=tests/test_live_integration.py --cov=. --cov-report=html

# Run live integration tests (requires API key)
export GEMINI_API_KEY=your-api-key-here
python tests/test_live_integration.py
```

## Code Quality

### Formatting and Linting
```bash
# Install development tools
pip install black ruff

# Format code
black .

# Lint code
ruff check .
```

### Pre-commit Checks
Before submitting a PR, ensure:
- [ ] All unit tests pass: `python -m pytest tests/ --ignore=tests/test_live_integration.py -v`
- [ ] Code is formatted: `black --check .`
- [ ] Code passes linting: `ruff check .`
- [ ] Live tests work (if you have API access): `python tests/test_live_integration.py`

## Adding New Features

### Adding a New Tool

1. **Create tool file**: `tools/your_tool.py`
2. **Inherit from BaseTool**: Implement all required methods
3. **Add system prompt**: Include prompt in `prompts/tool_prompts.py`
4. **Register tool**: Add to `TOOLS` dict in `server.py`
5. **Write tests**: Add unit tests that use mocks
6. **Test live**: Verify with live API calls

### Testing New Tools

```python
# Unit test example (tools/test_your_tool.py)
@pytest.mark.asyncio
@patch("tools.base.BaseTool.create_model")
async def test_your_tool(self, mock_create_model):
    mock_model = Mock()
    mock_model.generate_content.return_value = Mock(
        candidates=[Mock(content=Mock(parts=[Mock(text="Expected response")]))]
    )
    mock_create_model.return_value = mock_model
    
    tool = YourTool()
    result = await tool.execute({"param": "value"})
    
    assert len(result) == 1
    assert "Expected response" in result[0].text
```

## CI/CD Pipeline

The GitHub Actions workflow:

1. **Unit Tests**: Run on all Python versions (3.10, 3.11, 3.12)
2. **Linting**: Check code formatting and style
3. **Live Tests**: Only run if `GEMINI_API_KEY` secret is available

### Key Features:
- **✅ No API key required for PRs** - All contributors can run tests
- **🔒 Live verification available** - Maintainers can verify API integration
- **📊 Coverage reporting** - Track test coverage
- **🐍 Multi-Python support** - Ensure compatibility

## Contribution Guidelines

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make your changes**
4. **Add/update tests**
5. **Run tests locally**: Ensure unit tests pass
6. **Submit PR**: Include description of changes

### Code Standards

- **Follow existing patterns**: Look at existing tools for examples
- **Add comprehensive tests**: Both unit tests (required) and live tests (recommended)
- **Update documentation**: Update README if adding new features
- **Use type hints**: All new code should include proper type annotations
- **Keep it simple**: Follow SOLID principles and keep functions focused

### Security Considerations

- **Never commit API keys**: Use environment variables
- **Validate inputs**: Always validate user inputs in tools
- **Handle errors gracefully**: Provide meaningful error messages
- **Follow security best practices**: Sanitize file paths, validate file access

## Getting Help

- **Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check the README for usage examples

## License

By contributing, you agree that your contributions will be licensed under the MIT License.