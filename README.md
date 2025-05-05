# FreeWrite

FreeWrite是一个基于FastAPI的后端项目，提供用户认证和API服务。

## 功能特性

- 用户注册和登录认证
- 基于JWT的认证系统
- 异步PostgreSQL数据库操作
- Alembic数据库迁移

## 技术栈

- FastAPI：快速的API框架
- SQLAlchemy：ORM工具
- Pydantic：数据验证
- Alembic：数据库迁移
- PostgreSQL：数据库
- UV：依赖管理

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

本项目支持使用Docker进行部署，配置了完整的Docker环境。项目使用远程PostgreSQL数据库，本地仅需部署Redis和应用服务。前后端已合并到一个容器中运行。

### 准备工作

1. 确保安装了Docker和Docker Compose
2. 复制环境变量示例文件并根据需要修改

```bash
cp .env.example .env
```

3. 修改`.env`文件中的配置，特别是OpenAI API密钥

### 构建和启动

使用以下命令构建并启动所有服务：

```bash
docker-compose up -d
```

这将启动以下服务：
- Redis缓存
- 应用服务（含前端和后端）

> 注意：项目配置使用远程PostgreSQL数据库，确保数据库连接信息正确

### 查看服务状态

```bash
docker-compose ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看应用服务日志
docker-compose logs app
```

### 停止服务

```bash
docker-compose down
```

如果需要同时删除卷（会删除数据库数据）：

```bash
docker-compose down -v
```

### 访问应用

部署完成后，可以通过以下方式访问应用：

- 前端界面：http://localhost/
- 后端API：http://localhost/api/v1/

## API文档

启动服务后，可以访问以下URL查看API文档：

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc 