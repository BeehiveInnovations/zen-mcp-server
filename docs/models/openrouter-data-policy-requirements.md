# OpenRouter Data Policy Requirements for Free Models

**Last Updated:** 2025-11-10

---

## Overview

OpenRouter offers free models in exchange for data policy agreements. Some models require users to opt-in to specific privacy policies before they can be used.

**Important:** Models that require data policy opt-ins are **valid models** - they just need user configuration. They should NOT be removed from models.csv.

---

## Error Messages

### Data Policy Required (Valid Model)

**Error Pattern:**
```
Error code: 404
Message: 'No endpoints found matching your data policy (Free model training)'
```

or

```
Error code: 404
Message: 'No endpoints found matching your data policy (Free model publication)'
```

**Meaning:** Model exists but requires OpenRouter privacy setting opt-in

**Action:**
- ✅ Keep model in models.csv (valid)
- ⚙️  User needs to configure OpenRouter settings
- 🔄 Failover system will skip and try next model

---

### Model Not Found (Potentially Deprecated)

**Error Pattern:**
```
Error code: 404
Message: 'No endpoints found for [model-name]'
```

**Meaning:** Model may have been removed from OpenRouter

**Action:**
- ⚠️  Consider marking as deprecated in models.csv
- 🔍 Verify on https://openrouter.ai/models
- 🔄 Failover system will skip and try next model

---

## Required Data Policies

### Training Policy

**Setting:** "Allow training on prompts"
**URL:** https://openrouter.ai/settings/privacy

**Affected Models:**
- qwen/qwen-2.5-coder-32b-instruct:free
- qwen/qwen3-235b-a22b:free
- qwen/qwen3-32b:free
- qwen/qwen3-14b:free
- qwen/qwq-32b:free
- qwen/qwen2.5-vl-72b-instruct:free
- Most Qwen models

**What It Means:**
- OpenRouter may use your prompts to improve Qwen models
- Prompts are anonymized
- You can opt-out anytime

---

### Publication Policy

**Setting:** "Allow publication"
**URL:** https://openrouter.ai/settings/privacy

**Affected Models:**
- moonshotai/kimi-k2:free
- Most Moonshot/Kimi models

**What It Means:**
- OpenRouter may publish your prompts anonymously
- Used for research and model improvement
- You can opt-out anytime

---

## Models Without Policy Requirements

These models work without data policy opt-ins:

**DeepSeek Models:**
- deepseek/deepseek-chat:free
- deepseek/deepseek-r1-distill-llama-70b:free
- deepseek/deepseek-r1-0528-qwen3-8b:free

**Microsoft Models:**
- microsoft/phi-4-reasoning:free
- microsoft/mai-ds-r1:free

**Meta Models (varies):**
- meta-llama/llama-3.3-70b-instruct:free (may work)
- meta-llama/llama-3.2-11b-vision-instruct:free (may work)
- meta-llama/llama-3.2-3b-instruct:free (may work)

**Other:**
- mistralai/mistral-nemo:free
- openrouter/cypher-alpha:free
- tngtech/deepseek-r1t-chimera:free

---

## How Smart Failover Handles This

### Automatic Detection

The tiered_consensus failover system automatically detects data policy errors:

```python
if "data policy" in error_message:
    logger.info("Model requires OpenRouter data policy opt-in. Skipping.")
    # Try next model in failover pool
elif "no endpoints found for" in error_message:
    logger.warning("Model not found on OpenRouter (may be deprecated). Skipping.")
    # Try next model in failover pool
```

### User Experience

**Without Configuration:**
```
Try qwen/qwen-2.5-coder:free → Data policy required
⚙️  Model requires OpenRouter data policy opt-in. Skipping.
Try deepseek/deepseek-r1-distill:free → Success ✅
```

**With Configuration:**
```
Try qwen/qwen-2.5-coder:free → Success ✅ (policy enabled)
```

---

## Configuring OpenRouter Privacy Settings

### Step-by-Step

1. **Log in** to OpenRouter: https://openrouter.ai
2. **Navigate** to Settings → Privacy: https://openrouter.ai/settings/privacy
3. **Enable policies** as desired:
   - ☑️ "Allow training on prompts" (for Qwen models)
   - ☑️ "Allow publication" (for Moonshot models)
4. **Save changes**
5. **Test** tiered_consensus Level 1 again

### Privacy Considerations

**If you enable training:**
- ✅ Qwen models will work
- ⚠️  Your prompts may be used for training
- ℹ️  Prompts are anonymized
- 🔒 You can revoke anytime

**If you enable publication:**
- ✅ Moonshot models will work
- ⚠️  Your prompts may be published anonymously
- ℹ️  Used for research purposes
- 🔒 You can revoke anytime

**If you don't enable:**
- ❌ Policy-required models won't work
- ✅ Smart failover uses alternative models automatically
- 💰 May fall back to economy models (~$0.003 each)
- ✅ Still get real AI responses

---

## Model Status in models.csv

### Valid Models (Keep)

**Requires Training Policy:**
```csv
qwen/qwen-2.5-coder-32b-instruct:free,qwen,free,paid,131K,0.0,0.0,...
```
✅ Valid - Just needs configuration

**Requires Publication Policy:**
```csv
moonshotai/kimi-k2:free,moonshot,free,paid,200K,0.0,0.0,...
```
✅ Valid - Just needs configuration

**No Policy Required:**
```csv
deepseek/deepseek-chat:free,deepseek,free,paid,131K,0.0,0.0,...
```
✅ Valid - Works immediately

### Potentially Deprecated (Review)

**Model Not Found:**
```csv
meta-llama/llama-3.1-405b-instruct:free,meta,free,deprecated?,131K,0.0,0.0,...
```
⚠️  Returns "No endpoints found for model" - May be deprecated

**Action:** Verify on OpenRouter and update status if confirmed unavailable

---

## Recommendations

### For Privacy-Conscious Users

**Option 1:** Don't enable data policies
- Use smart failover to automatically find working models
- Accept occasional economy model fallback (~$0.003)
- Average cost: $0-$0.01 per Level 1 consensus

**Option 2:** Use Level 2 instead
- 6 models (3 free + 3 economy)
- More reliable (economy models don't need policies)
- Cost: ~$0.01 per consensus
- Better quality responses

### For Maximum Free Tier

**Enable Both Policies:**
- Access to all 20 free models
- Higher chance of $0 cost
- Smart failover more effective

---

## Monitoring

### Check Logs for Policy Errors

```bash
tail -f logs/mcp_server.log | grep "data policy"
```

**If you see many data policy errors:**
- Consider enabling policies
- Or accept economy model fallbacks
- Or use Level 2+ for reliability

### Track Failover Success Rate

```bash
grep -E "(Failover successful|All models failed)" logs/mcp_server.log | tail -20
```

**Good:** Mostly "Failover successful"
**Bad:** Many "All models failed" → Consider configuration

---

## Summary

| Error Type | Meaning | Model Status | Action |
|------------|---------|--------------|--------|
| "data policy (training)" | Needs opt-in | ✅ Valid | Keep in models.csv |
| "data policy (publication)" | Needs opt-in | ✅ Valid | Keep in models.csv |
| "No endpoints found for [model]" | Not found | ⚠️  Check | Verify & possibly deprecate |

**Key Insight:** Data policy errors indicate **valid models needing configuration**, NOT deprecated models.

---

**Last Updated:** 2025-11-10
**Maintainer:** Dev Team
