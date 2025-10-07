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
```env

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

# Azure OpenAI API (Responses API - supports GPT-5 and GPT-5-Codex)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-codex
# Get from: https://portal.azure.com/ (Keys and Endpoint section)

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

### Azure OpenAI GPT-5 Models Configuration

Azure OpenAI integration uses the **Responses API** exclusively for GPT-5 and GPT-5-Codex models. These models have specific requirements and constraints that differ from standard OpenAI models.

#### Critical Requirements for GPT-5/GPT-5-Codex

| Requirement | Details | Error if Violated |
|------------|---------|-------------------|
| **API Type** | Responses API ONLY | Chat Completions API not implemented |
| **Temperature** | Must be exactly 1.0 | 400 Error: "Unsupported value. Only the default (1) value is supported" |
| **Min Output Tokens** | Minimum 16 tokens | 400 Error if max_output_tokens < 16 |
| **API Version** | 2025-03-01-preview or later | Responses API not available in older versions |

#### Setup Steps

1. **Create Azure OpenAI Resource:**
   - Navigate to [Azure Portal](https://portal.azure.com/)
   - Create or select an Azure OpenAI resource
   - Request access to GPT-5 or GPT-5-Codex models if needed

2. **Deploy the Model:**
   - Go to "Model deployments" in your Azure OpenAI resource
   - Click "Create new deployment"
   - Select either `gpt-5` or `gpt-5-codex` as the model
   - Choose a deployment name (e.g., `gpt-5-production`)
   - Set capacity (TPM - Tokens Per Minute)

3. **Get Credentials:**
   - Navigate to "Keys and Endpoint" section
   - Copy either KEY 1 or KEY 2
   - Copy the Endpoint URL

4. **Configure Environment Variables:**
   ```env
   # All 4 variables are REQUIRED
   AZURE_OPENAI_API_KEY=your_api_key_from_azure
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_VERSION=2025-04-01-preview  # Minimum version for Responses API
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5  # Your deployment name from Azure Portal
   ```

#### Model Comparison

| Model | Context Window | Max Output | Vision Support | Code Specialization | Intelligence Score | Use Case |
|-------|---------------|------------|----------------|--------------------|--------------------|----------|
| **gpt-5** | 400K tokens | 128K tokens | ✅ Yes | Good | 16 | General purpose reasoning, complex analysis with images |
| **gpt-5-codex** | 400K tokens | 128K tokens | ❌ No | Elite | 17 | Code generation, refactoring, technical documentation |

#### Key Technical Details

**Responses API Specifics:**
- Endpoint: `/openai/deployments/{deployment}/responses`
- Different response format than Chat Completions API
- Supports reasoning tokens (internal thinking process)
- Response extraction from `output_text` or `output` array fields

**Reasoning Tokens:**
- GPT-5 models use internal "reasoning tokens" before generating output
- These tokens are not visible in the response but affect processing time
- Contributes to the model's advanced problem-solving capabilities

**Constraints and Limitations:**
```python
# Temperature MUST be 1.0
temperature = 1.0  # Cannot be changed

# Minimum output tokens
max_output_tokens = max(16, requested_tokens)  # Enforced minimum of 16

