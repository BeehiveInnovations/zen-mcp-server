# Custom Models & API Setup

This guide covers setting up multiple AI model providers including OpenRouter, custom API endpoints, and local model servers. The Zen MCP server supports a unified configuration for all these providers through a single model registry.

## Supported Providers

- **OpenRouter** - Unified access to multiple commercial models (GPT-4, Claude, Mistral, etc.)
- **Custom API endpoints** - Local models (Ollama, vLLM, LM Studio, text-generation-webui)
- **Self-hosted APIs** - Any OpenAI-compatible endpoint

## When to Use What

**Use OpenRouter when you want:**
- Access to models not available through native APIs (GPT-4, Claude, Mistral, etc.)
- Simplified billing across multiple model providers
- Experimentation with various models without separate API keys

**Use Custom URLs for:**
- **Local models** like Ollama (Llama, Mistral, etc.)
- **Self-hosted inference** with vLLM, LM Studio, text-generation-webui
- **Private/enterprise APIs** that use OpenAI-compatible format
- **Cost control** with local hardware

**Use native APIs (Gemini/OpenAI) when you want:**
- Direct access to specific providers without intermediary
- Potentially lower latency and costs
- Access to the latest model features immediately upon release

**Mix & Match:** You can use multiple providers simultaneously! For example:
- OpenRouter for expensive commercial models (GPT-4, Claude)
- Custom URLs for local models (Ollama Llama)
- Native APIs for specific providers (Gemini Pro with extended thinking)

**Note:** When multiple providers offer the same model name, native APIs take priority over OpenRouter.

## Model Aliases

The server uses `conf/custom_models.json` to map convenient aliases to both OpenRouter and custom model names. Some popular aliases:

| Alias | Maps to OpenRouter Model |
|-------|-------------------------|
| `opus` | `anthropic/claude-3-opus` |
| `sonnet`, `claude` | `anthropic/claude-3-sonnet` |
| `haiku` | `anthropic/claude-3-haiku` |
| `gpt4o`, `4o` | `openai/gpt-4o` |
| `gpt4o-mini`, `4o-mini` | `openai/gpt-4o-mini` |
| `gemini`, `pro-openrouter` | `google/gemini-pro-1.5` |
| `flash-openrouter` | `google/gemini-flash-1.5-8b` |
| `mistral` | `mistral/mistral-large` |
| `deepseek`, `coder` | `deepseek/deepseek-coder` |
| `perplexity` | `perplexity/llama-3-sonar-large-32k-online` |

View the full list in [`conf/custom_models.json`](conf/custom_models.json). 

**Note:** While you can use any OpenRouter model by its full name, models not in the config file will use generic capabilities (32K context window, no extended thinking, etc.) which may not match the model's actual capabilities. For best results, add new models to the config file with their proper specifications.

## Quick Start

### Option 1: OpenRouter Setup

