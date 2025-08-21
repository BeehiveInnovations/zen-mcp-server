# Docker 部署指南

本指南介绍使用 Docker 和 Docker Compose 在生产环境中部署 Zen MCP Server。

## 快速开始

1. **克隆仓库**：
   ```bash
   git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
   cd zen-mcp-server
   ```

2. **配置环境变量**：
   ```bash
   cp .env.example .env
   # 编辑 .env 文件添加您的 API 密钥
   ```

3. **使用 Docker Compose 部署**：
   ```bash
   # Linux/macOS
   ./docker/scripts/deploy.sh
   
   # Windows PowerShell
   .\docker\scripts\deploy.ps1
   ```

## 环境配置

### 必需的 API 密钥

必须在 `.env` 文件中配置至少一个 API 密钥：

```env
# Google Gemini（推荐）
GEMINI_API_KEY=your_gemini_api_key_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# X.AI GROK
XAI_API_KEY=your_xai_api_key_here

# OpenRouter（统一访问）
OPENROUTER_API_KEY=your_openrouter_api_key_here

# 附加提供商
DIAL_API_KEY=your_dial_api_key_here
DIAL_API_HOST=your_dial_host
```

### 可选配置

```env
# 默认模型选择
DEFAULT_MODEL=auto

# 日志记录
LOG_LEVEL=INFO
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5

# 高级设置
DEFAULT_THINKING_MODE_THINKDEEP=high
DISABLED_TOOLS=
MAX_MCP_OUTPUT_TOKENS=

# 时区
TZ=UTC
```

## 部署脚本

### Linux/macOS 部署

使用提供的 bash 脚本进行稳健部署：

```bash
./docker/scripts/deploy.sh
```

**功能：**
- ✅ 环境验证
- ✅ 指数退避健康检查
- ✅ 自动日志管理
- ✅ 服务状态监控

### Windows PowerShell 部署

在 Windows 环境中使用 PowerShell 脚本：

```powershell
.\docker\scripts\deploy.ps1
```

**附加选项：**
```powershell
# 跳过健康检查
.\docker\scripts\deploy.ps1 -SkipHealthCheck

# 自定义超时
.\docker\scripts\deploy.ps1 -HealthCheckTimeout 120
```

## Docker 架构

### 多阶段构建

Dockerfile 使用多阶段构建以优化镜像大小：

1. **构建阶段**：安装依赖项并创建虚拟环境
2. **运行阶段**：仅复制必要文件以获得最小占用空间

### 安全功能

- **非 root 用户**：以 `zenuser`（UID/GID 1000）身份运行
- **只读文件系统**：容器文件系统不可变
- **无新权限**：防止权限提升
- **安全 tmpfs**：具有严格权限的临时目录

### 资源管理

默认资源限制：
```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

## 服务管理

### 启动服务

```bash
# 后台启动
docker-compose up -d

# 带日志启动
docker-compose up
```

### 监控

```bash
# 查看服务状态
docker-compose ps

# 跟踪日志
docker-compose logs -f zen-mcp

# 查看健康状态
docker inspect zen-mcp-server --format='{{.State.Health.Status}}'
```

### 停止服务

```bash
# 优雅停止
docker-compose down

