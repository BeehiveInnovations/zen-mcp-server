# OpenRouter Setup

OpenRouter provides unified access to multiple AI models (GPT-4, Claude, Mistral, etc.) through a single API.

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

That's it! Docker Compose already includes all necessary configuration.

### 3. Use Any Model
```
# Examples
"Use gpt-4 via zen to review this code"
"Use claude-3-opus via zen to debug this error"
"Use mistral-large via zen to optimize this algorithm"
```

## Cost Control (Recommended)

Restrict which models can be used to prevent unexpected charges:

```bash
# Add to .env file - only allow specific models
OPENROUTER_ALLOWED_MODELS=gpt-4,claude-3-sonnet,mistral-large
```

Check current model pricing at [openrouter.ai/models](https://openrouter.ai/models).

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
- **"Model not in allow-list"**: Update `OPENROUTER_ALLOWED_MODELS` in .env