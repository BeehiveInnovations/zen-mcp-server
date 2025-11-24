# Zen MCP Server - Configuration Guide

## Overview

This guide explains configuration for both the current **Tool/Registry System** (production) and the future **LangGraph System** (development).

## Current System Configuration (Tool/Registry)

### Required API Keys

You must configure at least one AI provider. The server will automatically detect and prioritize available providers.

#### Option 1: Native APIs (Recommended for Direct Access)

```bash
# OpenAI (GPT models: o3, o4, gpt-5)
OPENAI_API_KEY=sk-your-openai-key-here

# Google Gemini (Flash/Pro models: gemini-2.5-flash, gemini-2.5-pro)
GEMINI_API_KEY=AIza-your-gemini-key-here

# X.AI (GROK models: grok-3, grok-3-fast)
XAI_API_KEY=xai-your-xai-key-here

# DIAL (Enterprise unified access)
DIAL_API_KEY=dial-your-dial-key-here
# DIAL_API_HOST=https://core.dialx.ai  # Optional custom host
# DIAL_API_VERSION=2025-01-01-preview  # Optional API version
```

#### Option 2: OpenRouter (Multiple Models via Single API)

```bash
# Access to 100+ models through one API
OPENROUTER_API_KEY=sk-or-your-openrouter-key-here
```

#### Option 3: Custom/Local Models

```bash
# Ollama, vLLM, LM Studio, or any OpenAI-compatible endpoint
CUSTOM_API_URL=http://localhost:11434/v1  # Ollama example
CUSTOM_API_KEY=  # Leave empty for unauthenticated endpoints
CUSTOM_MODEL_NAME=llama3.2  # Default model for custom endpoint
```

### Optional Configuration

```bash
# Model Selection
DEFAULT_MODEL=auto  # Let Claude choose best model per task
# Alternative: gpt-4o, gemini-2.5-flash, claude-sonnet-4.1, etc.

# Tool Management (optimize context window usage)
DISABLED_TOOLS=analyze,refactor,testgen,secaudit,docgen,tracer
# Available: chat,thinkdeep,planner,consensus,codereview,precommit,debug
#           challenge,listmodels,version (always enabled)

# Conversation Settings
CONVERSATION_TIMEOUT_HOURS=3  # How long threads persist
MAX_CONVERSATION_TURNS=20     # Max exchanges per thread

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_MAX_SIZE=10MB  # File rotation size

# Model Restrictions (optional)
# OPENAI_ALLOWED_MODELS=o3-mini,o4-mini
# GOOGLE_ALLOWED_MODELS=flash,pro
# XAI_ALLOWED_MODELS=grok-3
# DIAL_ALLOWED_MODELS=o3,o4-mini,sonnet-4.1
```

## Future System Configuration (LangGraph)

### Gateway Configuration

```bash
# Unified Gateway (Bifrost or LiteLLM)
UNIFIED_LLM_GATEWAY=http://localhost:8080
UNIFIED_LLM_API_KEY=sk-gateway-key-if-required

# Redis Persistence (Required for LangGraph)
REDIS_URL=redis://localhost:6379/0
```

### Gateway Deployment Examples

#### Bifrost (Go-based, Recommended)

```bash
# Deploy Bifrost with your API keys
docker run -d -p 8080:8080 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  -e XAI_API_KEY=$XAI_API_KEY \
  bifrost/bifrost:latest
```

#### LiteLLM (Python-based)

```bash
# Deploy LiteLLM
pip install litellm
litellm --model list --port 8080
```

## Configuration Priority & Detection

### Provider Priority (Current System)

1. **Native APIs** (fastest, most direct)
   - OpenAI → Gemini → XAI → DIAL
2. **Custom Endpoints** (local/private models)
3. **OpenRouter** (catch-all for everything else)

### Auto Mode Model Selection

The server automatically selects the best model based on:

| Task Category | Preferred Models | Rationale |
|---------------|------------------|------------|
| **Analysis** | gemini-2.5-pro, gpt-4o | Strong reasoning, large context |
| **Coding** | gpt-4o, claude-sonnet-4.1 | Code generation quality |
| **Chat** | gemini-2.5-flash, gpt-4o-mini | Fast response, good reasoning |
| **Consensus** | Multiple models via OpenRouter | Diverse perspectives |
| **Debug** | o3-mini, o4-mini | Deep reasoning capabilities |

