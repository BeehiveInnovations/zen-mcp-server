# Gemini MCP Server for Claude Code

<div align="center">
  <img src="https://github.com/user-attachments/assets/0990ee89-9160-45d6-a407-ee925bcb43cb" width="600">
  
  **🤖 Claude + Gemini = Your Ultimate AI Development Team**
</div>

The ultimate development partner for Claude - a Model Context Protocol server that gives Claude access to Google's Gemini 2.5 Pro for extended thinking, code analysis, and problem-solving. **Automatically reads files and directories, passing their contents to Gemini for analysis within its 1M token context.**

## Why This Server?

Claude is brilliant, but sometimes you need:
- **A senior developer partner** to validate and extend ideas ([`chat`](#1-chat---general-development-chat--collaborative-thinking))
- **A second opinion** on complex architectural decisions - augment Claude's extended thinking with Gemini's perspective ([`think_deeper`](#2-think_deeper---extended-reasoning-partner))
- **Professional code reviews** with actionable feedback across entire repositories ([`review_code`](#3-review_code---professional-code-review))
- **Pre-commit validation** with deep analysis that finds edge cases, validates your implementation against original requirements, and catches subtle bugs Claude might miss ([`review_changes`](#4-review_changes---pre-commit-validation))
- **Expert debugging** for tricky issues with full system context ([`debug_issue`](#5-debug_issue---expert-debugging-assistant))
- **Massive context window** (1M tokens) - Gemini 2.5 Pro can analyze entire codebases, read hundreds of files at once, and provide comprehensive insights ([`analyze`](#6-analyze---smart-file-analysis))
- **Deep code analysis** across massive codebases that exceed Claude's context limits ([`analyze`](#6-analyze---smart-file-analysis))
- **Dynamic collaboration** - Gemini can request additional context from Claude mid-analysis for more thorough insights

This server makes Gemini your development sidekick, handling what Claude can't or extending what Claude starts.

## File & Directory Support

All tools accept both individual files and entire directories. The server:
- **Automatically expands directories** to find all code files recursively
- **Intelligently filters** hidden files, caches, and non-code files
- **Handles mixed inputs** like `"analyze main.py, src/, and tests/"`
- **Manages token limits** by loading as many files as possible within Gemini's context

## Quickstart (5 minutes)

### Prerequisites
- **Python 3.10 or higher** (required by the `mcp` package)
- Git

### 1. Get a Gemini API Key
Visit [Google AI Studio](https://makersuite.google.com/app/apikey) and generate an API key. For best results with Gemini 2.5 Pro, use a paid API key as the free tier has limited access to the latest models.

### 2. Clone and Set Up the Repository
Clone this repository to a location on your computer and install dependencies:

```bash
# Example: Clone to your home directory
cd ~
git clone https://github.com/BeehiveInnovations/gemini-mcp-server.git
cd gemini-mcp-server

# Run the setup script to install dependencies
# macOS/Linux:
./setup.sh

# Windows:
setup.bat
```

**Note the full path** - you'll need it in the next step:
- **macOS/Linux**: `/Users/YOUR_USERNAME/gemini-mcp-server`
- **Windows**: `C:\Users\YOUR_USERNAME\gemini-mcp-server`

**Important**: The setup script will:
- Create a Python virtual environment
- Install all required dependencies (mcp, google-genai, etc.)
- Verify your Python installation
- Provide next steps for configuration

If you encounter any issues during setup, see the [Troubleshooting](#troubleshooting) section.

### 3. Configure Claude Desktop
Add the server to your `claude_desktop_config.json`:

**Option A: Edit the config file directly**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Option B: Use Claude Desktop UI (macOS)**
- Open Claude Desktop
- Go to **Settings** → **Developer** → **Edit Config**
- This will open the `claude_desktop_config.json` file in your default editor

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

**Windows (Native Python):**
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

**Windows (Using WSL):**
If your development environment is in WSL, use `wsl.exe` as a bridge:
```json
{
  "mcpServers": {
    "gemini": {
      "command": "wsl.exe",
      "args": ["/home/YOUR_WSL_USERNAME/gemini-mcp-server/run_gemini.sh"],
      "env": {
        "GEMINI_API_KEY": "your-gemini-api-key-here"
      }
    }
  }
}
```

**Important**: 
- Replace `YOUR_USERNAME` with your actual Windows username
- Replace `YOUR_WSL_USERNAME` with your WSL username
- Use the full absolute path where you cloned the repository
- Windows native: Note the double backslashes `\\` in the path
- WSL: Use Linux-style paths starting with `/`
- See `examples/` folder for complete configuration examples

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
- **Need a thinking partner?** → `chat` (brainstorm ideas, get second opinions, validate approaches)
- **Need deeper thinking?** → `think_deeper` (extends Claude's analysis, finds edge cases)
- **Code needs review?** → `review_code` (bugs, security, performance issues)
- **Pre-commit validation?** → `review_changes` (validate git changes before committing)
- **Something's broken?** → `debug_issue` (root cause analysis, error tracing)
- **Want to understand code?** → `analyze` (architecture, patterns, dependencies)
- **Server info?** → `get_version` (version and configuration details)

**Pro Tip:** You can control the depth of Gemini's analysis with thinking modes to manage token costs. For quick tasks use "minimal" or "low" to save tokens, for complex problems use "high" or "max" when quality matters more than cost. [Learn more about thinking modes](#thinking-modes---managing-token-costs--quality)

## Windows Setup Guide

### Option 1: Native Windows (Recommended)

For the smoothest experience on Windows, we recommend running the server natively:

1. **Install Python on Windows**
   - Download from [python.org](https://python.org) or install via Microsoft Store
   - Ensure Python 3.10 or higher

2. **Set up the project**
   ```powershell
   cd C:\Users\YOUR_USERNAME\gemini-mcp-server
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Claude Desktop** using the Windows native configuration shown above

### Option 2: Using WSL (Advanced)

If you prefer to use WSL (Windows Subsystem for Linux):

1. **Prerequisites**
   - WSL2 installed with a Linux distribution (e.g., Ubuntu)
   - Python installed in your WSL environment
   - Project cloned inside WSL (recommended: `~/gemini-mcp-server`)

2. **Set up in WSL**
   ```bash
   # Inside WSL terminal
   cd ~/gemini-mcp-server
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   chmod +x run_gemini.sh
   ```

3. **Configure Claude Desktop** using the WSL configuration shown above

**Important WSL Notes:**
- For best performance, clone the repository inside WSL (`~/`) rather than on Windows (`/mnt/c/`)
- Ensure `run_gemini.sh` has Unix line endings (LF, not CRLF)
- If you have multiple WSL distributions, specify which one: `wsl.exe -d Ubuntu-22.04`

**Tools Overview:**
1. [`chat`](#1-chat---general-development-chat--collaborative-thinking) - Collaborative thinking and development conversations
2. [`think_deeper`](#2-think_deeper---extended-reasoning-partner) - Extended reasoning and problem-solving
3. [`review_code`](#3-review_code---professional-code-review) - Professional code review with severity levels
4. [`review_changes`](#4-review_changes---pre-commit-validation) - Validate git changes before committing
5. [`debug_issue`](#5-debug_issue---expert-debugging-assistant) - Root cause analysis and debugging
6. [`analyze`](#6-analyze---smart-file-analysis) - General-purpose file and code analysis
7. [`get_version`](#7-get_version---server-information) - Get server version and configuration

### 1. `chat` - General Development Chat & Collaborative Thinking
**Your thinking partner - bounce ideas, get second opinions, brainstorm collaboratively**

**Thinking Mode:** Default is `medium` (8,192 tokens). Use `low` for quick questions to save tokens, or `high` for complex discussions when thoroughness matters.

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to explain how async/await works in Python"
"Get gemini to compare Redis vs Memcached for session storage"
"Share my authentication design with gemini and get their opinion"
"Brainstorm with gemini about scaling strategies for our API"
```

**Managing Token Costs:**
```
# Save tokens (~6k) for simple questions
"Use gemini with minimal thinking to explain what a REST API is"
"Chat with gemini using low thinking mode about Python naming conventions"

# Use default for balanced analysis
"Get gemini to review my database schema design" (uses default medium)

# Invest tokens for complex discussions
"Use gemini with high thinking to brainstorm distributed system architecture"
```

**Collaborative Workflow:**
```
"Research the best message queue for our use case (high throughput, exactly-once delivery).
Use gemini to compare RabbitMQ, Kafka, and AWS SQS. Based on gemini's analysis and your research,
recommend the best option with implementation plan."

"Design a caching strategy for our API. Get gemini's input on Redis vs Memcached vs in-memory caching.
Combine both perspectives to create a comprehensive caching implementation guide."
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
- **Dynamic collaboration**: Gemini can request additional files or context during the conversation if needed for a more thorough response

**Triggers:** ask, explain, compare, suggest, what about, brainstorm, discuss, share my thinking, get opinion

### 2. `think_deeper` - Extended Reasoning Partner

<div align="center">
  <img src="https://github.com/user-attachments/assets/0f3c8e2d-a236-4068-a80e-46f37b0c9d35" width="600">
</div>

**Prompt:**
```
Study the code properly, think deeply about what this does and then see if there's any room for improvement in
terms of performance optimizations, brainstorm with gemini on this to get feedback and then confirm any change by
first adding a unit test with `measure` and measuring current code and then implementing the optimization and
measuring again to ensure it improved, then share results. Check with gemini in between as you make tweaks.
```

**Get a second opinion to augment Claude's own extended thinking**

**Thinking Mode:** Default is `max` (32,768 tokens) for deepest analysis. Reduce to save tokens if you need faster/cheaper responses.

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to think deeper about my authentication design"
"Use gemini to extend my analysis of this distributed system architecture"
```

**Managing Token Costs:**
```
# Save significant tokens when deep analysis isn't critical
"Use gemini to think deeper with medium thinking about this refactoring approach" (saves ~24k tokens)
"Get gemini to think deeper using high thinking mode about this design" (saves ~16k tokens)

# Use default max only for critical analysis
"Use gemini to think deeper about this security architecture" (uses default max - 32k tokens)

# For simple validations
"Use gemini with low thinking to validate my basic approach" (saves ~30k tokens!)
```

**Collaborative Workflow:**
```
"Design an authentication system for our SaaS platform. Then use gemini to review your design
 for security vulnerabilities. After getting gemini's feedback, incorporate the suggestions and
show me the final improved design."

"Create an event-driven architecture for our order processing system. Use gemini to think deeper
about event ordering and failure scenarios. Then integrate gemini's insights and present the enhanced architecture."
```

**Key Features:**
- **Uses Gemini's specialized thinking models** for enhanced reasoning capabilities
- Provides a second opinion on Claude's analysis
- Challenges assumptions and identifies edge cases Claude might miss
- Offers alternative perspectives and approaches
- Validates architectural decisions and design patterns
- Can reference specific files for context: `"Use gemini to think deeper about my API design with reference to api/routes.py"`

**Triggers:** think deeper, ultrathink, extend my analysis, validate my approach

### 3. `review_code` - Professional Code Review  
**Comprehensive code analysis with prioritized feedback**

**Thinking Mode:** Default is `medium` (8,192 tokens). Use `high` for security-critical code (worth the extra tokens) or `low` for quick style checks (saves ~6k tokens).

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to review auth.py for issues"
"Use gemini to do a security review of auth/ focusing on authentication"
```

**Managing Token Costs:**
```
# Save tokens for style/formatting reviews
"Use gemini with minimal thinking to check code style in utils.py" (saves ~8k tokens)
"Review this file with gemini using low thinking for basic issues" (saves ~6k tokens)

# Default for standard reviews
"Use gemini to review the API endpoints" (uses default medium)

# Invest tokens for critical code
"Get gemini to review auth.py with high thinking mode for security issues" (adds ~8k tokens)
"Use gemini with max thinking to audit our encryption module" (adds ~24k tokens - justified for security)
```

**Collaborative Workflow:**
```
"Refactor the authentication module to use dependency injection. Then use gemini to
review your refactoring for any security vulnerabilities. Based on gemini's feedback,
make any necessary adjustments and show me the final secure implementation."

"Optimize the slow database queries in user_service.py. Get gemini to review your optimizations
 for potential regressions or edge cases. Incorporate gemini's suggestions and present the final optimized queries."
```

**Key Features:**
- Issues prioritized by severity (🔴 CRITICAL → 🟢 LOW)
- Supports specialized reviews: security, performance, quick
- Can enforce coding standards: `"Use gemini to review src/ against PEP8 standards"`
- Filters by severity: `"Get gemini to review auth/ - only report critical vulnerabilities"`

**Triggers:** review code, check for issues, find bugs, security check

### 4. `review_changes` - Pre-Commit Validation
**Comprehensive review of staged/unstaged git changes across multiple repositories**

**Thinking Mode:** Default is `medium` (8,192 tokens). Use `high` or `max` for critical releases when thorough validation justifies the token cost.

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to review my pending changes before I commit"
"Get gemini to validate all my git changes match the original requirements"
"Review pending changes in the frontend/ directory"
```

**Managing Token Costs:**
```
# Save tokens for small changes
"Use gemini with low thinking to review my README updates" (saves ~6k tokens)
"Review my config changes with gemini using minimal thinking" (saves ~8k tokens)

# Default for regular commits
"Use gemini to review my feature changes" (uses default medium)

# Invest tokens for critical releases
"Use gemini with high thinking to review changes before production release" (adds ~8k tokens)
"Get gemini to validate all changes with max thinking for this security patch" (adds ~24k tokens - worth it!)
```

**Collaborative Workflow:**
```
"I've implemented the user authentication feature. Use gemini to review all pending changes
across the codebase to ensure they align with the security requirements. Fix any issues
gemini identifies before committing."

"Review all my changes for the API refactoring task. Get gemini to check for incomplete
implementations or missing test coverage. Update the code based on gemini's findings."
```

**Key Features:**
- **Recursive repository discovery** - finds all git repos including nested ones
- **Validates changes against requirements** - ensures implementation matches intent
- **Detects incomplete changes** - finds added functions never called, missing tests, etc.
- **Multi-repo support** - reviews changes across multiple repositories in one go
- **Configurable scope** - review staged, unstaged, or compare against branches
- **Security focused** - catches exposed secrets, vulnerabilities in new code
- **Smart truncation** - handles large diffs without exceeding context limits

**Parameters:**
- `path`: Starting directory to search for repos (default: current directory)
- `original_request`: The requirements/ticket for context
- `compare_to`: Compare against a branch/tag instead of local changes
- `review_type`: full|security|performance|quick
- `severity_filter`: Filter by issue severity
- `max_depth`: How deep to search for nested repos

**Triggers:** review pending changes, check my changes, validate changes, pre-commit review

### 5. `debug_issue` - Expert Debugging Assistant
**Root cause analysis for complex problems**

**Thinking Mode:** Default is `medium` (8,192 tokens). Use `high` for tricky bugs (investment in finding root cause) or `low` for simple errors (save tokens).

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to debug this TypeError: 'NoneType' object has no attribute 'split'"
"Get gemini to debug why my API returns 500 errors with the full stack trace: [paste traceback]"
```

**Managing Token Costs:**
```
# Save tokens for simple errors
"Use gemini with minimal thinking to debug this syntax error" (saves ~8k tokens)
"Debug this import error with gemini using low thinking" (saves ~6k tokens)

# Default for standard debugging
"Use gemini to debug why this function returns null" (uses default medium)

# Invest tokens for complex bugs
"Use gemini with high thinking to debug this race condition" (adds ~8k tokens)
"Get gemini to debug this memory leak with max thinking mode" (adds ~24k tokens - find that leak!)
```

**Collaborative Workflow:**
```
"I'm getting 'ConnectionPool limit exceeded' errors under load. Debug the issue and use
gemini to analyze it deeper with context from db/pool.py. Based on gemini's root cause analysis,
implement a fix and get gemini to validate the solution will scale."

"Debug why tests fail randomly on CI. Once you identify potential causes, share with gemini along
with test logs and CI configuration. Apply gemini's debugging strategy, then use gemini to
suggest preventive measures."
```

**Key Features:**
- Generates multiple ranked hypotheses for systematic debugging
- Accepts error context, stack traces, and logs
- Can reference relevant files for investigation
- Supports runtime info and previous attempts
- Provides structured root cause analysis with validation steps
- Can request additional context when needed for thorough analysis

**Triggers:** debug, error, failing, root cause, trace, not working

### 6. `analyze` - Smart File Analysis
**General-purpose code understanding and exploration**

**Thinking Mode:** Default is `medium` (8,192 tokens). Use `high` for architecture analysis (comprehensive insights worth the cost) or `low` for quick file overviews (save ~6k tokens).

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to analyze main.py to understand how it works"
"Get gemini to do an architecture analysis of the src/ directory"
```

**Managing Token Costs:**
```
# Save tokens for quick overviews
"Use gemini with minimal thinking to analyze what config.py does" (saves ~8k tokens)
"Analyze this utility file with gemini using low thinking" (saves ~6k tokens)

# Default for standard analysis
"Use gemini to analyze the API structure" (uses default medium)

# Invest tokens for deep analysis
"Use gemini with high thinking to analyze the entire codebase architecture" (adds ~8k tokens)
"Get gemini to analyze system design with max thinking for refactoring plan" (adds ~24k tokens)
```

**Collaborative Workflow:**
```
"Analyze our project structure in src/ and identify architectural improvements. Share your
analysis with gemini for a deeper review of design patterns and anti-patterns. Based on both
analyses, create a refactoring roadmap."

"Perform a security analysis of our authentication system. Use gemini to analyze auth/, middleware/, and api/ for vulnerabilities.
Combine your findings with gemini's to create a comprehensive security report."
```

**Key Features:**
- Analyzes single files or entire directories
- Supports specialized analysis types: architecture, performance, security, quality
- Uses file paths (not content) for clean terminal output
- Can identify patterns, anti-patterns, and refactoring opportunities

**Triggers:** analyze, examine, look at, understand, inspect

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
- `thinking_mode`: minimal|low|medium|high|max (default: medium)

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
- `thinking_mode`: minimal|low|medium|high|max (default: medium)

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
- `thinking_mode`: minimal|low|medium|high|max (default: medium)

```
"Use gemini to debug this error with context from the entire backend/ directory"
```

**`think_deeper`** - Extended analysis with file context
- `current_analysis`: Your current thinking (required)
- `problem_context`: Additional context
- `focus_areas`: Specific aspects to focus on
- `files`: Files or directories for context
- `thinking_mode`: minimal|low|medium|high|max (default: max)

```
"Use gemini to think deeper about my design with reference to the src/models/ directory"
```

## Collaborative Workflows

### Design → Review → Implement
```
"Design a real-time collaborative editor. Use gemini to think deeper about edge cases and scalability.
Implement an improved version incorporating gemini's suggestions."
```

### Code → Review → Fix
```
"Implement JWT authentication. Get gemini to do a security review. Fix any issues gemini identifies and
show me the secure implementation."
```

### Debug → Analyze → Solution
```
"Debug why our API crashes under load. Use gemini to analyze deeper with context from api/handlers/. Implement a
fix based on gemini's root cause analysis."
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

### Tool Selection Guidance
To help choose the right tool for your needs:

**Decision Flow:**
1. **Have a specific error/exception?** → Use `debug_issue`
2. **Want to find bugs/issues in code?** → Use `review_code`
3. **Want to understand how code works?** → Use `analyze`
4. **Have analysis that needs extension/validation?** → Use `think_deeper`
5. **Want to brainstorm or discuss?** → Use `chat`

**Key Distinctions:**
- `analyze` vs `review_code`: analyze explains, review_code prescribes fixes
- `chat` vs `think_deeper`: chat is open-ended, think_deeper extends specific analysis
- `debug_issue` vs `review_code`: debug diagnoses runtime errors, review finds static issues

## Thinking Modes - Managing Token Costs & Quality

Control Gemini's reasoning depth to balance between response quality and token consumption. Each thinking mode uses a different amount of tokens, directly affecting API costs and response time.

### Thinking Modes & Token Budgets

| Mode | Token Budget | Use Case | Cost Impact |
|------|-------------|----------|-------------|
| `minimal` | 128 tokens | Simple, straightforward tasks | Lowest cost |
| `low` | 2,048 tokens | Basic reasoning tasks | 16x more than minimal |
| `medium` | 8,192 tokens | **Default** - Most development tasks | 64x more than minimal |
| `high` | 16,384 tokens | Complex problems requiring thorough analysis | 128x more than minimal |
| `max` | 32,768 tokens | Exhaustive reasoning (default for `think_deeper`) | 256x more than minimal |

### How to Use Thinking Modes

You can control thinking modes using natural language in your prompts. Remember: higher thinking modes = more tokens = higher cost but better quality:

#### Natural Language Examples

| Your Goal | Example Prompt |
|-----------|----------------|
| **Quick task** | "Use gemini to format this code with minimal thinking" |
| **Standard analysis** | "Get gemini to review auth.py" (uses default `medium`) |
| **Deep analysis** | "Use gemini to review this security module with high thinking mode" |
| **Maximum depth** | "Get gemini to think deeper with max thinking about this architecture" |
| **Compare approaches** | "First analyze this with low thinking, then again with high thinking" |

#### Optimizing Token Usage & Costs

**Use lower modes (`minimal`, `low`) to save tokens when:**
- Doing simple formatting or style checks
- Getting quick explanations of basic concepts
- Working with straightforward code
- You need faster responses
- Working within tight token budgets

**Use higher modes (`high`, `max`) when quality justifies the cost:**
- Debugging complex issues (worth the extra tokens to find root causes)
- Reviewing security-critical code (cost of tokens < cost of vulnerabilities)
- Analyzing system architecture (comprehensive analysis saves development time)
- Finding subtle bugs or edge cases
- Working on performance optimizations

**Token Cost Examples:**
- `minimal` (128 tokens) vs `max` (32,768 tokens) = 256x difference in thinking tokens
- For a simple formatting check, using `minimal` instead of the default `medium` saves ~8,000 thinking tokens
- For critical security reviews, the extra tokens in `high` or `max` mode are a worthwhile investment

**Examples by scenario:**
```
# Quick style check
"Use gemini to review formatting in utils.py with minimal thinking"

# Security audit
"Get gemini to do a security review of auth/ with thinking mode high"

# Complex debugging
"Use gemini to debug this race condition with max thinking mode"

# Architecture analysis
"Analyze the entire src/ directory architecture with high thinking"
```

## Advanced Features

### Dynamic Context Requests
Tools can request additional context from Claude during execution. When Gemini needs more information to provide a thorough analysis, it will ask Claude for specific files or clarification, enabling true collaborative problem-solving.

**Example:** If Gemini is debugging an error but needs to see a configuration file that wasn't initially provided, it can request: 
```json
{
  "status": "requires_clarification",
  "question": "I need to see the database configuration to understand this connection error",
  "files_needed": ["config/database.yml", "src/db_connection.py"]
}
```

Claude will then provide the requested files and Gemini can continue with a more complete analysis.

### Standardized Response Format
All tools now return structured JSON responses for consistent handling:
```json
{
  "status": "success|error|requires_clarification",
  "content": "The actual response content",
  "content_type": "text|markdown|json",
  "metadata": {"tool_name": "analyze", ...}
}
```

This enables better integration, error handling, and support for the dynamic context request feature.

## Configuration

The server includes several configurable properties that control its behavior:

### Model Configuration
- **`GEMINI_MODEL`**: `"gemini-2.5-pro-preview-06-05"` - The latest Gemini 2.5 Pro model with native thinking support
- **`MAX_CONTEXT_TOKENS`**: `1,000,000` - Maximum input context (1M tokens for Gemini 2.5 Pro)

### Temperature Defaults
Different tools use optimized temperature settings:
- **`TEMPERATURE_ANALYTICAL`**: `0.2` - Used for code review and debugging (focused, deterministic)
- **`TEMPERATURE_BALANCED`**: `0.5` - Used for general chat (balanced creativity/accuracy)
- **`TEMPERATURE_CREATIVE`**: `0.7` - Used for deep thinking and architecture (more creative)


## File Path Requirements

**All file paths must be absolute paths.**

When using any Gemini tool, always provide absolute paths:
```
✅ "Use gemini to analyze /Users/you/project/src/main.py"
❌ "Use gemini to analyze ./src/main.py"  (will be rejected)
```

### Security & File Access

By default, the server allows access to files within your home directory. This is necessary for the server to work with any file you might want to analyze from Claude.

**To restrict access to a specific project directory**, set the `MCP_PROJECT_ROOT` environment variable:
```json
"env": {
  "GEMINI_API_KEY": "your-key",
  "MCP_PROJECT_ROOT": "/Users/you/specific-project"
}
```

This creates a sandbox limiting file access to only that directory and its subdirectories.

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

## Testing

### Unit Tests (No API Key Required)
The project includes comprehensive unit tests that use mocks and don't require a Gemini API key:

```bash
# Run all unit tests
python -m pytest tests/ --ignore=tests/test_live_integration.py -v

# Run with coverage
python -m pytest tests/ --ignore=tests/test_live_integration.py --cov=. --cov-report=html
```

### Live Integration Tests (API Key Required)
To test actual API integration:

```bash
# Set your API key
export GEMINI_API_KEY=your-api-key-here

# Run live integration tests
python tests/test_live_integration.py
```

### GitHub Actions CI/CD
The project includes GitHub Actions workflows that:

- **✅ Run unit tests automatically** - No API key needed, uses mocks
- **✅ Test on Python 3.10, 3.11, 3.12** - Ensures compatibility
- **✅ Run linting and formatting checks** - Maintains code quality  
- **🔒 Run live tests only if API key is available** - Optional live verification

The CI pipeline works without any secrets and will pass all tests using mocked responses. Live integration tests only run if a `GEMINI_API_KEY` secret is configured in the repository.

## Troubleshooting

### Windows/WSL Issues

**Error: `spawn P:\path\to\run_gemini.bat ENOENT`**

This error occurs when Claude Desktop (running on Windows) can't properly execute the server. Common causes:

1. **Wrong execution environment**: You're trying to run WSL-based code from Windows
   - **Solution**: Use the WSL bridge configuration with `wsl.exe` (see Windows Setup Guide above)

2. **Path format mismatch**: Using Linux paths (`/mnt/c/...`) in Windows context
   - **Solution**: Use Windows paths for native execution, Linux paths only after `wsl.exe`

3. **Missing dependencies**: Python or required packages not installed in the execution environment
   - **Solution**: Ensure Python and dependencies are installed where you're trying to run (Windows or WSL)

**Testing your setup:**
- Windows users: Run `test_wsl_setup.bat` to verify your WSL configuration
- Check Python availability: `python --version` (Windows) or `wsl python3 --version` (WSL)

### Common Issues

**"ModuleNotFoundError: No module named 'mcp'" or "No matching distribution found for mcp"**
- This means either:
  1. Python dependencies aren't installed - run the setup script
  2. Your Python version is too old - the `mcp` package requires Python 3.10+
- **Solution**: 
  - First check your Python version: `python3 --version` or `python --version`
  - If below 3.10, upgrade Python from https://python.org
  - Then run the setup script:
    - macOS/Linux: `./setup.sh` 
    - Windows: `setup.bat`
- If you still see this error, manually activate the virtual environment and install:
  ```bash
  # macOS/Linux:
  source venv/bin/activate
  pip install -r requirements.txt
  
  # Windows:
  venv\Scripts\activate.bat
  pip install -r requirements.txt
  ```

**"Virtual environment not found" warning**
- This is just a warning that can be ignored if dependencies are installed system-wide
- To fix: Run the setup script to create the virtual environment

**"GEMINI_API_KEY environment variable is required"**
- Ensure you've added your API key to the Claude Desktop configuration
- The key should be in the `env` section of your MCP server config

**"Connection failed" in Claude Desktop**
- Verify the command path is correct and uses proper escaping (`\\` for Windows paths)
- Ensure the script has execute permissions (Linux/macOS: `chmod +x run_gemini.sh`)
- Check Claude Desktop logs for detailed error messages

**Performance issues with WSL**
- Files on Windows drives (`/mnt/c/`) are slower to access from WSL
- For best performance, clone the repository inside WSL (`~/gemini-mcp-server`)

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Built with the power of **Claude + Gemini** collaboration 🤝
- [MCP (Model Context Protocol)](https://modelcontextprotocol.com) by Anthropic
- [Claude Code](https://claude.ai/code) - Your AI coding assistant
- [Gemini 2.5 Pro](https://ai.google.dev/) - Extended thinking & analysis engine
