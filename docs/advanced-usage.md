# Advanced Usage Guide

This guide covers advanced features, configuration options, and workflows for power users of the Zen MCP server.

## Table of Contents

- [Model Configuration](#model-configuration)
- [Thinking Modes](#thinking-modes)
- [Tool Parameters](#tool-parameters)
- [Collaborative Workflows](#collaborative-workflows)
- [Working with Large Prompts](#working-with-large-prompts)
- [Web Search Integration](#web-search-integration)
- [System Prompts](#system-prompts)

## Model Configuration

**Auto Mode (Recommended):**
Set `DEFAULT_MODEL=auto` in your .env file and Claude will intelligently select the best model for each task:

```env
# .env file
DEFAULT_MODEL=auto  # Claude picks the best model automatically

# API Keys (at least one required)
GEMINI_API_KEY=your-gemini-key    # Enables Gemini Pro & Flash
OPENAI_API_KEY=your-openai-key    # Enables O3, O3-mini
```

**How Auto Mode Works:**
- Claude analyzes each request and selects the optimal model
- Model selection is based on task complexity, requirements, and model strengths
- You can always override: "Use flash for quick check" or "Use o3 to debug"

**Supported Models & When Claude Uses Them:**

| Model | Provider | Context | Strengths | Auto Mode Usage |
|-------|----------|---------|-----------|------------------|
| **`pro`** (Gemini 2.5 Pro) | Google | 1M tokens | Extended thinking (up to 32K tokens), deep analysis | Complex architecture, security reviews, deep debugging |
| **`flash`** (Gemini 2.0 Flash) | Google | 1M tokens | Ultra-fast responses | Quick checks, formatting, simple analysis |
| **`o3`** | OpenAI | 200K tokens | Strong logical reasoning | Debugging logic errors, systematic analysis |
| **`o3-mini`** | OpenAI | 200K tokens | Balanced speed/quality | Moderate complexity tasks |
| **`llama`** (Llama 3.2) | Custom/Local | 128K tokens | Local inference, privacy | On-device analysis, cost-free processing |
| **Any model** | OpenRouter | Varies | Access to GPT-4, Claude, Llama, etc. | User-specified or based on task requirements |

**Mix & Match Providers:** Use multiple providers simultaneously! Set both `OPENROUTER_API_KEY` and `CUSTOM_API_URL` to access 
cloud models (expensive/powerful) AND local models (free/private) in the same conversation.

**Manual Model Selection:**
You can specify a default model instead of auto mode:

```env
# Use a specific model by default
DEFAULT_MODEL=gemini-2.5-pro-preview-06-05  # Always use Gemini Pro
DEFAULT_MODEL=flash                         # Always use Flash
DEFAULT_MODEL=o3                           # Always use O3
```

**Per-Request Model Override:**
Regardless of your default setting, you can specify models per request:
- "Use **pro** for deep security analysis of auth.py"
- "Use **flash** to quickly format this code"
- "Use **o3** to debug this logic error"
- "Review with **o3-mini** for balanced analysis"

**Model Capabilities:**
- **Gemini Models**: Support thinking modes (minimal to max), web search, 1M context
- **O3 Models**: Excellent reasoning, systematic analysis, 200K context

## Thinking Modes

**Claude automatically manages thinking modes based on task complexity**, but you can also manually control Gemini's reasoning depth to balance between response quality and token consumption. Each thinking mode uses a different amount of tokens, directly affecting API costs and response time.

### Thinking Modes & Token Budgets

These only apply to models that support customizing token usage for extended thinking, such as Gemini 2.5 Pro.

| Mode | Token Budget | Use Case | Cost Impact |
|------|-------------|----------|-------------|
| `minimal` | 128 tokens | Simple, straightforward tasks | Lowest cost |
| `low` | 2,048 tokens | Basic reasoning tasks | 16x more than minimal |
| `medium` | 8,192 tokens | **Default** - Most development tasks | 64x more than minimal |
| `high` | 16,384 tokens | Complex problems requiring thorough analysis (default for `thinkdeep`) | 128x more than minimal |
| `max` | 32,768 tokens | Exhaustive reasoning | 256x more than minimal |

### How to Use Thinking Modes

**Claude automatically selects appropriate thinking modes**, but you can override this by explicitly requesting a specific mode in your prompts. Remember: higher thinking modes = more tokens = higher cost but better quality:

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
# Quick style check with o3
"Use flash to review formatting in utils.py"

# Security audit with o3
"Get o3 to do a security review of auth/ with thinking mode high"

# Complex debugging, letting claude pick the best model
"Use zen to debug this race condition with max thinking mode"

# Architecture analysis with Gemini 2.5 Pro
"Analyze the entire src/ directory architecture with high thinking using pro"
```

## Tool Parameters

All tools that work with files support **both individual files and entire directories**. The server automatically expands directories, filters for relevant code files, and manages token limits.

### File-Processing Tools

**`analyze`** - Analyze files or directories
- `files`: List of file paths or directories (required)
- `question`: What to analyze (required)  
- `model`: auto|pro|flash|o3|o3-mini (default: server default)
- `analysis_type`: architecture|performance|security|quality|general
- `output_format`: summary|detailed|actionable
- `thinking_mode`: minimal|low|medium|high|max (default: medium, Gemini only)
- `use_websearch`: Enable web search for documentation and best practices - allows model to request Claude perform searches (default: true)

```
"Analyze the src/ directory for architectural patterns" (auto mode picks best model)
"Use flash to quickly analyze main.py and tests/ to understand test coverage" 
"Use o3 for logical analysis of the algorithm in backend/core.py"
"Use pro for deep analysis of the entire backend/ directory structure"
```

**`codereview`** - Review code files or directories
- `files`: List of file paths or directories (required)
- `model`: auto|pro|flash|o3|o3-mini (default: server default)
- `review_type`: full|security|performance|quick
- `focus_on`: Specific aspects to focus on
- `standards`: Coding standards to enforce
- `severity_filter`: critical|high|medium|all
- `thinking_mode`: minimal|low|medium|high|max (default: medium, Gemini only)

```
"Review the entire api/ directory for security issues" (auto mode picks best model)
"Use pro to review auth/ for deep security analysis"
"Use o3 to review logic in algorithms/ for correctness"
"Use flash to quickly review src/ with focus on performance, only show critical issues"
```

**`debug`** - Debug with file context
- `error_description`: Description of the issue (required)
- `model`: auto|pro|flash|o3|o3-mini (default: server default)
- `error_context`: Stack trace or logs
- `files`: Files or directories related to the issue
- `runtime_info`: Environment details
- `previous_attempts`: What you've tried
- `thinking_mode`: minimal|low|medium|high|max (default: medium, Gemini only)
- `use_websearch`: Enable web search for error messages and solutions - allows model to request Claude perform searches (default: true)

```
"Debug this logic error with context from backend/" (auto mode picks best model)
"Use o3 to debug this algorithm correctness issue"
"Use pro to debug this complex architecture problem"
```

**`thinkdeep`** - Extended analysis with file context
- `current_analysis`: Your current thinking (required)
- `model`: auto|pro|flash|o3|o3-mini (default: server default)
- `problem_context`: Additional context
- `focus_areas`: Specific aspects to focus on
- `files`: Files or directories for context
- `thinking_mode`: minimal|low|medium|high|max (default: max, Gemini only)
- `use_websearch`: Enable web search for documentation and insights - allows model to request Claude perform searches (default: true)

```
"Think deeper about my design with reference to src/models/" (auto mode picks best model)
"Use pro to think deeper about this architecture with extended thinking"
"Use o3 to think deeper about the logical flow in this algorithm"
```

## Collaborative Workflows

### Design → Review → Implement
```
Think hard about designing and developing a fun calculator app in swift. Review your design plans with o3, taking in
their suggestions but keep the feature-set realistic and doable without adding bloat. Begin implementing and in between
implementation, get a codereview done by Gemini Pro and chat with Flash if you need to for creative directions.   
```

### Code → Review → Fix
```
Implement a new screen where the locations taken from the database display on a map, with pins falling from
the top and landing with animation. Once done, codereview with gemini pro and o3 both and ask them to critique your
work. Fix medium to critical bugs / concerns / issues and show me the final product
```

### Debug → Analyze → Solution → Precommit Check → Publish
```
Take a look at these log files saved under subfolder/diagnostics.log there's a bug where the user says the app
crashes at launch. Think hard and go over each line, tallying it with corresponding code within the project. After
you've performed initial investigation, ask gemini pro to analyze the log files and the related code where you 
suspect lies the bug and then formulate and implement a bare minimal fix. Must not regress. Perform a precommit
with zen in the end using gemini pro to confirm we're okay to publish the fix 
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

## Working with Large Prompts

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
Zen MCP: "The prompt is too large for MCP's token limits (>50,000 characters). 
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

## Web Search Integration

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

**Web search control:**
Web search is enabled by default, allowing models to request Claude perform searches for current documentation and solutions. If you prefer the model to work only with its training data, you can disable web search:
```
"Use gemini to review this code with use_websearch false"
```

## System Prompts

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