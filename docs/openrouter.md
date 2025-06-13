# OpenRouter Setup

OpenRouter provides unified access to multiple AI models (GPT-4, Claude, Mistral, etc.) through a single API.

## When to Use OpenRouter

**Use OpenRouter when you want:**
- Access to models not available through native APIs (GPT-4, Claude, Mistral, etc.)
- Simplified billing across multiple model providers
- Experimentation with various models without separate API keys

**Use native APIs (Gemini/OpenAI) when you want:**
- Direct access to specific providers without intermediary
- Potentially lower latency and costs
- Access to the latest model features immediately upon release

**Important:** Don't use both OpenRouter and native APIs simultaneously - this creates ambiguity about which provider serves each model.

## Model Aliases

The server uses `conf/openrouter_models.json` to map convenient aliases to OpenRouter model names. Some popular aliases:

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

View the full list in [`conf/openrouter_models.json`](conf/openrouter_models.json). 

**Note:** While you can use any OpenRouter model by its full name, models not in the config file will use generic capabilities (32K context window, no extended thinking, etc.) which may not match the model's actual capabilities. For best results, add new models to the config file with their proper specifications.

## Quick Start

### 1. Get API Key
1. Sign up at [openrouter.ai](https://openrouter.ai/)
2. Create an API key from your dashboard
3. Add credits to your account

### 2. Set Environment Variable
```bash
# Add to your .env file
OPENROUTER_API_KEY=your-openrouter-api-key
```

> **Note:** Control which models can be used directly in your OpenRouter dashboard at [openrouter.ai](https://openrouter.ai/). 
> This gives you centralized control over model access and spending limits.

That's it! Docker Compose already includes all necessary configuration.

### 3. Use Models

**Using model aliases (from conf/openrouter_models.json):**
```
# Use short aliases:
"Use opus for deep analysis"         # → anthropic/claude-3-opus
"Use sonnet to review this code"     # → anthropic/claude-3-sonnet
"Use gpt4o via zen to analyze this"          # → openai/gpt-4o
"Use mistral via zen to optimize"            # → mistral/mistral-large
```

**Using full model names:**
```
# Any model available on OpenRouter:
"Use anthropic/claude-3-opus via zen for deep analysis"
"Use openai/gpt-4o via zen to debug this"
"Use deepseek/deepseek-coder via zen to generate code"
```

Check current model pricing at [openrouter.ai/models](https://openrouter.ai/models).

## Model Configuration

The server uses `conf/openrouter_models.json` to define model aliases and capabilities. You can:

1. **Use the default configuration** - Includes popular models with convenient aliases
2. **Customize the configuration** - Add your own models and aliases
3. **Override the config path** - Set `OPENROUTER_MODELS_PATH` environment variable

### Adding Custom Models

Edit `conf/openrouter_models.json` to add new models:

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