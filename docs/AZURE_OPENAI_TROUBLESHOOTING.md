# Azure OpenAI Troubleshooting Guide

This guide provides comprehensive troubleshooting information for Azure OpenAI integration with Zen MCP Server.

## Implementation Overview

**IMPORTANT:** This implementation uses Azure OpenAI **Responses API** exclusively.

- Works with both **GPT-5** and **GPT-5-Codex** models
- Uses Responses API (not Chat Completions API) as required by GPT-5-Codex
- Different content extraction methods than standard Chat Completions
- Supports multi-turn conversations with proper session management

---

## Common Issues and Solutions

### 1. Missing Environment Variables

**Problem:** Azure OpenAI provider not available or returns configuration errors.

**Solution:** Ensure all required environment variables are set in your `.env` file:

```bash
# Required Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-codex  # or gpt-5
AZURE_OPENAI_API_VERSION=2025-03-01-preview  # Must be 2025-03-01-preview or later
```

**Verify configuration:**
```bash
# Check if variables are set
grep "AZURE_OPENAI" .env

# Expected output should show all four variables with values
```

---

### 2. Invalid API Key

**Problem:** Authentication errors when making API calls.

**Error Message:**
```
401 Unauthorized: Invalid API key provided
```

**Solution:**
1. Verify your API key in Azure Portal:
   - Go to Azure Portal → Your Azure OpenAI resource
   - Navigate to "Keys and Endpoint"
   - Copy either KEY 1 or KEY 2
   - Update `AZURE_OPENAI_API_KEY` in `.env` file

2. Ensure no extra spaces or quotes in the API key:
```bash
# Correct format
AZURE_OPENAI_API_KEY=abcd1234567890...

# Incorrect format (no quotes needed)
AZURE_OPENAI_API_KEY="abcd1234567890..."
```

---

### 3. Wrong Endpoint Format

**Problem:** Connection errors or invalid endpoint errors.

**Error Message:**
```
Invalid URL or endpoint format
```

**Solution:** Ensure endpoint follows correct format:

```bash
# Correct format
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com

# Incorrect formats (missing https://)
AZURE_OPENAI_ENDPOINT=your-resource-name.openai.azure.com

# Incorrect formats (trailing slash)
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
```

**Verify endpoint:**
```bash
# Test endpoint connectivity
curl -I https://your-resource-name.openai.azure.com
```

---

### 4. Old API Version

**Problem:** Responses API not available or unsupported API version.

**Error Message:**
```
API version not supported or Responses API not available
```

**Solution:** Update to required API version:

```bash
# Required version for Responses API
AZURE_OPENAI_API_VERSION=2025-03-01-preview

# Older versions NOT supported for Responses API
AZURE_OPENAI_API_VERSION=2024-10-21  # Too old
AZURE_OPENAI_API_VERSION=2024-08-01-preview  # Too old
```

**Note:** The Responses API requires API version `2025-03-01-preview` or later. Earlier versions only support Chat Completions API.

---

### 5. Deployment Name Mismatch

**Problem:** Deployment not found or model not available.

**Error Message:**
```
404 Not Found: The API deployment for this resource does not exist
```

**Solution:**
1. Verify deployment name in Azure Portal:
   - Go to Azure Portal → Your Azure OpenAI resource
   - Navigate to "Model deployments"
   - Copy exact deployment name (case-sensitive)

2. Update deployment name in `.env`:
```bash
# Use exact deployment name from Azure Portal
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-codex

# Common deployment names
# AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5
# AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-codex
# AZURE_OPENAI_DEPLOYMENT_NAME=my-gpt5-deployment
```

**Verify deployment exists:**
```bash
# List deployments using Azure CLI
az cognitiveservices account deployment list \
  --name your-resource-name \
  --resource-group your-resource-group
```

---

### 6. Temperature Validation Errors

**Problem:** Invalid temperature value for GPT-5-Codex.

**Error Message:**
```
Temperature must be exactly 1.0 for GPT-5-Codex model
Invalid temperature value: must be 1.0
```

**Solution:** The implementation enforces temperature=1.0 for GPT-5-Codex:

```python
# Temperature is automatically set to 1.0 for GPT-5-Codex
# No configuration needed - handled internally

# For other models (if supported later), temperature can vary
# But for GPT-5-Codex: temperature=1.0 is required
```

**Note:** This is a GPT-5-Codex requirement enforced by Azure, not a server limitation.

---

### 7. Rate Limiting

**Problem:** Too many requests or quota exceeded.

**Error Message:**
```
429 Too Many Requests: Rate limit exceeded
403 Forbidden: Quota exceeded
```

**Solution:**
1. Check your Azure quota:
   - Go to Azure Portal → Your Azure OpenAI resource
   - Navigate to "Quotas"
   - Verify Tokens Per Minute (TPM) limit

2. Implement retry logic (already built-in):
   - The server automatically retries with exponential backoff
   - Wait a few moments between requests

3. Request quota increase:
   - Contact Azure support to increase your TPM quota
   - Upgrade to higher tier if available

