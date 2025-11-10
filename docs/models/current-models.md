# Current Configured Models Analysis

This document provides a comprehensive analysis of the AI models currently configured in the Zen MCP Server for LLM selection and optimization.

## 📋 Important Notes

### Provider Attribution
OpenRouter routes models through multiple infrastructure providers for redundancy, cost optimization, and load balancing. You may see Anthropic models showing "Google" as the provider in API responses - this is normal OpenRouter behavior and does not affect model capabilities or quality. The routing is transparent and ensures high availability.

### Recent Configuration Changes (2025-11-10)
- **Removed**: Claude Opus 4.1 ($75/M - eliminated ultra-premium tier)
- **Added**: 4 new high-value models including Qwen VL 235B for OCR, Grok Code Fast for coding, Qwen Coder for budget development, and GLM 4.6 for provider diversification
- **Current Count**: 24 models (was 21)
- **Cost Savings**: ~$50/M by removing Opus 4.1 and adding cost-efficient alternatives

## Model Selection Summary

**Total Models**: 24  
**Free Models**: 9 (37.5%)  
**Paid Models**: 15 (62.5%)  
**Context Range**: 65K to 1,048K tokens  

## Model Rankings and Specifications

| Rank | Model | Tier | Status | Context | Input Cost | Output Cost | Key Strengths |
|------|-------|------|--------|---------|------------|-------------|---------------|
| 1 | anthropic/claude-opus-4.1 | Premium | PAID | 200K | $15/M | $75/M | World's best coding (72.5% SWE-bench) |
| 2 | openai/gpt-5 | Premium | PAID | 400K | $2/M | $8/M | Software-on-demand (74.9% SWE-bench) |
| 3 | anthropic/claude-sonnet-4 | Premium | PAID | 200K | $3/M | $15/M | Balanced performance (72.7% SWE-bench) |
| 4 | openai/o3 | High-Perf | PAID | 200K | $2/M | $10/M | Advanced reasoning (ELO 2706) |
| 5 | openai/o4-mini | High-Perf | PAID | 200K | ~$0.15/M | ~$0.6/M | Latest balanced model |
| 6 | openai/o3-mini | High-Perf | PAID | 200K | ~$0.2/M | ~$0.8/M | Cost-efficient reasoning |
| 7 | google/gemini-2.5-pro | High-Perf | PAID | 1048K | $1.25-2.5/M | $10-15/M | Massive context, UI development |
| 8 | google/gemini-2.5-flash | High-Perf | PAID | 1048K | $0.075/M | $0.30/M | Speed + large context |
| 9 | deepseek/deepseek-r1-0528 | Open Source | PAID | 65K | $0.55/M | $2.19/M | Matches O1 performance |
| 10 | qwen/qwen3-coder | Open Source | PAID | 131K | $0.20/M | $0.80/M | Coding specialist (85% HumanEval) |
| 11 | deepseek/deepseek-r1-distill-llama-70b:free | Free Champion | FREE | 131K | $0/M | $0/M | Best free reasoning model |
| 12 | meta-llama/llama-3.1-405b-instruct:free | Free Champion | FREE | 131K | $0/M | $0/M | Largest free model (80.5% HumanEval) |
| 13 | qwen/qwen-2.5-coder-32b-instruct:free | Free Champion | FREE | 131K | $0/M | $0/M | Free coding specialist |
| 14 | meta-llama/llama-4-maverick:free | Free Tier | FREE | 131K | $0/M | $0/M | Latest Meta architecture |
| 15 | meta-llama/llama-3.3-70b-instruct:free | Free Tier | FREE | 131K | $0/M | $0/M | Efficient 70B performance |
| 16 | qwen/qwen2.5-vl-72b-instruct:free | Free Tier | FREE | 131K | $0/M | $0/M | Vision-language capabilities |
| 17 | microsoft/phi-4-reasoning:free | Free Tier | FREE | 131K | $0/M | $0/M | Debugging specialist |
| 18 | qwen/qwq-32b:free | Free Tier | FREE | 131K | $0/M | $0/M | Free reasoning model |
| 19 | moonshotai/kimi-k2:free | Free Tier | FREE | 200K | $0/M | $0/M | Alternative provider |
| 20 | openai/gpt-5-mini | Supporting | PAID | 400K | ~$0.50/M | ~$2/M | Speed-optimized GPT-5 |
| 21 | openai/gpt-5-nano | Supporting | PAID | 400K | ~$0.20/M | ~$0.80/M | Lightweight GPT-5 |
| 22 | openai/gpt-5-chat | Supporting | PAID | 400K | ~$2/M | ~$8/M | Conversation-optimized |
| 23 | mistralai/mistral-large-2411 | Supporting | PAID | 128K | $2/M | $6/M | European alternative |
| 24 | moonshotai/kimi-k2 | Supporting | PAID | 200K | $0.15/M | $2.50/M | Chinese provider option |

