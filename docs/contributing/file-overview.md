# Repository File Overview

## Purpose

This document provides a comprehensive guide to the repository structure, explaining the purpose and role of each directory and key file within the Gemini MCP Server project.

## Repository Structure

```
zen-mcp-server/
├── CLAUDE.md                    # Collaboration framework and development guidelines
├── README.md                    # Project overview and quick start guide
├── LICENSE                      # Project license (MIT)
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Poetry configuration and project metadata
├── pytest.ini                  # Test configuration
├── Dockerfile                   # Container image definition
├── docker-compose.yml          # Multi-service Docker orchestration
├── setup.py                     # Python package setup (legacy)
├── config.py                    # Centralized configuration management
├── server.py                    # Main MCP server entry point
├── gemini_server.py            # Gemini-specific server implementation
├── log_monitor.py              # Logging and monitoring utilities
├── setup-docker.sh            # Docker setup automation script
├── claude_config_example.json # Example Claude Desktop configuration
├── examples/                   # Configuration examples for different platforms
├── docs/                      # Complete project documentation
├── tools/                     # MCP tool implementations
├── utils/                     # Shared utility modules
├── prompts/                   # System prompts for different tool types
├── tests/                     # Comprehensive test suite
└── memory-bank/               # Memory Bank files for context preservation
```

## Core Configuration Files

### CLAUDE.md
**Purpose**: Defines the collaboration framework between Claude, Gemini, and human developers
**Key Components**:
- Tool selection matrix for appropriate AI collaboration
- Memory Bank integration protocols
- Mandatory collaboration patterns and workflows
- Quality gates and documentation standards

**When to Update**: When changing collaboration patterns, adding new tools, or modifying development workflows

### config.py
**Purpose**: Centralized configuration management for the MCP server
**Key Components**:
- Environment variable handling (`GEMINI_API_KEY`, `REDIS_URL`)
- Model configuration (`GEMINI_MODEL`, `MAX_CONTEXT_TOKENS`)
- Security settings (`PROJECT_ROOT`, path validation)
- Redis connection settings for conversation memory

**Dependencies**: Environment variables, Docker configuration
**Extension Points**: Add new configuration parameters for tools or features

### server.py
**Purpose**: Main MCP server implementation providing the protocol interface
**Key Components**:
- MCP protocol compliance (`@server.list_tools()`, `@server.call_tool()`)
- Tool registration and discovery system
- Request routing and response formatting
- Error handling and graceful degradation

**Dependencies**: `tools/` modules, `utils/` modules, MCP library
**Data Flow**: Claude → MCP Protocol → Tool Selection → Gemini API → Response

## Tool Architecture

### tools/ Directory
**Purpose**: Contains individual MCP tool implementations following plugin architecture

#### tools/base.py
**Purpose**: Abstract base class defining the tool interface contract
**Key Components**:
- `BaseTool` abstract class with `execute()` and `get_schema()` methods
- Standardized error handling patterns
- Response formatting utilities (`ToolOutput` dataclass)

**Extension Points**: Inherit from `BaseTool` to create new tools

#### Individual Tool Files

**tools/chat.py**
- **Purpose**: Quick questions, brainstorming, general collaboration
- **Thinking Mode**: Default 'medium' (8192 tokens)
- **Use Cases**: Immediate answers, idea exploration, simple code discussions

**tools/thinkdeep.py**
- **Purpose**: Complex architecture, system design, strategic planning
- **Thinking Mode**: Default 'high' (16384 tokens) 
- **Use Cases**: Major features, refactoring strategies, design decisions

**tools/analyze.py**
- **Purpose**: Code exploration, understanding existing systems
- **Thinking Mode**: Variable based on analysis scope
- **Use Cases**: Dependency analysis, pattern detection, codebase comprehension

**tools/codereview.py**
- **Purpose**: Code quality, security, bug detection
- **Thinking Mode**: Default 'medium' (8192 tokens)
- **Use Cases**: PR reviews, pre-commit validation, security audits

**tools/debug.py**
- **Purpose**: Root cause analysis, error investigation
- **Thinking Mode**: Default 'medium' (8192 tokens)
- **Use Cases**: Stack trace analysis, performance issues, bug diagnosis

**tools/precommit.py**
- **Purpose**: Automated quality gates before commits
- **Thinking Mode**: Default 'medium' (8192 tokens)
- **Use Cases**: Git repository validation, change analysis, quality assurance

