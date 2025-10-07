# Azure OpenAI GPT-5 and GPT-5-Codex Complete Guide

This comprehensive guide covers everything you need to know about using Azure OpenAI's GPT-5 and GPT-5-Codex models with the Zen MCP Server.

## Table of Contents

- [Overview](#overview)
- [Model Comparison](#model-comparison)
- [Critical Requirements](#critical-requirements)
- [Setup Walkthrough](#setup-walkthrough)
- [Technical Constraints](#technical-constraints)
- [Best Practices](#best-practices)
- [Cost Optimization](#cost-optimization)
- [Integration Patterns](#integration-patterns)
- [Troubleshooting](#troubleshooting)
- [FAQ](#frequently-asked-questions)

## Overview

Azure OpenAI provides access to two powerful GPT-5 models through the **Responses API** (not Chat Completions API):

- **GPT-5**: Advanced reasoning model with vision support for general-purpose tasks
- **GPT-5-Codex**: Elite code generation model specialized for programming tasks

Both models offer:
- 400K token context window (2x larger than O3's 200K)
- 128K token max output (4x larger than GPT-4.1's 32K)
- Extended reasoning capabilities with internal "reasoning tokens"
- Enterprise-grade security and compliance through Azure

## Model Comparison

| Feature | GPT-5 | GPT-5-Codex |
|---------|-------|-------------|
| **Context Window** | 400,000 tokens | 400,000 tokens |
| **Max Output** | 128,000 tokens | 128,000 tokens |
| **Vision Support** | ✅ Yes | ❌ No |
| **Code Specialization** | Good | Elite |
| **Intelligence Score** | 16 | 17 |
| **Temperature** | Fixed at 1.0 | Fixed at 1.0 |
| **Min Output Tokens** | 16 | 16 |
| **API Type** | Responses API only | Responses API only |
| **Best For** | General reasoning, architecture design, image analysis | Code generation, refactoring, technical documentation |

## Critical Requirements

### ⚠️ MUST READ - These are hard requirements, not recommendations:

1. **Responses API Only**
   - Chat Completions API is NOT implemented for these models
   - Endpoint: `/openai/deployments/{deployment}/responses`
   - Different response format than standard OpenAI

2. **Temperature Constraint**
   - MUST be exactly 1.0
   - Cannot be changed via API or configuration
   - Error if different: `"Unsupported value. Only the default (1) value is supported"`

3. **Minimum Output Tokens**
   - Must be at least 16 tokens
   - Parameter: `max_output_tokens` (not `max_completion_tokens`)
   - Error if less: `400 Bad Request: max_output_tokens must be at least 16`

4. **API Version Requirement**
   - Must use `2025-03-01-preview` or later
   - Earlier versions don't support Responses API
   - Recommended: `2025-04-01-preview`

## Setup Walkthrough

### Step 1: Azure Portal Setup

1. **Create Azure OpenAI Resource**
   ```
   Portal → Create Resource → Search "Azure OpenAI" → Create
   - Resource Group: Select or create new
   - Region: Choose supported region (e.g., East US, West Europe)
   - Pricing Tier: Standard S0
   - Name: Your unique resource name
   ```

2. **Request Model Access**
   ```
   Resource → Model deployments → Request access
   - Select GPT-5 and/or GPT-5-Codex
   - Provide use case justification
   - Wait for approval (usually 24-48 hours)
   ```

3. **Deploy the Model**
   ```
   Resource → Model deployments → Create new deployment
   - Model: gpt-5 or gpt-5-codex
   - Deployment name: Choose a name (e.g., "gpt5-prod")
   - Version: Select latest available
   - Capacity (TPM): Set based on needs (e.g., 120K)
   ```

4. **Get Credentials**
   ```
   Resource → Keys and Endpoint
   - Copy KEY 1 or KEY 2
   - Copy Endpoint URL
   - Note the deployment name from step 3
   ```

### Step 2: Configure Zen MCP Server

1. **Edit `.env` file:**
   ```env
   # Azure OpenAI Configuration (all 4 required)
   AZURE_OPENAI_API_KEY=your_key_from_step_4
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_VERSION=2025-04-01-preview
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt5-prod  # Your deployment name from step 3

   # Set as default model (optional)
   DEFAULT_MODEL=gpt-5  # or gpt-5-codex
   ```

2. **Verify Configuration:**
   ```bash
   # Check environment variables
   grep "AZURE_OPENAI" .env

   # Start server
   ./run-server.sh

   # Check logs for successful registration
   tail -f logs/mcp_server.log | grep "Azure"
   ```

### Step 3: Test the Setup

In Claude, test with:
```
"Use gpt-5 to explain the architecture of this codebase"
"Use gpt-5-codex to refactor this function for better performance"
```

## Technical Constraints

### Responses API Format

The Responses API uses a different format than Chat Completions:

**Request Structure:**
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 1.0,  // Must be exactly 1.0
  "max_output_tokens": 4096  // Minimum 16
}
```

**Response Structure:**
```json
{
  "output_text": "Generated response here...",
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 500,
    "total_tokens": 650,
    "reasoning_tokens": 2000  // Internal thinking tokens (not visible)
  }
}
```

### Reasoning Tokens

GPT-5 models use internal "reasoning tokens" that:
- Are not visible in the response
- Contribute to processing time
- Enable advanced problem-solving
- Don't count against output token limits
- Can be substantial (thousands of tokens)

### Error Handling

Common errors and their solutions:

| Error Code | Message | Solution |
|------------|---------|----------|
| 400 | "Unsupported value" for temperature | Server auto-sets to 1.0, check logs |
| 400 | "max_output_tokens must be at least 16" | Increase to minimum 16 |
| 401 | "Unauthorized" | Check API key validity |
| 404 | "Deployment not found" | Verify deployment name |
| 429 | "Rate limit exceeded" | Check TPM quota in Azure |

## Best Practices

### When to Use GPT-5 vs GPT-5-Codex

**Use GPT-5 when you need:**
- General reasoning and analysis
- Architecture design and planning
- Image/diagram understanding
- Business logic and documentation
- Multi-domain problem solving

**Use GPT-5-Codex when you need:**
- Code generation and completion
- Refactoring and optimization
- Technical documentation
- Bug fixing and debugging
- API design and implementation

### Optimal Workflows

1. **Architecture Review with Images:**
   ```
   "Use gpt-5 to analyze this architecture diagram and identify bottlenecks"
   ```

2. **Code Generation Pipeline:**
   ```
   "Use gpt-5 to design the API structure, then use gpt-5-codex to implement it"
   ```

3. **Comprehensive Code Review:**
   ```
   "Use gpt-5-codex for code quality review, then gpt-5 for architectural implications"
   ```

### Token Management

With 400K context and 128K output capacity:

- **Batch Processing**: Process entire codebases in single requests
- **Detailed Analysis**: Request comprehensive reports without truncation
- **Context Preservation**: Include extensive history and documentation
- **Full Implementations**: Generate complete modules, not just snippets

## Cost Optimization

### Understanding Pricing

Azure OpenAI charges per 1K tokens:
- Input tokens (prompt)
- Output tokens (completion)
- Reasoning tokens (internal, may be charged separately)

### Optimization Strategies

1. **Use GPT-5-Codex only for code tasks**
   - Higher intelligence score but same cost
   - Specialized for programming

2. **Leverage the large context window**
   - Batch multiple questions in one request
   - Include all relevant context upfront

3. **Monitor token usage**
   ```bash
   # Check logs for token consumption
   grep "usage" logs/mcp_server.log | tail -20
   ```

4. **Set appropriate TPM limits in Azure**
   - Prevents unexpected costs
   - Ensures predictable billing

## Integration Patterns

### Multi-Model Workflows

**Pattern 1: Design → Implement → Review**
```
"Use gpt-5 to design the system architecture,
then gpt-5-codex to implement the core modules,
finally gemini pro to review the implementation"
```

**Pattern 2: Vision → Code → Test**
```
"Use gpt-5 to analyze this UI mockup image,
then gpt-5-codex to generate the React components,
finally o3 to create comprehensive tests"
```

### Conversation Threading

The Zen MCP Server maintains context across model switches:

```python
# Step 1: GPT-5 analyzes requirements
"Use gpt-5 to analyze these requirements and create a technical spec"

# Step 2: GPT-5-Codex implements (knows about step 1)
"Now use gpt-5-codex to implement based on the spec"

# Step 3: Review with another model (knows about steps 1 & 2)
"Use gemini pro to review if the implementation matches the spec"
```

## Troubleshooting

### Quick Diagnostic Checklist

- [ ] All 4 Azure environment variables set?
- [ ] API version is 2025-03-01-preview or later?
- [ ] Deployment name matches exactly (case-sensitive)?
- [ ] Endpoint includes `https://` prefix?
- [ ] API key is valid and not expired?
- [ ] Model deployment is in "Succeeded" state?
- [ ] Quota/TPM limits not exceeded?

### Debug Commands

```bash
# Test Azure connectivity
curl -I https://your-resource.openai.azure.com

# Check provider registration
grep "Azure OpenAI provider registered" logs/mcp_server.log

# Monitor API calls
tail -f logs/mcp_server.log | grep -E "(Azure|GPT-5|Responses)"

# View token usage
grep "reasoning_tokens" logs/mcp_server.log
```

### Getting Help

1. Check [AZURE_OPENAI_TROUBLESHOOTING.md](AZURE_OPENAI_TROUBLESHOOTING.md)
2. Review server logs: `logs/mcp_server.log`
3. Verify Azure Portal settings
4. Contact Azure support for quota/access issues

## Frequently Asked Questions

**Q: Can I change the temperature for GPT-5 models?**
A: No, temperature is fixed at 1.0 for all Azure GPT-5 models. This is an Azure platform constraint.

**Q: Why use Responses API instead of Chat Completions?**
A: GPT-5-Codex requires Responses API. For consistency, both models use the same API.

**Q: Can I use multiple GPT-5 deployments?**
A: Yes, but only one at a time. Change `AZURE_OPENAI_DEPLOYMENT_NAME` to switch.

**Q: How do reasoning tokens affect billing?**
A: Reasoning tokens are internal and may be billed separately. Check Azure pricing documentation.

**Q: Can I use GPT-5 for image generation?**
A: No, GPT-5 supports image analysis (input) but not generation (output).

**Q: What's the difference in response time?**
A: GPT-5-Codex is optimized for code and may be faster for programming tasks. GPT-5 may take longer due to broader reasoning.

**Q: Can I use streaming with GPT-5?**
A: Final output can stream, but reasoning tokens are processed internally first.

**Q: Is GPT-5-Codex better than GPT-5 for all code tasks?**
A: Generally yes, but GPT-5 might be better for high-level architecture and design discussions.

## Summary

Azure OpenAI's GPT-5 and GPT-5-Codex models offer unprecedented capabilities with their 400K context and 128K output capacity. By understanding their constraints (Responses API only, temperature=1.0, min 16 tokens) and following best practices, you can leverage these powerful models effectively in your workflows.

Key takeaways:
- Always use Responses API, not Chat Completions
- Temperature is fixed at 1.0 (non-negotiable)
- Minimum 16 output tokens required
- GPT-5 for general + vision, GPT-5-Codex for code
- Leverage the massive context window for comprehensive analysis
- Combine with other models for optimal workflows

For additional help, refer to the [main documentation](index.md) or [troubleshooting guide](AZURE_OPENAI_TROUBLESHOOTING.md).