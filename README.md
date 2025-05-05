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

## API文档

启动服务后，可以访问以下URL查看API文档：

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc 