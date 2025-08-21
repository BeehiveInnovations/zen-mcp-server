# 添加新提供商

本指南说明如何为 Zen MCP Server 添加新的 AI 模型提供商支持。提供商系统设计为可扩展的，并遵循简单的模式。

## 概述

每个提供商：
- 继承自 `ModelProvider`（基类）或 `OpenAICompatibleProvider`（用于 OpenAI 兼容的 API）
- 使用 `ModelCapabilities` 对象定义支持的模型
- 实现一些核心抽象方法
- 通过环境变量自动注册

## 选择您的实现路径

**选项 A：完整提供商（`ModelProvider`）**
- 用于具有独特功能或自定义身份验证的 API
- 完全控制 API 调用和响应处理
- 必需方法：`generate_content()`、`count_tokens()`、`get_capabilities()`、`validate_model_name()`、`supports_thinking_mode()`、`get_provider_type()`

**选项 B：OpenAI 兼容（`OpenAICompatibleProvider`）**
- 用于遵循 OpenAI 聊天完成格式的 API
- 只需定义：模型配置、功能和验证
- 自动继承所有 API 处理

⚠️ **重要**：如果使用别名（如 `"gpt"` → `"gpt-4"`），请重写 `generate_content()` 以在 API 调用前解析它们。

## 逐步指南

### 1. 添加提供商类型

在 `providers/base.py` 中将您的提供商添加到 `ProviderType` 枚举：

```python
class ProviderType(Enum):
    GOOGLE = "google"
    OPENAI = "openai"
    EXAMPLE = "example"  # 添加这行
```

### 2. 创建提供商实现

#### 选项 A：完整提供商（原生实现）

创建 `providers/example.py`：

```python
"""示例模型提供商实现。"""

import logging
from typing import Optional
from .base import ModelCapabilities, ModelProvider, ModelResponse, ProviderType, RangeTemperatureConstraint

logger = logging.getLogger(__name__)

class ExampleModelProvider(ModelProvider):
    """示例模型提供商实现。"""
    
    # 使用 ModelCapabilities 对象定义模型（类似 Gemini 提供商）
    SUPPORTED_MODELS = {
        "example-large": ModelCapabilities(
            provider=ProviderType.EXAMPLE,
            model_name="example-large",
            friendly_name="Example Large",
            context_window=100_000,
            max_output_tokens=50_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="用于复杂任务的大型模型",
            aliases=["large", "big"],
        ),
        "example-small": ModelCapabilities(
            provider=ProviderType.EXAMPLE,
            model_name="example-small",
            friendly_name="Example Small",
            context_window=32_000,
            max_output_tokens=16_000,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="用于简单任务的快速模型",
            aliases=["small", "fast"],
        ),
    }
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        # 在这里初始化您的 API 客户端
    
    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        resolved_name = self._resolve_model_name(model_name)
        
        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型：{model_name}")
        
        # 如果需要，应用限制
        from utils.model_restrictions import get_restriction_service
        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.EXAMPLE, resolved_name, model_name):
            raise ValueError(f"模型 '{model_name}' 不被允许。")
        
        return self.SUPPORTED_MODELS[resolved_name]
    
    def generate_content(self, prompt: str, model_name: str, system_prompt: Optional[str] = None, 
                        temperature: float = 0.7, max_output_tokens: Optional[int] = None, **kwargs) -> ModelResponse:
        resolved_name = self._resolve_model_name(model_name)
        
        # 您的 API 调用逻辑在这里
        # response = your_api_client.generate(...)
        
        return ModelResponse(
            content="生成的响应",  # 来自您的 API
            usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            model_name=resolved_name,
            friendly_name="Example",
            provider=ProviderType.EXAMPLE,
        )
    
    def count_tokens(self, text: str, model_name: str) -> int:
        return len(text) // 4  # 简单估计
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.EXAMPLE
    
    def validate_model_name(self, model_name: str) -> bool:
        resolved_name = self._resolve_model_name(model_name)
        return resolved_name in self.SUPPORTED_MODELS
    
    def supports_thinking_mode(self, model_name: str) -> bool:
        capabilities = self.get_capabilities(model_name)
        return capabilities.supports_extended_thinking
```

#### 选项 B：OpenAI 兼容提供商（简化）

对于 OpenAI 兼容的 API：

```python
"""示例 OpenAI 兼容提供商。"""

from typing import Optional
from .base import ModelCapabilities, ModelResponse, ProviderType, RangeTemperatureConstraint
from .openai_compatible import OpenAICompatibleProvider

class ExampleProvider(OpenAICompatibleProvider):
    """示例 OpenAI 兼容提供商。"""
    
    FRIENDLY_NAME = "Example"
    
    # 使用 ModelCapabilities 定义模型（与其他提供商一致）
    SUPPORTED_MODELS = {
        "example-model-large": ModelCapabilities(
            provider=ProviderType.EXAMPLE,
            model_name="example-model-large",
            friendly_name="Example Large",
            context_window=128_000,
            max_output_tokens=64_000,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            aliases=["large", "big"],
        ),
    }
    
    def __init__(self, api_key: str, **kwargs):
        kwargs.setdefault("base_url", "https://api.example.com/v1")
        super().__init__(api_key, **kwargs)
    
    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        resolved_name = self._resolve_model_name(model_name)
        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型：{model_name}")
        return self.SUPPORTED_MODELS[resolved_name]
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.EXAMPLE
    
    def validate_model_name(self, model_name: str) -> bool:
        resolved_name = self._resolve_model_name(model_name)
        return resolved_name in self.SUPPORTED_MODELS
    
    def generate_content(self, prompt: str, model_name: str, **kwargs) -> ModelResponse:
        # 重要：在 API 调用前解析别名
        resolved_model_name = self._resolve_model_name(model_name)
        return super().generate_content(prompt=prompt, model_name=resolved_model_name, **kwargs)
```