#### 1. Get API Key
1. Sign up at [openrouter.ai](https://openrouter.ai/)
2. Create an API key from your dashboard
3. Add credits to your account

#### 2. Set Environment Variable
```bash
# Add to your .env file
OPENROUTER_API_KEY=your-openrouter-api-key
```

> **Note:** Control which models can be used directly in your OpenRouter dashboard at [openrouter.ai](https://openrouter.ai/). 
> This gives you centralized control over model access and spending limits.

That's it! Docker Compose already includes all necessary configuration.

### Option 2: Custom API Setup (Ollama, vLLM, etc.)

For local models like Ollama, vLLM, LM Studio, or any OpenAI-compatible API:

#### 1. Start Your Local Model Server
```bash
# Example: Ollama
ollama serve
ollama pull llama3.2

# Example: vLLM
python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-2-7b-chat-hf

# Example: LM Studio (enable OpenAI compatibility in settings)
# Server runs on localhost:1234
```

#### 2. Configure Environment Variables
```bash
# Add to your .env file
CUSTOM_API_URL=http://host.docker.internal:11434/v1  # Ollama example
CUSTOM_API_KEY=                                      # Empty for Ollama (no auth needed)
CUSTOM_MODEL_NAME=llama3.2                          # Default model to use
```

**Important: Docker URL Configuration**

Since the Zen MCP server always runs in Docker, you must use `host.docker.internal` instead of `localhost` to connect to local models running on your host machine:

```bash
# For Ollama, vLLM, LM Studio, etc. running on your host machine
CUSTOM_API_URL=http://host.docker.internal:11434/v1  # Ollama default port (NOT localhost!)
```

❌ **Never use:** `http://localhost:11434/v1` - Docker containers cannot reach localhost  
✅ **Always use:** `http://host.docker.internal:11434/v1` - This allows Docker to access host services

#### 3. Examples for Different Platforms

**Ollama:**
```bash
CUSTOM_API_URL=http://host.docker.internal:11434/v1
CUSTOM_API_KEY=
CUSTOM_MODEL_NAME=llama3.2
```

**vLLM:**
```bash
CUSTOM_API_URL=http://host.docker.internal:8000/v1
CUSTOM_API_KEY=
CUSTOM_MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
```

**LM Studio:**
```bash
CUSTOM_API_URL=http://host.docker.internal:1234/v1
CUSTOM_API_KEY=lm-studio  # Or any value, LM Studio often requires some key
CUSTOM_MODEL_NAME=local-model
```

**text-generation-webui (with OpenAI extension):**
```bash
CUSTOM_API_URL=http://host.docker.internal:5001/v1
CUSTOM_API_KEY=
CUSTOM_MODEL_NAME=your-loaded-model
```

## Using Models

**Using model aliases (from conf/openrouter_models.json):**
```
# OpenRouter models:
"Use opus for deep analysis"         # → anthropic/claude-3-opus
"Use sonnet to review this code"     # → anthropic/claude-3-sonnet
"Use gpt4o via zen to analyze this"  # → openai/gpt-4o
"Use mistral via zen to optimize"    # → mistral/mistral-large

# Local models (with custom URL configured):
"Use local-llama to analyze this code"     # → llama3.2 (local)
"Use local to debug this function"         # → llama3.2 (local)
```

**Using full model names:**
```
# OpenRouter models:
"Use anthropic/claude-3-opus via zen for deep analysis"
"Use openai/gpt-4o via zen to debug this"
"Use deepseek/deepseek-coder via zen to generate code"

# Local/custom models:
"Use llama3.2 via zen to review this"
"Use meta-llama/Llama-2-7b-chat-hf via zen to analyze"
```

**For OpenRouter:** Check current model pricing at [openrouter.ai/models](https://openrouter.ai/models).  
**For Local models:** Context window and capabilities are defined in `conf/custom_models.json`.

## Model Configuration

The server uses `conf/custom_models.json` to define model aliases and capabilities. You can:

1. **Use the default configuration** - Includes popular models with convenient aliases
2. **Customize the configuration** - Add your own models and aliases
3. **Override the config path** - Set `CUSTOM_MODELS_CONFIG_PATH` environment variable to an absolute path on disk

### Adding Custom Models

Edit `conf/custom_models.json` to add new models:

```json
{
  "model_name": "vendor/model-name",
  "aliases": ["short-name", "nickname"],
  "context_window": 128000,
  "supports_extended_thinking": false,
  "supports_json_mode": true,
  "supports_function_calling": true,
  "description": "Model description"
}
```

**Field explanations:**
- `context_window`: Total tokens the model can process (input + output combined)
- `supports_extended_thinking`: Whether the model has extended reasoning capabilities
- `supports_json_mode`: Whether the model can guarantee valid JSON output
- `supports_function_calling`: Whether the model supports function/tool calling

## Available Models

Popular models available through OpenRouter:
- **GPT-4** - OpenAI's most capable model
- **Claude 3** - Anthropic's models (Opus, Sonnet, Haiku)
- **Mistral** - Including Mistral Large
- **Llama 3** - Meta's open models
- Many more at [openrouter.ai/models](https://openrouter.ai/models)

## Troubleshooting

- **"Model not found"**: Check exact model name at openrouter.ai/models
- **"Insufficient credits"**: Add credits to your OpenRouter account
- **"Model not available"**: Check your OpenRouter dashboard for model access permissions