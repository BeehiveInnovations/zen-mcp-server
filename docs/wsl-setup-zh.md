# WSL（Windows Linux 子系统）设置指南

本指南提供在 Windows 上使用 WSL 设置 Zen MCP Server 的详细说明。

## WSL 先决条件

```bash
# 更新 WSL 并确保您有最新的 Ubuntu 发行版
sudo apt update && sudo apt upgrade -y

# 安装必需的系统依赖项
sudo apt install -y python3-venv python3-pip curl git

# 安装 Node.js 和 npm（Claude Code CLI 需要）
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# 全局安装 Claude Code CLI
npm install -g @anthropic-ai/claude-code
```

## WSL 特定安装步骤

1. **在 WSL 环境中克隆仓库**（不要在 Windows 文件系统中）：
   ```bash
   # 导航到您的主目录或 WSL 中的首选位置
   cd ~
   
   # 克隆仓库
   git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
   cd zen-mcp-server
   ```

2. **运行设置脚本**：
   ```bash
   # 使脚本可执行并运行
   chmod +x run-server.sh
   ./run-server.sh
   ```

3. **验证 Claude Code 可以找到 MCP 服务器**：
   ```bash
   # 列出配置的 MCP 服务器
   claude mcp list
   
   # 您应该在输出中看到 'zen' 列出
   # 如果没有，设置脚本将提供正确的配置
   ```

## WSL 问题故障排除

### Python 环境问题

```bash
# 如果遇到 Python 虚拟环境问题
sudo apt install -y python3.12-venv python3.12-dev

# 确保 pip 是最新的
python3 -m pip install --upgrade pip
```

### 路径问题

- 始终为 MCP 配置使用完整的 WSL 路径（例如，`/home/YourName/zen-mcp-server/`）
- 设置脚本自动检测 WSL 并配置正确的路径

### Claude Code 连接问题

```bash
# 如果 Claude Code 无法连接到 MCP 服务器，检查配置
cat ~/.claude.json | grep -A 10 "zen"

# 配置应显示正确的 WSL 路径到 Python 可执行文件
# 示例："/home/YourName/zen-mcp-server/.zen_venv/bin/python"
```

### 性能提示

为了获得最佳性能，请将您的 zen-mcp-server 目录保存在 WSL 文件系统中（例如，`~/zen-mcp-server`），而不是 Windows 文件系统（`/mnt/c/...`）中。
