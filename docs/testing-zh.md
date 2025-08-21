# 测试指南

本项目通过单元测试和集成模拟器测试提供全面的测试覆盖。

## 运行测试

### 先决条件
- 环境设置：`./run-server.sh`
  - 使用 `./run-server.sh -f` 在启动后自动跟踪日志

### 单元测试

使用 pytest 运行所有单元测试：
```bash
# 运行所有测试并输出详细信息
python -m pytest -xvs

# 运行特定测试文件
python -m pytest tests/test_providers.py -xvs
```

### 模拟器测试

模拟器测试复制真实的 Claude CLI 与独立 MCP 服务器的交互。与测试隔离函数的单元测试不同，模拟器测试验证完整的端到端流程，包括：
- 实际的 MCP 协议通信
- 独立服务器交互
- 跨工具的多轮对话
- 日志输出验证

**重要**：模拟器测试需要在 `.env` 文件中设置 `LOG_LEVEL=DEBUG` 来验证详细的执行日志。

#### 测试期间监控日志

**重要**：MCP stdio 协议在工具执行期间会干扰 stderr 输出。工具执行日志被写入本地日志文件。这是基于 stdio 的 MCP 协议的已知限制。

要在测试执行期间监控日志：

```bash
# 启动服务器并自动跟踪日志
./run-server.sh -f

# 或手动监控主服务器日志（包含所有工具执行详情）
tail -f -n 500 logs/mcp_server.log

# 监控 MCP 活动日志（工具调用和完成）
tail -f logs/mcp_activity.log

# 检查日志文件大小（日志在 20MB 时轮转）
ls -lh logs/mcp_*.log*
```

**日志轮转**：所有日志文件都配置为在 20MB 时自动轮转，以防止磁盘空间问题。服务器保留：
- mcp_server.log 的 10 个轮转文件（总计 200MB）
- mcp_activity.log 的 5 个轮转文件（总计 100MB）

**为什么日志出现在文件中**：MCP stdio_server 在工具执行期间捕获 stderr，以防止干扰 JSON-RPC 协议通信。这意味着工具执行日志被写入文件而不是显示在控制台输出中。

#### 运行所有模拟器测试
```bash
# 运行所有模拟器测试
python communication_simulator_test.py

# 运行详细输出用于调试
python communication_simulator_test.py --verbose

# 测试后保留服务器日志以供检查
python communication_simulator_test.py --keep-logs
```

#### 运行单个测试
要隔离运行单个模拟器测试（对调试或测试开发有用）：

```bash
# 按名称运行特定测试
python communication_simulator_test.py --individual basic_conversation

# 可用测试示例：
python communication_simulator_test.py --individual content_validation
python communication_simulator_test.py --individual cross_tool_continuation
python communication_simulator_test.py --individual memory_validation
```

#### 其他选项
```bash
# 列出所有可用的模拟器测试及其描述
python communication_simulator_test.py --list-tests

# 运行多个特定测试（不是全部）
python communication_simulator_test.py --tests basic_conversation content_validation
```

### 代码质量检查

提交前，确保所有代码检查通过：
```bash
# 运行所有代码检查
ruff check .
black --check .
isort --check-only .

# 自动修复问题
ruff check . --fix
black .
isort .
```

## 每个测试套件涵盖的内容

### 单元测试
测试隔离的组件和函数：
- **提供商功能**：模型初始化、API 交互、能力检查
- **工具操作**：所有 MCP 工具（chat、analyze、debug 等）
- **对话记忆**：线程、延续、历史管理
- **文件处理**：路径验证、令牌限制、去重
- **自动模式**：模型选择逻辑和回退行为

### HTTP 录制/回放测试（HTTP 传输录制器）
对昂贵 API 调用（如 o3-pro）的测试使用自定义录制/回放：
- **真实 API 验证**：针对实际提供商响应的测试
- **成本效率**：录制一次，永久回放
- **提供商兼容性**：根据真实 API 验证修复
- 使用 HTTP 传输录制器进行基于 httpx 的 API 调用
- 详见 [HTTP 录制/回放测试指南](./vcr-testing-zh.md)

### 模拟器测试
通过模拟实际的 Claude 提示来验证真实世界使用场景：
- **基本对话**：使用真实提示的多轮聊天功能
- **跨工具延续**：跨不同工具的上下文保持
- **文件去重**：重复文件引用的高效处理
- **模型选择**：正确路由到配置的提供商
- **令牌分配**：实践中的上下文窗口管理
- **Redis 验证**：对话持久化和检索

## 贡献

有关详细的贡献指南、测试要求和代码质量标准，请查看我们的[贡献指南](./contributions-zh.md)。

### 快速测试参考

```bash
# 运行质量检查
./code_quality_checks.sh

# 运行单元测试
python -m pytest -xvs

# 运行模拟器测试（用于工具变更）
python communication_simulator_test.py
```

记住：提交 PR 前所有测试必须通过。完整要求请查看[贡献指南](./contributions-zh.md)。