## Migration Path

### Phase 1: Current Configuration (Now)
- Use individual API keys (as shown above)
- Run with `./run-server.sh`
- Full feature set available

### Phase 2: Gateway Setup (Optional)
- Deploy Bifrost/LiteLLM
- Migrate API keys to gateway
- Test with current tools using gateway provider

### Phase 3: LangGraph Transition (Future)
- Deploy Redis for persistence
- Run with `python server_graph.py`
- Use multi-agent architecture

## Troubleshooting

### Common Issues

#### "No valid API keys found"
**Solution**: Ensure at least provider has valid key:
```bash
# Test your keys
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

#### "Model not available"
**Solution**: Check model restrictions and availability:
```bash
# List available models
python -c "
from providers.registry import ModelProviderRegistry
print(list(ModelProviderRegistry.get_available_models().keys()))
"
```

#### "Gateway connection failed"
**Solution**: Verify gateway deployment:
```bash
# Test gateway health
curl http://localhost:8080/v1/models

# Check gateway logs
docker logs <gateway_container>
```

#### "Redis connection failed"
**Solution**: Verify Redis server:
```bash
# Test Redis connection
redis-cli -u redis://localhost:6379 ping

# Check Redis logs
docker logs <redis_container>
```

### Configuration Validation

```bash
# Validate current configuration
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

required_keys = ['OPENAI_API_KEY', 'GEMINI_API_KEY', 'OPENROUTER_API_KEY']
found_keys = [k for k in required_keys if os.getenv(k)]
print(f'Configured providers: {found_keys}')
"
```

## Advanced Configuration

### Custom Model Registry

```bash
# Override default model configurations
CUSTOM_MODELS_CONFIG_PATH=/path/to/custom_models.json
```

### Performance Tuning

```bash
# Conversation memory optimization
CONVERSATION_TIMEOUT_HOURS=1  # Shorter for memory efficiency
MAX_CONVERSATION_TURNS=10     # Fewer turns

# File processing limits
MAX_FILE_SIZE_MB=50  # Maximum file size for analysis
MAX_FILES_PER_REQUEST=20  # Maximum files per analysis
```

### Security Settings

```bash
# PII detection and sanitization
ENABLE_PII_SANITIZATION=true
PII_SANITIZATION_METHOD=redact  # redact, remove, hash

# API rate limiting
REQUEST_RATE_LIMIT=100  # Requests per minute
```

## Environment-Specific Configurations

### Development
```bash
LOG_LEVEL=DEBUG
DISABLED_TOOLS=  # Enable all tools for testing
CONVERSATION_TIMEOUT_HOURS=1  # Shorter for development
```

### Production
```bash
LOG_LEVEL=INFO
DISABLED_TOOLS=analyze,refactor,testgen,secaudit,docgen,tracer
CONVERSATION_TIMEOUT_HOURS=6  # Longer for production use
```

### Testing
```bash
LOG_LEVEL=DEBUG
DEFAULT_MODEL=gpt-4o-mini  # Cost-effective for testing
CONVERSATION_TIMEOUT_HOURS=0.5  # Very short for test isolation
```

## Configuration Examples by Use Case

### Individual Developer
```bash
OPENAI_API_KEY=sk-your-key
DEFAULT_MODEL=auto
DISABLED_TOOLS=secaudit,precommit  # Disable enterprise features
```

### Enterprise Team
```bash
DIAL_API_KEY=enterprise-dial-key
DEFAULT_MODEL=auto
OPENAI_ALLOWED_MODELS=o3-mini,gpt-4o  # Cost control
GOOGLE_ALLOWED_MODELS=flash  # Speed preference
```

### Privacy-Focused (Local Models)
```bash
CUSTOM_API_URL=http://localhost:11434/v1
CUSTOM_MODEL_NAME=llama3.2
DEFAULT_MODEL=llama3.2
# No external API keys
```

### Research/Academic
```bash
OPENROUTER_API_KEY=sk-or-key  # Access to diverse models
DEFAULT_MODEL=auto
DISABLED_TOOLS=  # Enable all research tools
```

---

*For LangGraph-specific configuration, see [`docs/MIGRATION_GUIDE.md`](docs/MIGRATION_GUIDE.md)*
