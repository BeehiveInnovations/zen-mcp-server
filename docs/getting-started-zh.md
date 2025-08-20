# Zen MCP服务器入门指南

本指南将引导您从零开始设置Zen MCP服务器，包括安装、配置和首次使用。

## 前置要求

- **Python 3.10+**（推荐3.12）
- **Git**
- **[已安装uv](https://docs.astral.sh/uv/getting-started/installation/)**（用于uvx方法）
- **Windows用户**：Claude Code CLI需要WSL2

## 步骤1：获取API密钥

您至少需要一个API密钥。根据您的需求选择：

### 选项A：OpenRouter（推荐新手使用）
**一个API访问多个模型**
- 访问[OpenRouter](https://openrouter.ai/)并注册
- 生成API密钥
- 在仪表板中控制支出限制
- 通过一个API访问GPT-4、Claude、Gemini等更多模型

### 选项B：原生提供商API

**Gemini（Google）：**
- 访问[Google AI Studio](https://makersuite.google.com/app/apikey)
- 生成API密钥
- **注意**：对于Gemini 2.5 Pro，请使用付费API密钥（免费层访问受限）

**OpenAI：**
- 访问[OpenAI平台](https://platform.openai.com/api-keys)
- 生成API密钥以访问O3、GPT-5

**X.AI（Grok）：**
- 访问[X.AI控制台](https://console.x.ai/)
- 生成API密钥以访问Grok模型

**DIAL平台：**
- 访问[DIAL平台](https://dialx.ai/)
- 生成API密钥以获得厂商无关的模型访问

### 选项C：本地模型（免费）

**Ollama：**
```bash
# 安装Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 启动Ollama服务
ollama serve

# 拉取模型（如Llama 3.2）
ollama pull llama3.2
```

**其他本地选项：**
- **vLLM**：自托管推理服务器
- **LM Studio**：带有OpenAI兼容API的本地模型托管
- **Text Generation WebUI**：流行的本地界面

👉 **[完整自定义模型设置指南](custom_models.md)**

## 步骤2：安装

选择您首选的安装方法：

### 方法A：使用uvx即时设置（推荐）

**前置要求**：[先安装uv](https://docs.astral.sh/uv/getting-started/installation/)

**对于Claude Desktop：**
1. 打开Claude Desktop → 设置 → 开发者 → 编辑配置
2. 添加此配置：

```json
{
  "mcpServers": {
    "zen": {
      "command": "sh",
      "args": [
        "-c", 
        "exec $(which uvx || echo uvx) --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server"
      ],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:~/.local/bin",
        "GEMINI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**对于Claude Code CLI：**
在项目根目录创建`.mcp.json`：

```json
{
  "mcpServers": {
    "zen": {
      "command": "sh", 
      "args": [
        "-c",
        "exec $(which uvx || echo uvx) --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server"
      ],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:~/.local/bin",
        "GEMINI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**对于Gemini CLI：**
编辑`~/.gemini/settings.json`：

```json
{
  "mcpServers": {
    "zen": {
      "command": "sh",
      "args": [
        "-c",
        "exec $(which uvx || echo uvx) --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server"  
      ],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:~/.local/bin",
        "GEMINI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**uvx方法的优势：**
- ✅ 无需手动设置
- ✅ 始终拉取最新版本
- ✅ 无需管理本地依赖
- ✅ 无需Python环境设置即可工作

### 方法B：克隆并设置

```bash
# 克隆仓库
git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
cd zen-mcp-server

# 一键设置（处理所有事情）
./run-server.sh

# 或者对于Windows PowerShell：
./run-server.ps1

# 查看Claude Desktop的配置
./run-server.sh -c

# 查看所有选项
./run-server.sh --help
```

**设置脚本的功能：**
- ✅ 创建Python虚拟环境
- ✅ 安装所有依赖
- ✅ 为API密钥创建.env文件
- ✅ 配置Claude集成
- ✅ 提供复制粘贴配置

**更新后：** 在`git pull`后始终重新运行`./run-server.sh`。

**Windows用户**：详细的WSL配置请参阅[WSL设置指南](wsl-setup.md)。

## 步骤3：配置API密钥

### 对于uvx安装：
直接将API密钥添加到上面显示的MCP配置中。

### 对于克隆安装：
编辑`.env`文件：

```bash
nano .env
```

添加您的API密钥（至少需要一个）：
```env
# 选择您的提供商（至少需要一个）
GEMINI_API_KEY=your-gemini-api-key-here      # 用于Gemini模型  
OPENAI_API_KEY=your-openai-api-key-here      # 用于O3、GPT-5
XAI_API_KEY=your-xai-api-key-here            # 用于Grok模型
OPENROUTER_API_KEY=your-openrouter-key       # 用于多个模型

# DIAL平台（可选）
DIAL_API_KEY=your-dial-api-key-here
DIAL_API_HOST=https://core.dialx.ai          # 默认主机（可选）
DIAL_API_VERSION=2024-12-01-preview          # API版本（可选） 
DIAL_ALLOWED_MODELS=o3,gemini-2.5-pro       # 限制模型（可选）

# 自定义/本地模型（Ollama、vLLM等）
CUSTOM_API_URL=http://localhost:11434/v1     # Ollama示例
CUSTOM_API_KEY=                              # Ollama为空
CUSTOM_MODEL_NAME=llama3.2                   # 默认模型名称
```

**重要注意事项：**
- ⭐ **无需重启** - 更改立即生效 
- ⭐ 如果配置了多个API，原生API优先于OpenRouter
- ⭐ 在[`conf/custom_models.json`](../conf/custom_models.json)中配置模型别名

## 步骤4：测试安装

### 对于Claude Desktop：
1. 重启Claude Desktop
2. 打开新对话
3. 尝试：`"使用zen列出可用模型"`

### 对于Claude Code CLI：
1. 退出任何现有的Claude会话
2. 从项目目录运行`claude`
3. 尝试：`"使用zen聊聊Python最佳实践"`

### 对于Gemini CLI：
**注意**：虽然Zen MCP连接到Gemini CLI，但工具调用还不能正常工作。请参阅[Gemini CLI设置](gemini-setup.md)获取更新。

### 测试命令：
```
"使用zen列出可用模型"
"与zen聊聊API设计的最佳方法"
"使用zen thinkdeep和gemini pro讨论扩展策略"
"用o3调试这个错误：[粘贴错误]"
```

## 步骤5：开始使用Zen

### 基本使用模式：

**让Claude选择模型：**
```
"使用zen分析这段代码的安全问题"
"用zen调试这个竞态条件"
"使用zen规划数据库迁移"
```

**指定模型：**
```  
"使用zen和gemini pro审查这个复杂算法"
"用zen的o3进行逻辑分析调试"
"通过zen让flash快速格式化这段代码"
```

**多模型工作流程：**
```
"使用zen从pro和o3获得这个架构的共识"
"用gemini代码审查，然后用o3进行预提交验证"
"用flash分析，如果发现问题再用pro深入研究"
```

### 快速工具参考：

**🤝 协作**：`chat`、`thinkdeep`、`planner`、`consensus`
**🔍 代码分析**：`analyze`、`codereview`、`debug`、`precommit`
**⚒️ 开发**：`refactor`、`testgen`、`secaudit`、`docgen`
**🔧 实用工具**：`challenge`、`tracer`、`listmodels`、`version`

👉 **[完整工具参考](tools/)**，包含详细示例和参数

## 常见问题和解决方案

### "zen not found"或"command not found"

**对于uvx安装：**
- 确保`uv`已安装并在PATH中
- 尝试：`which uvx`验证uvx可用
- 检查PATH包含`/usr/local/bin`和`~/.local/bin`

**对于克隆安装：**
- 重新运行`./run-server.sh`验证设置
- 检查虚拟环境：`which python`应显示`.zen_venv/bin/python`

### API密钥问题

**"Invalid API key"错误：**
- 验证`.env`文件或MCP配置中的API密钥
- 直接使用提供商的API测试API密钥
- 检查密钥周围是否有多余的空格或引号

**"Model not available"：**
- 运行`"使用zen列出可用模型"`查看配置了什么
- 检查环境变量中的模型限制
- 验证API密钥是否有权访问请求的模型

### 性能问题

**响应缓慢：**
- 使用更快的模型：`flash`而不是`pro`
- 降低思考模式：`minimal`或`low`而不是`high`
- 限制模型访问以防止昂贵的模型选择

**令牌限制错误：**
- 使用上下文窗口更大的模型
- 将大请求分解为较小的块
- 参阅[处理大型提示](advanced-usage.md#working-with-large-prompts)

### 更多帮助

👉 **[完整故障排除指南](troubleshooting.md)**，包含详细解决方案

👉 **[高级使用指南](advanced-usage.md)**，适用于高级用户功能

👉 **[配置参考](configuration.md)**，涵盖所有选项

## 下一步？

🎯 **尝试主README中的示例工作流程**

📚 **探索[工具参考](tools/)**了解每个工具的功能

⚡ **阅读[高级使用指南](advanced-usage.md)**以了解复杂工作流程

🔧 **查看[配置选项](configuration.md)**以自定义行为

💡 **加入讨论并获得帮助**在项目问题或讨论中

## 快速配置模板

### 开发设置（平衡）
```env
DEFAULT_MODEL=auto
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
GOOGLE_ALLOWED_MODELS=flash,pro
OPENAI_ALLOWED_MODELS=o4-mini,o3-mini
```

### 成本优化设置
```env  
DEFAULT_MODEL=flash
GEMINI_API_KEY=your-key
GOOGLE_ALLOWED_MODELS=flash
```

### 高性能设置
```env
DEFAULT_MODEL=auto
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
GOOGLE_ALLOWED_MODELS=pro
OPENAI_ALLOWED_MODELS=o3
```

### 本地优先设置
```env
DEFAULT_MODEL=auto
CUSTOM_API_URL=http://localhost:11434/v1
CUSTOM_MODEL_NAME=llama3.2
# 添加云API作为备份
GEMINI_API_KEY=your-key
```

与您的AI开发团队愉快编码！🤖✨