---

## Responses API Specific Issues

### Understanding Responses API

**Key Differences from Chat Completions API:**

1. **Endpoint URL:**
   ```bash
   # Responses API (what we use)
   POST https://{resource}.openai.azure.com/openai/deployments/{deployment}/responses

   # Chat Completions API (NOT used)
   POST https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions
   ```

2. **Content Extraction:**
   ```python
   # Responses API - two possible formats
   # Format 1: output_text field
   content = response_data.get("output_text", "")

   # Format 2: output array
   output = response_data.get("output", [])
   if output and len(output) > 0:
       content = output[0].get("content", "")
   ```

3. **Required Models:**
   - GPT-5-Codex: **Requires** Responses API
   - GPT-5: Works with Responses API

### Responses API Error Handling

**Problem:** Empty or missing response content.

**Solution:** The implementation handles multiple content extraction methods:

```python
# Check multiple possible response formats
# 1. Try output_text field
# 2. Try output array
# 3. Try choices array (fallback)
# 4. Return error if none found
```

If you see empty responses, check server logs:
```bash
tail -n 100 logs/mcp_server.log | grep "Azure OpenAI"
```

---

## Configuration Validation

### Verify Azure Credentials

**Step 1: Check environment variables**
```bash
# View current configuration
grep "AZURE_OPENAI" .env

# Expected output:
# AZURE_OPENAI_API_KEY=sk-...
# AZURE_OPENAI_ENDPOINT=https://...
# AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-codex
# AZURE_OPENAI_API_VERSION=2025-03-01-preview
```

**Step 2: Test API key validity**
```bash
# Using curl to test authentication
curl -X POST "https://your-resource.openai.azure.com/openai/deployments/gpt-5-codex/responses?api-version=2025-03-01-preview" \
  -H "api-key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "test"}],
    "temperature": 1.0
  }'
```

### Test Endpoint Connectivity

**Check DNS resolution:**
```bash
# Verify endpoint resolves
nslookup your-resource.openai.azure.com
```

**Check network connectivity:**
```bash
# Test HTTPS connection
curl -I https://your-resource.openai.azure.com
```

**Expected response:**
```
HTTP/2 401
# 401 is expected without API key - confirms endpoint is reachable
```

### Verify Deployment Exists

**Using Azure CLI:**
```bash
# List all deployments
az cognitiveservices account deployment list \
  --name your-resource-name \
  --resource-group your-resource-group \
  --query "[].{name:name, model:properties.model.name}" \
  --output table

# Expected output:
# Name              Model
# ----------------  -------------
# gpt-5-codex       gpt-5-codex
```

**Using Azure Portal:**
1. Navigate to your Azure OpenAI resource
2. Click "Model deployments"
3. Verify deployment name and model

### Verify API Version Support

**Check supported API versions:**
```bash
# List available API versions for your resource
az cognitiveservices account show \
  --name your-resource-name \
  --resource-group your-resource-group \
  --query "properties.capabilities"
```

**Ensure using latest version:**
- API version must be `2025-03-01-preview` or later
- Older versions do not support Responses API

---

## Common Error Messages

### Authentication Errors

**Error:** `401 Unauthorized`
```json
{
  "error": {
    "code": "401",
    "message": "Access denied due to invalid subscription key or wrong API endpoint."
  }
}
```

**Solutions:**
1. Verify `AZURE_OPENAI_API_KEY` is correct
2. Check API key is not expired
3. Ensure using correct endpoint
4. Regenerate API key if needed

---

### API Version Errors

**Error:** `API version not supported`
```json
{
  "error": {
    "code": "InvalidApiVersion",
    "message": "The requested API version is not supported."
  }
}
```

**Solutions:**
1. Update `AZURE_OPENAI_API_VERSION=2025-03-01-preview`
2. Verify your resource supports this API version
3. Check Azure region availability

---

### Deployment Not Found Errors

**Error:** `404 Not Found`
```json
{
  "error": {
    "code": "DeploymentNotFound",
    "message": "The API deployment for this resource does not exist."
  }
}
```

**Solutions:**
1. Verify deployment name is correct (case-sensitive)
2. Check deployment exists in Azure Portal
3. Ensure deployment is in "Succeeded" state
4. Verify using correct resource/endpoint

---

### Temperature Constraint Errors

**Error:** `Invalid temperature value`
```json
{
  "error": {
    "code": "InvalidParameter",
    "message": "Temperature must be exactly 1.0 for GPT-5-Codex model."
  }
}
```

**Solutions:**
- This is enforced by Azure for GPT-5-Codex
- The implementation automatically sets temperature=1.0
- If you see this error, check server logs for configuration issues

---

### Content Extraction Errors

**Error:** Empty response or missing content

**Symptoms:**
- Tool returns empty string
- No visible output from model
- Logs show successful API call but no content

**Solutions:**
1. Check server logs for response format:
```bash
tail -n 200 logs/mcp_server.log | grep "Azure OpenAI response"
```

2. Verify Responses API is being used (not Chat Completions):
```bash
grep "responses?" logs/mcp_server.log
```

