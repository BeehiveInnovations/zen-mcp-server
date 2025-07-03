# Research Tool - Fast Web Research & Technical Investigation

**Rapid technical research and information gathering using Perplexity Sonar and other advanced models**

The `research` tool enables fast, targeted web research for technical questions, troubleshooting, and current developments. It leverages Perplexity Sonar and other advanced models to provide up-to-date answers, code examples, and best practices from the web, including Stack Overflow, GitHub, documentation sites, and more.

This tool is particularly powerful for:
- Getting current information on rapidly evolving technologies
- Finding solutions to specific error messages or technical problems
- Researching best practices and industry standards
- Comparing different approaches or technologies
- Discovering new libraries, frameworks, or tools
- Understanding complex technical concepts with real-world examples

## Example Prompts

```
Research the latest best practices for securing FastAPI applications
```

```
Find recent solutions for Python 'ModuleNotFoundError' when using poetry
```

```
What are the most common causes of 'database is locked' errors in SQLite?
```

```
Compare the performance characteristics of Redis vs Memcached for session storage
```

```
Find examples of implementing OAuth2 with PKCE in React applications
```

```
Research domain:github.com: What are the most popular Python libraries for machine learning in 2025?
```

## How It Works

The research tool sends your query to Perplexity Sonar (or another selected model) to perform a web search and synthesize relevant, up-to-date information. It can:

- Summarize documentation, blog posts, and Q&A threads
- Provide code snippets and configuration examples
- Suggest related questions for further investigation
- Filter results by domain (e.g., only Stack Overflow or GitHub)
- Return answers with references and links when available

**Key Features:**
- **Fast, focused research** for technical and coding questions
- **Domain filtering** to target or exclude specific sites
- **Recency filtering** to get the most current information
- **Related questions** to expand your investigation
- **Multi-model support** (Perplexity, Gemini, etc.)
- **Integration with other tools** for deeper analysis

## Tool Parameters

**Core Parameters:**
- `query`: The research question or topic (required) - Be as specific as possible for better results
- `model`: AI model to use for research (see Model Selection below)

**Search Control:**
- `domain_filter`: List of domains to include or exclude (optional)
  - Include specific domains: `['stackoverflow.com', 'github.com']`
  - Exclude domains: `['-reddit.com', '-quora.com']` (use '-' prefix)
- `recency_filter`: How recent the information should be
  - Options: `hour`, `day`, `week`, `month`, `year`
  - Useful for getting the latest updates or avoiding outdated information
- `search_mode`: Quality vs speed trade-off
  - `web`: Comprehensive web search (slowest, most thorough)
  - `high`: Detailed search with good coverage (recommended for complex topics)
  - `medium`: Balanced speed and quality (default, good for most cases)
  - `low`: Fast search for quick answers

**Output Control:**
- `return_related_questions`: Include suggested follow-up questions (boolean)
- `max_tokens`: Maximum response length (100-4096, higher = more detailed)

**Context Integration:**
- `files`: Optional code files for context (provide full absolute paths)
- `images`: Optional images for visual context (diagrams, screenshots, etc.)
- `use_websearch`: Enable/disable web search functionality (default: true)

**Advanced Parameters:**
- `continuation_id`: Continue a previous research thread
- `temperature`: Response creativity (0.0-1.0, lower = more focused)
- `thinking_mode`: Depth of analysis (minimal, low, medium, high, max)

## Model Selection

The research tool supports multiple AI models optimized for different research scenarios:

**Perplexity Models (Recommended for most research):**
- `sonar` / `perplexity`: Fast search-augmented model (127K context)
- `sonar-pro` / `perplexity-pro`: High-quality search with better analysis (127K context) 
- `sonar-reasoning` / `perplexity-reasoning`: Advanced reasoning with search capabilities (127K context)
- `sonar-reasoning-pro` / `perplexity-reasoning-pro`: Enterprise-grade reasoning with search (127K context)
- `sonar-deep-research` / `deep-research`: Deep research for comprehensive analysis (127K context)
- `r1` / `r1-1776`: DeepSeek R1 model, offline (no web search), pure reasoning (127K context)

