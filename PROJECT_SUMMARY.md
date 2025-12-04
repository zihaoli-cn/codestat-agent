# CodeStat Agent - 项目总结

## 项目概述

**CodeStat Agent** 是一个基于 Webhook 的代码行数统计自动化工具，支持 Gitea、GitHub 和 GitLab 三大平台。该项目采用 Docker 容器化技术，实现了轻量级、可扩展的代码统计解决方案。

**GitHub 仓库**: https://github.com/zihaoli-cn/codestat-agent

---

## 核心特性

### 1. 多平台 Webhook 支持

项目实现了统一的 Webhook 抽象层，通过工厂模式支持三种 Git 平台：

- **Gitea**: 使用 `X-Gitea-Signature` 进行签名验证
- **GitHub**: 使用 `X-Hub-Signature-256` 进行签名验证
- **GitLab**: 使用 `X-Gitlab-Token` 进行签名验证

所有平台的 Webhook 事件都被解析为统一的 `PushEvent` 模型，确保后续处理逻辑的一致性。

### 2. Docker 容器化执行

每个仓库拥有独立的 Docker 容器，基于轻量级的 Alpine Linux 镜像（约 50MB）：

- 预装 `git` 和 `cloc` 工具
- 容器资源限制：512MB 内存，50% CPU
- 持久化存储：仓库代码通过卷挂载到宿主机
- 增量拉取：首次 `git clone`，后续 `git pull`

### 3. 智能任务调度

任务调度器负责管理代码统计任务的生命周期：

- 自动过滤非主分支推送
- 为每个任务分配唯一 ID
- 后台监控任务状态（每 5 秒检查一次）
- 超时控制（默认 10 分钟）
- 自动清理已完成的容器

### 4. 灵活配置系统

支持全局和仓库级别的 CLOC 配置：

```json
{
  "exclude_ext": ["md", "txt"],
  "exclude_lang": ["Markdown", "YAML"],
  "include_ext": ["py", "js"],
  "use_gitignore": true,
  "timeout": 600
}
```

Worker 容器会自动将 `.gitignore` 文件转换为 CLOC 排除列表。

### 5. 持久化存储

使用 SQLite 数据库存储：

- 仓库配置信息
- 任务执行历史
- 统计结果（JSON 格式）

数据库采用 SQLAlchemy ORM，支持异步操作。

### 6. Web 可视化界面

基于 FastAPI + Tailwind CSS + Alpine.js 构建的单页应用：

- **仓库管理**: 查看已配置的仓库列表
- **任务监控**: 实时查看任务状态和结果
- **容器管理**: 查看运行中的容器，支持停止和清理操作
- **自动刷新**: 每 10 秒自动更新数据

### 7. RESTful API

提供完整的 REST API 用于编程集成：

- `GET /api/repositories` - 列出所有仓库
- `POST /api/repositories/{id}` - 创建或更新仓库配置
- `GET /api/tasks` - 查询任务列表（支持过滤）
- `GET /api/containers` - 查看容器状态
- `POST /api/containers/{id}/stop` - 停止容器

---

## 技术架构

### 目录结构

```
codestat-agent/
├── src/
│   ├── webhook/          # Webhook 抽象层
│   │   ├── models.py     # 事件模型
│   │   ├── parser.py     # 平台解析器
│   │   └── handler.py    # 请求处理器
│   ├── task/             # 任务调度
│   │   ├── models.py     # 任务模型
│   │   ├── container.py  # 容器管理器
│   │   └── scheduler.py  # 任务调度器
│   ├── storage/          # 数据存储
│   │   ├── models.py     # 数据库模型
│   │   └── database.py   # 数据库管理器
│   ├── web/              # Web 界面
│   │   ├── api.py        # API 路由
│   │   └── templates/    # HTML 模板
│   └── main.py           # 应用入口
├── docker/               # Worker 容器
│   ├── Dockerfile        # Worker 镜像
│   ├── worker.sh         # 执行脚本
│   └── build.sh          # 构建脚本
├── docker-compose.yml    # 部署配置
├── Dockerfile.app        # 主应用镜像
└── requirements.txt      # Python 依赖
```

### 技术栈

- **后端框架**: FastAPI 0.109.0（异步、高性能）
- **容器管理**: Docker Python SDK 7.0.0
- **数据库**: SQLite + SQLAlchemy 2.0.25（异步 ORM）
- **前端**: Tailwind CSS + Alpine.js（轻量级）
- **Worker 镜像**: Alpine Linux 3.19 + Git + CLOC

### 工作流程

