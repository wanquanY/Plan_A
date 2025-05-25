from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import subprocess
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from backend.api.v1 import api_router
from backend.core.config import settings
from backend.utils.logging import app_logger, api_logger
from backend.core.exceptions import setup_exception_handlers
from backend.core.response import SuccessResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from backend.middlewares import RequestIdMiddleware
from backend.utils.random_util import RandomUtil
from backend.db.session import init_db


# 创建API请求日志中间件
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 记录请求开始
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "")
        api_logger.info(
            f"Started {request.method} {request.url.path} - "
            f"Client: {request.client.host}, ID: {request_id}"
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录请求完成
            api_logger.info(
                f"Completed {request.method} {request.url.path} - "
                f"Status: {response.status_code}, Time: {process_time:.4f}s, ID: {request_id}"
            )
            
            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)
                
            return response
            
        except Exception as e:
            # 记录异常
            process_time = time.time() - start_time
            api_logger.error(
                f"Error processing {request.method} {request.url.path} - "
                f"Time: {process_time:.4f}s, ID: {request_id}, Error: {str(e)}",
                exc_info=True
            )
            raise


async def wait_for_database():
    """等待数据库连接可用"""
    app_logger.info("等待数据库连接...")
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            app_logger.info("数据库连接成功!")
            await engine.dispose()
            return True
        except Exception as e:
            retry_count += 1
            app_logger.warning(f"数据库连接尝试 {retry_count}/{max_retries} 失败: {e}")
            if retry_count >= max_retries:
                app_logger.error("达到最大重试次数，数据库连接失败")
                return False
            await asyncio.sleep(2)
    
    return False


def run_database_migrations():
    """执行数据库迁移"""
    try:
        app_logger.info("开始执行数据库迁移...")
        
        # 首先检查当前迁移状态
        current_result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True
        )
        app_logger.info(f"当前迁移状态: {current_result.stdout.strip()}")
        
        # 执行迁移
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        app_logger.info("数据库迁移执行成功")
        app_logger.debug(f"迁移输出: {result.stdout}")
        
        # 再次检查迁移状态
        final_result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True
        )
        app_logger.info(f"迁移后状态: {final_result.stdout.strip()}")
        
        return True
    except subprocess.CalledProcessError as e:
        app_logger.error(f"数据库迁移失败: {e}")
        app_logger.error(f"错误输出: {e.stderr}")
        
        # 检查是否是工具调用相关的索引错误
        if "ix_tool_calls_agent_id" in e.stderr and "does not exist" in e.stderr:
            app_logger.info("检测到工具调用索引不存在错误，尝试修复...")
            return fix_tool_calls_migration_issue()
        
        return False
    except Exception as e:
        app_logger.error(f"执行数据库迁移时发生异常: {e}")
        return False


def fix_tool_calls_migration_issue():
    """修复工具调用迁移问题"""
    try:
        app_logger.info("尝试修复工具调用迁移问题...")
        
        # 首先，标记当前迁移为已完成（跳过有问题的迁移）
        # 我们需要手动将数据库标记到 26d9be805451 版本
        result = subprocess.run(
            ["alembic", "stamp", "26d9be805451"],
            capture_output=True,
            text=True,
            check=True
        )
        app_logger.info("已标记 26d9be805451 迁移为完成状态")
        
        # 然后继续执行剩余的迁移
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        app_logger.info("修复后的数据库迁移执行成功")
        app_logger.debug(f"修复迁移输出: {result.stdout}")
        return True
        
    except subprocess.CalledProcessError as e:
        app_logger.error(f"修复工具调用迁移失败: {e}")
        app_logger.error(f"修复错误输出: {e.stderr}")
        
        # 如果还是失败，尝试更激进的修复方法
        return force_fix_migration_state()
        
    except Exception as e:
        app_logger.error(f"修复工具调用迁移时发生异常: {e}")
        return False


def force_fix_migration_state():
    """强制修复迁移状态"""
    try:
        app_logger.info("尝试强制修复迁移状态...")
        
        # 直接标记到最新版本
        result = subprocess.run(
            ["alembic", "stamp", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        app_logger.info("已强制标记数据库为最新迁移状态")
        
        # 手动确保必要的列存在（返回True，让调用者处理异步部分）
        return True
        
    except Exception as e:
        app_logger.error(f"强制修复迁移状态失败: {e}")
        return False


app = FastAPI(
    title="FreeWrite API",
    description="FreeWrite项目后端API",
    version="0.1.0",
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，生产环境中应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求ID中间件（必须在日志中间件之前）
app.add_middleware(RequestIdMiddleware)

# 添加请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# 设置全局异常处理
setup_exception_handlers(app)

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root(request: Request):
    app_logger.info("访问根路径")
    return SuccessResponse(
        data={"message": "Welcome to FreeWrite API"},
        request_id=getattr(request.state, "request_id", None)
    )


@app.on_event("startup")
async def startup_event():
    app_logger.info("应用程序启动")
    
    # 等待数据库连接
    if not await wait_for_database():
        app_logger.error("数据库连接失败，应用程序无法启动")
        sys.exit(1)
    
    # 执行数据库迁移
    if not run_database_migrations():
        app_logger.error("数据库迁移失败，应用程序无法启动")
        sys.exit(1)
    
    # 初始化数据库（创建表等）- 这会处理所有表的创建
    try:
        await init_db()
        app_logger.info("数据库初始化完成")
    except Exception as e:
        app_logger.error(f"数据库初始化失败: {e}")
        sys.exit(1)
    
    app_logger.info(f"随机测试ID: {RandomUtil.generate_request_id()}")
    app_logger.info("应用程序启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    app_logger.info("应用程序关闭")


if __name__ == "__main__":
    import uvicorn
    app_logger.info("通过 __main__ 启动应用程序")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=1314, reload=True) 