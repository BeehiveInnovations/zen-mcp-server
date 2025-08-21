# 自定义模型和API设置

本指南涵盖设置多个AI模型提供商，包括OpenRouter、自定义API端点和本地模型服务器。Zen MCP服务器通过单一模型注册表支持所有这些提供商的统一配置。

## 支持的提供商

- **OpenRouter** - 统一访问多个商业模型（GPT-4、Claude、Mistral等）
- **自定义API端点** - 本地模型（Ollama、vLLM、LM Studio、text-generation-webui）
- **自托管API** - 任何OpenAI兼容端点

## 何时使用什么

**在以下情况使用OpenRouter：**
- 访问通过原生API不可用的模型（GPT-4、Claude、Mistral等）
- 跨多个模型提供商的简化计费
- 无需单独API密钥即可试验各种模型

**在以下情况使用自定义URL：**
- **本地模型**如Ollama（Llama、Mistral等）
- **自托管推理**使用vLLM、LM Studio、text-generation-webui
- **私有/企业API**使用OpenAI兼容格式
- **成本控制**使用本地硬件

**在以下情况使用原生API（Gemini/OpenAI）：**
- 无需中介即可直接访问特定提供商
- 潜在的更低延迟和成本
- 在发布时立即访问最新模型功能

**混合搭配：** 您可以同时使用多个提供商！例如：
- OpenRouter用于昂贵的商业模型（GPT-4、Claude）
- 自定义URL用于本地模型（Ollama Llama）
- 原生API用于特定提供商（带扩展思考的Gemini Pro）

**注意：** 当多个提供商提供相同模型名称时，原生API优先于OpenRouter。

## 模型别名

服务器使用`conf/custom_models.json`将便利别名映射到OpenRouter和自定义模型名称。这个统一注册表支持云模型（通过OpenRouter）和本地模型（通过自定义端点）。

### OpenRouter模型（云）

|| 别名 | 映射到OpenRouter模型 |
||-------|-------------------------|
|| `opus` | `anthropic/claude-opus-4` |
|| `sonnet`, `claude` | `anthropic/claude-sonnet-4` |
|| `haiku` | `anthropic/claude-3.5-haiku` |
|| `gpt4o`, `4o` | `openai/gpt-4o` |
|| `gpt4o-mini`, `4o-mini` | `openai/gpt-4o-mini` |
|| `pro`, `gemini` | `google/gemini-2.5-pro` |
|| `flash` | `google/gemini-2.5-flash` |
|| `mistral` | `mistral/mistral-large` |
|| `deepseek`, `coder` | `deepseek/deepseek-coder` |
|| `perplexity` | `perplexity/llama-3-sonar-large-32k-online` |

### 自定义/本地模型

|| 别名 | 映射到本地模型 | 注意 |
||-------|-------------------|------|
|| `local-llama`, `local` | `llama3.2` | 需要配置`CUSTOM_API_URL` |

查看[`conf/custom_models.json`](conf/custom_models.json)中的完整列表。

**注意：** 虽然您可以使用其完整名称使用任何OpenRouter模型，但不在配置文件中的模型将使用通用能力（32K上下文窗口、无扩展思考等），这可能不匹配模型的实际能力。为获得最佳结果，将新模型添加到配置文件中并提供其适当规格。

## 快速开始

### 选项1：OpenRouter设置

