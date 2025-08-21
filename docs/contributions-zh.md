# 为 Zen MCP Server 贡献代码

感谢您对为 Zen MCP Server 贡献代码的兴趣！本指南将帮助您了解我们的开发流程、编码标准以及如何提交高质量的贡献。

## 开始

1. **在 GitHub 上 Fork 仓库**
2. **本地克隆您的 fork**
3. **设置开发环境**：
   ```bash
   ./run-server.sh
   ```
4. **从 `main` 创建功能分支**：
   ```bash
   git checkout -b feat/your-feature-name
   ```

## 开发流程

### 1. 代码质量标准

我们维护高代码质量标准。**所有贡献必须通过我们的自动化检查**。

#### 必需的代码质量检查

**选项 1 - 自动化（推荐）：**
```bash
# 安装 pre-commit 钩子（一次性设置）
pre-commit install

# 现在代码检查在每次提交时自动运行
# 包括：ruff（带自动修复）、black、isort
```

**选项 2 - 手动：**
```bash
# 运行综合质量检查脚本
./code_quality_checks.sh
```

此脚本自动运行：
- Ruff 代码检查与自动修复
- Black 代码格式化
- isort 导入排序
- 完整单元测试套件（361 个测试）
- 验证所有检查 100% 通过

**手动命令**（如果您喜欢单独运行）：
```bash
# 运行所有代码检查（必须 100% 通过）
ruff check .
black --check .
isort --check-only .

# 如果需要，自动修复问题
ruff check . --fix
black .
isort .

# 运行完整单元测试套件（必须 100% 通过）
python -m pytest -xvs

# 为工具变更运行模拟器测试
python communication_simulator_test.py
```

**重要**：
- **每个测试都必须通过** - 我们对 CI 中失败的测试零容忍
- 所有代码检查必须通过（ruff、black、isort）
- 导入排序必须正确
- GitHub Actions 中的测试失败将导致 PR 被拒绝

### 2. 测试要求

#### 何时添加测试

1. **新功能必须包含测试**：
   - 在 `tests/` 中为新函数或类添加单元测试
   - 测试成功和错误情况

2. **工具变更需要模拟器测试**：
   - 在 `simulator_tests/` 中为新工具或修改的工具添加模拟器测试
   - 使用展示功能的现实提示
   - 通过服务器日志验证输出

3. **错误修复需要回归测试**：
   - 添加本来可以捕获错误的测试
   - 确保错误不会重复出现

#### 测试命名约定
- 单元测试：`test_<feature>_<scenario>.py`
- 模拟器测试：`test_<tool>_<behavior>.py`

### 3. Pull Request 流程

#### PR 标题格式

您的 PR 标题必须遵循以下格式之一：

**版本提升前缀**（触发版本提升）：
- `feat: <description>` - 新功能（MINOR 版本提升）
- `fix: <description>` - 错误修复（PATCH 版本提升）
- `breaking: <description>` 或 `BREAKING CHANGE: <description>` - 破坏性变更（MAJOR 版本提升）
- `perf: <description>` - 性能改进（PATCH 版本提升）
- `refactor: <description>` - 代码重构（PATCH 版本提升）

**非版本前缀**（无版本提升）：
- `docs: <description>` - 仅文档
- `chore: <description>` - 维护任务
- `test: <description>` - 测试添加/变更
- `ci: <description>` - CI/CD 变更
- `style: <description>` - 代码样式变更

**其他选项**：
- `docs: <description>` - 仅文档变更
- `chore: <description>` - 维护任务

#### PR 检查清单

使用我们的 [PR 模板](../.github/pull_request_template.md) 并确保：

- [ ] PR 标题遵循上述格式指南
- [ ] 激活了虚拟环境并运行了 `./code_quality_checks.sh`（所有检查 100% 通过）
- [ ] 完成自我审查
- [ ] 为所有变更添加了测试
- [ ] 根据需要更新了文档
- [ ] 所有单元测试通过
- [ ] 相关模拟器测试通过（如果有工具变更）
- [ ] 准备好接受审查

### 4. 代码样式指南

#### Python 代码样式
- 遵循 PEP 8 与 Black 格式化
- 为函数参数和返回值使用类型提示
- 为所有公共函数和类添加文档字符串
- 尽可能保持函数专注且少于 50 行
- 使用描述性变量名

#### 示例：
```python
def process_model_response(
    response: ModelResponse,
    max_tokens: Optional[int] = None
) -> ProcessedResult:
    """处理和验证模型响应。

    参数：
        response: 来自模型提供商的原始响应
        max_tokens: 用于截断的可选令牌限制

    返回：
        包含验证和格式化内容的 ProcessedResult

    抛出：
        ValueError: 如果响应无效或超出限制
    """
    # 实现在这里
```

#### 导入组织
导入必须由 isort 组织到这些组：
1. 标准库导入
2. 第三方导入
3. 本地应用程序导入

### 5. 特定贡献类型

#### 添加新提供商
查看我们的详细指南：[添加新提供商](./adding_providers-zh.md)

#### 添加新工具
查看我们的详细指南：[添加新工具](./adding_tools-zh.md)

#### 修改现有工具
1. 确保向后兼容性，除非明确破坏性变更
2. 更新所有受影响的测试
3. 如果行为发生变化，更新文档
4. 为新功能添加模拟器测试

### 6. 文档标准

- 为面向用户的变更更新 README.md
- 为所有新代码添加文档字符串
- 更新相关的 docs/ 文件
- 为新功能包含示例
- 保持文档简洁明了

### 7. 提交消息指南

编写清晰、描述性的提交消息：
- 第一行：简要摘要（50 个字符或更少）
- 空行
- 如果需要，详细说明
- 引用问题："Fixes #123"

示例：
```
feat: 为 Gemini 提供商添加重试逻辑

为 Gemini API 调用中的瞬时错误实现
指数退避。最多重试 2 次，延迟
可配置。

Fixes #45
```

## 常见问题和解决方案

### 代码检查失败
```bash
# 自动修复大多数问题
ruff check . --fix
black .
isort .
```

### 测试失败
- 检查测试输出以查看具体错误
- 运行单独测试进行调试：`pytest tests/test_specific.py -xvs`
- 确保为模拟器测试设置了服务器环境

### 导入错误
- 验证虚拟环境已激活
- 检查所有依赖项已安装：`pip install -r requirements.txt`

## 获取帮助

- **问题**：使用"question"标签打开 GitHub issue
- **错误报告**：使用错误报告模板
- **功能请求**：使用功能请求模板
- **讨论**：使用 GitHub Discussions 进行一般话题

## 行为准则

- 保持尊重和包容
- 欢迎新手并帮助他们开始
- 专注于建设性反馈
- 假定善意

## 认可

贡献者在以下方面得到认可：
- GitHub 贡献者页面
- 重要贡献的发布说明
- 卓越工作的特别提及

感谢您为 Zen MCP Server 贡献代码！您的努力帮助使这个工具对每个人都更好。