# 强制停止
docker-compose down --timeout 10
```

## 健康检查

容器包含全面的健康检查：

- **进程检查**：验证 server.py 正在运行
- **导入检查**：验证关键 Python 模块
- **目录检查**：确保日志目录可写
- **API 检查**：测试提供商连接

健康检查配置：
```yaml
healthcheck:
  test: ["CMD", "python", "/usr/local/bin/healthcheck.py"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## 持久数据

### 卷

- **日志**：`./logs:/app/logs` - 应用程序日志
- **配置**：`zen-mcp-config:/app/conf` - 配置持久化
- **时间同步**：`/etc/localtime:/etc/localtime:ro` - 主机时区同步

**注意**：`zen-mcp-config` 是一个命名的 Docker 卷，它在容器重启之间保持配置数据。由于这个持久卷，放置在容器内 `/app/conf` 中的所有数据都会被保留。这适用于 `docker-compose run` 和 `docker-compose up` 命令。

### 日志管理

日志自动轮转，具有可配置的保留期：

```env
LOG_MAX_SIZE=10MB      # 最大日志文件大小
LOG_BACKUP_COUNT=5     # 要保留的备份文件数量
```

## 网络

### 默认配置

- **网络**：`zen-network`（桥接）
- **子网**：`172.20.0.0/16`
- **隔离**：容器在隔离网络中运行

### 端口暴露

默认情况下，不暴露端口。MCP 服务器在与 Claude Desktop 或其他 MCP 客户端一起使用时通过 stdio 通信。

对于外部访问（高级用户）：
```yaml
ports:
  - "3000:3000"  # 如果需要，添加到服务配置
```

## 故障排除

### 常见问题

**1. 健康检查失败：**
```bash
# 检查日志
docker-compose logs zen-mcp

# 手动健康检查
docker exec zen-mcp-server python /usr/local/bin/healthcheck.py
```

**2. 权限错误：**
```bash
# 修复日志目录权限
sudo chown -R 1000:1000 ./logs
```

**3. 环境变量未加载：**
```bash
# 验证 .env 文件存在且可读
ls -la .env
cat .env
```

**4. API 密钥验证错误：**
```bash
# 检查容器中的环境变量
docker exec zen-mcp-server env | grep -E "(GEMINI|OPENAI|XAI)"
```

### 调试模式

启用详细日志记录进行故障排除：

```env
LOG_LEVEL=DEBUG
```

## 生产考虑

### 安全

1. **在生产中使用 Docker secrets** 存储 API 密钥：
   ```yaml
   secrets:
     gemini_api_key:
       external: true
   ```

2. **启用 AppArmor/SELinux**（如果可用）

3. **定期安全更新**：
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

### 监控

考虑与监控解决方案集成：

- **Prometheus**：健康检查指标
- **Grafana**：日志可视化
- **AlertManager**：健康状态警报

### 备份

备份持久卷：
```bash
# 备份配置
docker run --rm -v zen-mcp-config:/data -v $(pwd):/backup alpine tar czf /backup/config-backup.tar.gz -C /data .

# 恢复配置
docker run --rm -v zen-mcp-config:/data -v $(pwd):/backup alpine tar xzf /backup/config-backup.tar.gz -C /data
```

## 性能调优

### 资源优化

根据您的工作负载调整限制：

```yaml
deploy:
  resources:
    limits:
      memory: 1G        # 为重工作负载增加
      cpus: '1.0'       # 为并发请求提供更多 CPU
```

### 内存管理

监控内存使用：
```bash
docker stats zen-mcp-server
```

如果需要，调整 Python 内存设置：
```env
PYTHONMALLOC=pymalloc
MALLOC_ARENA_MAX=2
```

## 与 Claude Desktop 集成

配置 Claude Desktop 使用容器化服务器。**根据您的需求选择以下配置之一：**

### 选项 1：直接 Docker 运行（推荐）

**对大多数用户来说最简单、最可靠的选项。**

```json
{
  "mcpServers": {
    "zen-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--env-file",
        "/absolute/path/to/zen-mcp-server/.env",
        "-v",
        "/absolute/path/to/zen-mcp-server/logs:/app/logs",
        "zen-mcp-server:latest"
      ]
    }
  }
}
```

**Windows 示例**：
```json
{
  "mcpServers": {
    "zen-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--env-file",
        "C:/path/to/zen-mcp-server/.env",
        "-v",
        "C:/path/to/zen-mcp-server/logs:/app/logs",
        "zen-mcp-server:latest"
      ]
    }
  }
}
```

### 选项 2：Docker Compose 运行（一次性，使用 docker-compose.yml）

**使用 docker-compose.yml 的高级配置，无持久容器。**

```json
{
  "mcpServers": {
    "zen-mcp": {
      "command": "docker-compose",
      "args": [
        "-f", "/absolute/path/to/zen-mcp-server/docker-compose.yml",
        "run", "--rm", "zen-mcp"
      ]
    }
  }
}
```

### 选项 3：内联环境变量（高级）

**用于高度定制需求。**

```json
{
  "mcpServers": {
    "zen-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e", "GEMINI_API_KEY=your_key_here",
        "-e", "LOG_LEVEL=INFO",
        "-e", "DEFAULT_MODEL=auto",
        "-v", "/path/to/logs:/app/logs",
        "zen-mcp-server:latest"
      ]
    }
  }
}
```

### 配置说明

**重要说明：**
- 将 `/absolute/path/to/zen-mcp-server` 替换为项目的实际路径。
- 始终为 Docker 卷使用正斜杠 `/`，即使在 Windows 上也是如此。
- 确保 `.env` 文件存在并包含您的 API 密钥。
- **持久卷**：Docker Compose 选项（选项 2）自动使用 `zen-mcp-config` 命名卷进行持久配置存储。

**环境文件要求：**
```env
# 至少需要一个 API 密钥
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
# ... 其他密钥
```

**故障排除：**
- 如果选项 1 失败：检查 Docker 镜像是否存在（`docker images zen-mcp-server`）。
- 如果选项 2 失败：验证 compose 文件路径并确保服务未在使用中。
- 权限问题：确保 `logs` 文件夹可写。

## 高级配置

### 自定义网络

对于复杂部署：
```yaml
networks:
  zen-network:
    driver: bridge
      ipam:
        config:
          - subnet: 172.20.0.0/16
            gateway: 172.20.0.1
```

### 多实例

使用不同配置运行多个实例：
```bash
# 复制 compose 文件
cp docker-compose.yml docker-compose.dev.yml

# 修改服务名称和端口
# 使用自定义 compose 文件部署
docker-compose -f docker-compose.dev.yml up -d
```

## 迁移和更新

### 更新服务器

```bash
# 拉取最新更改
git pull origin main

# 重建并重启
docker-compose down
docker-compose build --no-cache
./docker/scripts/deploy.sh
```

### 数据迁移

升级时，配置保存在命名卷 `zen-mcp-config` 中。

对于主要版本升级，请检查 [CHANGELOG](../CHANGELOG.md) 以了解破坏性变更。

## 支持

如有任何问题，请在 GitHub 上提交 issue 或咨询官方文档。


---

**下一步：**
- 查看[配置指南](configuration-zh.md)了解详细的环境变量选项
- 查看[高级使用](advanced-usage-zh.md)了解自定义模型配置
- 查看[故障排除](troubleshooting-zh.md)了解常见问题和解决方案
