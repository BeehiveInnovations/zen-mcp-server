# Zen MCP: 多种工作流程，一个上下文

[zen_web.webm](https://github.com/user-attachments/assets/851e3911-7f06-47c0-a4ab-a2601236697c)

<div align="center">
  <b>🤖 <a href="https://www.anthropic.com/claude-code">Claude Code</a> 或 <a href="https://github.com/google-gemini/gemini-cli">Gemini CLI</a> + [Gemini / OpenAI / Grok / OpenRouter / DIAL / Ollama / Anthropic / 任何模型] = 您的终极AI开发团队</b>
</div>

<br/>

**Claude Code 的 AI 编排工具** - 一个模型上下文协议服务器，为您选择的CLI工具（如 [Claude Code](https://www.anthropic.com/claude-code)）提供访问多个AI模型的能力，以增强代码分析、问题解决和协作开发。

**真正的AI协作与对话连续性** - Claude保持控制，但从最适合各个子任务的AI获得见解。上下文在工具和模型之间无缝传递，实现复杂的工作流程，如：多模型代码审查 → 自动化规划 → 实施 → 预提交验证。

> **您掌控一切。** Claude编排AI团队，但您决定工作流程。制作强大的提示，精确地在需要时引入Gemini Pro、GPT 5、Flash或本地离线模型。

#### 推荐AI技术栈

使用Claude Code与 **Opus 4.1**（用于所有代理工作）+ **Gemini 2.5 Pro**（用于深度思考、审查、帮助调试、执行预提交分析、一般讨论）并获得卓越的结果。

## 快速开始（5分钟）

**前置要求：** Python 3.10+、Git、[已安装uv](https://docs.astral.sh/uv/getting-started/installation/)

**1. 获取API密钥**（选择一个或多个）：
- **[OpenRouter](https://openrouter.ai/)** - 使用一个API访问多个模型
- **[Gemini](https://makersuite.google.com/app/apikey)** - Google的最新模型
- **[OpenAI](https://platform.openai.com/api-keys)** - O3、GPT-5系列
- **[X.AI](https://console.x.ai/)** - Grok模型
- **[DIAL](https://dialx.ai/)** - 厂商无关的模型访问
- **[Ollama](https://ollama.ai/)** - 本地模型（免费）

**2. 安装**（选择一种）：

**选项A：使用uvx即时设置**（推荐）
```json
// 添加到 ~/.claude/settings.json 或 .mcp.json
{
  "mcpServers": {
    "zen": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/BeehiveInnovations/zen-mcp-server.git", "zen-mcp-server"],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:~/.local/bin",
        "GEMINI_API_KEY": "your-key-here"
      }
    }
  }
}
```

**选项B：克隆并设置**
```bash
git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
cd zen-mcp-server
./run-server.sh  # 处理一切：设置、配置、API密钥
```

**3. 开始使用！**
```
"使用zen和gemini pro分析这段代码的安全问题"
"用o3调试这个错误，然后让flash建议优化方案"
"用zen规划迁移策略，从多个模型获得共识"
```

👉 **[完整设置指南](docs/getting-started-zh.md)** 包含详细的安装、配置和故障排除

## 核心工具

**协作与规划**
- **[`chat`](docs/tools/chat-zh.md)** - 头脑风暴想法、获得第二意见、验证方法
- **[`thinkdeep`](docs/tools/thinkdeep-zh.md)** - 扩展推理、边缘案例分析、替代观点
- **[`planner`](docs/tools/planner-zh.md)** - 将复杂项目分解为结构化、可行的计划
- **[`consensus`](docs/tools/consensus-zh.md)** - 从多个AI模型获得专家意见，支持立场引导

**代码分析与质量**
- **[`analyze`](docs/tools/analyze-zh.md)** - 理解整个代码库的架构、模式、依赖关系
- **[`codereview`](docs/tools/codereview-zh.md)** - 具有严重性级别和可行反馈的专业审查
- **[`debug`](docs/tools/debug-zh.md)** - 系统化调查和根本原因分析
- **[`precommit`](docs/tools/precommit-zh.md)** - 提交前验证更改，防止回归

**开发工具**
- **[`refactor`](docs/tools/refactor-zh.md)** - 智能代码重构，专注于分解
- **[`testgen`](docs/tools/testgen-zh.md)** - 包含边缘案例的全面测试生成
- **[`secaudit`](docs/tools/secaudit-zh.md)** - 基于OWASP Top 10的安全审计
- **[`docgen`](docs/tools/docgen-zh.md)** - 生成带有复杂性分析的文档

**实用工具**
- **[`challenge`](docs/tools/challenge-zh.md)** - 防止"您说得绝对正确！"式回应，提供批判性分析
- **[`tracer`](docs/tools/tracer-zh.md)** - 用于调用流映射的静态分析提示

👉 **[完整工具参考](docs/tools-zh.md)** 包含示例、参数和工作流程

## 主要特性

**AI编排**
- **自动模型选择** - Claude为每个任务选择合适的AI
- **多模型工作流程** - 在单个对话中链接不同模型
- **对话连续性** - 在工具和模型之间保持上下文
- **[上下文复活](docs/context-revival.md)** - 即使在上下文重置后也能继续对话

**模型支持**
- **多个提供商** - Gemini、OpenAI、X.AI、OpenRouter、DIAL、Ollama
- **最新模型** - GPT-5、Gemini 2.5 Pro、O3、Grok-4、本地Llama
- **[思考模式](docs/advanced-usage.md#thinking-modes)** - 控制推理深度与成本
- **视觉支持** - 分析图像、图表、屏幕截图

**开发者体验**
- **引导式工作流程** - 系统化调查防止仓促分析
- **智能文件处理** - 自动扩展目录、管理令牌限制
- **网络搜索集成** - 访问当前文档和最佳实践
- **[大型提示支持](docs/advanced-usage.md#working-with-large-prompts)** - 绕过MCP的25K令牌限制

## 示例工作流程

**多模型代码审查：**
```
"使用gemini pro和o3执行代码审查，然后使用planner创建修复策略"
```
→ Claude系统化审查代码 → 咨询Gemini Pro → 获得O3的观点 → 创建统一行动计划

**协作调试：**
```
"使用最大思考模式调试这个竞态条件，然后用precommit验证修复"
```
→ 深度调查 → 专家分析 → 解决方案实施 → 预提交验证

**架构规划：**
```
"规划我们的微服务迁移，从pro和o3获得方法共识"
```
→ 结构化规划 → 多个专家意见 → 建立共识 → 实施路线图

👉 **[高级使用指南](docs/advanced-usage-zh.md)** 用于复杂工作流程、模型配置和高级用户功能

## 为什么选择Zen MCP？

**问题：** Claude很出色，但有时需要：
- 复杂决策的多个AI观点
- 防止仓促分析的系统化工作流程
- 超出其限制的扩展上下文
- 访问专业模型（推理、速度、本地）

**解决方案：** Zen将AI模型编排为Claude的开发团队：
- **Claude保持控制** - 您向Claude给出指令
- **模型提供专业知识** - 每个AI贡献其优势
- **上下文无缝流动** - 跨工具的完整对话历史
- **您决定工作流程** - 简单请求或复杂编排

## 快速链接

**📖 文档**
- [入门指南](docs/getting-started-zh.md) - 完整设置指南
- [工具参考](docs/tools-zh.md) - 所有工具及示例
- [高级使用](docs/advanced-usage-zh.md) - 高级用户功能
- [配置](docs/configuration-zh.md) - 环境变量、限制

**🔧 设置与支持**
- [WSL设置](docs/wsl-setup.md) - Windows用户
- [故障排除](docs/troubleshooting-zh.md) - 常见问题
- [贡献](docs/contributions.md) - 代码标准、PR流程

## 许可证

Apache 2.0许可证 - 详情请参阅[LICENSE](LICENSE)文件。

## 致谢

基于**多模型AI**协作的力量构建 🤝
- **A**ctual **I**ntelligence 由真正的人类提供
- [MCP (模型上下文协议)](https://modelcontextprotocol.com) 由Anthropic提供
- [Claude Code](https://claude.ai/code) - 您的AI编码编排器
- [Gemini 2.5 Pro & Flash](https://ai.google.dev/) - 扩展思考与快速分析
- [OpenAI O3 & GPT-5](https://openai.com/) - 强大推理与最新功能

### Star历史

[![Star History Chart](https://api.star-history.com/svg?repos=BeehiveInnovations/zen-mcp-server&type=Date)](https://www.star-history.com/#BeehiveInnovations/zen-mcp-server&Date)
