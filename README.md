# Plan_A

Plan_A的初心和目标是构建一个懂业务，能行动，产出质量高，能够让大家出门玩耍Agent可以在家自动办公的自动化办公文档产品。基于FastAPI的后端和VUE前端的全栈项目，提供用户认证和API服务。

## 功能特性

- 用户注册和登录认证
- 基于JWT的认证系统
- 异步PostgreSQL数据库操作
- Alembic数据库迁移
- 智能Agent助手系统
- 文档自动编辑和处理
- 工具调用和配置管理
- MCP（Model Context Protocol）服务集成
- 实时聊天和对话管理
- 多格式文档支持（Markdown、LaTeX、HTML等）

## 项目路线图

### 🎯 第一阶段：Cursor式智能辅助办公工具
> **目标**：打造类似Cursor的智能编程助手体验，专注于文档处理和办公自动化

| 功能模块 | 状态 | 核心能力 | 详细描述 | 优先级 |
|---------|------|----------|----------|--------|
| **Agent智能助手** | ✅ 已完成 | 文档理解与编辑 | • 自动读取文档内容并理解上下文<br>• 智能文档编辑和内容生成<br>• 基于需求的自动化文档处理 | 🔥 高 |
| **工具调用系统** | ✅ 已完成 | 扩展能力管理 | • 灵活的工具配置和管理<br>• 自定义工具扩展支持<br>• 工具调用历史追踪 | 🔥 高 |
| **MCP服务集成** | ✅ 已完成 | 外部服务接入 | • MCP协议标准化实现<br>• 外部服务无缝接入<br>• 服务配置和管理界面 | 🔥 高 |
| **办公软件集成** | 🚧 开发中 | 企业生态连接 | • 微信消息通知和交互<br>• 飞书文档和日历集成<br>• 企业微信群组管理<br>• 钉钉审批流程对接 | 🟡 中 |
| **动态上下文压缩** | 🚧 开发中 | 内容优化管理 | • 智能内容摘要和压缩<br>• 上下文窗口优化管理<br>• 长文档处理能力增强 | 🟡 中 |
| **智能文档发现** | 📋 计划中 | 关联分析推荐 | • Agent主动查找相关文档<br>• 跨文档关联分析<br>• 智能推荐相关内容 | 🟡 中 |
| **知识库系统** | 📋 计划中 | 企业知识管理 | • 企业级知识库构建<br>• 文档索引和检索优化<br>• 知识图谱构建 | 🟡 中 |
| **多级目录文档** | 📋 计划中 | 协作文档管理 | • 飞书式层级文档结构<br>• 文档权限和协作管理<br>• 版本控制和历史追踪 | 🟢 低 |

### 🚀 第二阶段：Manus式可控自主规划办公
> **目标**：实现可控的自主办公系统，Agent能够理解业务需求并自主规划执行方案

| 核心系统 | 状态 | 核心能力 | 技术特性 | 应用场景 |
|---------|------|----------|----------|----------|
| **业务理解引擎** | 🎯 规划中 | 智能业务分析 | • 业务流程自动分析<br>• 需求意图智能识别<br>• 上下文业务知识学习 | 会议纪要处理<br>项目需求分析 |
| **自主任务规划** | 🎯 规划中 | 任务分解执行 | • 复杂任务自动分解<br>• 多步骤执行计划生成<br>• 依赖关系和优先级管理 | 项目管理<br>工作流自动化 |
| **可控执行框架** | 🎯 规划中 | 人机协作控制 | • 人机协作决策机制<br>• 关键节点确认和干预<br>• 执行过程实时监控 | 风险控制<br>质量保证 |
| **智能办公生态** | 🎯 规划中 | 全场景办公整合 | • 跨平台消息智能路由<br>• 办公流程自动化编排<br>• 多系统数据同步协调<br>• 智能会议和协作管理 | 无缝办公体验<br>企业协作优化 |
| **结果交付系统** | 🎯 规划中 | 自动化输出 | • 自动化报告生成<br>• 多格式输出支持<br>• 质量评估和反馈机制 | 报告生成<br>文档交付 |


## 技术栈

### 后端
- FastAPI：快速的API框架
- SQLAlchemy：ORM工具
- Pydantic：数据验证
- Alembic：数据库迁移
- PostgreSQL：数据库
- UV：依赖管理

