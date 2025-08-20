# 高级使用指南

本指南涵盖Zen MCP服务器高级用户的高级功能、配置选项和工作流程。

## 目录

- [模型配置](#模型配置)
- [模型使用限制](#模型使用限制)
- [思考模式](#思考模式)
- [工具参数](#工具参数)
- [上下文复活：超越上下文限制的AI记忆](#上下文复活超越上下文限制的ai记忆)
- [协作工作流程](#协作工作流程)
- [处理大型提示](#处理大型提示)
- [视觉支持](#视觉支持)
- [网络搜索集成](#网络搜索集成)
- [系统提示](#系统提示)

## 模型配置

**基本配置**请参阅[配置指南](configuration.md)，该指南涵盖API密钥、模型选择和环境变量。

本节重点介绍高级用户的**高级模型使用模式**：

**每请求模型覆盖：**
无论您的默认配置如何，都可以为每个请求指定模型：
- "使用**pro**对auth.py进行深度安全分析"
- "使用**flash**快速格式化这段代码"
- "使用**o3**调试这个逻辑错误"
- "用**o4-mini**进行平衡分析审查"
- "使用**gpt4.1**进行全面的代码库分析"

**Claude的自动模式决策矩阵：**

|| 模型 | 提供商 | 上下文 | 优势 | 自动模式使用 |
||-------|----------|---------|-----------|------------------|
|| **`pro`**（Gemini 2.5 Pro） | Google | 1M tokens | 扩展思考（最多32K tokens），深度分析 | 复杂架构，安全审查，深度调试 |
|| **`flash`**（Gemini 2.5 Flash） | Google | 1M tokens | 具有思考的超快响应 | 快速检查，格式化，简单分析 |
|| **`flash-2.0`**（Gemini 2.0 Flash） | Google | 1M tokens | 支持音频/视频的最新快速模型 | 多模态输入的快速分析 |
|| **`flashlite`**（Gemini 2.0 Flash Lite） | Google | 1M tokens | 轻量级纯文本模型 | 无视觉的快速文本处理 |
|| **`o3`** | OpenAI | 200K tokens | 强逻辑推理 | 调试逻辑错误，系统分析 |
|| **`o3-mini`** | OpenAI | 200K tokens | 平衡速度/质量 | 中等复杂性任务 |
|| **`o4-mini`** | OpenAI | 200K tokens | 最新推理模型 | 针对较短上下文优化 |
|| **`gpt4.1`** | OpenAI | 1M tokens | 扩展上下文的最新GPT-4 | 大型代码库分析，全面审查 |
|| **`gpt5`**（GPT-5） | OpenAI | 400K tokens | 具有推理支持的高级模型 | 需要高级推理的复杂问题 |
|| **`gpt5-mini`**（GPT-5 Mini） | OpenAI | 400K tokens | 具有推理的高效变体 | 平衡性能和能力 |
|| **`gpt5-nano`**（GPT-5 Nano） | OpenAI | 400K tokens | 最快、最便宜的GPT-5变体 | 摘要和分类任务 |
|| **`grok-4-latest`** | X.AI | 256K tokens | 具有推理、视觉的最新旗舰模型 | 复杂分析，推理任务 |
|| **`grok-3`** | X.AI | 131K tokens | 高级推理模型 | 深度分析，复杂问题 |
|| **`grok-3-fast`** | X.AI | 131K tokens | 更高性能变体 | 具有推理的快速响应 |
|| **`llama`**（Llama 3.2） | 自定义/本地 | 128K tokens | 本地推理，隐私 | 设备上分析，免费处理 |
|| **任何模型** | OpenRouter | 变化 | 访问GPT-4、Claude、Llama等 | 用户指定或基于任务要求 |

**混合匹配提供商：** 同时使用多个提供商！设置`OPENROUTER_API_KEY`和`CUSTOM_API_URL`在同一对话中访问云模型（昂贵/强大）和本地模型（免费/私有）。

**模型能力：**
- **Gemini模型**：支持思考模式（minimal到max），网络搜索，1M上下文
  - **Pro 2.5**：最多32K思考tokens的深度分析
  - **Flash 2.5**：支持思考的超快（24K思考tokens）
  - **Flash 2.0**：支持音频/视频输入的最新快速模型（24K思考tokens）
  - **Flash Lite 2.0**：纯文本轻量级模型（不支持思考）
- **O3/O4模型**：出色的推理，系统分析，200K上下文
- **GPT-4.1**：扩展上下文窗口（1M tokens），通用能力
- **GPT-5系列**：高级推理模型，400K上下文
  - **GPT-5**：具有推理支持和视觉的全功能
  - **GPT-5 Mini**：平衡效率和能力
  - **GPT-5 Nano**：针对快速、低成本任务优化
- **Grok-4**：扩展思考支持，视觉能力，256K上下文
- **Grok-3模型**：高级推理，131K上下文

## 模型使用限制

**完整限制配置**请参阅[配置指南](configuration.md#model-usage-restrictions)。

**高级限制策略：**

**成本控制示例：**
```env
# 开发：允许实验
GOOGLE_ALLOWED_MODELS=flash,pro
OPENAI_ALLOWED_MODELS=o4-mini,o3-mini

# 生产：成本优化  
GOOGLE_ALLOWED_MODELS=flash
OPENAI_ALLOWED_MODELS=o4-mini

# 高性能：质量优于成本
GOOGLE_ALLOWED_MODELS=pro
OPENAI_ALLOWED_MODELS=o3,o4-mini
```

**重要注意事项：**
- 限制适用于包括自动模式在内的所有使用
- `OPENROUTER_ALLOWED_MODELS`仅影响通过自定义提供商访问的OpenRouter模型（custom_models.json中`is_custom: false`）
- 自定义本地模型（`is_custom: true`）不受任何限制影响

## 思考模式

**Claude自动根据任务复杂性管理思考模式**，但您也可以手动控制Gemini的推理深度，以在响应质量和token消耗之间取得平衡。每种思考模式使用不同数量的tokens，直接影响API成本和响应时间。

### 思考模式和Token预算

这些仅适用于支持自定义token使用进行扩展思考的模型，如Gemini 2.5 Pro。

|| 模式 | Token预算 | 使用场景 | 成本影响 |
||------|-------------|----------|-------------|
|| `minimal` | 128 tokens | 简单、直接的任务 | 最低成本 |
|| `low` | 2,048 tokens | 基本推理任务 | 比minimal多16倍 |
|| `medium` | 8,192 tokens | **默认** - 大多数开发任务 | 比minimal多64倍 |
|| `high` | 16,384 tokens | 需要彻底分析的复杂问题（thinkdeep的默认） | 比minimal多128倍 |
|| `max` | 32,768 tokens | 详尽推理 | 比minimal多256倍 |

### 如何使用思考模式

**Claude自动选择适当的思考模式**，但您可以在提示中明确请求特定模式来覆盖此设置。记住：更高的思考模式 = 更多tokens = 更高成本但更好质量：

#### 优化Token使用和成本

**在大多数情况下，让Claude自动管理思考模式**以获得成本和质量的最佳平衡。当您有特定要求时手动覆盖：

**使用较低模式（`minimal`、`low`）节省tokens当：**
- 进行简单格式化或样式检查
- 获取基本概念的快速解释
- 处理直接的代码
- 需要更快响应
- 在紧张的token预算内工作

**使用较高模式（`high`、`max`）当质量证明成本合理时：**
- 调试复杂问题（额外tokens的成本 < 找到根本原因的价值）
- 审查安全关键代码（tokens成本 < 漏洞成本）
- 分析系统架构（全面分析节省开发时间）
- 查找细微错误或边缘情况
- 进行性能优化

**Token成本示例：**
- `minimal`（128 tokens）vs `max`（32,768 tokens）= 思考tokens相差256倍
- 对于简单格式检查，使用`minimal`而不是默认的`medium`节省约8,000思考tokens
- 对于关键安全审查，`high`或`max`模式的额外tokens是值得的投资

**按场景示例：**
```
# 用o3快速样式检查
"使用flash审查utils.py中的格式"

# 用o3安全审计
"让o3用高思考模式对auth/进行安全审查"

# 复杂调试，让claude选择最佳模型
"使用zen用max思考模式调试这个竞态条件"

# 用Gemini 2.5 Pro进行架构分析
"用pro高思考分析整个src/目录架构"
```

## 工具参数

所有处理文件的工具都支持**单个文件和整个目录**。服务器自动扩展目录，过滤相关代码文件，并管理token限制。

### 文件处理工具

**`analyze`** - 分析文件或目录
- `files`：文件路径或目录列表（必需）
- `question`：要分析的内容（必需）  
- `model`：auto|pro|flash|flash-2.0|flashlite|o3|o3-mini|o4-mini|gpt4.1|gpt5|gpt5-mini|gpt5-nano（默认：服务器默认）
- `analysis_type`：architecture|performance|security|quality|general
- `output_format`：summary|detailed|actionable
- `thinking_mode`：minimal|low|medium|high|max（默认：medium，仅Gemini）
- `use_websearch`：启用网络搜索文档和最佳实践 - 允许模型请求Claude执行搜索（默认：true）

```
"分析src/目录的架构模式"（自动模式选择最佳模型）
"使用flash快速分析main.py和tests/以了解测试覆盖率" 
"使用o3对backend/core.py中的算法进行逻辑分析"
"使用pro深度分析整个backend/目录结构"
```

**`codereview`** - 审查代码文件或目录
- `files`：文件路径或目录列表（必需）
- `model`：auto|pro|flash|flash-2.0|flashlite|o3|o3-mini|o4-mini|gpt4.1|gpt5|gpt5-mini|gpt5-nano（默认：服务器默认）
- `review_type`：full|security|performance|quick
- `focus_on`：要关注的具体方面
- `standards`：要执行的编码标准
- `severity_filter`：critical|high|medium|all
- `thinking_mode`：minimal|low|medium|high|max（默认：medium，仅Gemini）

```
"审查整个api/目录的安全问题"（自动模式选择最佳模型）
"使用pro对auth/进行深度安全分析审查"
"使用o3审查algorithms/中的逻辑正确性"
"使用flash快速审查src/并专注于性能，只显示关键问题"
```

**`debug`** - 带文件上下文的调试
- `error_description`：问题描述（必需）
- `model`：auto|pro|flash|flash-2.0|flashlite|o3|o3-mini|o4-mini|gpt4.1|gpt5|gpt5-mini|gpt5-nano（默认：服务器默认）
- `error_context`：堆栈跟踪或日志
- `files`：与问题相关的文件或目录
- `runtime_info`：环境详细信息
- `previous_attempts`：您已尝试的方法
- `thinking_mode`：minimal|low|medium|high|max（默认：medium，仅Gemini）
- `use_websearch`：启用错误消息和解决方案的网络搜索 - 允许模型请求Claude执行搜索（默认：true）

```
"用backend/上下文调试这个逻辑错误"（自动模式选择最佳模型）
"使用o3调试这个算法正确性问题"
"使用pro调试这个复杂的架构问题"
```

**`thinkdeep`** - 带文件上下文的扩展分析
- `current_analysis`：您当前的思考（必需）
- `model`：auto|pro|flash|flash-2.0|flashlite|o3|o3-mini|o4-mini|gpt4.1|gpt5|gpt5-mini|gpt5-nano（默认：服务器默认）
- `problem_context`：附加上下文
- `focus_areas`：要关注的具体方面
- `files`：上下文的文件或目录
- `thinking_mode`：minimal|low|medium|high|max（默认：max，仅Gemini）
- `use_websearch`：启用文档和见解的网络搜索 - 允许模型请求Claude执行搜索（默认：true）

```
"参考src/models/深入思考我的设计"（自动模式选择最佳模型）
"使用pro用扩展思考深入思考这个架构"
"使用o3深入思考这个算法中的逻辑流"
```

**`testgen`** - 带边缘情况覆盖的全面测试生成
- `files`：要生成测试的代码文件或目录（必需）
- `prompt`：测试内容、测试目标和范围的描述（必需）
- `model`：auto|pro|flash|flash-2.0|flashlite|o3|o3-mini|o4-mini|gpt4.1|gpt5|gpt5-mini|gpt5-nano（默认：服务器默认）
- `test_examples`：作为样式/模式参考的可选现有测试文件
- `thinking_mode`：minimal|low|medium|high|max（默认：medium，仅Gemini）

```
"为User.login()方法生成带边缘情况的测试"（自动模式选择最佳模型）
"使用pro用max思考模式为src/payment.py生成全面测试"
"使用o3为sort_functions.py中的算法正确性生成测试"
"按照tests/unit/的模式为新auth模块生成测试"
```

**`refactor`** - 专注于分解的智能代码重构
- `files`：要分析重构机会的代码文件或目录（必需）
- `prompt`：重构目标、上下文和具体关注领域的描述（必需）
- `refactor_type`：codesmells|decompose|modernize|organization（必需）
- `model`：auto|pro|flash|flash-2.0|flashlite|o3|o3-mini|o4-mini|gpt4.1|gpt5|gpt5-mini|gpt5-nano（默认：服务器默认）
- `focus_areas`：要关注的具体领域（如'performance'、'readability'、'maintainability'、'security'）
- `style_guide_examples`：作为样式/模式参考的可选现有代码文件
- `thinking_mode`：minimal|low|medium|high|max（默认：medium，仅Gemini）
- `continuation_id`：多轮对话的线程延续ID

```
"分析遗留代码库的分解机会"（自动模式选择最佳模型）
"使用pro用max思考模式识别认证模块中的代码异味"
"使用pro按照examples/modern-patterns.js现代化这个JavaScript代码"
"重构src/以获得更好的组织，专注于可维护性和可读性"
```

## 上下文复活：超越上下文限制的AI记忆

**Zen MCP服务器最具革命性的功能**是它即使在Claude的内存重置后也能保持对话上下文的能力。这实现了跨多个会话和上下文边界的真正持久AI协作。

### **突破**

即使当Claude的上下文重置或压缩时，对话也可以无缝继续，因为其他模型（O3、Gemini）可以访问存储在内存中的完整对话历史，并可以"提醒"Claude讨论的所有内容。

### 主要优势

- **持久对话**跨Claude的上下文重置
- **跨工具延续**完全保持上下文
- **多会话工作流程**保持完整历史
- **真正的AI编排**模型可以建立在彼此的工作基础上
- **无缝交接**在不同工具和模型之间

### 快速示例

```
会话1："用gemini pro设计RAG系统"
[Claude的上下文重置]
会话2："用o3继续我们的RAG讨论"
→ O3接收完整历史并提醒Claude讨论的所有内容
```

**📖 [阅读完整的上下文复活指南](context-revival.md)** 获取详细示例、技术架构、配置选项和最佳实践。

**另见：** [AI对AI协作指南](ai-collaboration.md) 用于多模型协调和对话线程。

## 协作工作流程

### 设计 → 审查 → 实施
```
努力思考设计和开发一个有趣的swift计算器应用。用o3审查你的设计计划，接受
他们的建议但保持功能集现实可行，不添加臃肿。开始实施，在实施之间，
让Gemini Pro进行代码审查，如果需要创意方向可以与Flash聊天。   
```

### 代码 → 审查 → 修复
```
实施一个新屏幕，其中从数据库获取的位置显示在地图上，图钉从
顶部掉落并带有动画着陆。完成后，用gemini pro和o3同时进行代码审查，让他们批评你的
工作。修复中等到关键的错误/关注/问题并向我展示最终产品
```

### 调试 → 分析 → 解决方案 → 预提交检查 → 发布
```
查看保存在subfolder/diagnostics.log下的这些日志文件，有一个错误，用户说应用程序
在启动时崩溃。努力思考并逐行检查，将其与项目内的相应代码进行核对。在您
进行初步调查后，让gemini pro分析日志文件和您怀疑
有错误的相关代码，然后制定并实施一个最小的修复。不能回归。最后用zen使用gemini pro进行预提交
确认我们可以发布修复 
```

### 重构 → 审查 → 实施 → 测试
```
使用zen分析这个遗留认证模块的分解机会。代码变得难以
维护，我们需要将其分解。使用gemini pro高思考模式识别代码异味并建议
现代化策略。审查重构计划后，逐步实施更改，然后
用zen生成全面测试以确保没有损坏。
```

### 工具选择指南
帮助选择适合您需求的正确工具：

**决策流程：**
1. **有特定错误/异常？** → 使用`debug`
2. **想在代码中找到错误/问题？** → 使用`codereview`
3. **想了解代码如何工作？** → 使用`analyze`
4. **需要全面测试覆盖？** → 使用`testgen`
5. **想重构/现代化代码？** → 使用`refactor`
6. **有需要扩展/验证的分析？** → 使用`thinkdeep`
7. **想头脑风暴或讨论？** → 使用`chat`

**关键区别：**
- `analyze` vs `codereview`：analyze解释，codereview规定修复
- `chat` vs `thinkdeep`：chat是开放式的，thinkdeep扩展具体分析
- `debug` vs `codereview`：debug诊断运行时错误，review找到静态问题
- `testgen` vs `debug`：testgen创建测试套件，debug只是找到问题并推荐解决方案
- `refactor` vs `codereview`：refactor建议结构改进，codereview找到错误/问题
- `refactor` vs `analyze`：refactor提供可行的重构步骤，analyze提供理解

## 视觉支持

Zen MCP服务器支持具有视觉能力的模型来分析图像、图表、屏幕截图和视觉内容。视觉支持与所有工具和对话线程无缝配合。

**支持的模型：**
- **Gemini 2.5 Pro & Flash**：出色的图表、架构分析、UI模型（最多20MB总计）
- **OpenAI O3/O4系列**：强大的视觉调试、错误屏幕截图（最多20MB总计）
- **通过OpenRouter的Claude模型**：适合代码屏幕截图、视觉分析（最多5MB总计）
- **自定义模型**：支持因模型而异，强制执行40MB最大值以防滥用

**使用示例：**
```bash
# 用错误屏幕截图调试
"使用zen用堆栈跟踪屏幕截图和error.py调试这个错误"

# 用图表进行架构分析  
"用gemini pro分析这个系统架构图的瓶颈"

# 用模型进行UI审查
"与flash聊聊这个UI模型 - 布局直观吗？"

# 带视觉上下文的代码审查
"审查这个认证代码以及错误对话框屏幕截图"
```

**支持的图像格式：**
- **图像**：JPG、PNG、GIF、WebP、BMP、SVG、TIFF
- **文档**：PDF（模型支持的地方）
- **数据URL**：来自Claude的Base64编码图像

**关键功能：**
- **自动验证**：文件类型、魔术字节和大小验证
- **对话上下文**：图像在工具切换和延续中持续存在
- **预算管理**：超出限制时自动丢弃旧图像
- **模型能力感知**：仅向具有视觉能力的模型发送图像

**最佳实践：**
- 包含图像时描述它们："登录错误屏幕截图"、"系统架构图"
- 使用适当的模型：Gemini用于复杂图表，O3用于调试视觉
- 考虑图像大小：较大的图像消耗更多模型容量

## 处理大型提示

MCP协议的组合请求+响应限制约为25K tokens。该服务器通过自动将大型提示作为文件处理来智能地解决此限制：

**工作原理：**
1. 当您发送大于配置限制（默认：50K字符约10-12K tokens）的提示时，服务器检测到这一点
2. 它响应一个特殊状态，要求Claude将提示保存到名为`prompt.txt`的文件
3. Claude保存提示并用文件路径重新发送请求
4. 服务器直接将文件内容读入Gemini的1M token上下文
5. 为响应保留完整的MCP token容量

**示例场景：**
```
# 您有一个大量代码审查请求和详细上下文
用户："使用gemini审查这段代码：[50,000+字符详细分析]"

# 服务器检测到大型提示并响应：
Zen MCP："提示对于MCP的token限制太大（>50,000字符）。
请将提示文本保存到名为'prompt.txt'的临时文件并重新发送
带有空提示字符串和包含在文件参数中的绝对文件路径的请求，
以及您希望作为上下文共享的任何其他文件。"

# Claude自动处理这个：
- 将您的提示保存到/tmp/prompt.txt
- 重新发送："使用gemini审查这段代码"，文件=["/tmp/prompt.txt", "/path/to/code.py"]

# 服务器通过Gemini的1M上下文处理大型提示
# 在MCP的响应限制内返回全面分析
```

此功能确保您可以向Gemini发送任意大的提示，而不会遇到MCP的协议限制，同时最大化详细响应的可用空间。

## 网络搜索集成

**用于增强分析的智能网络搜索建议**

现在默认为所有工具启用网络搜索。Gemini不是直接执行搜索，而是智能地分析何时来自网络的附加信息会增强其响应，并为Claude提供具体的搜索建议。

**工作原理：**
1. Gemini分析请求并识别当前文档、API参考或社区解决方案有价值的领域
2. 它基于其训练数据提供分析
3. 如果网络搜索能加强分析，Gemini包含"Claude推荐网络搜索"部分
4. Claude然后可以执行这些搜索并纳入发现

**示例：**
```
用户："使用gemini调试这个FastAPI异步错误"

Gemini的响应：
[... 调试分析 ...]

**Claude推荐网络搜索：**
- "FastAPI async def vs def performance 2024" - 验证异步端点的当前最佳实践
- "FastAPI BackgroundTasks memory leak" - 检查您使用版本的已知问题
- "FastAPI lifespan context manager pattern" - 探索适当的资源管理模式

Claude然后可以搜索这些具体主题并为您提供最新信息。
```

**优势：**
- 始终访问最新文档和最佳实践
- Gemini专注于推理什么信息会有帮助
- Claude保持对实际网络搜索的控制
- 两个AI助手之间更协作的方法
- 通过鼓励验证假设减少幻觉

**网络搜索控制：**
默认启用网络搜索，允许模型请求Claude执行当前文档和解决方案的搜索。如果您希望模型仅使用其训练数据工作，可以禁用网络搜索：
```
"使用gemini审查这段代码，use_websearch false"
```

## 系统提示

服务器使用精心制作的系统提示为每个工具提供专业知识：

### 提示架构
- **集中提示**：所有系统提示在`prompts/tool_prompts.py`中定义
- **工具集成**：每个工具继承自`BaseTool`并实现`get_system_prompt()`
- **提示流程**：`用户请求 → 工具选择 → 系统提示 + 上下文 → Gemini响应`

### 专业知识
每个工具都有一个定义其角色和方法的独特系统提示：
- **`thinkdeep`**：作为高级开发合作伙伴，挑战假设并找到边缘情况
- **`codereview`**：专家代码审查员，专注于安全/性能，使用严重性级别
- **`debug`**：系统调试器，提供根本原因分析和预防策略
- **`analyze`**：代码分析师，专注于架构、模式和可行见解

### 自定义
要修改工具行为，您可以：
1. 编辑`prompts/tool_prompts.py`中的提示进行全局更改
2. 在工具类中覆盖`get_system_prompt()`进行工具特定更改
3. 使用`temperature`参数调整响应风格（0.2用于专注，0.7用于创意）
