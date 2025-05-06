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

## 开始使用

### 环境准备

确保已安装Python 3.9+以及UV工具。

### 安装依赖

```bash
uv venv
source .venv/bin/activate  # 在Windows上使用 .venv\Scripts\activate
uv pip install -e .
```

### 数据库迁移

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 运行服务

```bash
uvicorn backend.main:app --reload
```

## Docker部署

本项目支持使用Docker进行部署，配置了完整的Docker环境。项目使用远程PostgreSQL数据库，本地仅需部署Redis、前端和后端服务。前后端已配置为独立容器，可以单独管理和扩展。

### 准备工作

1. 确保安装了Docker和Docker Compose
2. 复制环境变量示例文件并根据需要修改

```bash
cp .env.example .env
```

3. 修改`.env`文件中的配置，特别是数据库连接信息和OpenAI API密钥

### 部署方式

本项目提供两种部署方式：

#### 1. 前后端独立部署（推荐）

使用以下命令构建并启动所有服务：

```bash
docker-compose up -d
```

这将启动以下服务：
- Redis缓存服务
- 后端API服务（FastAPI，端口1314）
- 前端Web服务（Nginx，端口80）

独立部署的优势：
- 前后端可以独立扩展
- 可以分别更新和维护
- 更容易排查问题
- 更符合微服务架构设计

#### 2. 仅部署后端（可选）

如果只需要后端API服务，可以使用：

```bash
docker-compose up -d redis backend
```

#### 3. 仅部署前端（可选）

如果已有运行的后端服务，需要单独部署前端：

```bash
# 修改环境变量，指向已有的后端服务
export BACKEND_API_URL=http://your-backend-api-url/api/

# 运行前端服务
docker-compose up -d frontend
```

### 自定义API地址

前端服务默认连接到同一个docker-compose网络中的后端服务。如果需要自定义API地址，可以在启动前端容器时设置环境变量：

```bash
BACKEND_API_URL=http://custom-backend-url/api/ docker-compose up -d frontend
```

### 查看服务状态

```bash
docker-compose ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看后端服务日志
docker-compose logs backend

# 查看前端服务日志
docker-compose logs frontend
```

### 停止服务

```bash
docker-compose down
```

如果需要同时删除卷（会删除Redis数据）：

```bash
docker-compose down -v
```

### 访问应用

部署完成后，可以通过以下方式访问应用：

- 前端界面：http://localhost/
- 后端API：http://localhost:1314/api/v1/

## API文档

启动后端服务后，可以访问以下URL查看API文档：

- Swagger UI: http://localhost:1314/docs
- ReDoc: http://localhost:1314/redoc 