### 3. 注册您的提供商

在 `providers/registry.py` 中添加环境变量映射：

```python
# 在 _get_api_key_for_provider 方法中：
key_mapping = {
    ProviderType.GOOGLE: "GEMINI_API_KEY",
    ProviderType.OPENAI: "OPENAI_API_KEY", 
    ProviderType.EXAMPLE: "EXAMPLE_API_KEY",  # 添加这行
}
```

添加到 `server.py`：

1. **导入您的提供商**：
```python
from providers.example import ExampleModelProvider
```

2. **添加到 `configure_providers()` 函数**：
```python
# 检查 Example API 密钥
example_key = os.getenv("EXAMPLE_API_KEY")
if example_key:
    ModelProviderRegistry.register_provider(ProviderType.EXAMPLE, ExampleModelProvider)
    logger.info("找到 Example API 密钥 - Example 模型可用")
```

3. **添加到提供商优先级**（在 `providers/registry.py` 中）：
```python
PROVIDER_PRIORITY_ORDER = [
    ProviderType.GOOGLE,
    ProviderType.OPENAI, 
    ProviderType.EXAMPLE,     # 在这里添加您的提供商
    ProviderType.CUSTOM,      # 本地模型
    ProviderType.OPENROUTER,  # 全包（保持最后）
]
```

### 4. 环境配置

添加到您的 `.env` 文件：
```bash
# 您的提供商 API 密钥
EXAMPLE_API_KEY=your_api_key_here

# 可选：禁用特定工具
DISABLED_TOOLS=debug,tracer
```

**注意**：`ModelCapabilities` 中的 `description` 字段帮助 Claude 在自动模式下选择最佳模型。

### 5. 测试您的提供商

创建基本测试来验证您的实现：

```python
# 测试模型验证
provider = ExampleModelProvider("test-key")
assert provider.validate_model_name("large") == True
assert provider.validate_model_name("unknown") == False

# 测试功能
caps = provider.get_capabilities("large")
assert caps.context_window > 0
assert caps.provider == ProviderType.EXAMPLE
```

## 关键概念

### 提供商优先级
当用户请求模型时，按优先级顺序检查提供商：
1. **原生提供商**（Gemini、OpenAI、Example）- 处理其特定模型
2. **自定义提供商** - 处理本地/自托管模型
3. **OpenRouter** - 处理其他所有情况的万能解决方案

### 模型验证
您的 `validate_model_name()` 应该**仅**对您明确支持的模型返回 `True`：

```python
def validate_model_name(self, model_name: str) -> bool:
    resolved_name = self._resolve_model_name(model_name)
    return resolved_name in self.SUPPORTED_MODELS  # 要具体！
```

### 模型别名
基类通过 `ModelCapabilities` 中的 `aliases` 字段自动处理别名解析。

## 重要说明

### OpenAI 兼容提供商中的别名解析
如果使用带别名的 `OpenAICompatibleProvider`，**您必须重写 `generate_content()`** 以在 API 调用前解析别名：

```python
def generate_content(self, prompt: str, model_name: str, **kwargs) -> ModelResponse:
    # 在 API 调用前解析别名
    resolved_model_name = self._resolve_model_name(model_name)
    return super().generate_content(prompt=prompt, model_name=resolved_model_name, **kwargs)
```

如果没有这个，带有像 `"large"` 这样别名的 API 调用将失败，因为您的 API 不识别别名。

## 最佳实践

- **在模型验证中要具体** - 只接受您实际支持的模型
- **一致使用 ModelCapabilities 对象**（如 Gemini 提供商）
- **包含描述性别名** 以获得更好的用户体验
- **添加错误处理**和日志记录以便调试
- **使用真实 API 调用进行测试** 以验证一切正常工作
- **遵循现有模式** 在 `providers/gemini.py` 和 `providers/custom.py` 中

## 快速检查清单

- [ ] 添加到 `providers/base.py` 中的 `ProviderType` 枚举
- [ ] 创建具有所有必需方法的提供商类
- [ ] 在 `providers/registry.py` 中添加 API 密钥映射
- [ ] 在 `registry.py` 中添加到提供商优先级顺序
- [ ] 在 `server.py` 中导入和注册
- [ ] 基本测试验证模型验证和功能
- [ ] 使用真实 API 调用进行测试

## 示例

查看现有实现：
- **完整提供商**：`providers/gemini.py`
- **OpenAI 兼容**：`providers/custom.py`
- **基类**：`providers/base.py`

现代方法直接在 `SUPPORTED_MODELS` 中使用 `ModelCapabilities` 对象，使实现更清洁、更一致。
