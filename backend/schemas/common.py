from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List

T = TypeVar('T')


class PaginationParams(BaseModel):
    """分页参数"""
    skip: int = Field(0, ge=0, description="跳过的记录数")
    limit: int = Field(10, ge=1, le=100, description="每页记录数")


class PaginationResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    skip: int = Field(..., description="跳过的记录数")
    limit: int = Field(..., description="每页记录数")
    has_next: bool = Field(..., description="是否有下一页") 