# Z.AI Integration for Zen MCP Server

This guide explains how to set up and use Z.AI's GLM models with the Zen MCP Server in Claude Code.

## 🚀 Quick Start

### Prerequisites

- Claude Code CLI installed
- Git installed
- Python 3.9+ installed
- A Z.AI account with API access

### Installation Steps

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone <zen-mcp-server-repo-url>
   cd zen-mcp-server
   ```

2. **Get your Z.AI API Key**:
   - Visit: https://z.ai/manage-apikey/apikey-list
   - Sign in or create an account
   - Generate an API key (format: `xxxxxxxx.yyyyyyyy`)
   - Copy the key

3. **Run the setup script**:
   ```bash
   ./setup-zai.sh
   ```

   The script will:
   - Prompt you for your Z.AI API Key
   - Set up the Python virtual environment
   - Install all dependencies
   - Configure the .env file
   - Register the MCP server with Claude Code

4. **Restart Claude Code**:
   ```bash
   exit  # Exit current Claude session
   claude  # Start new session
   ```

5. **Test the integration**:
   ```bash
   zen chat with glm
   ```

## 📋 What's Included

### Z.AI Provider

The Z.AI provider (`providers/zai.py`) includes:

- **Endpoint**: `https://api.z.ai/api/coding/paas/v4` (Coding API optimized for development tools)
- **Model**: GLM-4.6 with 128K context window
- **Capabilities**:
  - Extended thinking support
  - JSON mode
  - Function calling
  - Image support (multimodal)
  - Temperature control

### Model Aliases

You can use any of these aliases to access GLM-4.6:
- `glm`
- `glm-4`
- `glm-4.6`
- `glm4.6`

## 🔧 Manual Configuration

If the setup script doesn't work or you prefer manual setup:

### 1. Configure .env file

Edit `.env` and add:
```bash
ZAI_API_KEY=your_zai_api_key_here
```

### 2. Run the main setup script

```bash
./run-server.sh
```

### 3. Configure Claude Code MCP

```bash
# Remove old configuration
claude mcp remove zen -s local

# Add new configuration with Z.AI key
source .env
claude mcp add zen "$(pwd)/.zen_venv/bin/python" "$(pwd)/server.py" \
  --env ZAI_API_KEY="$ZAI_API_KEY" \
  --env LOG_LEVEL=INFO
```

### 4. Restart Claude Code

Exit and restart your Claude Code session for changes to take effect.

## 💡 Usage Examples

### Basic Chat
```bash
zen chat with glm and say hello
```

### Deep Thinking
```bash
zen thinkdeep with glm about architectural patterns for microservices
```

### Code Review
```bash
zen codereview with glm focusing on security
```

### Consensus Building
```bash
zen consensus with multiple models including glm
```

### Planning
```bash
zen planner with glm for project architecture
```

## 🔍 Troubleshooting

### Error: "Insufficient balance or no resource package"

This error occurs when:
- Using the wrong API endpoint (common API vs. coding API)
- API key is not valid or expired
- Subscription doesn't cover API usage

**Solution**:
- Verify you're using the **Coding API** endpoint: `https://api.z.ai/api/coding/paas/v4`
- Check your subscription at https://z.ai
- Ensure your API key is active

### Error: "Model 'glm-4.6' is not available"

This means the MCP server hasn't restarted with the new configuration.

**Solution**:
1. Restart Claude Code completely (exit and restart)
2. Check MCP status: `claude mcp list`
3. Verify zen MCP shows as "Connected"

### Check Server Logs

```bash
# View recent logs
tail -50 logs/mcp_server.log

# Follow logs in real-time
tail -f logs/mcp_server.log

# Search for Z.AI related logs
grep -i "zai\|glm" logs/mcp_server.log
```

### Verify Configuration

```bash
# Check MCP server status
claude mcp list

# Should show:
# zen ✓ Connected

# Check if Z.AI provider is initialized
grep "Z.AI" logs/mcp_server.log
# Should show: "Z.AI API key found - GLM models available"
```

## 🌐 API Endpoints

Z.AI provides different API endpoints for different use cases:

| Endpoint | Purpose | URL |
|----------|---------|-----|
| **Coding API** (Used) | Development tools, IDEs | `https://api.z.ai/api/coding/paas/v4` |
| Common API | General applications | `https://api.z.ai/api/paas/v4` |
| Anthropic Proxy | Claude Code (alternative) | `https://api.z.ai/api/anthropic` |

**Note**: This integration uses the **Coding API** which is optimized for development tools and typically has better pricing for coding tasks.

## 📊 Model Capabilities

**GLM-4.6 Specifications:**
- Context Window: 128,000 tokens
- Max Output: 8,000 tokens
- Multimodal: Yes (images up to 10MB)
- Extended Thinking: Yes
- JSON Mode: Yes
- Function Calling: Yes
- Temperature Control: Yes
- Intelligence Score: 85/100

## 🔐 Security Notes

- Never commit your `.env` file to version control
- Keep your Z.AI API key secure
- The `.env` file is included in `.gitignore`
- API keys are passed to the MCP server via environment variables
- Logs do not contain full API keys (truncated in logs)

## 📚 Additional Resources

- **Z.AI Documentation**: https://docs.z.ai
- **API Key Management**: https://z.ai/manage-apikey/apikey-list
- **Z.AI Claude Integration**: https://docs.z.ai/devpack/tool/claude
- **Z.AI Cline Integration**: https://docs.z.ai/devpack/tool/cline
- **Zen MCP Server Docs**: See main README.md

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs: `tail -f logs/mcp_server.log`
3. Verify API key at https://z.ai/manage-apikey/apikey-list
4. Ensure you've restarted Claude Code after configuration
5. Test the API directly with curl (see script for example)

## ✅ Verification Checklist

After setup, verify:

- [ ] Z.AI API key is in `.env` file
- [ ] `providers/zai.py` exists and uses coding endpoint
- [ ] Virtual environment created: `.zen_venv/` exists
- [ ] MCP configured: `claude mcp list` shows zen as Connected
- [ ] Claude Code restarted
- [ ] Test command works: `zen chat with glm`
- [ ] Server logs show: "Z.AI API key found - GLM models available"

## 🔄 Updating

To update the Z.AI integration:

```bash
cd zen-mcp-server
git pull
./setup-zai.sh
# Restart Claude Code
```

## 📝 Notes

- **Restart Required**: Always restart Claude Code after configuration changes
- **Coding Endpoint**: The integration uses Z.AI's Coding API endpoint which is optimized for development tools
- **Cost Effective**: The Coding API typically offers better pricing for coding-related tasks
- **Multiple Installs**: You can run this setup on multiple machines - just clone the repo and run `./setup-zai.sh`