#### tools/models.py
**Purpose**: Shared data models and Gemini API integration
**Key Components**:
- `ToolOutput` dataclass for standardized responses
- `GeminiClient` for API communication
- Thinking mode token allocations (`THINKING_MODE_TOKENS`)
- Pydantic models for request/response validation

**Dependencies**: `google-generativeai`, `pydantic`

## Utility Modules

### utils/ Directory
**Purpose**: Shared utilities used across multiple tools and components

#### utils/file_utils.py
**Purpose**: Secure file operations and content processing
**Key Components**:
- `validate_file_path()`: Multi-layer security validation
- `read_file_with_token_limit()`: Token-aware file reading
- `translate_docker_path()`: Host-to-container path mapping
- Priority-based file processing (source code > docs > logs)

**Security Features**:
- Directory traversal prevention
- Sandbox boundary enforcement (PROJECT_ROOT)
- Dangerous path pattern detection

**Data Flow**: File Request → Security Validation → Path Translation → Content Processing → Formatted Output

#### utils/git_utils.py
**Purpose**: Git repository operations for code analysis
**Key Components**:
- Repository state detection (staged, unstaged, committed changes)
- Branch comparison and diff analysis
- Commit history processing
- Change validation for precommit tool

**Dependencies**: `git` command-line tool
**Integration**: Primary used by `precommit` tool for change analysis

#### utils/conversation_memory.py
**Purpose**: Cross-session context preservation and threading
**Key Components**:
- `ThreadContext` dataclass for conversation state
- `ConversationMemory` class for Redis-based persistence
- Thread reconstruction and continuation support
- Automatic cleanup of expired conversations

**Data Flow**: Tool Execution → Context Storage → Redis Persistence → Context Retrieval → Thread Reconstruction

**Dependencies**: Redis server, `redis-py` library

#### utils/token_utils.py
**Purpose**: Token management and context optimization
**Key Components**:
- Token counting and estimation
- Context budget allocation
- Content truncation with structure preservation
- Priority-based token distribution

**Integration**: Used by all tools for managing Gemini API token limits

## System Prompts

### prompts/ Directory
**Purpose**: Standardized system prompts for different tool types

#### prompts/tool_prompts.py
**Purpose**: Template prompts for consistent tool behavior
**Key Components**:
- Base prompt templates for each tool type
- Context formatting patterns
- Error message templates
- Response structure guidelines

**Extension Points**: Add new prompt templates for new tools or specialized use cases

## Testing Infrastructure

### tests/ Directory
**Purpose**: Comprehensive test suite ensuring code quality and reliability

#### Test Organization
```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                # Shared test fixtures and configuration
├── test_server.py             # MCP server integration tests
├── test_tools.py              # Individual tool functionality tests
├── test_utils.py              # Utility module tests
├── test_config.py             # Configuration validation tests
└── specialized test files...   # Feature-specific test suites
```

#### Key Test Files

**conftest.py**
- **Purpose**: Shared pytest fixtures and test configuration
- **Components**: Mock clients, temporary directories, sample data

**test_server.py**
- **Purpose**: MCP protocol and server integration testing
- **Coverage**: Tool registration, request routing, error handling

**test_tools.py**
- **Purpose**: Individual tool functionality validation
- **Coverage**: Tool execution, parameter validation, response formatting

**test_utils.py**
- **Purpose**: Utility module testing
- **Coverage**: File operations, security validation, token management

## Memory Bank System

### memory-bank/ Directory
**Purpose**: Local file-based context preservation system

#### Memory Bank Files

**productContext.md**
- **Purpose**: High-level project overview and goals
- **Content**: Project description, key features, overall architecture
- **Update Triggers**: Fundamental project changes, feature additions

**activeContext.md**
- **Purpose**: Current development status and recent changes
- **Content**: Current focus, recent changes, open questions/issues
- **Update Triggers**: Session changes, progress updates

**progress.md**
- **Purpose**: Task tracking using structured format
- **Content**: Completed tasks, current tasks, next steps
- **Update Triggers**: Task completion, milestone achievements

**decisionLog.md**
- **Purpose**: Architectural decisions with rationale
- **Content**: Technical decisions, rationale, implementation details
- **Update Triggers**: Significant architectural choices, design decisions

**systemPatterns.md**
- **Purpose**: Recurring patterns and standards documentation
- **Content**: Coding patterns, architectural patterns, testing patterns
- **Update Triggers**: Pattern introduction, standard modifications

