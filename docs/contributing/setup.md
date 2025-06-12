# Development Environment Setup

This guide helps you set up a development environment for contributing to the Gemini MCP Server.

## Prerequisites

### Required Software
- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
- **Git** - [Download](https://git-scm.com/downloads)
- **Claude Desktop** - [Download](https://claude.ai/download) (for testing)

### Recommended Tools
- **VS Code** with Python extension
- **PyCharm** or your preferred Python IDE
- **pytest** for running tests
- **black** and **ruff** for code formatting

## Quick Setup

### 1. Clone Repository

```bash
git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
cd zen-mcp-server
```

### 2. Choose Development Method

#### Option A: Docker Development (Recommended)

Best for consistency and avoiding local Python environment issues:

```bash
# One-command setup
./setup-docker.sh

# Development with auto-reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

#### Option B: Local Python Development

For direct Python development and debugging:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 3. Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit with your API key
nano .env
# Add: GEMINI_API_KEY=your-gemini-api-key-here
```

### 4. Verify Setup

```bash
# Run unit tests
python -m pytest tests/ --ignore=tests/test_live_integration.py -v

# Test with live API (requires API key)
python tests/test_live_integration.py

# Run linting
black --check .
ruff check .
```

## Development Workflows

### Code Quality Tools

```bash
# Format code
black .

# Lint code
ruff check .
ruff check . --fix  # Auto-fix issues

# Type checking
mypy .

# Run all quality checks
./scripts/quality-check.sh  # If available
```

### Testing Strategy

#### Unit Tests (No API Key Required)
```bash
# Run all unit tests
python -m pytest tests/ --ignore=tests/test_live_integration.py -v

# Run with coverage
python -m pytest tests/ --ignore=tests/test_live_integration.py --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/test_tools.py -v
```

#### Live Integration Tests (API Key Required)
```bash
# Set API key
export GEMINI_API_KEY=your-api-key-here

# Run live tests
python tests/test_live_integration.py

# Or specific live test
python -m pytest tests/test_live_integration.py::test_chat_tool -v
```

### Adding New Tools

1. **Create tool file**: `tools/your_tool.py`
2. **Inherit from BaseTool**: Implement required methods
3. **Add system prompt**: Include in `prompts/tool_prompts.py`
4. **Register tool**: Add to `TOOLS` dict in `server.py`
5. **Write tests**: Add unit tests with mocks
6. **Test live**: Verify with actual API calls

#### Tool Template

```python
# tools/your_tool.py
from typing import Any, Optional
from mcp.types import TextContent
from pydantic import Field
from .base import BaseTool, ToolRequest
from prompts import YOUR_TOOL_PROMPT

class YourToolRequest(ToolRequest):
    """Request model for your tool"""
    param1: str = Field(..., description="Required parameter")
    param2: Optional[str] = Field(None, description="Optional parameter")

class YourTool(BaseTool):
    """Your tool description"""
    
    def get_name(self) -> str:
        return "your_tool"
    
    def get_description(self) -> str:
        return "Your tool description for Claude"
    
    def get_system_prompt(self) -> str:
        return YOUR_TOOL_PROMPT
    
    def get_request_model(self):
        return YourToolRequest
    
    async def prepare_prompt(self, request: YourToolRequest) -> str:
        # Build your prompt here
        return f"Your prompt with {request.param1}"
```

### Docker Development

#### Development Compose File

Create `docker-compose.dev.yml`:

```yaml
services:
  gemini-mcp:
    build:
      context: .
      dockerfile: Dockerfile.dev  # If you have a dev Dockerfile
    volumes:
      - .:/app  # Mount source code for hot reload
    environment:
      - LOG_LEVEL=DEBUG
    command: ["python", "-m", "server", "--reload"]  # If you add reload support
```

#### Development Commands

```bash
# Start development environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run tests in container
docker compose exec gemini-mcp python -m pytest tests/ -v

# Access container shell
docker compose exec gemini-mcp bash

# View logs
docker compose logs -f gemini-mcp
```

## IDE Configuration

### VS Code

**Recommended extensions:**
- Python
- Pylance
- Black Formatter
- Ruff
- Docker

**Settings** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests/",
    "--ignore=tests/test_live_integration.py"
  ]
}
```

### PyCharm

1. **Configure interpreter**: Settings → Project → Python Interpreter
2. **Set up test runner**: Settings → Tools → Python Integrated Tools → Testing
3. **Configure code style**: Settings → Editor → Code Style → Python (use Black)

## Debugging

### Local Debugging

```python
# Add to your code for debugging
import pdb; pdb.set_trace()

# Or use your IDE's debugger
```

### Container Debugging

```bash
# Run container in debug mode
docker compose exec gemini-mcp python -m pdb server.py

# Or add debug prints
LOG_LEVEL=DEBUG docker compose up
```

### Testing with Claude Desktop

1. **Configure Claude Desktop** to use your development server
2. **Use development container**:
   ```json
   {
     "mcpServers": {
       "gemini-dev": {
         "command": "docker",
         "args": [
           "exec", "-i", "zen-mcp-server", 
           "python", "server.py"
         ]
       }
     }
   }
   ```

## Contributing Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the coding standards and add tests for your changes.

### 3. Run Quality Checks

```bash
# Format code
black .

# Check linting
ruff check .

# Run tests
python -m pytest tests/ --ignore=tests/test_live_integration.py -v

# Test with live API
export GEMINI_API_KEY=your-key
python tests/test_live_integration.py
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
# Create PR on GitHub
```

## Performance Considerations

### Profiling

```python
# Add profiling to your code
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    # Your code here
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats()
```

### Memory Usage

```bash
# Monitor memory usage
docker stats zen-mcp-server

# Profile memory in Python
pip install memory-profiler
python -m memory_profiler your_script.py
```

## Troubleshooting Development Issues

### Common Issues

1. **Import errors**: Check your Python path and virtual environment
2. **API rate limits**: Use mocks in tests to avoid hitting limits
3. **Docker issues**: Check Docker Desktop is running and has enough resources
4. **Test failures**: Ensure you're using the correct Python version and dependencies

### Clean Environment

```bash
# Reset Python environment
rm -rf venv/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Reset Docker environment
docker compose down -v
docker system prune -f
./setup-docker.sh
```

---

**Next Steps:**
- Read [Development Workflows](workflows.md)
- Review [Code Style Guide](code-style.md)
- Understand [Testing Strategy](testing.md)

