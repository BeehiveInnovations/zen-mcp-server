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

## Quick Start

### 1. Get API Key
1. Sign up at [openrouter.ai](https://openrouter.ai/)
2. Create an API key from your dashboard
3. Add credits to your account

### 2. Set Environment Variable
```bash
# Add to your .env file
OPENROUTER_API_KEY=your-openrouter-api-key

# IMPORTANT: Set allowed models to control costs
OPENROUTER_ALLOWED_MODELS=gpt-4,claude-3-sonnet,mistral-large

# Or leave empty to allow ANY model (WARNING: risk of high costs!)
# OPENROUTER_ALLOWED_MODELS=
```

That's it! Docker Compose already includes all necessary configuration.

### 3. Use Models

**If you set OPENROUTER_ALLOWED_MODELS:**
```
# Only these models will work:
"Use gpt-4 via zen to review this code"
"Use claude-3-sonnet via zen to debug this error"
"Use mistral-large via zen to optimize this algorithm"
```

**If you leave OPENROUTER_ALLOWED_MODELS empty:**
```
# ANY model available on OpenRouter will work:
"Use gpt-4o via zen to analyze this"
"Use claude-3-opus via zen for deep analysis"
"Use deepseek-coder via zen to generate code"
# WARNING: Some models can be very expensive!
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