## Model Selection Guidelines by Task Type

### 🏆 Best Overall Coding Models
1. **Claude Opus 4.1** - Premium choice for complex, multi-file coding tasks
2. **GPT-5** - Excellent value premium model for software generation
3. **Claude Sonnet 4** - Balanced performance for production coding

### 💰 Best Value Models
1. **Gemini 2.5 Flash** - Ultra-efficient with 1M+ context at $0.075/$0.30/M
2. **DeepSeek R1** - Near-premium performance at $0.55/$2.19/M
3. **Qwen3 Coder** - Specialized coding at $0.20/$0.80/M

### 🆓 Best Free Models
1. **meta-llama/llama-3.1-405b-instruct:free** - Largest free model, 80.5% HumanEval
2. **deepseek/deepseek-r1-distill-llama-70b:free** - Best free reasoning
3. **qwen/qwen-2.5-coder-32b-instruct:free** - Free coding specialist

### 🧠 Best Reasoning Models
1. **OpenAI O3** - ELO 2706 competitive programming
2. **DeepSeek R1** - Matches OpenAI O1 at fraction of cost
3. **Claude Opus 4.1** - Sustained reasoning over hours

### ⚡ Best Speed/Efficiency
1. **Gemini 2.5 Flash** - 20-30% fewer tokens, massive context
2. **O4-mini** - Latest balanced model with fast reasoning
3. **GPT-5 variants** - Speed-optimized options

### 🎯 Specialized Use Cases
- **UI/Web Development**: Gemini 2.5 Pro (#1 WebDev Arena)
- **Debugging**: Microsoft Phi-4 Reasoning (free)
- **Vision Tasks**: Qwen 2.5 VL 72B (free)
- **Long Context**: Gemini models (1M+ tokens)
- **Multilingual**: Qwen models (92+ languages)

## Cost Analysis

### Premium Tier ($10+ output/M)
- Claude Opus 4.1: $15/$75/M - Top performance
- Claude Sonnet 4: $3/$15/M - Balanced premium
- OpenAI O3: $2/$10/M - Advanced reasoning
- Gemini 2.5 Pro: $1.25-2.5/$10-15/M - Context-dependent

### Value Tier ($1-10 output/M)
- GPT-5: $2/$8/M - Premium performance at lower cost
- Mistral Large 2411: $2/$6/M - European alternative
- Kimi K2: $0.15/$2.50/M - Alternative provider
- DeepSeek R1: $0.55/$2.19/M - Open source leader

### Economy Tier (<$1 output/M)
- Qwen3 Coder: $0.20/$0.80/M - Coding specialist
- O4-mini: ~$0.15/$0.6/M - Latest balanced
- O3-mini: ~$0.2/$0.8/M - Reasoning on budget
- Gemini Flash: $0.075/$0.30/M - Ultra-efficient

### Free Tier ($0/M)
9 models with zero cost, including top performers:
- Llama 3.1 405B, DeepSeek R1 Distill, Qwen Coder variants

## Benchmark Performance

### SWE-bench (Software Engineering)
- GPT-5: 74.9%
- Claude Opus 4.1: 72.5%
- Claude Sonnet 4: 72.7% (80.2% high-compute)

### HumanEval (Code Generation)
- Qwen models: 85%+
- Llama 3.1 405B: 80.5%
- Most models: 70-85% range

### Competitive Programming
- OpenAI O3: ELO 2706 (89th percentile)
- Advanced reasoning models excel

## Provider Information

All models are accessed through **OpenRouter** with a single API key, providing:
- Unified access to 24 models from 6+ providers
- Transparent pricing with no markup
- Automatic failover and load balancing
- Usage tracking and cost optimization

## Usage Recommendations

**For Auto Selection**: Models are ranked by capability and cost-effectiveness. The system will automatically select the best model based on task requirements.

**For Manual Selection**: Choose based on:
- Budget constraints (free vs paid tiers)
- Context requirements (65K to 1M+ tokens)
- Task type (coding, reasoning, vision, etc.)
- Performance requirements (speed vs quality)

**Last Updated**: 2025-08-08
**Configuration Source**: OpenRouter via `.env` OPENROUTER_ALLOWED_MODELS`