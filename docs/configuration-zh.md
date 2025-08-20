# 配置指南

本指南涵盖了Zen MCP服务器的所有配置选项。服务器通过`.env`文件中定义的环境变量进行配置。

## 快速配置入门

**自动模式（推荐）：** 设置`DEFAULT_MODEL=auto`并让Claude智能地为每个任务选择最佳模型：

```env
# 基本配置
DEFAULT_MODEL=auto
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
```

## 完整配置参考

### 必需配置

**工作区根目录：**
```env

### API密钥（至少需要一个）

**重要：** 使用OpenRouter或原生API之一，不要同时使用！同时拥有两者会在哪个提供商服务哪个模型方面产生歧义。

**选项1：原生API（推荐直接访问）**
```env
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
# 获取地址：https://makersuite.google.com/app/apikey

# OpenAI API  
OPENAI_API_KEY=your_openai_api_key_here
# 获取地址：https://platform.openai.com/api-keys

# X.AI GROK API
XAI_API_KEY=your_xai_api_key_here
# 获取地址：https://console.x.ai/
```

**选项2：OpenRouter（通过一个API访问多个模型）**
```env
# OpenRouter统一模型访问
OPENROUTER_API_KEY=your_openrouter_api_key_here
# 获取地址：https://openrouter.ai/
# 如果使用OpenRouter，请注释掉上面的原生API密钥
```

**选项3：自定义API端点（本地模型）**
```env
# 用于Ollama、vLLM、LM Studio等
CUSTOM_API_URL=http://localhost:11434/v1  # Ollama示例
CUSTOM_API_KEY=                                      # Ollama为空
CUSTOM_MODEL_NAME=llama3.2                          # 默认模型
```

**本地模型连接：**
- 由于服务器原生运行，使用标准localhost URL
- 示例：Ollama使用`http://localhost:11434/v1`

### 模型配置

**默认模型选择：**
```env
# 选项：'auto'、'pro'、'flash'、'o3'、'o3-mini'、'o4-mini'等
DEFAULT_MODEL=auto  # Claude为每个任务选择最佳模型（推荐）
```

**可用模型：**
- **`auto`**：Claude自动选择最优模型
- **`pro`**（Gemini 2.5 Pro）：扩展思考，深度分析
- **`flash`**（Gemini 2.0 Flash）：超快响应
- **`o3`**：强逻辑推理（200K上下文）
- **`o3-mini`**：平衡速度/质量（200K上下文）
- **`o4-mini`**：最新推理模型，针对较短上下文优化
- **`grok-3`**：GROK-3高级推理（131K上下文）
- **`grok-4-latest`**：GROK-4最新旗舰模型（256K上下文）
- **自定义模型**：通过OpenRouter或本地API

### 思考模式配置

**ThinkDeep的默认思考模式：**
```env
# 仅适用于支持扩展思考的模型（如Gemini 2.5 Pro）
DEFAULT_THINKING_MODE_THINKDEEP=high

# 可用模式和令牌消耗：
#   minimal: 128 tokens   - 快速分析，最快响应
#   low:     2,048 tokens - 轻度推理任务  
#   medium:  8,192 tokens - 平衡推理
#   high:    16,384 tokens - 复杂分析（推荐用于thinkdeep）
#   max:     32,768 tokens - 最大推理深度
```

### 模型使用限制

控制每个提供商可以使用哪些模型，用于成本控制、合规性或标准化：

```env
# 格式：逗号分隔的列表（不区分大小写，容忍空格）
# 空或未设置 = 允许所有模型（默认）

# OpenAI模型限制
OPENAI_ALLOWED_MODELS=o3-mini,o4-mini,mini

# Gemini模型限制  
GOOGLE_ALLOWED_MODELS=flash,pro

# X.AI GROK模型限制
XAI_ALLOWED_MODELS=grok-3,grok-3-fast,grok-4-latest

# OpenRouter模型限制（影响通过自定义提供商的模型）
OPENROUTER_ALLOWED_MODELS=opus,sonnet,mistral
```

