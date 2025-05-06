from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, description="页码，从1开始")
    page_size: int = Field(10, description="每页条数")


class PaginationResponse(Generic[T], BaseModel):
    """分页响应模型"""
    items: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    pages: int = Field(..., description="总页数") 