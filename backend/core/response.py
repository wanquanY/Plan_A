from enum import Enum
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from pydantic import BaseModel, Field
from fastapi import status
from fastapi.responses import JSONResponse

T = TypeVar('T')


class ResponseCode(int, Enum):
    """统一响应状态码"""
    SUCCESS = 200  # 成功
    BAD_REQUEST = 400  # 错误的请求
    UNAUTHORIZED = 401  # 未授权
    FORBIDDEN = 403  # 禁止访问
    NOT_FOUND = 404  # 资源不存在
    METHOD_NOT_ALLOWED = 405  # 方法不允许
    REQUEST_TIMEOUT = 408  # 请求超时
    CONFLICT = 409  # 资源冲突
    GONE = 410  # 资源已删除
    PRECONDITION_FAILED = 412  # 前提条件失败
    UNPROCESSABLE_ENTITY = 422  # 请求格式正确，但语义错误
    TOO_MANY_REQUESTS = 429  # 请求过多
    INTERNAL_SERVER_ERROR = 500  # 服务器内部错误
    SERVICE_UNAVAILABLE = 503  # 服务不可用
    DATABASE_ERROR = 600  # 数据库错误
    BUSINESS_ERROR = 700  # 业务逻辑错误


class ErrorDetail(BaseModel):
    """错误详情"""
    field: Optional[str] = None  # 字段名，用于表单验证错误
    message: str  # 错误信息


class ResponseModel(BaseModel, Generic[T]):
    """统一响应模型"""
    code: int = Field(ResponseCode.SUCCESS.value, description="状态码")
    msg: str = Field("success", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    errors: Optional[List[ErrorDetail]] = Field(None, description="错误详情")
    timestamp: str = Field(..., description="时间戳")
    request_id: Optional[str] = Field(None, description="请求ID")


class ResponseUtil:
    """响应工具类"""
    
    @staticmethod
    def success(
        data: Any = None, 
        msg: str = "success", 
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """成功响应"""
        import time
        from datetime import datetime
        return {
            "code": ResponseCode.SUCCESS.value,
            "msg": msg,
            "data": data,
            "errors": None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "request_id": request_id
        }
    
    @staticmethod
    def error(
        code: int = ResponseCode.INTERNAL_SERVER_ERROR.value,
        msg: str = "服务器内部错误",
        errors: Optional[List[ErrorDetail]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """错误响应"""
        import time
        from datetime import datetime
        return {
            "code": code,
            "msg": msg,
            "data": None,
            "errors": errors,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "request_id": request_id
        }
    
    @staticmethod
    def validation_error(
        errors: List[Dict[str, Any]],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """验证错误响应"""
        error_details = []
        for error in errors:
            error_detail = ErrorDetail(
                field=".".join(str(loc) for loc in error["loc"]),
                message=error["msg"]
            )
            # 转换为字典以支持JSON序列化
            error_details.append(error_detail.dict())
        
        return ResponseUtil.error(
            code=ResponseCode.UNPROCESSABLE_ENTITY.value,
            msg="请求参数验证失败",
            errors=error_details,
            request_id=request_id
        )
    
    @staticmethod
    def bad_request(
        msg: str = "请求参数错误",
        errors: Optional[List[ErrorDetail]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """请求参数错误响应"""
        return ResponseUtil.error(
            code=ResponseCode.BAD_REQUEST.value,
            msg=msg,
            errors=errors,
            request_id=request_id
        )
    
    @staticmethod
    def unauthorized(
        msg: str = "未登录或登录已过期",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """未授权响应"""
        return ResponseUtil.error(
            code=ResponseCode.UNAUTHORIZED.value,
            msg=msg,
            request_id=request_id
        )
    
    @staticmethod
    def forbidden(
        msg: str = "权限不足",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """禁止访问响应"""
        return ResponseUtil.error(
            code=ResponseCode.FORBIDDEN.value,
            msg=msg,
            request_id=request_id
        )
    
    @staticmethod
    def not_found(
        msg: str = "资源不存在",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """资源不存在响应"""
        return ResponseUtil.error(
            code=ResponseCode.NOT_FOUND.value,
            msg=msg,
            request_id=request_id
        )
    
    @staticmethod
    def business_error(
        msg: str = "业务处理失败",
        errors: Optional[List[ErrorDetail]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """业务错误响应"""
        return ResponseUtil.error(
            code=ResponseCode.BUSINESS_ERROR.value,
            msg=msg,
            errors=errors,
            request_id=request_id
        )
    
    @staticmethod
    def database_error(
        msg: str = "数据库操作失败",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """数据库错误响应"""
        return ResponseUtil.error(
            code=ResponseCode.DATABASE_ERROR.value,
            msg=msg,
            request_id=request_id
        )


class APIResponse(JSONResponse):
    """API响应类"""
    
    def __init__(
        self,
        content: Any = None,
        status_code: int = status.HTTP_200_OK,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background=None,
        request_id: Optional[str] = None,
        msg: str = "success",
        error_code: int = ResponseCode.SUCCESS.value
    ):
        """
        初始化API响应
        
        如果content是字典且包含code字段，则直接使用content
        否则包装为统一响应格式
        """
        import time
        from datetime import datetime
        
        if content is None or not isinstance(content, dict) or "code" not in content:
            content = {
                "code": error_code,
                "msg": msg,
                "data": content,
                "errors": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "request_id": request_id
            }
        
        super().__init__(content, status_code, headers, media_type, background)


class SuccessResponse(APIResponse):
    """成功响应"""
    
    def __init__(
        self, 
        data: Any = None, 
        msg: str = "success",
        status_code: int = status.HTTP_200_OK, 
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ):
        super().__init__(
            content=ResponseUtil.success(data, msg, request_id),
            status_code=status_code,
            headers=headers
        )


class ErrorResponse(APIResponse):
    """错误响应"""
    
    def __init__(
        self,
        msg: str = "服务器内部错误",
        code: int = ResponseCode.INTERNAL_SERVER_ERROR.value,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: Optional[Dict[str, str]] = None,
        errors: Optional[List[ErrorDetail]] = None,
        request_id: Optional[str] = None
    ):
        super().__init__(
            content=ResponseUtil.error(code, msg, errors, request_id),
            status_code=status_code,
            headers=headers
        ) 