1. Git 平台发送 Webhook 到 `/webhook/{provider}`
2. `WebhookHandler` 验证签名并解析事件
3. 如果是主分支推送，`TaskScheduler` 创建新任务
4. `ContainerManager` 启动或复用仓库专属容器
5. Worker 容器执行 `git pull` 和 `cloc` 命令
6. 结果保存为 JSON 文件并写入数据库
7. Web 界面实时展示任务状态和结果

---

## 部署指南

### 快速启动

```bash
# 1. 克隆仓库
git clone https://github.com/zihaoli-cn/codestat-agent.git
cd codestat-agent

# 2. 构建 Worker 镜像
./docker/build.sh

# 3. 启动服务
docker-compose up -d

# 4. 访问 Web 界面
open http://localhost:8000
```

### 配置 Webhook

在 Git 平台的仓库设置中添加 Webhook：

- **URL**: `http://<your-server>:8000/webhook/gitea`（或 `github`/`gitlab`）
- **Content Type**: `application/json`
- **Secret**: 自定义密钥（需与 API 配置一致）
- **Events**: 选择 `Push events`

### 添加仓库

使用 API 添加仓库配置：

```bash
curl -X POST http://localhost:8000/api/repositories/my_repo \
  -H "Content-Type: application/json" \
  -d '{
    "repository_name": "owner/repo",
    "repository_url": "https://gitea.com/owner/repo.git",
    "webhook_secret": "your-secret",
    "cloc_config": {
      "use_gitignore": true,
      "exclude_lang": ["Markdown"]
    }
  }'
```

---

## 设计亮点

### 1. 接口优先设计

所有模块都先定义清晰的接口和数据模型，再实现具体逻辑：

- `PushEvent`: 统一的推送事件模型
- `WebhookParser`: 抽象解析器接口
- `ClocConfig`: 配置模型（支持转换为命令行参数）

### 2. 增量式拉取

通过持久化卷存储，避免重复克隆：

```bash
# 首次执行
git clone --branch main https://repo.git /workspace/repo

# 后续执行
cd /workspace/repo
git fetch origin main
git checkout <commit-sha>
```

这大幅减少了网络传输和执行时间。

### 3. 资源隔离

每个仓库独立容器，避免相互干扰：

- 内存限制：512MB
- CPU 限制：50%
- 网络隔离：专用 Docker 网络

### 4. 错误处理

完善的错误处理机制：

- Webhook 签名验证失败返回 401
- 容器启动失败自动标记任务为 FAILED
- 任务超时自动停止容器
- 异常不会导致整个服务崩溃

### 5. 可扩展性

架构设计支持未来扩展：

- 新增 Git 平台只需实现 `WebhookParser` 接口
- 支持切换到 PostgreSQL/MySQL（只需修改数据库 URL）
- 可集成消息队列（如 Redis）实现分布式调度

---

## 使用示例

### 查看任务结果

```bash
# 获取最近的任务列表
curl http://localhost:8000/api/tasks?limit=10

# 查看特定任务的详细结果
curl http://localhost:8000/api/tasks/{task_id}
```

返回的 `result` 字段包含完整的 CLOC 输出：

```json
{
  "header": {
    "n_files": 25,
    "n_lines": 2183,
    "n_blank": 312,
    "n_comment": 145
  },
  "Python": {
    "nFiles": 15,
    "blank": 200,
    "comment": 100,
    "code": 1500
  }
}
```

### 管理容器

```bash
# 查看所有容器
curl http://localhost:8000/api/containers

# 停止特定仓库的容器
curl -X POST http://localhost:8000/api/containers/my_repo/stop

# 清理所有已停止的容器
curl -X POST http://localhost:8000/api/containers/cleanup
```

---

## 未来改进方向

1. **认证授权**: 添加 API 密钥或 OAuth 认证
2. **通知系统**: 任务完成后发送邮件/Slack 通知
3. **历史趋势**: 展示代码行数随时间变化的图表
4. **并行执行**: 支持同时运行多个任务
5. **分布式部署**: 使用 Kubernetes 进行容器编排
6. **更多统计工具**: 支持 `tokei`、`scc` 等其他工具

---

## 总结

CodeStat Agent 是一个生产就绪的代码统计自动化工具，具有以下优势：

- ✅ **兼容性强**: 支持三大主流 Git 平台
- ✅ **轻量高效**: 基于 Alpine Linux，镜像仅 50MB
- ✅ **易于部署**: 一键 Docker Compose 启动
- ✅ **可视化管理**: 直观的 Web 界面
- ✅ **灵活配置**: 支持细粒度的 CLOC 参数
- ✅ **代码质量**: 接口清晰，易于维护和扩展

项目已成功推送到 GitHub：https://github.com/zihaoli-cn/codestat-agent

欢迎使用和贡献！
