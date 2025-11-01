# Z.AI Integration Installation Guide

## 📦 What's in the zip file

The `zai-integration.zip` file contains all the files needed to add Z.AI GLM model support to your zen-mcp-server installation:

**Core Provider Files:**
- `providers/zai.py` - Z.AI provider implementation (NEW)
- `providers/__init__.py` - Updated to export ZAIProvider
- `providers/registry.py` - Updated with Z.AI provider registration
- `providers/shared/provider_type.py` - Added ZAI provider type
- `server.py` - Updated to initialize Z.AI provider

**Setup & Documentation:**
- `setup-zai.sh` - Automated setup script
- `README-ZAI.md` - Complete usage documentation
- `docs/zai-integration.md` - Technical integration details

## 🚀 Installation Instructions

### Option 1: Using the Automated Script (Recommended)

1. **Extract the zip file** in your zen-mcp-server directory:
   ```bash
   cd /path/to/zen-mcp-server
   unzip zai-integration.zip
   ```

2. **Run the setup script**:
   ```bash
   ./setup-zai.sh
   ```

   The script will:
   - Prompt you for your Z.AI API Key
   - Set up the Python virtual environment
   - Install dependencies
   - Configure the .env file
   - Register MCP server with Claude Code
   - Test the connection

3. **Restart Claude Code**:
   ```bash
   exit  # Exit current Claude session
   claude  # Start new session
   ```

4. **Test the integration**:
   ```bash
   zen chat with glm
   ```

### Option 2: Manual Installation

1. **Extract the zip file**:
   ```bash
   cd /path/to/zen-mcp-server
   unzip zai-integration.zip
   ```

2. **Get your Z.AI API Key**:
   - Visit: https://z.ai/manage-apikey/apikey-list
   - Copy your API key

3. **Update .env file**:
   ```bash
   echo "ZAI_API_KEY=your_api_key_here" >> .env
   ```

4. **Run the main setup**:
   ```bash
   ./run-server.sh
   ```

5. **Configure Claude MCP**:
   ```bash
   source .env
   claude mcp remove zen -s local
   claude mcp add zen "$(pwd)/.zen_venv/bin/python" "$(pwd)/server.py" \
     --env ZAI_API_KEY="$ZAI_API_KEY" \
     --env LOG_LEVEL=INFO
   ```

6. **Restart Claude Code** and test

## ✅ Verification

After installation, verify everything is working:

```bash
# Check MCP status
claude mcp list
# Should show: zen ✓ Connected

# Check server logs
tail -20 logs/mcp_server.log | grep "Z.AI"
# Should show: "Z.AI API key found - GLM models available"

# Test the model
zen chat with glm
```

## 📄 Files Explained

- **providers/zai.py**: Implements the Z.AI provider with the correct Coding API endpoint (`https://api.z.ai/api/coding/paas/v4`)
- **providers/__init__.py**: Exports ZAIProvider for use in server.py
- **providers/registry.py**: Adds Z.AI to provider priority list and API key mapping
- **providers/shared/provider_type.py**: Defines the ZAI provider type enum
- **server.py**: Initializes and registers Z.AI provider on server startup
- **setup-zai.sh**: Automated setup script (recommended)
- **README-ZAI.md**: Complete documentation with usage examples and troubleshooting

## 🔧 What Gets Modified

The zip file will **overwrite** these existing files:
- `providers/__init__.py`
- `providers/registry.py`
- `providers/shared/provider_type.py`
- `server.py`

And **add** these new files:
- `providers/zai.py`
- `setup-zai.sh`
- `README-ZAI.md`
- `docs/zai-integration.md`

**Important**: If you have local modifications to the overwritten files, back them up first!

## 🌐 Key Technical Details

**Endpoint Used**: `https://api.z.ai/api/coding/paas/v4`
- This is Z.AI's **Coding API** endpoint
- Optimized for development tools and IDEs
- Different from the common API endpoint (`/api/paas/v4`)
- Using the wrong endpoint causes "Insufficient balance" errors even with valid keys

**Model Aliases**:
- `glm`, `glm-4`, `glm-4.6`, `glm4.6` all resolve to GLM-4.6

**Model Capabilities**:
- 128K context window
- Extended thinking support
- Multimodal (image support)
- JSON mode
- Function calling

## 🔍 Troubleshooting

**"Insufficient balance" error even with valid subscription**:
- This was the original issue! Make sure `providers/zai.py` uses the **Coding API endpoint**
- Check line 44: should be `https://api.z.ai/api/coding/paas/v4`

**MCP server not connecting**:
- Restart Claude Code (exit and start new session)
- Check: `claude mcp list`
- View logs: `tail -f logs/mcp_server.log`

**Model not found**:
- Restart Claude Code
- Verify server logs show "Z.AI API key found"
- Check `.env` has `ZAI_API_KEY=...`

For detailed troubleshooting, see **README-ZAI.md** included in the zip.

## 📚 Next Steps

After successful installation:

1. Read **README-ZAI.md** for usage examples
2. Try different zen tools: `chat`, `thinkdeep`, `codereview`, etc.
3. Check out **docs/zai-integration.md** for technical details

## 🆘 Need Help?

- Check logs: `tail -f logs/mcp_server.log`
- Verify API key: https://z.ai/manage-apikey/apikey-list
- Review README-ZAI.md troubleshooting section
- Ensure you restarted Claude Code after installation