**Data Flow**: Development Activity → Memory Bank Updates → Context Preservation → Cross-Session Continuity

## Documentation Structure

### docs/ Directory
**Purpose**: Complete project documentation following CLAUDE.md standards

#### Documentation Categories

**docs/architecture/**
- `overview.md`: High-level system architecture and component relationships
- `components.md`: Detailed component descriptions and interactions
- `data-flow.md`: Data flow patterns and processing pipelines
- `decisions/`: Architecture Decision Records (ADRs)

**docs/api/**
- `mcp-protocol.md`: MCP protocol implementation details
- `tools/`: Individual tool API documentation

**docs/contributing/**
- `setup.md`: Development environment setup
- `workflows.md`: Development workflows and processes
- `code-style.md`: Coding standards and style guide
- `testing.md`: Testing strategies and requirements
- `file-overview.md`: This file - repository structure guide

**docs/user-guides/**
- `installation.md`: Installation and setup instructions
- `configuration.md`: Configuration options and examples
- `troubleshooting.md`: Common issues and solutions

## Configuration Examples

### examples/ Directory
**Purpose**: Platform-specific configuration examples for different deployment scenarios

**claude_config_macos.json**
- macOS-specific Claude Desktop configuration
- Local development setup patterns
- File path configurations for macOS

**claude_config_wsl.json**
- Windows Subsystem for Linux configuration
- Path translation patterns for WSL environment
- Docker integration considerations

**claude_config_docker_home.json**
- Docker-based deployment configuration
- Container path mapping examples
- Volume mount configurations

## Container Configuration

### Dockerfile
**Purpose**: Container image definition for consistent deployment
**Key Components**:
- Python 3.9 base image
- Dependency installation (requirements.txt)
- Application code copying
- Entry point configuration (`server.py`)

**Build Process**: Source Code → Dependency Installation → Application Setup → Runnable Container

### docker-compose.yml
**Purpose**: Multi-service orchestration for complete system deployment
**Services**:
- `gemini-server`: Main MCP server application
- `redis`: Conversation memory persistence
- Volume mounts for configuration and data persistence

**Data Flow**: Docker Compose → Service Orchestration → Network Configuration → Volume Mounting → System Startup

## Extension Guidelines

### Adding New Tools

1. **Create Tool Class**: Inherit from `BaseTool` in `tools/new_tool.py`
2. **Implement Interface**: Define `execute()` and `get_schema()` methods
3. **Add Registration**: Update `server.py` tool discovery
4. **Create Tests**: Add comprehensive tests in `tests/`
5. **Update Documentation**: Add API documentation in `docs/api/tools/`

### Adding New Utilities

1. **Create Module**: Add new utility in `utils/new_utility.py`
2. **Define Interface**: Clear function signatures with type hints
3. **Add Security**: Validate inputs and handle errors gracefully
4. **Write Tests**: Comprehensive unit tests with mocking
5. **Update Dependencies**: Document component interactions

### Modifying Configuration

1. **Update config.py**: Add new configuration parameters
2. **Environment Variables**: Define environment variable mappings
3. **Validation**: Add configuration validation logic
4. **Documentation**: Update configuration guide
5. **Examples**: Provide example configurations

## Dependencies & Integration Points

### External Dependencies
- **MCP Library**: Protocol implementation and compliance
- **Google Generative AI**: Gemini API integration
- **Redis**: Conversation memory persistence
- **Docker**: Containerization and deployment
- **pytest**: Testing framework

### Internal Integration Points
- **Tool Registration**: `server.py` ↔ `tools/` modules
- **Configuration**: `config.py` → All modules
- **File Operations**: `utils/file_utils.py` → All file-accessing tools
- **Memory Management**: `utils/conversation_memory.py` → All tools supporting continuation
- **Security**: `utils/file_utils.py` validation → All file operations

### Data Flow Integration
1. **Request Flow**: Claude → `server.py` → Tool Selection → `tools/` → `utils/` → Gemini API
2. **Response Flow**: Gemini API → `tools/` → `utils/` → `server.py` → Claude
3. **Memory Flow**: Tool Execution → `utils/conversation_memory.py` → Redis → Context Retrieval
4. **Security Flow**: File Request → `utils/file_utils.py` → Validation → Safe Processing

---

This file overview provides the foundation for understanding the repository structure and serves as a guide for contributors to navigate the codebase effectively and make informed architectural decisions.

