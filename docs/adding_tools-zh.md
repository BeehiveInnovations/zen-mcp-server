# 为 Zen MCP Server 添加工具

本指南说明如何为 Zen MCP Server 添加新工具。工具使 Claude 能够与 AI 模型交互，执行代码分析、调试和协作思考等专门任务。

## 工具类型

Zen 支持两种工具架构：

### 简单工具
- **模式**：单个请求 → AI 响应 → 格式化输出
- **用例**：聊天、快速分析、简单任务
- **优势**：简洁、轻量、易于实现
- **基类**：`SimpleTool`（`tools/simple/base.py`）

### 多步骤工作流工具
- **模式**：逐步调查，Claude 在步骤之间暂停进行调查
- **用例**：复杂分析、调试、代码审查、安全审计
- **优势**：系统化调查、专家分析集成、复杂任务产生更好结果
- **基类**：`WorkflowTool`（`tools/workflow/base.py`）

**建议**：对于大多数复杂分析任务使用工作流工具，因为它们通过强制系统化调查产生显著更好的结果。

## 实现指南

### 简单工具示例

```python
from tools.simple.base import SimpleTool
from tools.shared.base_models import ToolRequest
from pydantic import Field

class ChatTool(SimpleTool):
    def get_name(self) -> str:
        return "chat"
    
    def get_description(self) -> str:
        return "通用聊天与协作思考..."
    
    def get_tool_fields(self) -> dict:
        return {
            "prompt": {
                "type": "string", 
                "description": "您的问题或想法..."
            },
            "files": SimpleTool.FILES_FIELD  # 重用通用字段
        }
    
    def get_required_fields(self) -> list[str]:
        return ["prompt"]
    
    async def prepare_prompt(self, request) -> str:
        return self.prepare_chat_style_prompt(request)
```

### 工作流工具示例

```python  
from tools.workflow.base import WorkflowTool

class DebugTool(WorkflowTool):
    def get_name(self) -> str:
        return "debug"
    
    def get_description(self) -> str:
        return "调试和根本原因分析 - 逐步调查..."
    
    def get_required_actions(self, step_number, confidence, findings, total_steps):
        if step_number == 1:
            return ["搜索与问题相关的代码", "检查相关文件"]
        return ["跟踪执行流程", "用代码证据验证假设"]
    
    def should_call_expert_analysis(self, consolidated_findings):
        return len(consolidated_findings.relevant_files) > 0
    
    def prepare_expert_analysis_context(self, consolidated_findings):
        return f"调查发现：{consolidated_findings.findings}"
```

## 关键实现要点

### 简单工具
- 继承自 `SimpleTool`
- 实现：`get_name()`、`get_description()`、`get_tool_fields()`、`prepare_prompt()`
- 重写：`get_required_fields()`、`format_response()`（可选）

### 工作流工具
- 继承自 `WorkflowTool`
- 实现：`get_name()`、`get_description()`、`get_required_actions()`、`should_call_expert_analysis()`、`prepare_expert_analysis_context()`
- 重写：`get_tool_fields()`（可选）

### 注册
1. 在 `systemprompts/` 中创建系统提示
2. 在 `server.py` 中导入
3. 添加到 `TOOLS` 字典

## 测试您的工具

### 模拟器测试（推荐）
最重要的验证是将您的工具添加到模拟器测试套件：

```python
# 添加到 communication_simulator_test.py
def test_your_tool_validation(self):
    """使用真实 API 调用测试您的新工具"""
    response = self.call_tool("your_tool", {
        "prompt": "测试工具功能",
        "model": "flash"
    })
    
    # 验证响应结构和内容
    self.assertIn("status", response)
    self.assertEqual(response["status"], "success")
```

**为什么模拟器测试很重要：**
- 测试与 Claude 的实际 MCP 通信
- 验证真实的 AI 模型交互
- 捕获单元测试遗漏的集成问题
- 确保正确的对话线程
- 验证文件处理和去重

### 运行测试
```bash
# 测试您的特定工具
python communication_simulator_test.py --individual your_tool_validation

# 快速综合测试
python communication_simulator_test.py --quick
```

## 学习示例

- **简单工具**：`tools/chat.py` - 简洁的请求/响应模式
- **工作流工具**：`tools/debug.py` - 多步骤调查与专家分析

**建议**：从现有工具作为模板开始，探索基类以了解可用的钩子和方法。
