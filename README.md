# Claude Code + Gemini: Working Together as One

  https://github.com/user-attachments/assets/a67099df-9387-4720-9b41-c986243ac11b

<div align="center">  
  <b>🤖 Claude + Gemini = Your Ultimate AI Development Team</b>
</div>

<br/>

The ultimate development partner for Claude - a Model Context Protocol server that gives Claude access to Google's Gemini 2.5 Pro for extended thinking, code analysis, and problem-solving. **Automatically reads files and directories, passing their contents to Gemini for analysis within its 1M token context.**

**Think of it as Claude Code _for_ Claude Code.**

## Quick Navigation

- **Getting Started**
  - [Quickstart](#quickstart-5-minutes) - Get running in 5 minutes with Docker
  - [Available Tools](#available-tools) - Overview of all tools
  - [AI-to-AI Conversations](#ai-to-ai-conversation-threading) - Multi-turn conversations

- **Tools Reference**
  - [`chat`](#1-chat---general-development-chat--collaborative-thinking) - Collaborative thinking
  - [`thinkdeep`](#2-thinkdeep---extended-reasoning-partner) - Extended reasoning
  - [`codereview`](#3-codereview---professional-code-review) - Code review
  - [`precommit`](#4-precommit---pre-commit-validation) - Pre-commit validation
  - [`debug`](#5-debug---expert-debugging-assistant) - Debugging help
  - [`analyze`](#6-analyze---smart-file-analysis) - File analysis

- **Advanced Topics**
  - [Thinking Modes](#thinking-modes---managing-token-costs--quality) - Control depth vs cost
  - [Working with Large Prompts](#working-with-large-prompts) - Bypass MCP's 25K token limit
  - [Web Search Integration](#web-search-integration) - Smart search recommendations
  - [Collaborative Workflows](#collaborative-workflows) - Multi-tool patterns
  - [Tool Parameters](#tool-parameters) - Detailed parameter reference
  - [Docker Architecture](#docker-architecture) - How Docker integration works

- **Resources**
  - [Windows Setup](#windows-setup-guide) - WSL setup instructions for Windows
  - [Troubleshooting](#troubleshooting) - Common issues and solutions
  - [Contributing](#contributing) - How to contribute
  - [Testing](#testing) - Running tests

## Why This Server?

Claude is brilliant, but sometimes you need:
- **A senior developer partner** to validate and extend ideas ([`chat`](#1-chat---general-development-chat--collaborative-thinking))
- **A second opinion** on complex architectural decisions - augment Claude's extended thinking with Gemini's perspective ([`thinkdeep`](#2-thinkdeep---extended-reasoning-partner))
- **Professional code reviews** with actionable feedback across entire repositories ([`codereview`](#3-codereview---professional-code-review))
- **Pre-commit validation** with deep analysis that finds edge cases, validates your implementation against original requirements, and catches subtle bugs Claude might miss ([`precommit`](#4-precommit---pre-commit-validation))
- **Expert debugging** for tricky issues with full system context ([`debug`](#5-debug---expert-debugging-assistant))
- **Massive context window** (1M tokens) - Gemini 2.5 Pro can analyze entire codebases, read hundreds of files at once, and provide comprehensive insights ([`analyze`](#6-analyze---smart-file-analysis))
- **Deep code analysis** across massive codebases that exceed Claude's context limits ([`analyze`](#6-analyze---smart-file-analysis))
- **Dynamic collaboration** - Gemini can request additional context from Claude mid-analysis for more thorough insights
- **Smart file handling** - Automatically expands directories, filters irrelevant files, and manages token limits when analyzing `"main.py, src/, tests/"`
- **[Bypass MCP's token limits](#working-with-large-prompts)** - Work around MCP's 25K combined token limit by automatically handling large prompts as files, preserving the full capacity for responses

This server makes Gemini your development sidekick, handling what Claude can't or extending what Claude starts.

<div align="center">
  <img src="https://github.com/user-attachments/assets/0f3c8e2d-a236-4068-a80e-46f37b0c9d35" width="600">
</div>

**Prompt Used:**
```
Study the code properly, think deeply about what this does and then see if there's any room for improvement in
terms of performance optimizations, brainstorm with gemini on this to get feedback and then confirm any change by
first adding a unit test with `measure` and measuring current code and then implementing the optimization and
measuring again to ensure it improved, then share results. Check with gemini in between as you make tweaks.
```

The final implementation resulted in a 26% improvement in JSON parsing performance for the selected library, reducing processing time through targeted, collaborative optimizations guided by Gemini’s analysis and Claude’s refinement.

## Quickstart (5 minutes)

### Prerequisites

- Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop/))
- Git
- **Windows users**: WSL2 is required for Claude Code CLI

### 1. Get a Gemini API Key
Visit [Google AI Studio](https://makersuite.google.com/app/apikey) and generate an API key. For best results with Gemini 2.5 Pro, use a paid API key as the free tier has limited access to the latest models.

### 2. Clone and Set Up

```bash
# Clone to your preferred location
git clone https://github.com/BeehiveInnovations/gemini-mcp-server.git
cd gemini-mcp-server

# One-command setup (includes Redis for AI conversations)
./setup-docker.sh
```

**What this does:**
- **Builds Docker images** with all dependencies (including Redis for conversation threading)
- **Creates .env file** (automatically uses `$GEMINI_API_KEY` if set in environment)
- **Starts Redis service** for AI-to-AI conversation memory
- **Starts MCP server** ready to connect
- **Shows exact Claude Desktop configuration** to copy
- **Multi-turn AI conversations** - Gemini can ask follow-up questions that persist across requests

### 3. Add Your API Key

```bash
# Edit .env to add your Gemini API key (if not already set in environment)
nano .env

# The file will contain:
# GEMINI_API_KEY=your-gemini-api-key-here
# REDIS_URL=redis://redis:6379/0  (automatically configured)
# WORKSPACE_ROOT=/workspace  (automatically configured)
```

### 4. Configure Claude Desktop

**Find your config file:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
- **Windows (WSL required)**: Access from WSL using `/mnt/c/Users/USERNAME/AppData/Roaming/Claude/claude_desktop_config.json`

**Or use Claude Desktop UI (macOS):**
- Open Claude Desktop
- Go to **Settings** → **Developer** → **Edit Config**

**Or use Claude Code CLI (Recommended):**
```bash
# Add the MCP server directly via Claude Code CLI
claude mcp add gemini -s user -- docker exec -i gemini-mcp-server python server.py

# List your MCP servers to verify
claude mcp list

# Remove if needed
claude mcp remove gemini
```

#### Docker Configuration (Copy from setup script output)

The setup script shows you the exact configuration. It looks like this:

```json
{
  "mcpServers": {
    "gemini": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "gemini-mcp-server",
        "python",
        "server.py"
      ]
    }
  }
}
```

**How it works:**
- **Docker Compose services** run continuously in the background
- **Redis** automatically handles conversation memory between requests  
- **AI-to-AI conversations** persist across multiple exchanges
- **File access** through mounted workspace directory

**That's it!** The Docker setup handles all dependencies, Redis configuration, and service management automatically.

### 5. Restart Claude Desktop
Completely quit and restart Claude Desktop for the changes to take effect.

### 6. Start Using It!

Just ask Claude naturally:
- "Use gemini to think deeper about this architecture design" → `thinkdeep`
- "Get gemini to review this code for security issues" → `codereview`
- "Get gemini to debug why this test is failing" → `debug`
- "Use gemini to analyze these files to understand the data flow" → `analyze`
- "Brainstorm with gemini about scaling strategies" → `chat`
- "Share my implementation plan with gemini for feedback" → `chat`
- "Get gemini's opinion on my authentication design" → `chat`

## AI-to-AI Conversation Threading

This server enables **true AI collaboration** between Claude and Gemini, where they can coordinate and question each other's approaches:

**How it works:**
- **Gemini can ask Claude follow-up questions** to clarify requirements or gather more context
- **Claude can respond** with additional information, files, or refined instructions
- **Claude can work independently** between exchanges - implementing solutions, gathering data, or performing analysis
- **Claude can return to Gemini** with progress updates and new context for further collaboration
- **Cross-tool continuation** - Start with one tool (e.g., `analyze`) and continue with another (e.g., `codereview`) using the same conversation thread
- **Both AIs coordinate their approaches** - questioning assumptions, validating solutions, and building on each other's insights
- Each conversation maintains full context while only sending incremental updates
- Conversations are automatically managed with Redis for persistence

**Example of AI-to-AI coordination:**
1. You: "Chat with gemini to debate SwiftUI vs UIKit - which is better for iOS development?"
2. Claude: "I'll present SwiftUI's case: Modern declarative syntax, automatic state management, cross-platform compatibility, and Apple's clear future direction make SwiftUI the superior choice for new projects."
3. Gemini: "I disagree. UIKit remains superior for production apps: mature ecosystem, granular control, extensive third-party support, proven performance in complex UIs, and better debugging tools. SwiftUI still has too many limitations."
4. Claude: "While UIKit has maturity advantages, SwiftUI's rapid evolution, simplified development workflow, and Apple's investment make it the strategic choice. The learning curve pays off with faster development and maintainable code."
5. **Final recommendation**: After this AI debate, Claude concludes: "Based on our discussion, SwiftUI is recommended for new projects despite Gemini's valid UIKit points."

**Asynchronous workflow example:**
- Claude can work independently between exchanges (analyzing code, implementing fixes, gathering data)
- Return to Gemini with progress updates and additional context  
- Each exchange shares only incremental information while maintaining full conversation history
- Automatically bypasses MCP's 25K token limits through incremental updates

**Enhanced collaboration features:**
- **Cross-questioning**: AIs can challenge each other's assumptions and approaches
- **Coordinated problem-solving**: Each AI contributes their strengths to complex problems
- **Context building**: Claude gathers information while Gemini provides deep analysis
- **Approach validation**: AIs can verify and improve each other's solutions
- **Cross-tool continuation**: Seamlessly continue conversations across different tools while preserving all context
- **Asynchronous workflow**: Conversations don't need to be sequential - Claude can work on tasks between exchanges, then return to Gemini with additional context and progress updates
- **Incremental updates**: Share only new information in each exchange while maintaining full conversation history
- **Automatic 25K limit bypass**: Each exchange sends only incremental context, allowing unlimited total conversation size
- Up to 5 exchanges per conversation with 1-hour expiry
- Thread-safe with Redis persistence across all tools

**Cross-tool continuation example:**
```
1. Claude: "Use gemini to analyze /src/auth.py for security issues"
   → Gemini analyzes and finds vulnerabilities, provides continuation_id

2. Claude: "Use gemini to review the authentication logic thoroughly"
   → Uses same continuation_id, Gemini sees previous analysis and files
   → Provides detailed code review building on previous findings  

3. Claude: "Use gemini to help debug the auth test failures"
   → Same continuation_id, full context from analysis + review
   → Gemini provides targeted debugging with complete understanding
```

## Available Tools

**Quick Tool Selection Guide:**
- **Need a thinking partner?** → `chat` (brainstorm ideas, get second opinions, validate approaches)
- **Need deeper thinking?** → `thinkdeep` (extends Claude's analysis, finds edge cases)
- **Code needs review?** → `codereview` (bugs, security, performance issues)
- **Pre-commit validation?** → `precommit` (validate git changes before committing)
- **Something's broken?** → `debug` (root cause analysis, error tracing)
- **Want to understand code?** → `analyze` (architecture, patterns, dependencies)
- **Server info?** → `get_version` (version and configuration details)

**Pro Tip:** You can control the depth of Gemini's analysis with thinking modes to manage token costs. For quick tasks use "minimal" or "low" to save tokens, for complex problems use "high" or "max" when quality matters more than cost. [Learn more about thinking modes](#thinking-modes---managing-token-costs--quality)

**Tools Overview:**
1. [`chat`](#1-chat---general-development-chat--collaborative-thinking) - Collaborative thinking and development conversations
2. [`thinkdeep`](#2-thinkdeep---extended-reasoning-partner) - Extended reasoning and problem-solving
3. [`codereview`](#3-codereview---professional-code-review) - Professional code review with severity levels
4. [`precommit`](#4-precommit---pre-commit-validation) - Validate git changes before committing
5. [`debug`](#5-debug---expert-debugging-assistant) - Root cause analysis and debugging
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
- **Web search capability**: Analyzes when web searches would be helpful and recommends specific searches for Claude to perform, ensuring access to current documentation and best practices
### 2. `thinkdeep` - Extended Reasoning Partner

**Get a second opinion to augment Claude's own extended thinking**

**Thinking Mode:** Default is `high` (16,384 tokens) for deep analysis. Claude will automatically choose the best mode based on complexity - use `low` for quick validations, `medium` for standard problems, `high` for complex issues (default), or `max` for extremely complex challenges requiring deepest analysis.

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to think deeper about my authentication design"
"Use gemini to extend my analysis of this distributed system architecture"
```

**With Web Search (for exploring new technologies):**
```
"Use gemini to think deeper about using HTMX vs React for this project - enable web search to explore current best practices"
"Get gemini to think deeper about implementing WebAuthn authentication with web search enabled for latest standards"
```

**Managing Token Costs:**
```
# Claude will intelligently select the right mode, but you can override:
"Use gemini to think deeper with medium thinking about this refactoring approach" (saves ~8k tokens vs default)
"Get gemini to think deeper using low thinking to validate my basic approach" (saves ~14k tokens vs default)

# Use default high for most complex problems
"Use gemini to think deeper about this security architecture" (uses default high - 16k tokens)

# For extremely complex challenges requiring maximum depth
"Use gemini with max thinking to solve this distributed consensus problem" (adds ~16k tokens vs default)
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
- **Enhanced Critical Evaluation (v2.10.0)**: After Gemini's analysis, Claude is prompted to critically evaluate the suggestions, consider context and constraints, identify risks, and synthesize a final recommendation - ensuring a balanced, well-considered solution
- **Web search capability**: When enabled (default: true), identifies areas where current documentation or community solutions would strengthen the analysis and suggests specific searches for Claude
### 3. `codereview` - Professional Code Review  
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
### 4. `precommit` - Pre-Commit Validation
**Comprehensive review of staged/unstaged git changes across multiple repositories**

**Thinking Mode:** Default is `medium` (8,192 tokens). Use `high` or `max` for critical releases when thorough validation justifies the token cost.

<div align="center">
  <img src="https://github.com/user-attachments/assets/584adfa6-d252-49b4-b5b0-0cd6e97fb2c6" width="950">
</div>

**Prompt:**
```
Now use gemini and perform a review and precommit and ensure original requirements are met, no duplication of code or
logic, everything should work as expected
```

How beautiful is that? Claude used `precommit` twice and `codereview` once and actually found and fixed two critical errors before commit!

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
- `original_request`: The requirements for context
- `compare_to`: Compare against a branch/tag instead of local changes
- `review_type`: full|security|performance|quick
- `severity_filter`: Filter by issue severity
- `max_depth`: How deep to search for nested repos
### 5. `debug` - Expert Debugging Assistant
**Root cause analysis for complex problems**

**Thinking Mode:** Default is `medium` (8,192 tokens). Use `high` for tricky bugs (investment in finding root cause) or `low` for simple errors (save tokens).

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to debug this TypeError: 'NoneType' object has no attribute 'split'"
"Get gemini to debug why my API returns 500 errors with the full stack trace: [paste traceback]"
```

**With Web Search (for unfamiliar errors):**
```
"Use gemini to debug this cryptic Kubernetes error with web search enabled to find similar issues"
"Debug this React hydration error with gemini - enable web search to check for known solutions"
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
- **Web search capability**: When enabled (default: true), identifies when searching for error messages, known issues, or documentation would help solve the problem and recommends specific searches for Claude
### 6. `analyze` - Smart File Analysis
**General-purpose code understanding and exploration**

**Thinking Mode:** Default is `medium` (8,192 tokens). Use `high` for architecture analysis (comprehensive insights worth the cost) or `low` for quick file overviews (save ~6k tokens).

#### Example Prompts:

**Basic Usage:**
```
"Use gemini to analyze main.py to understand how it works"
"Get gemini to do an architecture analysis of the src/ directory"
```

**With Web Search (for unfamiliar code):**
```
"Use gemini to analyze this GraphQL schema with web search enabled to understand best practices"
"Analyze this Rust code with gemini - enable web search to look up unfamiliar patterns and idioms"
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
- **Web search capability**: When enabled with `use_websearch`, can look up framework documentation, design patterns, and best practices relevant to the code being analyzed
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
- `use_websearch`: Enable web search for documentation and best practices (default: false)

```
"Use gemini to analyze the src/ directory for architectural patterns"
"Get gemini to analyze main.py and tests/ to understand test coverage"
```

**`codereview`** - Review code files or directories
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

**`debug`** - Debug with file context
- `error_description`: Description of the issue (required)
- `error_context`: Stack trace or logs
- `files`: Files or directories related to the issue
- `runtime_info`: Environment details
- `previous_attempts`: What you've tried
- `thinking_mode`: minimal|low|medium|high|max (default: medium)
- `use_websearch`: Enable web search for error messages and solutions (default: false)

```
"Use gemini to debug this error with context from the entire backend/ directory"
```

**`thinkdeep`** - Extended analysis with file context
- `current_analysis`: Your current thinking (required)
- `problem_context`: Additional context
- `focus_areas`: Specific aspects to focus on
- `files`: Files or directories for context
- `thinking_mode`: minimal|low|medium|high|max (default: max)
- `use_websearch`: Enable web search for documentation and insights (default: false)

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
- ❌ "Use the thinkdeep tool with current_analysis parameter..."
- ✅ "Use gemini to think deeper about this approach"

### Automatic Tool Selection
Claude will automatically pick the right tool based on your request:
- "review" → `codereview`
- "debug" → `debug`
- "analyze" → `analyze`
- "think deeper" → `thinkdeep`

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
1. **Have a specific error/exception?** → Use `debug`
2. **Want to find bugs/issues in code?** → Use `codereview`
3. **Want to understand how code works?** → Use `analyze`
4. **Have analysis that needs extension/validation?** → Use `thinkdeep`
5. **Want to brainstorm or discuss?** → Use `chat`

**Key Distinctions:**
- `analyze` vs `codereview`: analyze explains, codereview prescribes fixes
- `chat` vs `thinkdeep`: chat is open-ended, thinkdeep extends specific analysis
- `debug` vs `codereview`: debug diagnoses runtime errors, review finds static issues

## Thinking Modes - Managing Token Costs & Quality

**Claude automatically manages thinking modes based on task complexity**, but you can also manually control Gemini's reasoning depth to balance between response quality and token consumption. Each thinking mode uses a different amount of tokens, directly affecting API costs and response time.

### Thinking Modes & Token Budgets

| Mode | Token Budget | Use Case | Cost Impact |
|------|-------------|----------|-------------|
| `minimal` | 128 tokens | Simple, straightforward tasks | Lowest cost |
| `low` | 2,048 tokens | Basic reasoning tasks | 16x more than minimal |
| `medium` | 8,192 tokens | **Default** - Most development tasks | 64x more than minimal |
| `high` | 16,384 tokens | Complex problems requiring thorough analysis (default for `thinkdeep`) | 128x more than minimal |
| `max` | 32,768 tokens | Exhaustive reasoning | 256x more than minimal |

### How to Use Thinking Modes

**Claude automatically selects appropriate thinking modes**, but you can override this by explicitly requesting a specific mode in your prompts. Remember: higher thinking modes = more tokens = higher cost but better quality:

#### Natural Language Examples

| Your Goal | Example Prompt |
|-----------|----------------|
| **Auto-managed (recommended)** | "Use gemini to review auth.py" (Claude picks appropriate mode) |
| **Override for simple tasks** | "Use gemini to format this code with minimal thinking" |
| **Override for deep analysis** | "Use gemini to review this security module with high thinking mode" |
| **Override for maximum depth** | "Get gemini to think deeper with max thinking about this architecture" |
| **Compare approaches** | "First analyze this with low thinking, then again with high thinking" |

#### Optimizing Token Usage & Costs

**In most cases, let Claude automatically manage thinking modes** for optimal balance of cost and quality. Override manually when you have specific requirements:

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

### Working with Large Prompts

The MCP protocol has a combined request+response limit of approximately 25K tokens. This server intelligently works around this limitation by automatically handling large prompts as files:

**How it works:**
1. When you send a prompt larger than the configured limit (default: 50K characters ~10-12K tokens), the server detects this
2. It responds with a special status asking Claude to save the prompt to a file named `prompt.txt`
3. Claude saves the prompt and resends the request with the file path instead
4. The server reads the file content directly into Gemini's 1M token context
5. The full MCP token capacity is preserved for the response

**Example scenario:**
```
# You have a massive code review request with detailed context
User: "Use gemini to review this code: [50,000+ character detailed analysis]"

# Server detects the large prompt and responds:
Gemini MCP: "The prompt is too large for MCP's token limits (>50,000 characters). 
Please save the prompt text to a temporary file named 'prompt.txt' and resend 
the request with an empty prompt string and the absolute file path included 
in the files parameter, along with any other files you wish to share as context."

# Claude automatically handles this:
- Saves your prompt to /tmp/prompt.txt
- Resends: "Use gemini to review this code" with files=["/tmp/prompt.txt", "/path/to/code.py"]

# Server processes the large prompt through Gemini's 1M context
# Returns comprehensive analysis within MCP's response limits
```

This feature ensures you can send arbitrarily large prompts to Gemini without hitting MCP's protocol limitations, while maximizing the available space for detailed responses.

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

### Web Search Integration

**Smart web search recommendations for enhanced analysis**

Web search is now enabled by default for all tools. Instead of performing searches directly, Gemini intelligently analyzes when additional information from the web would enhance its response and provides specific search recommendations for Claude to execute.

**How it works:**
1. Gemini analyzes the request and identifies areas where current documentation, API references, or community solutions would be valuable
2. It provides its analysis based on its training data
3. If web searches would strengthen the analysis, Gemini includes a "Recommended Web Searches for Claude" section
4. Claude can then perform these searches and incorporate the findings

**Example:**
```
User: "Use gemini to debug this FastAPI async error"

Gemini's Response:
[... debugging analysis ...]

**Recommended Web Searches for Claude:**
- "FastAPI async def vs def performance 2024" - to verify current best practices for async endpoints
- "FastAPI BackgroundTasks memory leak" - to check for known issues with the version you're using
- "FastAPI lifespan context manager pattern" - to explore proper resource management patterns

Claude can then search for these specific topics and provide you with the most current information.
```

**Benefits:**
- Always access to latest documentation and best practices
- Gemini focuses on reasoning about what information would help
- Claude maintains control over actual web searches
- More collaborative approach between the two AI assistants
- Reduces hallucination by encouraging verification of assumptions

**Disabling web search:**
If you prefer Gemini to work only with its training data, you can disable web search:
```
"Use gemini to review this code with use_websearch false"
```

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

### Logging Configuration
Control logging verbosity via the `LOG_LEVEL` environment variable:
- **`DEBUG`**: Shows detailed operational messages, tool execution flow, conversation threading
- **`INFO`**: Shows general operational messages (default)
- **`WARNING`**: Shows only warnings and errors
- **`ERROR`**: Shows only errors

**Set in your .env file:**
```bash
LOG_LEVEL=DEBUG  # For troubleshooting
LOG_LEVEL=INFO   # For normal operation (default)
```

**For Docker:**
```bash
# In .env file
LOG_LEVEL=DEBUG

# Or set directly when starting
LOG_LEVEL=DEBUG docker compose up
```


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


## How System Prompts Work

The server uses carefully crafted system prompts to give each tool specialized expertise:

### Prompt Architecture
- **Centralized Prompts**: All system prompts are defined in `prompts/tool_prompts.py`
- **Tool Integration**: Each tool inherits from `BaseTool` and implements `get_system_prompt()`
- **Prompt Flow**: `User Request → Tool Selection → System Prompt + Context → Gemini Response`

### Specialized Expertise
Each tool has a unique system prompt that defines its role and approach:
- **`thinkdeep`**: Acts as a senior development partner, challenging assumptions and finding edge cases
- **`codereview`**: Expert code reviewer with security/performance focus, uses severity levels
- **`debug`**: Systematic debugger providing root cause analysis and prevention strategies
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

### Docker Issues

**"Connection failed" in Claude Desktop**
- Ensure Docker services are running: `docker compose ps`
- Check if the container name is correct: `docker ps` to see actual container names
- Verify your .env file has the correct GEMINI_API_KEY

**"GEMINI_API_KEY environment variable is required"**
- Edit your .env file and add your API key
- Restart services: `docker compose restart`

**Container fails to start**
- Check logs: `docker compose logs gemini-mcp`
- Ensure Docker has enough resources (memory/disk space)
- Try rebuilding: `docker compose build --no-cache`

**"spawn ENOENT" or execution issues**
- Verify the container is running: `docker compose ps`
- Check that Docker Desktop is running
- On Windows: Ensure WSL2 is properly configured for Docker

**Testing your Docker setup:**
```bash
# Check if services are running
docker compose ps

# Test manual connection
docker exec -i gemini-mcp-server-gemini-mcp-1 echo "Connection test"

# View logs
docker compose logs -f
```

**Conversation threading not working?**
If you're not seeing follow-up questions from Gemini:
```bash
# Check if Redis is running
docker compose logs redis

# Test conversation memory system
docker exec -i gemini-mcp-server-gemini-mcp-1 python debug_conversation.py

# Check for threading errors in logs
docker compose logs gemini-mcp | grep "threading failed"
```

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Built with the power of **Claude + Gemini** collaboration 🤝
- [MCP (Model Context Protocol)](https://modelcontextprotocol.com) by Anthropic
- [Claude Code](https://claude.ai/code) - Your AI coding assistant
- [Gemini 2.5 Pro](https://ai.google.dev/) - Extended thinking & analysis engine
