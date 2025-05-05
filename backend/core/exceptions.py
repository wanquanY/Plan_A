from typing import Optional, List, Dict, Any, Type, Union

from fastapi import Request, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.response import ResponseCode, ErrorDetail, ResponseUtil
from backend.utils.logging import api_logger


class BusinessException(Exception):
    """业务异常"""
    
    def __init__(
        self, 
        msg: str = "业务处理失败", 
        code: int = ResponseCode.BUSINESS_ERROR.value,
        errors: Optional[List[ErrorDetail]] = None,
        status_code: int = 400
    ):
        self.msg = msg
        self.code = code
        self.errors = errors
        self.status_code = status_code
        super().__init__(self.msg)


class DatabaseException(Exception):
    """数据库异常"""
    
    def __init__(
        self, 
        msg: str = "数据库操作失败", 
        code: int = ResponseCode.DATABASE_ERROR.value,
        status_code: int = 500
    ):
        self.msg = msg
        self.code = code
        self.status_code = status_code
        super().__init__(self.msg)


class NotFound(BusinessException):
    """资源不存在异常"""
    
    def __init__(self, msg: str = "资源不存在"):
        super().__init__(msg=msg, code=ResponseCode.NOT_FOUND.value, status_code=404)


class ValidationException(BusinessException):
    """数据验证异常"""
    
    def __init__(self, msg: str = "数据验证失败", errors: Optional[List[ErrorDetail]] = None):
        super().__init__(msg=msg, code=ResponseCode.UNPROCESSABLE_ENTITY.value, errors=errors, status_code=422)


class PermissionDeniedException(BusinessException):
    """权限不足异常"""
    
    def __init__(self, msg: str = "权限不足"):
        super().__init__(msg=msg, code=ResponseCode.FORBIDDEN.value, status_code=403)


class AuthenticationException(BusinessException):
    """认证失败异常"""
    
    def __init__(self, msg: str = "未登录或登录已过期"):
        super().__init__(msg=msg, code=ResponseCode.UNAUTHORIZED.value, status_code=401)


def setup_exception_handlers(app: FastAPI):
    """
    设置全局异常处理器
    
    Args:
        app: FastAPI应用实例
    """
    
    # 处理自定义业务异常
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        api_logger.warning(
            f"业务异常: {exc.msg}, 请求ID: {getattr(request.state, 'request_id', '')}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseUtil.error(
                code=exc.code,
                msg=exc.msg,
                errors=exc.errors,
                request_id=getattr(request.state, "request_id", None)
            )
        )
    
    # 处理数据库异常
    @app.exception_handler(DatabaseException)
    async def database_exception_handler(request: Request, exc: DatabaseException):
        api_logger.error(
            f"数据库异常: {exc.msg}, 请求ID: {getattr(request.state, 'request_id', '')}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseUtil.error(
                code=exc.code,
                msg=exc.msg,
                request_id=getattr(request.state, "request_id", None)
            )
        )
    
    # 处理FastAPI的HTTP异常
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = ResponseCode.BAD_REQUEST.value
        if exc.status_code == 401:
            code = ResponseCode.UNAUTHORIZED.value
        elif exc.status_code == 403:
            code = ResponseCode.FORBIDDEN.value
        elif exc.status_code == 404:
            code = ResponseCode.NOT_FOUND.value
        elif exc.status_code == 500:
            code = ResponseCode.INTERNAL_SERVER_ERROR.value
        
        api_logger.warning(
            f"HTTP异常: {exc.detail}, 状态码: {exc.status_code}, 请求ID: {getattr(request.state, 'request_id', '')}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseUtil.error(
                code=code,
                msg=exc.detail,
                request_id=getattr(request.state, "request_id", None)
            ),
            headers=getattr(exc, "headers", None)
        )
    
    # 处理请求验证异常
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        api_logger.warning(
            f"请求参数验证失败: {errors}, 请求ID: {getattr(request.state, 'request_id', '')}"
        )
        
        return JSONResponse(
            status_code=422,
            content=ResponseUtil.validation_error(
                errors=errors,
                request_id=getattr(request.state, "request_id", None)
            )
        )
    
    # 处理全局异常
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        api_logger.error(
            f"全局异常: {str(exc)}, 请求ID: {getattr(request.state, 'request_id', '')}",
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content=ResponseUtil.error(
                code=ResponseCode.INTERNAL_SERVER_ERROR.value,
                msg=f"服务器内部错误: {str(exc)}",
                request_id=getattr(request.state, "request_id", None)
            )
        ) 