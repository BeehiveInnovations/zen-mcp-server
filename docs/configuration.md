# Configuration Guide

This guide covers all configuration options for the Zen MCP Server. The server is configured through environment variables defined in your `.env` file.

## Quick Start Configuration

**Auto Mode (Recommended):** Set `DEFAULT_MODEL=auto` and let Claude intelligently select the best model for each task:

```env
# Basic configuration
DEFAULT_MODEL=auto
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
```

## Complete Configuration Reference

### Required Configuration

**Workspace Root:**

### API Keys (At least one required)

**Important:** Use EITHER OpenRouter OR native APIs, not both! Having both creates ambiguity about which provider serves each model.

**Option 1: Native APIs (Recommended for direct access)**
```env
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
# Get from: https://makersuite.google.com/app/apikey

# OpenAI API  
OPENAI_API_KEY=your_openai_api_key_here
# Get from: https://platform.openai.com/api-keys

# X.AI GROK API
XAI_API_KEY=your_xai_api_key_here
# Get from: https://console.x.ai/
```

**Option 2: OpenRouter (Access multiple models through one API)**
```env
# OpenRouter for unified model access
OPENROUTER_API_KEY=your_openrouter_api_key_here
# Get from: https://openrouter.ai/
# If using OpenRouter, comment out native API keys above
```

**Option 3: Custom API Endpoints (Local models)**
```env
# For Ollama, vLLM, LM Studio, etc.
CUSTOM_API_URL=http://localhost:11434/v1  # Ollama example
CUSTOM_API_KEY=                                      # Empty for Ollama
CUSTOM_MODEL_NAME=llama3.2                          # Default model
```

**Local Model Connection:**
- Use standard localhost URLs since the server runs natively
- Example: `http://localhost:11434/v1` for Ollama

### Model Configuration

**Default Model Selection:**
```env
# Options: 'auto', 'pro', 'flash', 'o3', 'o3-mini', 'o4-mini', etc.
DEFAULT_MODEL=auto  # Claude picks best model for each task (recommended)
```

**Available Models:**
- `auto`: Claude automatically selects the optimal model
- `pro` (Gemini 2.5 Pro): Extended thinking, deep analysis
- `flash` (Gemini 2.0 Flash): Ultra-fast responses  
- `o3`: Strong logical reasoning (200K context)
- `o3-mini`: Balanced speed/quality (200K context)
- `o4-mini`: Latest reasoning model, optimized for shorter contexts
- `grok`: GROK-3 advanced reasoning (131K context)
- Custom models: via OpenRouter or local APIs

### Thinking Mode Configuration

**Default Thinking Mode for ThinkDeep:**
```env
# Only applies to models supporting extended thinking (e.g., Gemini 2.5 Pro)
DEFAULT_THINKING_MODE_THINKDEEP=high

# Available modes and token consumption:
#   minimal: 128 tokens   - Quick analysis, fastest response
#   low:     2,048 tokens - Light reasoning tasks  
#   medium:  8,192 tokens - Balanced reasoning
#   high:    16,384 tokens - Complex analysis (recommended for thinkdeep)
#   max:     32,768 tokens - Maximum reasoning depth
```

### Model Usage Restrictions

Control which models can be used from each provider for cost control, compliance, or standardization:

```env
# Format: Comma-separated list (case-insensitive, whitespace tolerant)
# Empty or unset = all models allowed (default)

# OpenAI model restrictions
OPENAI_ALLOWED_MODELS=o3-mini,o4-mini,mini

# Gemini model restrictions  
GOOGLE_ALLOWED_MODELS=flash,pro

# X.AI GROK model restrictions
XAI_ALLOWED_MODELS=grok-3,grok-3-fast

# OpenRouter model restrictions (affects models via custom provider)
OPENROUTER_ALLOWED_MODELS=opus,sonnet,mistral
```

**Supported Model Names:**

- OpenAI Models: `o3`, `o3-mini`, `o4-mini`, `mini`
- Gemini Models: `gemini-2.5-flash`, `gemini-2.5-pro`, `flash`, `pro`
- X.AI GROK Models: `grok-3`, `grok-3-fast`, `grok`, `grok3`, `grokfast`

### Provider Priority

When multiple providers are configured, the server chooses providers in this priority order:
1. Native APIs (Google/Gemini, OpenAI, X.AI, DIAL)
2. Custom endpoints (local/self-hosted) via `CUSTOM_API_URL`
3. OpenRouter (catch-all unified API)

This mirrors the runtime logic in `providers/registry.py#get_provider_for_model()` and `server.configure_providers()`. Prefer native APIs for direct access; use custom for local models; rely on OpenRouter as the general fallback.

### General Settings

**DISABLED_TOOLS**
- Comma-separated list of tool names to disable at startup. Essential tools (`version`, `listmodels`) cannot be disabled.
```env
# Examples
DISABLED_TOOLS=                 # All tools enabled (default)
DISABLED_TOOLS=debug,tracer    # Disable specific tools
DISABLED_TOOLS=planner,consensus
```

**LOCALE**
- When set, tools will respond in the specified language while maintaining analysis quality. Use IETF tags.
```env
# Examples
LOCALE=fr-FR
LOCALE=ja-JP
LOCALE=
```

### MCP Transport and Large Prompts

The MCP protocol has a combined request+response token limit configured via Claude’s `MAX_MCP_OUTPUT_TOKENS`. The server computes a character-based input limit `MCP_PROMPT_SIZE_LIMIT` (≈ 60% of total tokens × ~4 chars/token) for user input crossing the MCP boundary.

- What is limited: user input text (e.g., request.prompt, prompt.txt), not internal system prompts or file embeddings.
- If user input exceeds `MCP_PROMPT_SIZE_LIMIT`, the server instructs you to save it as `prompt.txt` and resend it as a file. Internally, tools can still send very large contexts to external models (e.g., 1M tokens for Gemini).

```env
# Optional override: if Claude exposes a different limit
MAX_MCP_OUTPUT_TOKENS=25000
```

### Logging Configuration
```env
# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=DEBUG  # Default: detailed operational messages
```

## Configuration Examples

### Development Setup
```env
# Development with multiple providers
DEFAULT_MODEL=auto
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
XAI_API_KEY=your-xai-key
LOG_LEVEL=DEBUG
CONVERSATION_TIMEOUT_HOURS=1
```

### Production Setup
```env
# Production with cost controls
DEFAULT_MODEL=auto
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
GOOGLE_ALLOWED_MODELS=flash
OPENAI_ALLOWED_MODELS=o4-mini
LOG_LEVEL=INFO
CONVERSATION_TIMEOUT_HOURS=3
```

### Local Development
```env
# Local models only
DEFAULT_MODEL=llama3.2
CUSTOM_API_URL=http://localhost:11434/v1
CUSTOM_API_KEY=
CUSTOM_MODEL_NAME=llama3.2
LOG_LEVEL=DEBUG
```

### OpenRouter Only
```env
# Single API for multiple models
DEFAULT_MODEL=auto
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_ALLOWED_MODELS=opus,sonnet,gpt-4
LOG_LEVEL=INFO
```

## Related Documentation

- **[Advanced Usage Guide](advanced-usage.md)** - Advanced model usage patterns, thinking modes, and power user workflows
- **[Context Revival Guide](context-revival.md)** - Conversation persistence and context revival across sessions
- **[AI-to-AI Collaboration Guide](ai-collaboration.md)** - Multi-model coordination and conversation threading