### 前端
- UVE：UI框架
- Vite：构建工具
- TypeScript：类型系统

## Docker部署指南

本项目支持使用Docker进行灵活部署，提供多种部署方式满足不同需求。

### 环境准备

1. 安装Docker和Docker Compose
   ```bash
   # 检查安装情况
   docker --version
   docker-compose --version
   ```

2. 准备环境变量
   ```bash
   # 复制环境变量示例文件
   cp .env.example .env
   
   # 编辑环境变量
   vim .env  # 或使用其他编辑器
   ```

3. 环境变量配置要点：
   - 数据库连接信息（`POSTGRES_*`）
   - API路径前缀（`API_V1_STR`）
   - 安全密钥（`SECRET_KEY`）
   - 日志配置（`LOG_*`）
   - OpenAI集成配置（`OPENAI_*`）

### 部署方式

#### 方式一：一键部署（前后端+Redis）

最简单的方式，同时部署所有服务：

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看部署状态
docker-compose ps
```

这将启动：
- Redis服务（端口6379）
- 后端API服务（端口1314）
- 前端Web服务（端口80）

#### 方式二：仅部署后端（适合开发前端）

当你需要单独开发前端，但使用Docker部署后端时：

```bash
# 只启动Redis和后端服务
docker-compose up -d redis backend

# 检查后端服务状态
docker-compose ps backend
```

后端API将在 http://localhost:1314/api/v1 可用。

#### 方式三：仅部署前端（适合开发后端）

当你在本地运行后端，只需要Docker部署前端时：

```bash
# 指定后端API地址（替换为你本地后端地址）
BACKEND_API_URL=http://localhost:1314/api/ docker-compose up -d frontend

# 检查前端服务状态
docker-compose ps frontend
```

前端将在 http://localhost 可用，并连接到指定的后端API。

#### 方式四：完全分离部署

在不同环境中部署前后端：

1. 先部署后端：
   ```bash
   # 在后端服务器上
   docker-compose up -d redis backend
   ```

2. 再部署前端（在另一台服务器）：
   ```bash
   # 在前端服务器上，指向后端服务器地址
   BACKEND_API_URL=http://backend-server-ip:1314/api/ docker-compose up -d frontend
   ```

### 构建选项

项目使用单一Dockerfile通过构建参数实现前后端服务分离：

```bash
# 手动构建前端镜像
docker build --build-arg BUILD_TARGET=frontend -t freewrite-frontend .

# 手动构建后端镜像
docker build --build-arg BUILD_TARGET=backend -t freewrite-backend .
```

### 日志查看

#### 查看服务日志

```bash
# 查看所有服务的最新日志
docker-compose logs

# 持续查看日志（类似tail -f）
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend    # 查看后端日志
docker-compose logs -f frontend   # 查看前端日志
docker-compose logs -f redis      # 查看Redis日志

# 查看最近50行日志
docker-compose logs --tail=50 backend

# 查看容器内的具体日志文件
docker exec -it freewrite-backend ls -la /app/logs
docker exec -it freewrite-backend cat /app/logs/app.log
```

#### 应用日志文件

后端应用日志位于容器内的`/app/logs`目录，也已挂载到宿主机的`./logs`目录：

```bash
# 在宿主机查看日志文件
ls -la ./logs

# 查看具体日志内容
cat ./logs/app.log     # 应用主日志
cat ./logs/api.log     # API请求日志
cat ./logs/db.log      # 数据库操作日志
cat ./logs/error.log   # 错误日志
```

### 常用操作命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务但保留数据
docker-compose down

# 停止并删除所有数据（慎用！）
docker-compose down -v

# 重建并重启特定服务
docker-compose up -d --build backend

# 重启特定服务
docker-compose restart backend

# 查看容器资源使用情况
docker stats freewrite-backend freewrite-frontend

# 进入容器内部
docker exec -it freewrite-backend bash
docker exec -it freewrite-frontend sh
```

### 访问服务

部署完成后的访问地址：

- **前端界面**：http://localhost/
- **后端API**：http://localhost:1314/api/v1/
- **API文档**：
  - Swagger UI: http://localhost:1314/docs
  - ReDoc: http://localhost:1314/redoc 