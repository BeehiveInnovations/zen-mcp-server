# Zen MCP: One Context. Many Minds.

https://github.com/user-attachments/assets/8097e18e-b926-4d8b-ba14-a979e4c58bda

<div align="center">  
  <b>🤖 Claude + [Gemini / O3 / OpenRouter / Ollama / Any Model] = Your Ultimate AI Development Team</b>
</div>

<br/>

The ultimate development partners for Claude - a Model Context Protocol server that gives Claude access to multiple AI models for enhanced code analysis, 
problem-solving, and collaborative development.

**Features true AI orchestration with conversations that continue across tasks** - Give Claude a complex
task and let it orchestrate between models automatically. Claude stays in control, performs the actual work, 
but gets perspectives from the best AI for each subtask. Claude can switch between different tools _and_ models mid-conversation, 
with context carrying forward seamlessly.

**Example Workflow - Claude Code:**
1. Performs its own reasoning
2. Uses Gemini Pro to deeply [`analyze`](#6-analyze---smart-file-analysis) the code in question for a second opinion
3. Switches to O3 to continue [`chatting`](#1-chat---general-development-chat--collaborative-thinking) about its findings 
4. Uses Flash to evaluate formatting suggestions from O3
5. Performs the actual work after taking in feedback from all three
6. Returns to Pro for a [`precommit`](#4-precommit---pre-commit-validation) review

All within a single conversation thread! Gemini Pro in step 6 _knows_ what was recommended by O3 in step 3! Taking that context
and review into consideration to aid with its pre-commit review.

**Think of it as Claude Code _for_ Claude Code.** This MCP isn't magic. It's just **super-glue**.

> **Remember:** Claude stays in full control — but **YOU** call the shots. 
> Zen is designed to only encourage Claude to talk to other models when necessary.  
> **You're** the one who crafts the powerful prompt so that Claude brings in Gemini, Flash, O3 — or fly solo.  
> You're the guide. The prompter. The puppeteer. 
> ##### You are AI - **Actually Intelligent**.

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

- **Advanced Usage**
  - [Advanced Features](#advanced-features) - AI-to-AI conversations, large prompts, web search
  - [Complete Advanced Guide](docs/advanced-usage.md) - Model configuration, thinking modes, workflows, tool parameters

- **Setup & Support**
  - [Troubleshooting Guide](docs/troubleshooting.md) - Common issues and debugging steps
  - [License](#license) - Apache 2.0

## Why This Server?

Claude is brilliant, but sometimes you need:
- **Multiple AI perspectives** - Let Claude orchestrate between different models to get the best analysis
- **Automatic model selection** - Claude picks the right model for each task (or you can specify)
- **A senior developer partner** to validate and extend ideas ([`chat`](#1-chat---general-development-chat--collaborative-thinking))
- **A second opinion** on complex architectural decisions - augment Claude's thinking with perspectives from Gemini Pro, O3, or [dozens of other models via custom endpoints](docs/custom_models.md) ([`thinkdeep`](#2-thinkdeep---extended-reasoning-partner))
- **Professional code reviews** with actionable feedback across entire repositories ([`codereview`](#3-codereview---professional-code-review))
- **Pre-commit validation** with deep analysis using the best model for the job ([`precommit`](#4-precommit---pre-commit-validation))
- **Expert debugging** - O3 for logical issues, Gemini for architectural problems ([`debug`](#5-debug---expert-debugging-assistant))
- **Extended context windows beyond Claude's limits** - Delegate analysis to Gemini (1M tokens) or O3 (200K tokens) for entire codebases, large datasets, or comprehensive documentation
- **Model-specific strengths** - Extended thinking with Gemini Pro, fast iteration with Flash, strong reasoning with O3, local privacy with Ollama
- **Local model support** - Run models like Llama 3.2 locally via Ollama, vLLM, or LM Studio for privacy and cost control
- **Dynamic collaboration** - Models can request additional context and follow-up replies from Claude mid-analysis
- **Smart file handling** - Automatically expands directories, manages token limits based on model capacity
- **[Bypass MCP's token limits](docs/advanced-usage.md#working-with-large-prompts)** - Work around MCP's 25K limit automatically

This server orchestrates multiple AI models as your development team, with Claude automatically selecting the best model for each task or allowing you to choose specific models for different strengths.

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

### 1. Get API Keys (at least one required)

**Option A: OpenRouter (Access multiple models with one API)**
- **OpenRouter**: Visit [OpenRouter](https://openrouter.ai/) for access to multiple models through one API. [Setup Guide](docs/custom_models.md)
  - Control model access and spending limits directly in your OpenRouter dashboard
  - Configure model aliases in [`conf/custom_models.json`](conf/custom_models.json)

**Option B: Native APIs**
- **Gemini**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey) and generate an API key. For best results with Gemini 2.5 Pro, use a paid API key as the free tier has limited access to the latest models.
- **OpenAI**: Visit [OpenAI Platform](https://platform.openai.com/api-keys) to get an API key for O3 model access.

**Option C: Custom API Endpoints (Local models like Ollama, vLLM)**
[Please see the setup guide](docs/custom_models.md#option-2-custom-api-setup-ollama-vllm-etc). With a custom API you can use:
- **Ollama**: Run models like Llama 3.2 locally for free inference
- **vLLM**: Self-hosted inference server for high-throughput inference
- **LM Studio**: Local model hosting with OpenAI-compatible API interface
- **Text Generation WebUI**: Popular local interface for running models
- **Any OpenAI-compatible API**: Custom endpoints for your own infrastructure

> **Note:** Using all three options may create ambiguity about which provider / model to use if there is an overlap. 
> If all APIs are configured, native APIs will take priority when there is a clash in model name, such as for `gemini` and `o3`.
> Configure your model aliases and give them unique names in [`conf/custom_models.json`](conf/custom_models.json)

### 2. Clone and Set Up

```bash
# Clone to your preferred location
git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
cd zen-mcp-server

# One-command setup (includes Redis for AI conversations)
./run-server.sh
```

**What this does:**
- **Builds Docker images** with all dependencies (including Redis for conversation threading)
- **Creates .env file** (automatically uses `$GEMINI_API_KEY` and `$OPENAI_API_KEY` if set in environment)
- **Starts Redis service** for AI-to-AI conversation memory
- **Starts MCP server** with providers based on available API keys
- **Adds Zen to Claude Code automatically**

### 3. Add Your API Keys

```bash
# Edit .env to add your API keys (if not already set in environment)
nano .env

# The file will contain, at least one should be set:
# GEMINI_API_KEY=your-gemini-api-key-here  # For Gemini models
# OPENAI_API_KEY=your-openai-api-key-here  # For O3 model
# OPENROUTER_API_KEY=your-openrouter-key  # For OpenRouter (see docs/custom_models.md)

# For local models (Ollama, vLLM, etc.) - Note: Use host.docker.internal for Docker networking:
# CUSTOM_API_URL=http://host.docker.internal:11434/v1  # Ollama example (NOT localhost!)
# CUSTOM_API_KEY=                                      # Empty for Ollama
# CUSTOM_MODEL_NAME=llama3.2                          # Default model

# WORKSPACE_ROOT=/Users/your-username  (automatically configured)

# Note: At least one API key OR custom URL is required

# After making changes to .env, restart the server:
# ./run-server.sh
```

### 4. Configure Claude

#### If Setting up for Claude Code
Run the following commands on the terminal to add the MCP directly to Claude Code
```bash
# Add the MCP server directly via Claude Code CLI
claude mcp add zen -s user -- docker exec -i zen-mcp-server python server.py

# List your MCP servers to verify
claude mcp list

# Remove when needed
claude mcp remove zen -s user

# You may need to remove an older version of this MCP after it was renamed:
claude mcp remove gemini -s user
```
Now run `claude` on the terminal for it to connect to the newly added mcp server. If you were already running a `claude` code session,
please exit and start a new session.

#### If Setting up for Claude Desktop

- Open Claude Desktop
- Go to **Settings** → **Developer** → **Edit Config**

This will open a folder revealing `claude_desktop_config.json`.

2. ** Update Docker Configuration**

The setup script shows you the exact configuration. It looks like this. When you ran `run-server.sh` it should
have produced a configuration for you to copy:

```json
{
  "mcpServers": {
    "zen": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "zen-mcp-server",
        "python",
        "server.py"
      ]
    }
  }
}
```

Paste the above into `claude_desktop_config.json`. If you have several other MCP servers listed, simply add this below the rest after a `,` comma:
```json
  ... other mcp servers ... ,

  "zen": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "zen-mcp-server",
        "python",
        "server.py"
      ]
  }
```

3. **Restart Claude Desktop**
Completely quit and restart Claude Desktop for the changes to take effect.

### 5. Start Using It!

Just ask Claude naturally:
- "Think deeper about this architecture design with zen" → Claude picks best model + `thinkdeep`
- "Using zen perform a code review of this code for security issues" → Claude might pick Gemini Pro + `codereview`
- "Use zen and debug why this test is failing, the bug might be in my_class.swift" → Claude might pick O3 + `debug`
- "With zen, analyze these files to understand the data flow" → Claude picks appropriate model + `analyze`
- "Use flash to suggest how to format this code based on the specs mentioned in policy.md" → Uses Gemini Flash specifically
- "Think deeply about this and get o3 to debug this logic error I found in the checkOrders() function" → Uses O3 specifically
- "Brainstorm scaling strategies with pro. Study the code, pick your preferred strategy and debate with pro to settle on two best approaches" → Uses Gemini Pro specifically
- "Use local-llama to localize and add missing translations to this project" → Uses local Llama 3.2 via custom URL
- "First use local-llama for a quick local analysis, then use opus for a thorough security review" → Uses both providers in sequence

## Available Tools

**Quick Tool Selection Guide:**
- **Need a thinking partner?** → `chat` (brainstorm ideas, get second opinions, validate approaches)
- **Need deeper thinking?** → `thinkdeep` (extends analysis, finds edge cases)
- **Code needs review?** → `codereview` (bugs, security, performance issues)
- **Pre-commit validation?** → `precommit` (validate git changes before committing)
- **Something's broken?** → `debug` (root cause analysis, error tracing)
- **Want to understand code?** → `analyze` (architecture, patterns, dependencies)
- **Server info?** → `get_version` (version and configuration details)

**Auto Mode:** When `DEFAULT_MODEL=auto`, Claude automatically picks the best model for each task. You can override with: "Use flash for quick analysis" or "Use o3 to debug this".

**Model Selection Examples:**
- Complex architecture review → Claude picks Gemini Pro
- Quick formatting check → Claude picks Flash
- Logical debugging → Claude picks O3
- General explanations → Claude picks Flash for speed
- Local analysis → Claude picks your Ollama model

**Pro Tip:** Thinking modes (for Gemini models) control depth vs token cost. Use "minimal" or "low" for quick tasks, "high" or "max" for complex problems. [Learn more](docs/advanced-usage.md#thinking-modes)

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

#### Example Prompt:

```
Chat with zen and pick the best model for this job. I need to pick between Redis and Memcached for session storage 
and I need an expert opinion for the project I'm working on. Get a good idea of what the project does, pick one of the two options
and then debate with the other models to give me a final verdict
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

#### Example Prompt:

```
Think deeper about my authentication design with pro using max thinking mode and brainstorm to come up 
with the best architecture for my project
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

```
Perform a codereview with gemini pro and review auth.py for security issues and potential vulnerabilities.
I need an actionable plan but break it down into smaller quick-wins that we can implement and test rapidly 
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

**Prompt Used:**
```
Now use gemini and perform a review and precommit and ensure original requirements are met, no duplication of code or
logic, everything should work as expected
```

How beautiful is that? Claude used `precommit` twice and `codereview` once and actually found and fixed two critical errors before commit!

#### Example Prompts:

```
Use zen and perform a thorough precommit ensuring there aren't any new regressions or bugs introduced
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

**Key Features:**
- Analyzes single files or entire directories
- Supports specialized analysis types: architecture, performance, security, quality
- Uses file paths (not content) for clean terminal output
- Can identify patterns, anti-patterns, and refactoring opportunities
- **Web search capability**: When enabled with `use_websearch` (default: true), the model can request Claude to perform web searches and share results back to enhance analysis with current documentation, design patterns, and best practices
### 7. `get_version` - Server Information
```
"Get zen to show its version"
```

For detailed tool parameters and configuration options, see the [Advanced Usage Guide](docs/advanced-usage.md).



## Advanced Features

### AI-to-AI Conversation Threading

This server enables **true AI collaboration** between Claude and multiple AI models (Gemini, O3), where they can coordinate and question each other's approaches:

**How it works:**
- **Gemini can ask Claude follow-up questions** to clarify requirements or gather more context
- **Claude can respond** with additional information, files, or refined instructions
- **Claude can work independently** between exchanges - implementing solutions, gathering data, or performing analysis
- **Claude can return to Gemini** with progress updates and new context for further collaboration
- **Cross-tool continuation** - Start with one tool (e.g., `analyze`) and continue with another (e.g., `codereview`) using the same conversation thread
- **Both AIs coordinate their approaches** - questioning assumptions, validating solutions, and building on each other's insights
- Each conversation maintains full context while only sending incremental updates
- Conversations are automatically managed with Redis for persistence

**Example of Multi-Model AI Coordination:**
1. You: "Debate SwiftUI vs UIKit - which is better for iOS development?"
2. Claude (auto mode): "I'll orchestrate a debate between different models for diverse perspectives."
3. Gemini Pro: "From an architectural standpoint, SwiftUI's declarative paradigm and state management make it superior for maintainable, modern apps."
4. O3: "Logically analyzing the trade-offs: UIKit offers 15+ years of stability, complete control, and proven scalability. SwiftUI has <5 years maturity with ongoing breaking changes."
5. Claude: "Let me get Flash's quick take on developer experience..."
6. Gemini Flash: "SwiftUI = faster development, less code, better previews. UIKit = more control, better debugging, stable APIs."
7. **Claude's synthesis**: "Based on the multi-model analysis: Use SwiftUI for new projects prioritizing development speed, UIKit for apps requiring fine control or supporting older iOS versions."

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

**Cross-tool & Cross-Model Continuation Example:**
```
1. Claude: "Analyze /src/auth.py for security issues"
   → Auto mode: Claude picks Gemini Pro for deep security analysis
   → Pro analyzes and finds vulnerabilities, provides continuation_id

2. Claude: "Review the authentication logic thoroughly"
   → Uses same continuation_id, but Claude picks O3 for logical analysis
   → O3 sees previous Pro analysis and provides logic-focused review

3. Claude: "Debug the auth test failures"
   → Same continuation_id, Claude keeps O3 for debugging
   → O3 provides targeted debugging with full context from both previous analyses

4. Claude: "Quick style check before committing"
   → Same thread, but Claude switches to Flash for speed
   → Flash quickly validates formatting with awareness of all previous fixes
```

For more advanced features like working with large prompts and dynamic context requests, see the [Advanced Usage Guide](docs/advanced-usage.md).


## Configuration

**Auto Mode (Recommended):** Set `DEFAULT_MODEL=auto` in your .env file and Claude will intelligently select the best model for each task.

```env
# .env file
DEFAULT_MODEL=auto  # Claude picks the best model automatically

# API Keys (at least one required)
GEMINI_API_KEY=your-gemini-key    # Enables Gemini Pro & Flash
OPENAI_API_KEY=your-openai-key    # Enables O3, O3mini, O4-mini, O4-mini-high
```

**Available Models:**
- **`pro`** (Gemini 2.5 Pro): Extended thinking, deep analysis
- **`flash`** (Gemini 2.0 Flash): Ultra-fast responses
- **`o3`**: Strong logical reasoning  
- **`o3mini`**: Balanced speed/quality
- **`o4-mini`**: Latest reasoning model, optimized for shorter contexts
- **`o4-mini-high`**: Enhanced O4 with higher reasoning effort
- **Custom models**: via OpenRouter or local APIs (Ollama, vLLM, etc.)

For detailed configuration options, see the [Advanced Usage Guide](docs/advanced-usage.md).

## Testing

For information on running tests and contributing, see the [Testing Guide](docs/testing.md).

## License

Apache 2.0 License - see LICENSE file for details.

## Acknowledgments

Built with the power of **Multi-Model AI** collaboration 🤝
- [MCP (Model Context Protocol)](https://modelcontextprotocol.com) by Anthropic
- [Claude Code](https://claude.ai/code) - Your AI coding assistant & orchestrator
- [Gemini 2.5 Pro & 2.0 Flash](https://ai.google.dev/) - Extended thinking & fast analysis
- [OpenAI O3](https://openai.com/) - Strong reasoning & general intelligence