# API Version requirement
api_version = "2025-04-01-preview"  # Or later versions
```

#### Example Configurations

**GPT-5 General Purpose:**
```env
AZURE_OPENAI_API_KEY=sk-proj-abc123...
AZURE_OPENAI_ENDPOINT=https://contoso-ai.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-general
DEFAULT_MODEL=gpt-5  # Use GPT-5 as default
```

**GPT-5-Codex for Development:**
```env
AZURE_OPENAI_API_KEY=sk-proj-xyz789...
AZURE_OPENAI_ENDPOINT=https://dev-team.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=codex-production
DEFAULT_MODEL=gpt-5-codex  # Use Codex as default
```

**Multi-Model Setup:**
```env
# You can only have ONE deployment active at a time
# To switch models, change the AZURE_OPENAI_DEPLOYMENT_NAME
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5  # or gpt-5-codex
```

#### Common Configuration Errors

1. **Wrong API Version:**
   ```env
   # ❌ WRONG - Too old for Responses API
   AZURE_OPENAI_API_VERSION=2024-10-01-preview

   # ✅ CORRECT
   AZURE_OPENAI_API_VERSION=2025-04-01-preview
   ```

2. **Incorrect Endpoint Format:**
   ```env
   # ❌ WRONG - Missing https://
   AZURE_OPENAI_ENDPOINT=your-resource.openai.azure.com/

   # ✅ CORRECT
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   ```

3. **Temperature Modification Attempts:**
   ```python
   # ❌ This will cause a 400 error
   # The server enforces temperature=1.0 automatically
   # Do NOT try to override it in your prompts
   ```

#### Troubleshooting Quick Reference

| Error | Cause | Solution |
|-------|-------|----------|
| 400 "Unsupported value" | Temperature ≠ 1.0 | Server auto-sets to 1.0, check logs |
| 400 "Invalid max_output_tokens" | Value < 16 | Minimum is 16 tokens |
| 404 "Deployment not found" | Wrong deployment name | Verify in Azure Portal |
| 401 "Unauthorized" | Invalid API key | Regenerate key in Azure Portal |
| "Responses API not available" | Old API version | Use 2025-03-01-preview or later |

### Model Configuration

**Default Model Selection:**
```env
# Options: 'auto', 'pro', 'flash', 'o3', 'o3-mini', 'o4-mini', etc.
DEFAULT_MODEL=auto  # Claude picks best model for each task (recommended)
```

**Available Models:**
- **`auto`**: Claude automatically selects the optimal model
- **`pro`** (Gemini 2.5 Pro): Extended thinking, deep analysis
- **`flash`** (Gemini 2.0 Flash): Ultra-fast responses
- **`o3`**: Strong logical reasoning (200K context)
- **`o3-mini`**: Balanced speed/quality (200K context)
- **`o4-mini`**: Latest reasoning model, optimized for shorter contexts
- **`gpt-5`**: Azure OpenAI GPT-5 via Responses API (400K context, 128K output)
- **`gpt-5-codex`**: Azure OpenAI GPT-5-Codex specialized for code (400K context, 128K output)
- **`grok-3`**: GROK-3 advanced reasoning (131K context)
- **`grok-4-latest`**: GROK-4 latest flagship model (256K context)
- **Custom models**: via OpenRouter or local APIs

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
XAI_ALLOWED_MODELS=grok-3,grok-3-fast,grok-4-latest

# OpenRouter model restrictions (affects models via custom provider)
OPENROUTER_ALLOWED_MODELS=opus,sonnet,mistral
```

**Supported Model Names:**

**OpenAI Models:**
- `o3` (200K context, high reasoning)
- `o3-mini` (200K context, balanced)
- `o4-mini` (200K context, latest balanced)
- `mini` (shorthand for o4-mini)

**Gemini Models:**
- `gemini-2.5-flash` (1M context, fast)
- `gemini-2.5-pro` (1M context, powerful)
- `flash` (shorthand for Flash model)
- `pro` (shorthand for Pro model)

**X.AI GROK Models:**
- `grok-4-latest` (256K context, latest flagship model with reasoning, vision, and structured outputs)
- `grok-3` (131K context, advanced reasoning)
- `grok-3-fast` (131K context, higher performance)
- `grok` (shorthand for grok-4-latest)
- `grok4` (shorthand for grok-4-latest)
- `grok3` (shorthand for grok-3)
- `grokfast` (shorthand for grok-3-fast)

**Example Configurations:**
```env
# Cost control - only cheap models
OPENAI_ALLOWED_MODELS=o4-mini
GOOGLE_ALLOWED_MODELS=flash

# Single model standardization
OPENAI_ALLOWED_MODELS=o4-mini
GOOGLE_ALLOWED_MODELS=pro

# Balanced selection
GOOGLE_ALLOWED_MODELS=flash,pro
XAI_ALLOWED_MODELS=grok,grok-3-fast
```

### Advanced Configuration

**Custom Model Configuration:**
```env
# Override default location of custom_models.json
CUSTOM_MODELS_CONFIG_PATH=/path/to/your/custom_models.json
```

**Conversation Settings:**
```env
# How long AI-to-AI conversation threads persist in memory (hours)
# Conversations are auto-purged when claude closes its MCP connection or 
# when a session is quit / re-launched 
CONVERSATION_TIMEOUT_HOURS=5

# Maximum conversation turns (each exchange = 2 turns)
MAX_CONVERSATION_TURNS=20
```

**Logging Configuration:**
```env
# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=DEBUG  # Default: shows detailed operational messages
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

### Azure OpenAI Setup
```env
# Azure OpenAI with GPT-5-Codex
DEFAULT_MODEL=auto
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-codex
LOG_LEVEL=INFO
CONVERSATION_TIMEOUT_HOURS=3
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

## Important Notes

**Local Networking:**
- Use standard localhost URLs for local models
- The server runs as a native Python process

**API Key Priority:**
- Native APIs take priority over OpenRouter when both are configured
- Avoid configuring both native and OpenRouter for the same models

**Model Restrictions:**
- Apply to all usage including auto mode
- Empty/unset = all models allowed
- Invalid model names are warned about at startup

**Configuration Changes:**
- Restart the server with `./run-server.sh` after changing `.env`
- Configuration is loaded once at startup

## Related Documentation

- **[Advanced Usage Guide](advanced-usage.md)** - Advanced model usage patterns, thinking modes, and power user workflows
- **[Context Revival Guide](context-revival.md)** - Conversation persistence and context revival across sessions
- **[AI-to-AI Collaboration Guide](ai-collaboration.md)** - Multi-model coordination and conversation threading