# Zen MCP Server 语言配置

本指南说明如何配置和使用本地化功能来自定义 MCP 工具响应的语言。

## 概述

本地化功能允许您指定 MCP 工具应该使用哪种语言响应，同时保持其分析能力。这对于希望用母语接收答案的非英语用户特别有用。

## 配置

### 1. 环境变量

在 `.env` 文件中使用 `LOCALE` 环境变量设置语言：

```bash
# 在您的 .env 文件中
LOCALE=fr-FR
```

### 2. 支持的语言

您可以使用任何标准语言代码。示例：

- `fr-FR` - 法语（法国）
- `en-US` - 英语（美国）
- `zh-CN` - 中文（简体）
- `zh-TW` - 中文（繁体）
- `ja-JP` - 日语
- `ko-KR` - 韩语
- `es-ES` - 西班牙语（西班牙）
- `de-DE` - 德语（德国）
- `it-IT` - 意大利语（意大利）
- `pt-PT` - 葡萄牙语（葡萄牙）
- `ru-RU` - 俄语（俄罗斯）
- `ar-SA` - 阿拉伯语（沙特阿拉伯）

### 3. 默认行为

如果未指定语言（`LOCALE` 为空或未设置），工具将默认为英语。

## 技术实现

### 架构

本地化在 `tools/shared/base_tool.py` 中的 `BaseTool` 类中实现。所有工具自动继承此功能。

### `get_language_instruction()` 方法

```python
def get_language_instruction(self) -> str:
    """
    基于 LOCALE 配置生成语言指令。
    返回：
        str: 要添加到提示前面的语言指令，如果未设置区域设置则返回空字符串
    """
    from config import LOCALE
    if not LOCALE or not LOCALE.strip():
        return ""
    return f"Always respond in {LOCALE.strip()}.\n\n"
```

### 工具执行中的集成

语言指令自动添加到每个工具的系统提示前面：

```python
# 在 tools/simple/base.py 中
base_system_prompt = self.get_system_prompt()
language_instruction = self.get_language_instruction()
system_prompt = language_instruction + base_system_prompt
```

## 使用方法

### 1. 基本设置

1. 编辑您的 `.env` 文件：
   ```bash
   LOCALE=fr-FR
   ```
2. 重启 MCP 服务器：
   ```bash
   python server.py
   ```
3. 使用任何工具 - 响应将使用指定的语言。

### 2. 示例

**之前（默认英语）：**
```
工具：chat
输入："Explain how to use Python dictionaries"
输出："Python dictionaries are key-value pairs that allow you to store and organize data..."
```

**之后（使用 LOCALE=fr-FR）：**
```
工具：chat
输入："Explain how to use Python dictionaries"
输出："Les dictionnaires Python sont des paires clé-valeur qui permettent de stocker et d'organiser des données..."
```

### 3. 受影响的工具

所有 MCP 工具都受此配置影响：

- `chat` - 一般对话
- `codereview` - 代码审查
- `analyze` - 代码分析
- `debug` - 调试
- `refactor` - 重构
- `thinkdeep` - 深度思考
- `consensus` - 模型共识
- 以及所有其他工具...

## 最佳实践

### 1. 语言选择
- 使用标准语言代码（ISO 639-1 与 ISO 3166-1 国家代码）
- 如果需要，对地区变体要具体（例如，`zh-CN` vs `zh-TW`）

### 2. 一致性
- 在团队中使用相同的语言设置以保持一致性
- 在团队文档中记录选择的语言

### 3. 测试
- 使用不同工具测试配置以确保一致性

## 故障排除

### 问题：语言不改变
**解决方案：**
1. 检查 `LOCALE` 变量在 `.env` 中设置正确
2. 完全重启 MCP 服务器
3. 确保值中没有额外空格

### 问题：部分翻译的响应
**说明：**
- AI 模型有时可能混合语言
- 这取决于使用模型的多语言能力
- 技术术语可能保留英语

### 问题：配置错误
**解决方案：**
1. 检查 `.env` 文件的语法
2. 确保值周围没有引号

## 高级自定义

### 自定义语言指令

要自定义语言指令，请修改 `tools/shared/base_tool.py` 中的 `get_language_instruction()` 方法：

```python
def get_language_instruction(self) -> str:
    from config import LOCALE
    if not LOCALE or not LOCALE.strip():
        return ""
    # 自定义指令
    return f"Always respond in {LOCALE.strip()} and use a professional tone.\n\n"
```

### 单个工具自定义

您也可以在特定工具中重写方法以获得自定义行为：

```python
class MyCustomTool(SimpleTool):
    def get_language_instruction(self) -> str:
        from config import LOCALE
        if LOCALE == "fr-FR":
            return "Respond in French with precise technical vocabulary.\n\n"
        elif LOCALE == "zh-CN":
            return "请用中文回答，使用专业术语。\n\n"
        else:
            return super().get_language_instruction()
```

## 与其他功能的集成

本地化与所有其他 MCP 服务器功能配合使用：

- **对话线程** - 支持多语言对话
- **文件处理** - 文件分析使用指定语言
- **网络搜索** - 搜索指令保持功能性
- **模型选择** - 与所有支持的模型配合使用
