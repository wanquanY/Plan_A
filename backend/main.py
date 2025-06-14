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
        
        # 检查是否有多个头部迁移
        heads_result = subprocess.run(
            ["alembic", "heads"],
            capture_output=True,
            text=True
        )
        head_lines = [line.strip() for line in heads_result.stdout.strip().split('\n') if line.strip()]
        
        # 如果有多个头部，记录警告但继续
        if len(head_lines) > 1:
            app_logger.warning(f"检测到多个迁移头部: {head_lines}")
        
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
        
        # 检查是否是列已存在的错误
        if "already exists" in e.stderr and "column" in e.stderr:
            app_logger.info("检测到列已存在错误，可能数据库结构已是最新，尝试标记为当前状态...")
            return try_stamp_current_migration()
        
        # 检查是否是多头部错误
        if "Multiple head revisions" in e.stderr:
            app_logger.info("检测到多头部迁移错误，尝试解决...")
            return fix_multiple_heads_issue()
        
        return False
    except Exception as e:
        app_logger.error(f"执行数据库迁移时发生异常: {e}")
        return False


def try_stamp_current_migration():
    """尝试将数据库标记为当前迁移状态"""
    try:
        app_logger.info("尝试将数据库标记为最新迁移状态...")
        
        # 获取最新的头部迁移
        heads_result = subprocess.run(
            ["alembic", "heads"],
            capture_output=True,
            text=True,
            check=True
        )
        
        head_lines = [line.strip() for line in heads_result.stdout.strip().split('\n') if line.strip()]
        
        if head_lines:
            latest_head = head_lines[0].split()[0]  # 获取第一个头部的哈希
            app_logger.info(f"将数据库标记为迁移: {latest_head}")
            
            result = subprocess.run(
                ["alembic", "stamp", latest_head],
                capture_output=True,
                text=True,
                check=True
            )
            app_logger.info("数据库迁移状态标记成功")
            return True
        else:
            app_logger.error("无法获取迁移头部信息")
            return False
            
    except subprocess.CalledProcessError as e:
        app_logger.error(f"标记迁移状态失败: {e}")
        app_logger.error(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        app_logger.error(f"标记迁移状态时发生异常: {e}")
        return False


def fix_multiple_heads_issue():
    """修复多头部迁移问题"""
    try:
        app_logger.info("尝试修复多头部迁移问题...")
        
        # 获取所有头部
        heads_result = subprocess.run(
            ["alembic", "heads"],
            capture_output=True,
            text=True,
            check=True
        )
        
        head_lines = [line.strip() for line in heads_result.stdout.strip().split('\n') if line.strip()]
        
        if len(head_lines) > 1:
            app_logger.info(f"发现多个头部: {head_lines}")
            
            # 创建合并迁移
            head_hashes = [line.split()[0] for line in head_lines]
            merge_command = ["alembic", "merge"] + head_hashes + ["-m", "auto_merge_heads"]
            
            merge_result = subprocess.run(
                merge_command,
                capture_output=True,
                text=True,
                check=True
            )
            app_logger.info("合并迁移创建成功")
            
            # 执行升级
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                check=True
            )
            app_logger.info("合并后迁移执行成功")
            return True
        else:
            app_logger.info("没有发现多头部问题")
            return True
            
    except subprocess.CalledProcessError as e:
        app_logger.error(f"修复多头部迁移失败: {e}")
        app_logger.error(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        app_logger.error(f"修复多头部迁移时发生异常: {e}")
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
    
    # 初始化Redis服务
    try:
        from backend.services.redis_service import redis_service
        await redis_service.init()
        app_logger.info("Redis服务初始化完成")
    except Exception as e:
        app_logger.warning(f"Redis服务初始化失败，将使用无缓存模式: {e}")
    
    app_logger.info(f"随机测试ID: {RandomUtil.generate_request_id()}")
    app_logger.info("应用程序启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    app_logger.info("应用程序关闭")


if __name__ == "__main__":
    import uvicorn
    app_logger.info("通过 __main__ 启动应用程序")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=1314, reload=True) 