# HTTP 传输录制器测试

用于测试昂贵 API 调用（如 o3-pro）的自定义 HTTP 录制器，使用真实响应。

## 概述

HTTP 传输录制器在传输层捕获和回放 HTTP 交互，支持：
- 昂贵 API 的成本效率测试（录制一次，永久回放）
- 使用真实 API 响应的确定性测试
- 与 httpx 和 OpenAI SDK 的无缝集成
- 安全录制的自动 PII 清理

## 快速开始

```python
from tests.transport_helpers import inject_transport

# 使用自动传输注入的简单一行设置
def test_expensive_api_call(monkeypatch):
    inject_transport(monkeypatch, "tests/openai_cassettes/my_test.json")
    
    # 进行 API 调用 - 自动录制/回放并进行 PII 清理
    result = await chat_tool.execute({"prompt": "2+2?", "model": "o3-pro"})
```

## 工作原理

1. **首次运行**（录像带不存在）：录制真实 API 调用
2. **后续运行**（录像带存在）：回放保存的响应
3. **重新录制**：删除录像带文件并重新运行

## 测试中的用法

`transport_helpers.inject_transport()` 函数简化了测试设置：

```python
from tests.transport_helpers import inject_transport

async def test_with_recording(monkeypatch):
    # 一行设置 - 处理所有传输注入复杂性
    inject_transport(monkeypatch, "tests/openai_cassettes/my_test.json")
    
    # 正常使用 API - 录制/回放透明发生
    result = await chat_tool.execute({"prompt": "2+2?", "model": "o3-pro"})
```

对于手动设置，请参见 `test_o3_pro_output_text_fix.py`。

## 自动 PII 清理

所有录制都会自动清理以删除敏感数据：

- **API 密钥和令牌**：Bearer 令牌、API 密钥和认证头
- **个人数据**：电子邮件地址、IP 地址、电话号码
- **URL**：敏感查询参数和路径
- **自定义模式**：添加您自己的清理规则

默认情况下在 `RecordingTransport` 中启用清理。要禁用：

```python
transport = TransportFactory.create_transport(cassette_path, sanitize=False)
```

## 文件结构

```
tests/
├── openai_cassettes/           # 录制的 API 交互
│   └── *.json                  # 录像带文件
├── http_transport_recorder.py  # 传输实现
├── pii_sanitizer.py           # 自动 PII 清理
├── transport_helpers.py       # 简化的传输注入
├── sanitize_cassettes.py      # 批量清理脚本
└── test_o3_pro_output_text_fix.py  # 用法示例
```

## 清理现有录像带

使用 `sanitize_cassettes.py` 脚本清理现有录制：

```bash
# 清理所有录像带（创建备份）
python tests/sanitize_cassettes.py

# 清理特定录像带
python tests/sanitize_cassettes.py tests/openai_cassettes/my_test.json

# 跳过备份创建
python tests/sanitize_cassettes.py --no-backup
```

脚本将：
- 创建原始文件的时间戳备份
- 应用全面的 PII 清理
- 保留 JSON 结构和功能

## 成本管理

- **一次性成本**：仅初始录制
- **零持续成本**：回放免费
- **CI 友好**：回放不需要 API 密钥

## 重新录制

当 API 变更需要新录制时：

```bash
# 删除特定录像带
rm tests/openai_cassettes/my_test.json

# 使用真实 API 密钥运行测试
python -m pytest tests/test_o3_pro_output_text_fix.py
```

## 实现详情

- **RecordingTransport**：捕获真实 HTTP 调用并自动进行 PII 清理
- **ReplayTransport**：从录像带提供保存的响应
- **TransportFactory**：基于录像带存在自动选择模式
- **PIISanitizer**：敏感数据的全面清理（默认集成）

**安全注意**：虽然录制会自动清理，但在提交前始终检查新的录像带文件。清理器会删除已知的敏感数据模式，但特定领域的机密可能需要自定义规则。

实现详情请参见：
- `tests/http_transport_recorder.py` - 核心传输实现
- `tests/pii_sanitizer.py` - 清理模式和逻辑
- `tests/transport_helpers.py` - 简化的测试集成
