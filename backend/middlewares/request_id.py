#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
请求ID中间件
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from backend.utils.random_util import RandomUtil
from backend.utils.logging import api_logger

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    请求ID中间件，为每个请求分配唯一的请求ID
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """处理请求，添加请求ID"""
        # 从请求头中获取请求ID，如果没有则生成一个新的
        request_id = request.headers.get("X-Request-ID")
        
        if not request_id:
            request_id = RandomUtil.generate_request_id()
            api_logger.debug(f"生成新的请求ID: {request_id}")
        
        # 将请求ID添加到请求状态中，以便在后续处理中使用
        request.state.request_id = request_id
        
        # 继续处理请求
        response = await call_next(request)
        
        # 将请求ID添加到响应头中
        response.headers["X-Request-ID"] = request_id
        
        return response 