3. Check for multiple content extraction attempts in logs

---

## Testing and Validation

### Run Integration Tests

**Test Azure OpenAI provider:**
```bash
# Run integration tests (requires API keys)
./run_integration_tests.sh

# Run specific Azure OpenAI tests
python -m pytest tests/ -v -k "azure" -m integration
```

**Expected output:**
```
tests/test_azure_openai_integration.py::test_azure_provider_registration PASSED
tests/test_azure_openai_integration.py::test_azure_api_call PASSED
tests/test_azure_openai_integration.py::test_azure_responses_api PASSED
```

### Check Server Logs

**View recent Azure activity:**
```bash
# Filter for Azure OpenAI logs
tail -n 500 logs/mcp_server.log | grep -i "azure"

# View tool activity
tail -n 100 logs/mcp_activity.log

# Follow logs in real-time
tail -f logs/mcp_server.log
```

**Look for:**
- Provider registration confirmation
- API call attempts
- Response format handling
- Error messages

### Verify Provider Registration

**Check provider availability:**
```bash
# Start server and check logs
./run-server.sh

# Look for registration message
grep "Azure OpenAI provider registered" logs/mcp_server.log
```

**Expected log entry:**
```
INFO: Azure OpenAI provider registered successfully
INFO: Deployment: gpt-5-codex
INFO: API Version: 2025-03-01-preview
```

### Manual API Testing

**Test Responses API directly:**
```bash
# Create test script
cat > test_azure.sh << 'EOF'
#!/bin/bash
source .env

curl -X POST "${AZURE_OPENAI_ENDPOINT}/openai/deployments/${AZURE_OPENAI_DEPLOYMENT_NAME}/responses?api-version=${AZURE_OPENAI_API_VERSION}" \
  -H "api-key: ${AZURE_OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello in one word"}
    ],
    "temperature": 1.0,
    "max_tokens": 10
  }'
EOF

chmod +x test_azure.sh
./test_azure.sh
```

**Expected response:**
```json
{
  "output_text": "Hello",
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 1,
    "total_tokens": 13
  }
}
```

---

## Advanced Troubleshooting

### Enable Debug Logging

**Increase log verbosity:**
```bash
# Set debug level in environment
export LOG_LEVEL=DEBUG

# Restart server
./run-server.sh

# View detailed logs
tail -f logs/mcp_server.log
```

### Network Diagnostics

**Check firewall rules:**
```bash
# Test connectivity to Azure endpoint
telnet your-resource.openai.azure.com 443

# Check SSL certificate
openssl s_client -connect your-resource.openai.azure.com:443
```

**Verify DNS:**
```bash
# Check DNS resolution
dig your-resource.openai.azure.com

# Alternative DNS check
host your-resource.openai.azure.com
```

### Analyze Request/Response

**Enable request logging:**
```python
# In providers/azure_openai_provider.py
# Temporarily add debug prints to see full request/response

logger.debug(f"Request URL: {url}")
logger.debug(f"Request headers: {headers}")
logger.debug(f"Request body: {json.dumps(payload, indent=2)}")
logger.debug(f"Response status: {response.status_code}")
logger.debug(f"Response body: {response.text}")
```

**Check cassette recordings:**
```bash
# View recorded API interactions
ls -la tests/cassettes/azure_*.yaml
```

---

## Additional Resources

### Azure Documentation

- [Azure OpenAI Service Documentation](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/)
- [Responses API Reference](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/reference#responses-api)
- [GPT-5-Codex Model Details](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/concepts/models#gpt-5-codex)
- [API Version Support](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/api-version-deprecation)

### Project Documentation

- Main README: `E:\zen-mcp-server\README.md`
- Development Guide: `E:\zen-mcp-server\CLAUDE.md`
- Integration Tests: `E:\zen-mcp-server\tests\test_azure_openai_integration.py`
- Provider Implementation: `E:\zen-mcp-server\providers\azure_openai_provider.py`

### Getting Help

1. **Check server logs:** `tail -n 500 logs/mcp_server.log`
2. **Run diagnostics:** `./run_integration_tests.sh`
3. **Review Azure Portal:** Verify configuration and quotas
4. **Contact Azure Support:** For Azure-specific issues
5. **GitHub Issues:** Report bugs or request features

---

## Summary Checklist

Before opening an issue, verify:

- [ ] All environment variables set correctly in `.env`
- [ ] API key is valid and not expired
- [ ] Endpoint format is correct (https://...)
- [ ] API version is `2025-03-01-preview` or later
- [ ] Deployment name matches Azure Portal exactly
- [ ] Deployment is in "Succeeded" state
- [ ] Quota/rate limits not exceeded
- [ ] Network connectivity to Azure endpoint
- [ ] Server logs checked for specific errors
- [ ] Integration tests run successfully

---

**Last Updated:** 2025-10-03
**API Version Required:** 2025-03-01-preview or later
**Supported Models:** GPT-5, GPT-5-Codex
**Implementation:** Azure OpenAI Responses API
