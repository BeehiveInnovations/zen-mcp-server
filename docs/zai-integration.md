# Z.AI Provider Integration

## Overview

This document describes the Z.AI provider integration for the Zen MCP Server, which provides access to GLM-4.6 models through Z.AI's OpenAI-compatible API.

## What Was Changed

### 1. Created Z.AI Provider (`providers/zai.py`)

A dedicated provider class extending `OpenAICompatibleProvider` that:
- Uses the correct Z.AI endpoint: `https://api.z.ai/api/coding/paas/v4`
- Handles GLM model capabilities (GLM-4.6 with multimodal support)
- Resolves model aliases (glm, glm-4, glm4.6 → glm-4.6)
- Supports 128K context window with 8K max output tokens

### 2. Updated Provider Type Enum

Added `ZAI = "zai"` to `providers/shared/provider_type.py` to identify Z.AI as a distinct provider.

### 3. Registered Provider

Updated `providers/__init__.py` to export `ZAIProvider` and added server.py initialization logic to:
- Check for `ZAI_API_KEY` environment variable
- Register Z.AI provider when API key is present
- Log Z.AI availability

### 4. Environment Configuration

Updated `.env` file:
- Added `ZAI_API_KEY` configuration
- Moved API key from `CUSTOM_API_KEY` to dedicated `ZAI_API_KEY`
- Commented out old CUSTOM_API_URL configuration for Z.AI endpoint

### 5. Model Registry Cleanup

Removed GLM-4.6 from `conf/custom_models.json` since it's now handled by the dedicated Z.AI provider.

## API Endpoint Details

Based on Z.AI API documentation (https://docs.z.ai/api-reference/introduction):

- **Endpoint**: `https://api.z.ai/api/coding/paas/v4/chat/completions`
- **Authentication**: HTTP Bearer token via `ZAI_API_KEY`
- **Supported Model**: `glm-4.6`
- **Request Format**: OpenAI-compatible (messages, temperature, stream, etc.)

## Model Capabilities

GLM-4.6 features:
- **Context Window**: 128,000 tokens
- **Max Output**: 8,000 tokens
- **Extended Thinking**: Supported
- **JSON Mode**: Supported
- **Function Calling**: Supported
- **Images**: Supported (up to 10MB)
- **Temperature**: Supported
- **Intelligence Score**: 85 (high-quality model)

## Usage

### Environment Setup

```bash
# In .env file
ZAI_API_KEY=your_zai_api_key_here
```

### Model Names and Aliases

All of these resolve to `glm-4.6`:
- `glm-4.6` (canonical name)
- `glm4.6`
- `glm-4`
- `glm`

### Example Usage

```bash
# Using the chat tool with GLM
zen chat with glm-4.6

# Or using an alias
zen chat with glm
```

## Testing

After restarting your Claude session, test the integration:

```bash
# List available models (should show GLM models)
zen listmodels

# Test chat with GLM-4.6
zen chat with glm-4.6
```

## Key Differences from Custom Provider

The Z.AI provider differs from the generic Custom provider:

| Feature | Z.AI Provider | Custom Provider |
|---------|---------------|-----------------|
| Endpoint | Fixed (`https://api.z.ai/api/paas/v4`) | Configurable (`CUSTOM_API_URL`) |
| Models | GLM models only | Any OpenAI-compatible model |
| Configuration | Single `ZAI_API_KEY` | `CUSTOM_API_URL` + `CUSTOM_API_KEY` |
| Registry | Built-in capabilities | `custom_models.json` definitions |

## Troubleshooting

### Model Not Available

If GLM models don't appear after restart:
1. Check `ZAI_API_KEY` is set in `.env`
2. Verify API key is valid (not placeholder)
3. Check server logs: `tail -f logs/mcp_server.log`
4. Look for "Z.AI API key found" message

### API Errors

If you get API errors:
1. Verify the API key has access to GLM models
2. Check Z.AI service status
3. Review logs for detailed error messages
4. Ensure you're not hitting rate limits

## Files Modified

- `providers/zai.py` (new file)
- `providers/shared/provider_type.py`
- `providers/__init__.py`
- `server.py`
- `.env`
- `conf/custom_models.json`

## Next Steps

1. **Restart Claude session** (IMPORTANT - changes won't take effect until restart)
2. Test GLM-4.6 with chat tool
3. Verify model appears in listmodels output
4. Try different tools (thinkdeep, codereview, etc.) with GLM

## References

- Z.AI API Documentation: https://docs.z.ai/api-reference/introduction
- API Key Management: https://z.ai/manage-apikey/apikey-list