**支持的模型名称：**

**OpenAI模型：**
- `o3`（200K上下文，高推理）
- `o3-mini`（200K上下文，平衡）
- `o4-mini`（200K上下文，最新平衡）
- `mini`（o4-mini的简写）

**Gemini模型：**
- `gemini-2.5-flash`（1M上下文，快速）
- `gemini-2.5-pro`（1M上下文，强大）
- `flash`（Flash模型的简写）
- `pro`（Pro模型的简写）

**X.AI GROK模型：**
- `grok-4-latest`（256K上下文，最新旗舰模型，具有推理、视觉和结构化输出）
- `grok-3`（131K上下文，高级推理）
- `grok-3-fast`（131K上下文，更高性能）
- `grok`（grok-4-latest的简写）
- `grok4`（grok-4-latest的简写）
- `grok3`（grok-3的简写）
- `grokfast`（grok-3-fast的简写）

**配置示例：**
```env
# 成本控制 - 仅便宜模型
OPENAI_ALLOWED_MODELS=o4-mini
GOOGLE_ALLOWED_MODELS=flash

# 单一模型标准化
OPENAI_ALLOWED_MODELS=o4-mini
GOOGLE_ALLOWED_MODELS=pro

# 平衡选择
GOOGLE_ALLOWED_MODELS=flash,pro
XAI_ALLOWED_MODELS=grok,grok-3-fast
```

### 高级配置

**自定义模型配置：**
```env
# 覆盖custom_models.json的默认位置
CUSTOM_MODELS_CONFIG_PATH=/path/to/your/custom_models.json
```

**对话设置：**
```env
# AI对AI对话线程在内存中持续多长时间（小时）
# 当claude关闭其MCP连接或会话退出/重新启动时，对话会自动清除
CONVERSATION_TIMEOUT_HOURS=5

# 最大对话轮次（每次交换 = 2轮）
MAX_CONVERSATION_TURNS=20
```

**日志配置：**
```env
# 日志级别：DEBUG、INFO、WARNING、ERROR
LOG_LEVEL=DEBUG  # 默认：显示详细的操作消息
```

## 配置示例

### 开发设置
```env
# 多提供商开发
DEFAULT_MODEL=auto
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
XAI_API_KEY=your-xai-key
LOG_LEVEL=DEBUG
CONVERSATION_TIMEOUT_HOURS=1
```

### 生产设置
```env
# 带成本控制的生产
DEFAULT_MODEL=auto
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
GOOGLE_ALLOWED_MODELS=flash
OPENAI_ALLOWED_MODELS=o4-mini
LOG_LEVEL=INFO
CONVERSATION_TIMEOUT_HOURS=3
```

### 本地开发
```env
# 仅本地模型
DEFAULT_MODEL=llama3.2
CUSTOM_API_URL=http://localhost:11434/v1
CUSTOM_API_KEY=
CUSTOM_MODEL_NAME=llama3.2
LOG_LEVEL=DEBUG
```

### 仅OpenRouter
```env
# 单一API用于多个模型
DEFAULT_MODEL=auto
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_ALLOWED_MODELS=opus,sonnet,gpt-4
LOG_LEVEL=INFO
```

## 重要注意事项

**本地网络：**
- 对本地模型使用标准localhost URL
- 服务器作为原生Python进程运行

**API密钥优先级：**
- 配置了两者时，原生API优先于OpenRouter
- 避免为同一模型同时配置原生和OpenRouter

**模型限制：**
- 适用于包括自动模式在内的所有使用
- 空/未设置 = 允许所有模型
- 启动时会警告无效的模型名称

**配置更改：**
- 更改`.env`后使用`./run-server.sh`重启服务器
- 配置在启动时加载一次

## 相关文档

- **[高级使用指南](advanced-usage.md)** - 高级模型使用模式、思考模式和高级用户工作流程
- **[上下文复活指南](context-revival.md)** - 跨会话的对话持久性和上下文复活
- **[AI对AI协作指南](ai-collaboration.md)** - 多模型协调和对话线程