#### 1. 获取API密钥
1. 在[openrouter.ai](https://openrouter.ai/)注册
2. 从仪表板创建API密钥
3. 向您的账户添加积分

#### 2. 设置环境变量
```bash
# 添加到您的.env文件
OPENROUTER_API_KEY=your-openrouter-api-key
```

> **注意：** 直接在[openrouter.ai](https://openrouter.ai/)的OpenRouter仪表板中控制可以使用哪些模型。
> 这为您提供了模型访问和支出限制的集中控制。

就是这样！设置脚本自动处理所有必要配置。

### 选项2：自定义API设置（Ollama、vLLM等）

对于本地模型如Ollama、vLLM、LM Studio或任何OpenAI兼容API：

#### 1. 启动您的本地模型服务器
```bash
# 示例：Ollama
ollama serve
ollama pull llama3.2

# 示例：vLLM
python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-2-7b-chat-hf

# 示例：LM Studio（在设置中启用OpenAI兼容性）
# 服务器运行在localhost:1234
```

#### 2. 配置环境变量
```bash
# 添加到您的.env文件
CUSTOM_API_URL=http://localhost:11434/v1  # Ollama示例
CUSTOM_API_KEY=                                      # Ollama为空（无需认证）
CUSTOM_MODEL_NAME=llama3.2                          # 要使用的默认模型
```

**本地模型连接**

Zen MCP服务器原生运行，因此您可以使用标准localhost URL连接到本地模型：

```bash
# 对于在您机器上运行的Ollama、vLLM、LM Studio等
CUSTOM_API_URL=http://localhost:11434/v1  # Ollama默认端口
```

#### 3. 不同平台的示例

**Ollama：**
```bash
CUSTOM_API_URL=http://localhost:11434/v1
CUSTOM_API_KEY=
CUSTOM_MODEL_NAME=llama3.2
```

**vLLM：**
```bash
CUSTOM_API_URL=http://localhost:8000/v1
CUSTOM_API_KEY=
CUSTOM_MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
```

**LM Studio：**
```bash
CUSTOM_API_URL=http://localhost:1234/v1
CUSTOM_API_KEY=lm-studio  # 或任何值，LM Studio通常需要某个密钥
CUSTOM_MODEL_NAME=local-model
```

**text-generation-webui（带OpenAI扩展）：**
```bash
CUSTOM_API_URL=http://localhost:5001/v1
CUSTOM_API_KEY=
CUSTOM_MODEL_NAME=your-loaded-model
```

## 使用模型

**使用模型别名（来自conf/custom_models.json）：**
```
# OpenRouter模型：
"使用opus进行深度分析"         # → anthropic/claude-opus-4
"使用sonnet审查这段代码"     # → anthropic/claude-sonnet-4
"通过zen使用pro分析这个"    # → google/gemini-2.5-pro
"通过zen使用gpt4o分析这个"  # → openai/gpt-4o
"通过zen使用mistral优化"    # → mistral/mistral-large

# 本地模型（配置了自定义URL）：
"使用local-llama分析这段代码"     # → llama3.2（本地）
"使用local调试这个函数"         # → llama3.2（本地）
```

**使用完整模型名称：**
```
# OpenRouter模型：
"通过zen使用anthropic/claude-opus-4进行深度分析"
"通过zen使用openai/gpt-4o调试这个"
"通过zen使用deepseek/deepseek-coder生成代码"

# 本地/自定义模型：
"通过zen使用llama3.2审查这个"
"通过zen使用meta-llama/Llama-2-7b-chat-hf分析"
```

**对于OpenRouter：** 在[openrouter.ai/models](https://openrouter.ai/models)检查当前模型定价。
**对于本地模型：** 上下文窗口和能力在`conf/custom_models.json`中定义。

## 模型提供商选择

系统自动将模型路由到适当的提供商：

1. **`is_custom: true`的模型** → 始终路由到自定义API（需要`CUSTOM_API_URL`）
2. **`is_custom: false`或省略的模型** → 路由到OpenRouter（需要`OPENROUTER_API_KEY`）
3. **未知模型** → 基于模型名称模式的回退逻辑

**提供商优先级顺序：**
1. 原生API（Google、OpenAI） - 如果API密钥可用
2. 自定义端点 - 对于标记为`is_custom: true`的模型
3. OpenRouter - 云模型的综合处理

这确保了本地和云模型之间的清洁分离，同时保持对未知模型的灵活性。

## 模型配置

服务器使用`conf/custom_models.json`定义模型别名和能力。您可以：

1. **使用默认配置** - 包含带便利别名的流行模型
2. **自定义配置** - 添加您自己的模型和别名
3. **覆盖配置路径** - 设置`CUSTOM_MODELS_CONFIG_PATH`环境变量为磁盘上的绝对路径

### 添加自定义模型

编辑`conf/custom_models.json`添加新模型。配置支持OpenRouter（云）和自定义端点（本地）模型。

#### 添加OpenRouter模型

```json
{
  "model_name": "vendor/model-name",
  "aliases": ["short-name", "nickname"],
  "context_window": 128000,
  "supports_extended_thinking": false,
  "supports_json_mode": true,
  "supports_function_calling": true,
  "description": "模型描述"
}
```

#### 添加自定义/本地模型

```json
{
  "model_name": "my-local-model",
  "aliases": ["local-model", "custom"],
  "context_window": 128000,
  "supports_extended_thinking": false,
  "supports_json_mode": false,
  "supports_function_calling": false,
  "is_custom": true,
  "description": "我的自定义Ollama/vLLM模型"
}
```

**字段解释：**
- `model_name`：模型标识符（OpenRouter格式如`vendor/model`或本地名称如`llama3.2`）
- `aliases`：用户可以输入的简短名称数组，而不是完整模型名称
- `context_window`：模型可以处理的总tokens（输入+输出组合）
- `supports_extended_thinking`：模型是否具有扩展推理能力
- `supports_json_mode`：模型是否可以保证有效的JSON输出
- `supports_function_calling`：模型是否支持函数/工具调用
- `is_custom`：**对于应该只与自定义端点一起工作的模型设置为`true`**（Ollama、vLLM等）
- `description`：模型的人类可读描述

**重要：** 始终为本地模型设置`is_custom: true`。这确保它们仅在配置`CUSTOM_API_URL`时使用，并防止与OpenRouter冲突。

## 可用模型

通过OpenRouter可用的流行模型：
- **GPT-4** - OpenAI最强大的模型
- **Claude 4** - Anthropic的模型（Opus、Sonnet、Haiku）
- **Mistral** - 包括Mistral Large
- **Llama 3** - Meta的开放模型
- 更多请见[openrouter.ai/models](https://openrouter.ai/models)

## 故障排除

- **"找不到模型"**：在openrouter.ai/models检查确切模型名称
- **"积分不足"**：向您的OpenRouter账户添加积分
- **"模型不可用"**：检查您的OpenRouter仪表板以获取模型访问权限