**Other Models:**
- `gemini-2.5-flash` / `flash`: Ultra-fast responses (1M context) - good for quick research
- `gemini-2.5-pro` / `pro`: Deep analysis with thinking mode (1M context) - best for complex topics
- Custom models configured in your environment

**Model Recommendations:**
- **Quick answers**: `sonar` or `flash`
- **Comprehensive research**: `sonar-pro` or `sonar-deep-research`
- **Complex analysis**: `sonar-reasoning-pro` or `gemini-2.5-pro`
- **Pure reasoning (no web)**: `r1-1776`

## Usage Examples

**General Research:**
```
Research the pros and cons of using SQLite vs PostgreSQL for production web apps
```

**Error Troubleshooting:**
```
Find solutions for 'TypeError: cannot unpack non-iterable NoneType object' in Python
```

**Best Practices:**
```
What are the recommended ways to structure large Python projects?
```

**Domain-Specific Research:**
```
Research only on stackoverflow.com: How to mock HTTP requests in pytest
```

**Exclude Certain Domains:**
```
Research excluding reddit.com and quora.com: Best practices for Docker security
```

**Recency Filtering:**
```
Find the latest (past month) updates on Django async support
```

**With Context Files:**
```
Research authentication patterns for FastAPI, using this code as context: /path/to/auth.py
```

**Model-Specific Research:**
```
Use sonar-deep-research to analyze the current state of WebAssembly performance
```

**Multiple Related Questions:**
```
Research rate limiting strategies and return related questions for follow-up
```

## Configuration

The research tool can be configured through environment variables in your `.env` file:

```bash
# ===========================================
# Research Tool Configuration
# ===========================================

# Default model to use for research queries
# Options: sonar, sonar-pro, sonar-reasoning, sonar-reasoning-pro, sonar-deep-research, r1-1776
# Perplexity models are recommended for web research
RESEARCH_DEFAULT_MODEL=sonar-pro

# Default search mode balancing speed vs quality
# Options: web (most thorough), high (detailed), medium (balanced), low (fastest)
RESEARCH_DEFAULT_SEARCH_MODE=medium

# Default maximum tokens for research responses
# Range: 100-4096, higher values provide more detailed responses
RESEARCH_DEFAULT_MAX_TOKENS=2048

# Automatically export research results to markdown files
# Set to true to save all research queries and results for future reference
RESEARCH_EXPORT_TO_MD=false

# Directory for research exports (relative to project root)
# Research results will be saved as timestamped markdown files
RESEARCH_EXPORT_DIR=research_exports
```

**Configuration Details:**

- **RESEARCH_DEFAULT_MODEL**: Sets the default AI model for research. Perplexity models (`sonar-*`) are optimized for web research with real-time information access. Choose `sonar-pro` for balanced performance or `sonar-deep-research` for comprehensive analysis.

- **RESEARCH_DEFAULT_SEARCH_MODE**: Controls the trade-off between search quality and response speed:
  - `web`: Most comprehensive search, slower but thorough
  - `high`: Detailed search with good coverage, recommended for complex topics
  - `medium`: Balanced approach, good for most use cases (default)
  - `low`: Fast responses for simple queries

- **RESEARCH_DEFAULT_MAX_TOKENS**: Determines response length. Higher values allow for more detailed explanations and code examples but consume more API credits.

- **RESEARCH_EXPORT_TO_MD**: When enabled, automatically saves research queries and results to markdown files for documentation and future reference.

- **RESEARCH_EXPORT_DIR**: Specifies where exported research files are saved. Files are named with timestamps for easy organization.

## Advanced Features

## Advanced Features

**Research Pipeline:**
The tool supports the `research_pipeline` feature for conducting multi-step research investigations:
```
Execute a research pipeline on microservices architecture:
1. Current best practices for service communication
2. Common pitfalls in microservices deployment 
3. Monitoring and observability strategies
```

**Contextual Research:**
Provide code files or error logs as context for more targeted research:
```
Research authentication issues with this FastAPI code: /path/to/auth.py
```

