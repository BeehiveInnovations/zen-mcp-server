<div align="center">

#### Recommended AI Stack

<details>
<summary>For Claude Code Users</summary>

For best results when using [Claude Code](https://claude.ai/code):  

- **Sonnet 4.5** – All agentic work and orchestration  
- **Gemini 2.5 Pro** OR **GPT-5-Pro** – Deep thinking, code reviews, debugging, pre-commit analysis
</details>

<details>
<summary>For Codex Users</summary>

For best results when using [Codex CLI](https://developers.openai.com/codex/cli):  

- **GPT-5 Codex Medium** – All agentic work and orchestration  
- **Gemini 2.5 Pro** OR **GPT-5-Pro** – Deep thinking, code reviews, debugging, pre-commit analysis
</details>

## Quick Start (5 minutes)

**Prerequisites:**  
- Python 3.10+  
- Git  
- [uv installed](https://docs.astral.sh/uv/getting-started/installation/)

### 1. Get API Keys (choose one or more)
- **[OpenRouter](https://openrouter.ai/)** – Access multiple models with one API  
- **[Gemini](https://makersuite.google.com/app/apikey)** – Google's latest models  
- **[OpenAI](https://platform.openai.com/api-keys)** – O3, GPT-5 series  
- **[Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/)** – Enterprise deployments  
- **[X.AI](https://console.x.ai/)** – Grok models  
- **[DIAL](https://dialx.ai/)** – Vendor-agnostic model access  
- **[Ollama](https://ollama.ai/)** – Local models (free)

### 2. Install (choose one)

**Option A: Clone and Automatic Setup (recommended)**
```bash
git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
cd zen-mcp-server

# Handles everything: setup, config, API keys from system environment. 
# Auto-configures Claude Desktop, Claude Code, Gemini CLI, Codex CLI, Qwen CLI
# Enable / disable additional settings in .env
./run-server.sh
