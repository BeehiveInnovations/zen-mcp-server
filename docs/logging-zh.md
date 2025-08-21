# 日志记录

## 快速开始 - 跟踪日志

监控日志的最简单方法是在启动服务器时使用 `-f` 标志：

```bash
# 启动服务器并自动跟踪 MCP 日志
./run-server.sh -f
```

这将启动服务器并立即开始跟踪 MCP 服务器日志。

## 日志文件

日志存储在项目文件夹内的 `logs/` 目录中：

- **`mcp_server.log`** - 主服务器操作、API 调用和错误
- **`mcp_activity.log`** - 工具调用和对话跟踪

日志文件在达到 20MB 时自动轮转，最多保留 10 个轮转文件。

## 查看日志

监控 MCP 服务器活动：

```bash
# 实时跟踪日志
tail -f logs/mcp_server.log

# 查看最后 100 行
tail -n 100 logs/mcp_server.log

# 查看活动日志（仅工具调用）
tail -f logs/mcp_activity.log

# 搜索特定模式
grep "ERROR" logs/mcp_server.log
grep "tool_name" logs/mcp_activity.log
```

## 日志级别

使用 `.env` 文件中的 `LOG_LEVEL` 设置详细程度：

```env
# 选项：DEBUG、INFO、WARNING、ERROR
LOG_LEVEL=INFO
```

- **DEBUG**：用于调试的详细信息
- **INFO**：一般操作消息（默认）
- **WARNING**：警告消息
- **ERROR**：仅错误消息

## 日志格式

日志使用带有时间戳的标准化格式：

```
2024-06-14 10:30:45,123 - module.name - INFO - Message here
```

## 提示

- 使用 `./run-server.sh -f` 获得最简单的日志监控体验
- 活动日志仅显示工具相关事件，输出更清洁
- 主服务器日志包含所有操作详情
- 日志在服务器重启后持续存在
