# Gemini MCP Server for Claude Code

<div align="center">
  <img src="https://github.com/user-attachments/assets/0990ee89-9160-45d6-a407-ee925bcb43cb" width="600">
</div>

The ultimate development partner for Claude - a Model Context Protocol server that gives Claude access to Google's Gemini 2.5 Pro for extended thinking, code analysis, and problem-solving. **Automatically reads files and directories, passing their contents to Gemini for analysis within its 1M token context.**

## Why This Server?

Claude is brilliant, but sometimes you need:
- **A second opinion** on complex architectural decisions - augment Claude's extended thinking with Gemini's perspective ([`think_deeper`](#1-think_deeper---extended-reasoning-partner))
- **Massive context window** (1M tokens) - Gemini 2.5 Pro can analyze entire codebases, read hundreds of files at once, and provide comprehensive insights ([`analyze`](#4-analyze---smart-file-analysis))
- **Deep code analysis** across massive codebases that exceed Claude's context limits ([`analyze`](#4-analyze---smart-file-analysis))
- **Expert debugging** for tricky issues with full system context ([`debug_issue`](#3-debug_issue---expert-debugging-assistant))
- **Professional code reviews** with actionable feedback across entire repositories ([`review_code`](#2-review_code---professional-code-review))
- **A senior developer partner** to validate and extend ideas ([`chat`](#5-chat---general-development-chat--collaborative-thinking))

This server makes Gemini your development sidekick, handling what Claude can't or extending what Claude starts.

## File & Directory Support

All tools accept both individual files and entire directories. The server:
- **Automatically expands directories** to find all code files recursively
- **Intelligently filters** hidden files, caches, and non-code files
- **Handles mixed inputs** like `"analyze main.py, src/, and tests/"`
- **Manages token limits** by loading as many files as possible within Gemini's context

## Quickstart (5 minutes)

### 1. Get a Gemini API Key
Visit [Google AI Studio](https://makersuite.google.com/app/apikey) and generate an API key. For best results with Gemini 2.5 Pro, use a paid API key as the free tier has limited access to the latest models.

### 2. Clone the Repository
Clone this repository to a location on your computer:

```bash
# Example: Clone to your home directory
cd ~
git clone https://github.com/BeehiveInnovations/gemini-mcp-server.git

# The server is now at: ~/gemini-mcp-server
```

**Note the full path** - you'll need it in the next step:
- **macOS/Linux**: `/Users/YOUR_USERNAME/gemini-mcp-server`
- **Windows**: `C:\Users\YOUR_USERNAME\gemini-mcp-server`

### 3. Configure Claude Desktop
Add the server to your `claude_desktop_config.json`:

**Find your config file:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Add this configuration** (replace with YOUR actual paths):

**macOS/Linux:**
```json
{
  "mcpServers": {
    "gemini": {
      "command": "/Users/YOUR_USERNAME/gemini-mcp-server/run_gemini.sh",
      "env": {
        "GEMINI_API_KEY": "your-gemini-api-key-here"
      }
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "gemini": {
      "command": "C:\\Users\\YOUR_USERNAME\\gemini-mcp-server\\run_gemini.bat",
      "env": {
        "GEMINI_API_KEY": "your-gemini-api-key-here"
      }
    }
  }
}
```

**Important**: 
- Replace `YOUR_USERNAME` with your actual username
- Use the full absolute path where you cloned the repository
- Windows users: Note the double backslashes `\\` in the path

### 4. Restart Claude Desktop
Completely quit and restart Claude Desktop for the changes to take effect.

### 5. Connect to Claude Code

To use the server in Claude Code, run:
```bash
claude mcp add-from-claude-desktop -s user
```

### 6. Start Using It!

Just ask Claude naturally:
- "Use gemini to think deeper about this architecture design" → `think_deeper`
- "Get gemini to review this code for security issues" → `review_code`
- "Get gemini to debug why this test is failing" → `debug_issue`
- "Use gemini to analyze these files to understand the data flow" → `analyze`
- "Brainstorm with gemini about scaling strategies" → `chat`
- "Share my implementation plan with gemini for feedback" → `chat`
- "Get gemini's opinion on my authentication design" → `chat`

## Available Tools

**Quick Tool Selection Guide:**
- **Need deeper thinking?** → `think_deeper` (extends Claude's analysis, finds edge cases)
- **Code needs review?** → `review_code` (bugs, security, performance issues)
- **Something's broken?** → `debug_issue` (root cause analysis, error tracing)
- **Want to understand code?** → `analyze` (architecture, patterns, dependencies)
- **Need a thinking partner?** → `chat` (brainstorm ideas, get second opinions, validate approaches)
- **Check models?** → `list_models` (see available Gemini models)
- **Server info?** → `get_version` (version and configuration details)

**Tools Overview:**
1. [`think_deeper`](#1-think_deeper---extended-reasoning-partner) - Extended reasoning and problem-solving
2. [`review_code`](#2-review_code---professional-code-review) - Professional code review with severity levels
3. [`debug_issue`](#3-debug_issue---expert-debugging-assistant) - Root cause analysis and debugging
4. [`analyze`](#4-analyze---smart-file-analysis) - General-purpose file and code analysis
5. [`chat`](#5-chat---general-development-chat--collaborative-thinking) - Collaborative thinking and development conversations
6. [`list_models`](#6-list_models---see-available-gemini-models) - List available Gemini models
7. [`get_version`](#7-get_version---server-information) - Get server version and configuration

### 1. `think_deeper` - Extended Reasoning Partner
**Get a second opinion to augment Claude's own extended thinking**

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to think deeper about my authentication design"
"Use gemini to extend my analysis of this distributed system architecture"
```

**Collaborative Workflow:**
```
"Design an authentication system for our SaaS platform. Then use gemini to review your design for security vulnerabilities. After getting gemini's feedback, incorporate the suggestions and show me the final improved design."

"Create an event-driven architecture for our order processing system. Use gemini to think deeper about event ordering and failure scenarios. Then integrate gemini's insights and present the enhanced architecture."
```

**Key Features:**
- Provides a second opinion on Claude's analysis
- Challenges assumptions and identifies edge cases Claude might miss
- Offers alternative perspectives and approaches
- Validates architectural decisions and design patterns
- Can reference specific files for context: `"Use gemini to think deeper about my API design with reference to api/routes.py"`

**Triggers:** think deeper, ultrathink, extend my analysis, validate my approach

### 2. `review_code` - Professional Code Review  
**Comprehensive code analysis with prioritized feedback**

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to review auth.py for issues"
"Use gemini to do a security review of auth/ focusing on authentication"
```

**Collaborative Workflow:**
```
"Refactor the authentication module to use dependency injection. Then use gemini to review your refactoring for any security vulnerabilities. Based on gemini's feedback, make any necessary adjustments and show me the final secure implementation."

"Optimize the slow database queries in user_service.py. Get gemini to review your optimizations for potential regressions or edge cases. Incorporate gemini's suggestions and present the final optimized queries."
```

**Key Features:**
- Issues prioritized by severity (🔴 CRITICAL → 🟢 LOW)
- Supports specialized reviews: security, performance, quick
- Can enforce coding standards: `"Use gemini to review src/ against PEP8 standards"`
- Filters by severity: `"Get gemini to review auth/ - only report critical vulnerabilities"`

**Triggers:** review code, check for issues, find bugs, security check

### 3. `debug_issue` - Expert Debugging Assistant
**Root cause analysis for complex problems**

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to debug this TypeError: 'NoneType' object has no attribute 'split'"
"Get gemini to debug why my API returns 500 errors with the full stack trace: [paste traceback]"
```

**Collaborative Workflow:**
```
"I'm getting 'ConnectionPool limit exceeded' errors under load. Debug the issue and use gemini to analyze it deeper with context from db/pool.py. Based on gemini's root cause analysis, implement a fix and get gemini to validate the solution will scale."

"Debug why tests fail randomly on CI. Once you identify potential causes, share with gemini along with test logs and CI configuration. Apply gemini's debugging strategy, then use gemini to suggest preventive measures."
```

**Key Features:**
- Accepts error context, stack traces, and logs
- Can reference relevant files for investigation
- Supports runtime info and previous attempts
- Provides root cause analysis and solutions

**Triggers:** debug, error, failing, root cause, trace, not working

### 4. `analyze` - Smart File Analysis
**General-purpose code understanding and exploration**

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to analyze main.py to understand how it works"
"Get gemini to do an architecture analysis of the src/ directory"
```

**Collaborative Workflow:**
```
"Analyze our project structure in src/ and identify architectural improvements. Share your analysis with gemini for a deeper review of design patterns and anti-patterns. Based on both analyses, create a refactoring roadmap."

"Perform a security analysis of our authentication system. Use gemini to analyze auth/, middleware/, and api/ for vulnerabilities. Combine your findings with gemini's to create a comprehensive security report."
```

**Key Features:**
- Analyzes single files or entire directories
- Supports specialized analysis types: architecture, performance, security, quality
- Uses file paths (not content) for clean terminal output
- Can identify patterns, anti-patterns, and refactoring opportunities

**Triggers:** analyze, examine, look at, understand, inspect

### 5. `chat` - General Development Chat & Collaborative Thinking
**Your thinking partner - bounce ideas, get second opinions, brainstorm collaboratively**

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to explain how async/await works in Python"
"Get gemini to compare Redis vs Memcached for session storage"
"Share my authentication design with gemini and get their opinion"
"Brainstorm with gemini about scaling strategies for our API"
```

**Collaborative Workflow:**
```
"Research the best message queue for our use case (high throughput, exactly-once delivery). Use gemini to compare RabbitMQ, Kafka, and AWS SQS. Based on gemini's analysis and your research, recommend the best option with implementation plan."

"Design a caching strategy for our API. Get gemini's input on Redis vs Memcached vs in-memory caching. Combine both perspectives to create a comprehensive caching implementation guide."
```

**Key Features:**
- Collaborative thinking partner for your analysis and planning
- Get second opinions on your designs and approaches
- Brainstorm solutions and explore alternatives together
- Validate your checklists and implementation plans
- General development questions and explanations
- Technology comparisons and best practices
- Architecture and design discussions
- Can reference files for context: `"Use gemini to explain this algorithm with context from algorithm.py"`

**Triggers:** ask, explain, compare, suggest, what about, brainstorm, discuss, share my thinking, get opinion

### 6. `list_models` - See Available Gemini Models
```
"Use gemini to list available models"
"Get gemini to show me what models I can use"
```

### 7. `get_version` - Server Information
```
"Use gemini for its version"
"Get gemini to show server configuration"
```

## Tool Parameters

All tools that work with files support **both individual files and entire directories**. The server automatically expands directories, filters for relevant code files, and manages token limits.

### File-Processing Tools

**`analyze`** - Analyze files or directories
- `files`: List of file paths or directories (required)
- `question`: What to analyze (required)
- `analysis_type`: architecture|performance|security|quality|general
- `output_format`: summary|detailed|actionable

```
"Use gemini to analyze the src/ directory for architectural patterns"
"Get gemini to analyze main.py and tests/ to understand test coverage"
```

**`review_code`** - Review code files or directories
- `files`: List of file paths or directories (required)
- `review_type`: full|security|performance|quick
- `focus_on`: Specific aspects to focus on
- `standards`: Coding standards to enforce
- `severity_filter`: critical|high|medium|all

```
"Use gemini to review the entire api/ directory for security issues"
"Get gemini to review src/ with focus on performance, only show critical issues"
```

**`debug_issue`** - Debug with file context
- `error_description`: Description of the issue (required)
- `error_context`: Stack trace or logs
- `files`: Files or directories related to the issue
- `runtime_info`: Environment details
- `previous_attempts`: What you've tried

```
"Use gemini to debug this error with context from the entire backend/ directory"
```

**`think_deeper`** - Extended analysis with file context
- `current_analysis`: Your current thinking (required)
- `problem_context`: Additional context
- `focus_areas`: Specific aspects to focus on
- `files`: Files or directories for context

```
"Use gemini to think deeper about my design with reference to the src/models/ directory"
```

## Collaborative Workflows

### Design → Review → Implement
```
"Design a real-time collaborative editor. Use gemini to think deeper about edge cases and scalability. Implement an improved version incorporating gemini's suggestions."
```

### Code → Review → Fix
```
"Implement JWT authentication. Get gemini to do a security review. Fix any issues gemini identifies and show me the secure implementation."
```

### Debug → Analyze → Solution
```
"Debug why our API crashes under load. Use gemini to analyze deeper with context from api/handlers/. Implement a fix based on gemini's root cause analysis."
```

## Pro Tips

### Natural Language Triggers
The server recognizes natural phrases. Just talk normally:
- ❌ "Use the think_deeper tool with current_analysis parameter..."
- ✅ "Use gemini to think deeper about this approach"

### Automatic Tool Selection
Claude will automatically pick the right tool based on your request:
- "review" → `review_code`
- "debug" → `debug_issue`
- "analyze" → `analyze`
- "think deeper" → `think_deeper`

### Clean Terminal Output
All file operations use paths, not content, so your terminal stays readable even with large files.

### Context Awareness
Tools can reference files for additional context:
```
"Use gemini to debug this error with context from app.py and config.py"
"Get gemini to think deeper about my design, reference the current architecture.md"
```

## Configuration

The server includes several configurable properties that control its behavior:

### Model Configuration
- **`DEFAULT_MODEL`**: `"gemini-2.5-pro-preview-06-05"` - The default Gemini model used
- **`MAX_CONTEXT_TOKENS`**: `1,000,000` - Maximum input context (1M tokens for Gemini 2.5 Pro)
- **`MAX_OUTPUT_TOKENS`**: `32,768` - Maximum output tokens per response

### Temperature Defaults
Different tools use optimized temperature settings:
- **`TEMPERATURE_ANALYTICAL`**: `0.2` - Used for code review and debugging (focused, deterministic)
- **`TEMPERATURE_BALANCED`**: `0.5` - Used for general chat (balanced creativity/accuracy)
- **`TEMPERATURE_CREATIVE`**: `0.7` - Used for deep thinking and architecture (more creative)

### Customizing Output Length
Each tool accepts an optional `max_tokens` parameter to override the default:
```
"Use gemini to analyze main.py with max_tokens 16000"
"Get gemini to think deeper about this design with max_tokens 50000"
```

Note: The maximum supported output is 32,768 tokens for Gemini 2.5 Pro.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/BeehiveInnovations/gemini-mcp-server.git
   cd gemini-mcp-server
   ```

2. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set your Gemini API key:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

## How System Prompts Work

The server uses carefully crafted system prompts to give each tool specialized expertise:

### Prompt Architecture
- **Centralized Prompts**: All system prompts are defined in `prompts/tool_prompts.py`
- **Tool Integration**: Each tool inherits from `BaseTool` and implements `get_system_prompt()`
- **Prompt Flow**: `User Request → Tool Selection → System Prompt + Context → Gemini Response`

### Specialized Expertise
Each tool has a unique system prompt that defines its role and approach:
- **`think_deeper`**: Acts as a senior development partner, challenging assumptions and finding edge cases
- **`review_code`**: Expert code reviewer with security/performance focus, uses severity levels
- **`debug_issue`**: Systematic debugger providing root cause analysis and prevention strategies
- **`analyze`**: Code analyst focusing on architecture, patterns, and actionable insights

### Customization
To modify tool behavior, you can:
1. Edit prompts in `prompts/tool_prompts.py` for global changes
2. Override `get_system_prompt()` in a tool class for tool-specific changes
3. Use the `temperature` parameter to adjust response style (0.2 for focused, 0.7 for creative)

## Contributing

We welcome contributions! The modular architecture makes it easy to add new tools:

1. Create a new tool in `tools/`
2. Inherit from `BaseTool`
3. Implement required methods (including `get_system_prompt()`)
4. Add your system prompt to `prompts/tool_prompts.py`
5. Register your tool in `TOOLS` dict in `server.py`

See existing tools for examples.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Built with [MCP](https://modelcontextprotocol.com) by Anthropic and powered by Google's Gemini API.
