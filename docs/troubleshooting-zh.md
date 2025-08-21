# 故障排除指南

## 快速调试步骤

如果您在使用Zen MCP服务器时遇到问题，请按照以下步骤操作：

### 1. 检查MCP连接

打开Claude Desktop并输入`/mcp`查看zen是否已连接：
- ✅ 如果zen出现在列表中，连接正在工作
- ❌ 如果未列出或显示错误，继续步骤2

### 2. 以调试模式启动Claude

关闭Claude Desktop并以调试日志记录重启：

```bash
# macOS/Linux
claude --debug

# Windows（在WSL2中）
claude.exe --debug
```

在控制台输出中查找错误消息，特别是：
- API密钥错误
- Python/环境问题
- 文件权限错误

### 3. 验证API密钥

检查您的API密钥是否正确设置：

```bash
# 检查您的.env文件
cat .env

# 确保至少设置了一个密钥：
# GEMINI_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
```

如果需要更新API密钥，编辑`.env`文件，然后重启Claude以使更改生效。

### 4. 检查服务器日志

查看服务器日志以获取详细错误信息：

```bash
# 查看最近日志
tail -n 100 logs/mcp_server.log

# 实时跟踪日志
tail -f logs/mcp_server.log

# 或在启动时使用-f标志自动跟踪日志
./run-server.sh -f

# 搜索错误
grep "ERROR" logs/mcp_server.log
```

详细访问日志信息请参阅[日志文档](logging.md)。

### 5. 常见问题

**Claude Desktop中的"连接失败"**
- 确保Claude配置中的服务器路径正确
- 运行`./run-server.sh`验证设置并查看配置
- 检查Python是否已安装：`python3 --version`

**"需要API密钥环境变量"**
- 将API密钥添加到`.env`文件
- 更新`.env`后重启Claude Desktop

**文件路径错误**
- 始终使用绝对路径：`/Users/you/project/file.py`
- 从不使用相对路径：`./file.py`

**找不到Python模块**
- 运行`./run-server.sh`重新安装依赖
- 检查虚拟环境是否激活：应在Python路径中看到`.zen_venv`

### 6. 环境问题

**虚拟环境问题**
```bash
# 完全重置环境
rm -rf .zen_venv
./run-server.sh
```

**权限问题**
```bash
# 确保脚本可执行
chmod +x run-server.sh
```

### 7. 仍有问题？

如果尝试这些步骤后问题仍然存在：

1. **重现问题** - 记录导致问题的确切步骤
2. **收集日志** - 保存Claude调试模式和服务器日志中的相关错误消息
3. **打开GitHub问题**，包含：
   - 您的操作系统
   - Python版本：`python3 --version`
   - 日志中的错误消息
   - 重现步骤
   - 您已经尝试的方法

## Windows用户

**重要**：Windows用户必须使用WSL2。安装方法：

```powershell
wsl --install -d Ubuntu
```

然后在WSL2内按照标准设置进行操作。