**Domain Filtering Strategies:**
- **Include specific sites**: `['stackoverflow.com', 'github.com', 'docs.python.org']`
- **Exclude low-quality sources**: `['-quora.com', '-yahoo.com']`
- **Academic focus**: `['arxiv.org', 'scholar.google.com', 'researchgate.net']`
- **Official documentation only**: `['docs.python.org', 'nodejs.org', 'reactjs.org']`

**Time-Sensitive Research:**
- Use `recency_filter: 'month'` for rapidly evolving technologies (AI/ML, web frameworks)
- Use `recency_filter: 'week'` for breaking changes or security vulnerabilities
- Use `recency_filter: 'day'` for very recent issues or announcements

**Integration with Other Tools:**
- Follow up research with `debug` tool for systematic investigation
- Use `analyze` tool to examine code patterns discovered through research
- Combine with `codereview` to validate research findings against your codebase

**Export and Documentation:**
When `RESEARCH_EXPORT_TO_MD=true`, research results are automatically saved with:
- Timestamp and query information
- Full research results with sources
- Related questions for future investigation
- Organized file structure for easy reference

## When to Use Research vs Other Tools

- **Use `research`** for: Fast answers to technical questions, troubleshooting unknown issues, discovering new technologies, comparing approaches, getting current best practices
- **Use `debug`** for: Systematic investigation of specific errors or bugs in your existing codebase
- **Use `analyze`** for: Deep analysis of your own code structure and architectural patterns
- **Use `codereview`** for: Comprehensive security and quality reviews of your code
- **Use `chat`** for: General discussions and brainstorming without requiring web search

**Research Tool Decision Matrix:**

| Scenario | Best Tool | Why |
|----------|-----------|-----|
| "How do I fix this error?" | `research` → `debug` | Research solutions, then debug systematically |
| "What's the best library for X?" | `research` | Current recommendations and comparisons |
| "Is my code secure?" | `codereview` | Systematic security analysis |
| "Why is my app slow?" | `debug` or `analyze` | Investigate specific performance issues |
| "How does this framework work?" | `research` | Learn concepts and best practices |
| "Should I refactor this code?" | `analyze` → `research` | Analyze current code, research patterns |

## Research Example

**Prompt:**
```
Research the most effective strategies for handling rate limiting in REST APIs, focusing on recent developments
```

**Configuration Used:**
- Model: `sonar-pro` (high-quality search)
- Search Mode: `high` (detailed coverage)
- Recency Filter: `month` (recent developments)
- Max Tokens: `2048` (comprehensive response)

**Sample Result:**
The research would return:
- **Current Best Practices**: Token bucket, sliding window, distributed rate limiting patterns
- **Recent Developments**: New algorithms like sliding window counters, Redis-based solutions
- **Code Examples**: Implementation patterns in Python, Node.js, and Go
- **Performance Comparisons**: Benchmarks between different approaches
- **Industry Standards**: How major APIs (GitHub, Twitter, Google) handle rate limiting
- **Sources**: Links to Stack Overflow discussions, GitHub repositories, and technical blogs
- **Related Questions**: 
  - "How to test rate limiting in integration tests?"
  - "What are the best Redis patterns for distributed rate limiting?"
  - "How to handle rate limiting in microservices architectures?"

**Follow-up Research:**
```
Research distributed rate limiting patterns with Redis, excluding tutorial sites
```

This demonstrates how the tool provides comprehensive, current information with actionable insights and suggests logical next steps for deeper investigation.

## Best Practices

**Writing Effective Research Queries:**
- Be specific about your context (language, framework, use case)
- Include error messages or specific problems when troubleshooting
- Specify if you want current/recent information vs general concepts
- Mention your experience level if relevant (beginner, intermediate, expert)

**Optimizing Results:**
- Use domain filtering to focus on high-quality sources
- Set appropriate recency filters for rapidly changing technologies
- Choose the right model for your needs (speed vs depth)
- Follow up with related questions for comprehensive understanding

**Integration Workflow:**
1. **Research** for understanding and options
2. **Analyze** your current code for compatibility
3. **Debug** any implementation issues
4. **Codereview** the final solution
