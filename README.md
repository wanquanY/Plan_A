# FreeWrite

FreeWrite是一个基于FastAPI的后端和React前端的全栈项目，提供用户认证和API服务。

## 功能特性

- 用户注册和登录认证
- 基于JWT的认证系统
- 异步PostgreSQL数据库操作
- Alembic数据库迁移

## 技术栈

### 后端
- FastAPI：快速的API框架
- SQLAlchemy：ORM工具
- Pydantic：数据验证
- Alembic：数据库迁移
- PostgreSQL：数据库
- UV：依赖管理

### 前端
- React：UI框架
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