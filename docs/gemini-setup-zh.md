# Gemini CLI 设置

> **注意**：虽然 Zen MCP Server 成功连接到 Gemini CLI，但工具调用目前还不能
> 正常工作。我们将在集成完全功能化后更新本指南。

本指南说明如何配置 Zen MCP Server 与 [Gemini CLI](https://github.com/google-gemini/gemini-cli) 协同工作。

## 先决条件

- 已安装并配置 Zen MCP Server
- 已安装 Gemini CLI
- 在 `.env` 文件中配置至少一个 API 密钥

## 配置

1. 编辑 `~/.gemini/settings.json` 并添加：

```json
{
  "mcpServers": {
    "zen": {
      "command": "/path/to/zen-mcp-server/zen-mcp-server"
    }
  }
}
```

2. 将 `/path/to/zen-mcp-server` 替换为您实际的 Zen 安装路径。

3. 如果 `zen-mcp-server` 包装脚本不存在，请创建它：

```bash
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
exec .zen_venv/bin/python server.py "$@"
```

然后使其可执行：`chmod +x zen-mcp-server`

4. 重启 Gemini CLI。

现在所有 15 个 Zen 工具都可在您的 Gemini CLI 会话中使用。
