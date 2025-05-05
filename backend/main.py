from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

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
    app_logger.info(f"随机测试ID: {RandomUtil.generate_request_id()}")


@app.on_event("shutdown")
async def shutdown_event():
    app_logger.info("应用程序关闭")


if __name__ == "__main__":
    import uvicorn
    app_logger.info("通过 __main__ 启动应用程序")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=1314, reload=True) 